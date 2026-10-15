"""Idempotent, provenance-carrying loaders for the assessment data packet.

Rules this module follows (see DESIGN.md):
- A LoadBatch is created for every file before any row is written.
- A file whose SHA-256 already loaded OK is skipped unless --replace is given.
- Unparseable rows are rejected and logged to GapEntry; they are never guessed into shape.
- Ambiguous brand matches are queued (AMBIGUOUS_MAPPING), never auto-linked.
"""
import calendar
import csv
import datetime as dt
import hashlib
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from .models import (
    GapEntry,
    JanAushadhiItem,
    LoadBatch,
    NLEMEntry,
    PharmacyStockItem,
    Product,
    ProductIngredient,
    ProtocolDocument,
    ProtocolUnit,
    RegulatoryEvent,
    SevereInteraction,
)

# --- small parsing helpers -------------------------------------------------

def sha256_of(path: Path) -> str:
    """Hash a file, or a directory of files (sorted by name) for the PDF corpus."""
    h = hashlib.sha256()
    paths = sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else [path]
    for p in paths:
        h.update(p.name.encode())
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()


def _read_csv(path: Path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _clean(value) -> str:
    return (value or "").strip()


def _dec(value):
    value = _clean(value)
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _int(value):
    try:
        return int(_clean(value))
    except ValueError:
        return None


def _date(value):
    value = _clean(value)
    if not value:
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def _expiry(value):
    """'2026-07' -> last day of that month (a pack is usable through its expiry month)."""
    match = re.fullmatch(r"(\d{4})-(\d{2})", _clean(value))
    if not match:
        return None
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        return None
    return dt.date(year, month, calendar.monthrange(year, month)[1])


def _brand_key(text: str) -> str:
    """Normalise brand spelling for exact comparison only. Never used to pick a winner."""
    return re.sub(r"[\s\-]+", " ", text).strip().upper()


PACK_RE = re.compile(r"\b(TABLET|TAB|CAPSULE|CAP|STRIP|SYRUP|SYP|\d+\s?ML|\d+\s?'?S)\b", re.IGNORECASE)


def normalize_billed_name(billed: str):
    """Split pack tokens off a billing string. Returns (brand_key, pack_tokens)."""
    packs = " ".join(m.group(1).upper() for m in PACK_RE.finditer(billed))
    return _brand_key(PACK_RE.sub(" ", billed)), packs


class Collector:
    """Accumulates gap entries for one batch and writes them in one call."""

    def __init__(self, batch: LoadBatch):
        self.batch = batch
        self.rows = []

    def add(self, category, reason_code, source_ref, message, severity=GapEntry.MEDIUM, details=None):
        self.rows.append(
            GapEntry(
                dataset=self.batch.dataset,
                load_batch=self.batch,
                category=category,
                severity=severity,
                reason_code=reason_code[:64],
                source_ref=str(source_ref)[:255],
                message=message[:2000],
                details=details or {},
            )
        )

    def flush(self) -> int:
        GapEntry.objects.bulk_create(self.rows, batch_size=500)
        count = len(self.rows)
        self.rows = []
        return count


# --- per-dataset loaders ----------------------------------------------------
# Each loader returns {"read": n, "loaded": n, "rejected": n}.

DECOMP_METHOD = "SOURCE_COLUMNS"
UNIT_MISMATCH = "UNIT_MISMATCH_SUSPECTED"


def load_cdci(batch, path, gaps):
    rows = _read_csv(path)
    overrides = settings.BRAHMO["STRENGTH_UNIT_OVERRIDES"]
    seen, loaded, rejected = set(), 0, 0
    ingredient_rows = []

    for i, r in enumerate(rows, start=2):
        ref = f"{path.name}:{i}"
        pid = _clean(r.get("product_id"))
        brand = _clean(r.get("brand_name"))
        strength_text = _clean(r.get("strength_text"))
        if not pid or not brand:
            rejected += 1
            gaps.add(GapEntry.PARSE_REJECT, "MISSING_KEY_FIELD", ref, "product_id or brand_name is empty")
            continue
        if pid in seen:
            rejected += 1
            gaps.add(GapEntry.PARSE_REJECT, "DUPLICATE_PRODUCT_ID", ref, f"{pid} appears more than once")
            continue
        seen.add(pid)

        parts = []
        for n in (1, 2, 3):
            name = _clean(r.get(f"ingredient_{n}"))
            if name:
                parts.append((n, name, _dec(r.get(f"strength_{n}_mg"))))

        product = Product.objects.create(
            product_id=pid,
            brand_name=brand,
            manufacturer=_clean(r.get("manufacturer")),
            dose_form=_clean(r.get("dose_form")),
            strength_text=strength_text,
            is_fdc=len(parts) > 1,
            source=_clean(r.get("source")),
            source_version=_clean(r.get("source_version")),
            effective_from=_date(r.get("effective_from")),
            load_batch=batch,
        )

        for position, name, strength in parts:
            if strength is None:
                gaps.add(GapEntry.MISSING_DATA, "STRENGTH_MISSING", ref, f"{name} has no strength value")
            elif name.lower() not in strength_text.lower():
                gaps.add(GapEntry.ANOMALY, "INGREDIENT_NOT_IN_STRENGTH_TEXT", ref,
                         f"'{name}' absent from strength_text '{strength_text}'")
            expected_unit = overrides.get(name)
            if expected_unit and re.search(r"\bmg\b", strength_text, re.IGNORECASE):
                gaps.add(GapEntry.ANOMALY, UNIT_MISMATCH, ref,
                         f"{name} is usually expressed in {expected_unit}; source says mg",
                         severity=GapEntry.HIGH, details={"strength_text": strength_text})
            ingredient_rows.append(ProductIngredient(
                product=product, position=position, ingredient_name=name,
                strength_mg=strength, mapping_method=DECOMP_METHOD, confidence=Decimal("1.000"),
            ))
        loaded += 1

    ProductIngredient.objects.bulk_create(ingredient_rows, batch_size=500)

    # Brand names that repeat are a queue item, not an error: a stock line naming
    # one of them cannot be linked to a single product.
    duplicates = (Product.objects.values("brand_name")
                  .annotate(n=Count("id")).filter(n__gt=1))
    for d in duplicates:
        gaps.add(GapEntry.AMBIGUOUS_MAPPING, "BRAND_NAME_NOT_UNIQUE", path.name,
                 f"'{d['brand_name']}' is shared by {d['n']} products; brand lookups for it are ambiguous",
                 severity=GapEntry.HIGH, details={"brand_name": d["brand_name"], "count": d["n"]})
    return {"read": len(rows), "loaded": loaded, "rejected": rejected}


def load_nlem(batch, path, gaps):
    rows = _read_csv(path)
    objs, rejected = [], 0
    for i, r in enumerate(rows, start=2):
        medicine = _clean(r.get("medicine"))
        if not medicine:
            rejected += 1
            gaps.add(GapEntry.PARSE_REJECT, "MISSING_MEDICINE", f"{path.name}:{i}", "empty medicine name")
            continue
        objs.append(NLEMEntry(
            medicine=medicine,
            therapeutic_category=_clean(r.get("therapeutic_category")),
            care_levels=_clean(r.get("care_levels")),
            edition=_clean(r.get("nlem_edition")),
            load_batch=batch,
        ))
    NLEMEntry.objects.bulk_create(objs, batch_size=500)
    return {"read": len(rows), "loaded": len(objs), "rejected": rejected}


def load_jan_aushadhi(batch, path, gaps):
    rows = _read_csv(path)
    objs, rejected = [], 0
    for i, r in enumerate(rows, start=2):
        mrp = _dec(r.get("mrp_inr"))
        ref = f"{path.name}:{i}"
        if mrp is None or not _clean(r.get("generic_name")):
            rejected += 1
            gaps.add(GapEntry.PARSE_REJECT, "MRP_OR_NAME_INVALID", ref, "generic_name or mrp_inr unreadable")
            continue
        objs.append(JanAushadhiItem(
            generic_name=_clean(r.get("generic_name")),
            strength=_clean(r.get("strength")),
            pack=_clean(r.get("pack")),
            mrp_inr=mrp,
            catalog_version=_clean(r.get("catalog_version")),
            load_batch=batch,
        ))
    JanAushadhiItem.objects.bulk_create(objs, batch_size=500)
    return {"read": len(rows), "loaded": len(objs), "rejected": rejected}


def load_gazette(batch, path, gaps):
    rows = _read_csv(path)
    loaded, rejected = 0, 0
    codes = {_clean(r.get("event_id")) for r in rows}
    effective = {_clean(r.get("event_id")): _date(r.get("effective_date")) for r in rows}
    allowed_actions = settings.BRAHMO["REGULATORY_ACTIONS"]
    allowed_targets = settings.BRAHMO["REGULATORY_TARGET_TYPES"]

    for i, r in enumerate(rows, start=2):
        ref = f"{path.name}:{i}"
        event_id = _clean(r.get("event_id"))
        published, effective_on = _date(r.get("date_published")), _date(r.get("effective_date"))
        action = _clean(r.get("action")).upper()
        target = _clean(r.get("target_type")).upper()
        if not event_id or published is None or effective_on is None:
            rejected += 1
            gaps.add(GapEntry.PARSE_REJECT, "EVENT_DATES_MISSING", ref, "event_id or a required date is missing")
            continue
        if action not in allowed_actions or target not in allowed_targets:
            rejected += 1
            gaps.add(GapEntry.PARSE_REJECT, "UNKNOWN_ACTION_OR_TARGET", ref, f"action={action} target={target}")
            continue

        supersedes = _clean(r.get("supersedes_event_id"))
        if supersedes and supersedes not in codes:
            gaps.add(GapEntry.SOURCE_CONFLICT, "SUPERSEDED_EVENT_NOT_IN_FILE", ref,
                     f"{event_id} supersedes {supersedes}, which is not in this file")
        elif supersedes and effective.get(supersedes) and effective[supersedes] > effective_on:
            gaps.add(GapEntry.SOURCE_CONFLICT, "SUPERSESSION_CHRONOLOGY", ref,
                     f"{event_id} takes effect before the event it supersedes ({supersedes})",
                     severity=GapEntry.HIGH)

        RegulatoryEvent.objects.create(
            event_id=event_id,
            notification_id=_clean(r.get("notification_id")),
            date_published=published,
            effective_date=effective_on,
            action=action,
            target_type=target,
            target_description=_clean(r.get("target_description")),
            supersedes_event_code=supersedes,
            note=_clean(r.get("note")),
            load_batch=batch,
        )
        loaded += 1
    return {"read": len(rows), "loaded": loaded, "rejected": rejected}


def load_interactions(batch, path, gaps):
    rows = _read_csv(path)
    allowed = settings.BRAHMO["SEVERITY_VALUES"]
    objs, seen, rejected = [], set(), 0
    for i, r in enumerate(rows, start=2):
        a, b = _clean(r.get("ingredient_a")), _clean(r.get("ingredient_b"))
        severity = _clean(r.get("severity")).upper()
        ref = f"{path.name}:{i}"
        if not a or not b or severity not in allowed:
            rejected += 1
            gaps.add(GapEntry.PARSE_REJECT, "PAIR_OR_SEVERITY_INVALID", ref, f"{a!r} / {b!r} / {severity!r}")
            continue
        key = "|".join(sorted([a.lower(), b.lower()]))
        if key in seen:
            rejected += 1
            gaps.add(GapEntry.PARSE_REJECT, "DUPLICATE_PAIR", ref, f"{a} + {b} already loaded")
            continue
        seen.add(key)
        objs.append(SevereInteraction(
            pair_key=key, ingredient_a=a, ingredient_b=b, severity=severity,
            note=_clean(r.get("note")), source_tag=_clean(r.get("source_tag")), load_batch=batch,
        ))
    SevereInteraction.objects.bulk_create(objs, batch_size=500)
    return {"read": len(rows), "loaded": len(objs), "rejected": rejected}


def load_stock(batch, path, gaps):
    """Pharmacy stock: every line is untrusted. Matching is exact-only and never silent."""
    rows = _read_csv(path)
    index = {}
    for pid, brand in Product.objects.values_list("id", "brand_name"):
        index.setdefault(_brand_key(brand), []).append(pid)

    objs, rejected = [], 0
    for i, r in enumerate(rows, start=2):
        ref = f"{path.name}:{i}"
        name = _clean(r.get("item_name_as_billed"))
        if not name:
            rejected += 1
            gaps.add(GapEntry.PARSE_REJECT, "BILLED_NAME_EMPTY", ref, "item_name_as_billed is empty")
            continue

        qty, mrp = _int(r.get("qty_units")), _dec(r.get("mrp_inr"))
        expiry = _expiry(r.get("expiry"))
        problems = [code for code, bad in (("QTY_INVALID", qty is None), ("MRP_INVALID", mrp is None),
                                           ("EXPIRY_INVALID", expiry is None)) if bad]
        if problems:
            gaps.add(GapEntry.ANOMALY, problems[0], ref, f"unparsed fields: {', '.join(problems)}",
                     details={"fields": problems})

        key, packs = normalize_billed_name(name)
        candidates = index.get(key, [])
        matched_id, status = None, PharmacyStockItem.UNMATCHED
        if len(candidates) == 1:
            matched_id, status = candidates[0], PharmacyStockItem.EXACT_UNIQUE
        elif len(candidates) > 1:
            status = PharmacyStockItem.AMBIGUOUS
            gaps.add(GapEntry.AMBIGUOUS_MAPPING, "BRAND_NAME_NOT_UNIQUE", ref,
                     f"'{name}' matches {len(candidates)} CDCI products; left unlinked",
                     severity=GapEntry.HIGH)
        else:
            gaps.add(GapEntry.MISSING_DATA, "NO_CDCI_BRAND_MATCH", ref,
                     f"'{name}' has no CDCI brand match (normalised key '{key}')")

        objs.append(PharmacyStockItem(
            line_no=i, item_name_as_billed=name[:255], billed_brand_key=key[:255],
            pack_tokens=packs[:64], qty_units=qty, mrp_inr=mrp, batch=_clean(r.get("batch"))[:64],
            expiry_text=_clean(r.get("expiry"))[:16], expiry_date=expiry,
            parse_status="PARTIAL" if problems else "PARSED",
            match_status=status, matched_product_id=matched_id, load_batch=batch,
        ))
    PharmacyStockItem.objects.bulk_create(objs, batch_size=500)
    return {"read": len(rows), "loaded": len(objs), "rejected": rejected}


# --- protocols --------------------------------------------------------------

SPECIALTY_BY_PREFIX = {
    "GP": "General Practice",
    "PED": "Paediatrics",
    "GYN": "Gynaecology",
    "ORT": "Orthopaedics",
}
SKIP_HEADINGS = {"STANDARD TREATMENT WORKFLOW"}
META = {
    "code": re.compile(r"Code:\s*([A-Z0-9-]+)"),
    "version": re.compile(r"Version:\s*(\d[\d.]*)"),
    "effective": re.compile(r"Effective:\s*(\d{4}-\d{2}-\d{2})"),
    "supersedes": re.compile(r"Supersedes:\s*([^\n]+)"),
}
DOSE_RE = re.compile(r"\d\s*(?:mg|mcg|µg|ml|g|%|mmol)\b", re.IGNORECASE)
REFERRAL_WORDS = ("REFER", "RED FLAG", "IMAGE")
AVOID_WORDS = ("DO NOT", "AVOID")
MONITOR_WORDS = ("TARGET", "MONITOR", "REVIEW", "FOLLOW")


def _unit_type_for_section(section: str) -> str:
    """Section headings in the STW pack decide the unit type. Keyword table, reviewed by hand."""
    s = section.upper()
    if any(w in s for w in REFERRAL_WORDS):
        return ProtocolUnit.REFERRAL
    if any(w in s for w in AVOID_WORDS):
        return ProtocolUnit.CONTRAINDICATION
    if any(w in s for w in MONITOR_WORDS):
        return ProtocolUnit.MONITORING
    if "FIRST-LINE" in s or "MANAGEMENT" in s or "TREATMENT" in s:
        return ProtocolUnit.RECOMMENDATION
    return ProtocolUnit.WORKFLOW_STEP


def _is_heading(line: str) -> bool:
    return (line == line.upper() and not line.startswith("•")
            and len(line) < 80 and any(ch.isalpha() for ch in line))


def _parse_stw_text(text: str):
    """Pull metadata, title and sections from one STW page's extracted text."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    meta = {}
    for key, pattern in META.items():
        m = pattern.search(text)
        if m:
            meta[key] = m.group(1).strip()
    title = next((ln for ln in lines if ln.upper() not in SKIP_HEADINGS and not _is_heading(ln)
                  and "Code:" not in ln and "Version:" not in ln), "")
    units, section = [], "HEADER"
    for ln in lines:
        if ln.upper() in SKIP_HEADINGS or ln.startswith(("Code:", "Version:")):
            continue
        if _is_heading(ln):
            section = ln
            continue
        if ln.startswith("•"):
            body = ln.lstrip("•").strip()
            units.append((section, body))
    return meta, title, units


def load_stw_corpus(batch, path, gaps):
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is pinned in requirements
        raise RuntimeError("pypdf is required to parse the STW corpus") from exc

    files = sorted(path.glob("STW_*.pdf"))
    read = loaded = rejected = 0
    for pdf_path in files:
        read += 1
        ref = pdf_path.name
        reader = PdfReader(str(pdf_path))
        full_text = "\n".join((page.extract_text() or "") for page in reader.pages)
        meta, title, _ = _parse_stw_text(full_text)
        if "code" not in meta or "version" not in meta:
            rejected += 1
            gaps.add(GapEntry.PARSE_REJECT, "STW_HEADER_UNPARSED", ref,
                     "Code or Version not found on page; document not loaded")
            continue

        prefix = pdf_path.stem.split("_")[1] if "_" in pdf_path.stem else ""
        effective = _date(meta.get("effective"))
        if effective is None:
            gaps.add(GapEntry.MISSING_DATA, "EFFECTIVE_DATE_MISSING", ref,
                     "No effective date printed; retrieval cannot rank by currency")
        doc = ProtocolDocument.objects.create(
            code=meta["code"], version=meta["version"], source_kind=ProtocolDocument.NATIONAL,
            title=title[:255], specialty=SPECIALTY_BY_PREFIX.get(prefix, "Unassigned")[:128],
            effective_date=effective, supersedes_text=meta.get("supersedes", "")[:255],
            status_note="ARCHIVE" if "ARCHIVE" in full_text.upper() else "CURRENT_OR_SUPERSEDED_SEE_VERSION",
            source_file=pdf_path.name, load_batch=batch,
        )

        ordinal = 0
        objs = []
        for page_no, page in enumerate(reader.pages, start=1):
            _, _, units = _parse_stw_text(page.extract_text() or "")
            for section, body in units:
                ordinal += 1
                objs.append(ProtocolUnit(
                    document=doc, ordinal=ordinal, page_no=page_no, section=section[:128],
                    unit_type=_unit_type_for_section(section), text=body,
                    has_dose_text=bool(DOSE_RE.search(body)),
                ))
        ProtocolUnit.objects.bulk_create(objs, batch_size=500)
        loaded += 1
    return {"read": read, "loaded": loaded, "rejected": rejected}


def load_local_protocol(batch, path, gaps):
    text = path.read_text(encoding="utf-8")
    header = re.search(
        r"Document:\*\*\s*([A-Z0-9-]+).*?Version:\*\*\s*([0-9.]+).*?Approved:\*\*\s*(\d{4}-\d{2}-\d{2})",
        text, re.S,
    )
    if not header:
        gaps.add(GapEntry.PARSE_REJECT, "PROTOCOL_HEADER_UNPARSED", path.name, "document header not found")
        return {"read": 1, "loaded": 0, "rejected": 1}

    title_line = next((ln for ln in text.splitlines() if ln.startswith("# ")), "# Clinic protocol")
    doc = ProtocolDocument.objects.create(
        code=header.group(1), version=header.group(2), source_kind=ProtocolDocument.LOCAL,
        title=title_line.lstrip("# ").strip()[:255],
        specialty="Adult general medicine (clinic-specific)",
        effective_date=_date(header.group(3)),
        status_note="Internal clinic document. Not national guidance.",
        source_file=path.name, load_batch=batch,
    )
    objs = []
    for line in text.splitlines():
        step = re.match(r"^(\d+)\.\s+(.*)$", line.strip())
        if not step:
            continue
        body = step.group(2).replace("**", "")
        objs.append(ProtocolUnit(
            document=doc, ordinal=len(objs) + 1, page_no=1, section=f"Step {step.group(1)}",
            unit_type=_unit_type_for_local(body), text=body, has_dose_text=bool(DOSE_RE.search(body)),
        ))
    ProtocolUnit.objects.bulk_create(objs)
    return {"read": len(objs), "loaded": len(objs), "rejected": 0}


def _unit_type_for_local(body: str) -> str:
    low = body.lower()
    if re.search(r"\b(admit|refer|escalate)\b", low):
        return ProtocolUnit.REFERRAL
    if re.search(r"\b(avoid|do not)\b", low):
        return ProtocolUnit.CONTRAINDICATION
    return ProtocolUnit.RECOMMENDATION


# --- orchestration ----------------------------------------------------------

def _clear_products():
    Product.objects.all().delete()


def _clear_stock():
    PharmacyStockItem.objects.all().delete()


def _clear_national():
    ProtocolDocument.objects.filter(source_kind=ProtocolDocument.NATIONAL).delete()


def _clear_local():
    ProtocolDocument.objects.filter(source_kind=ProtocolDocument.LOCAL).delete()


def _plan(data_dir: Path):
    """Order matters: CDCI loads before stock so stock lines can be matched."""
    return [
        ("cdci", data_dir / "cdci_drug_subset.csv", load_cdci, "CDCI-SUBSET-2026Q2", _clear_products),
        ("nlem", data_dir / "nlem_extract.csv", load_nlem, "NLEM 2022",
         lambda: NLEMEntry.objects.all().delete()),
        ("jan_aushadhi", data_dir / "jan_aushadhi_extract.csv", load_jan_aushadhi, "PMBJP-2026-05",
         lambda: JanAushadhiItem.objects.all().delete()),
        ("regulatory_gazette", data_dir / "regulatory_gazette_events.csv", load_gazette, "",
         lambda: RegulatoryEvent.objects.all().delete()),
        ("severe_interactions", data_dir / "severe_interaction_seed.csv", load_interactions, "",
         lambda: SevereInteraction.objects.all().delete()),
        ("pharmacy_stock", data_dir / "pharmacy_stock.csv", load_stock, "", _clear_stock),
        ("stw_corpus", data_dir / "corpus", load_stw_corpus, "", _clear_national),
        ("local_protocol", data_dir / "local_protocol_acute_fever.md", load_local_protocol, "", _clear_local),
    ]


def _run(dataset, path, loader, source_version, clear, replace):
    if not path.exists():
        GapEntry.objects.create(
            dataset=dataset, category=GapEntry.MISSING_DATA, severity=GapEntry.HIGH,
            reason_code="SOURCE_NOT_FOUND", source_ref=str(path),
            message="Expected packet file not found; dataset not loaded",
        )
        return {"dataset": dataset, "status": "MISSING"}

    digest = sha256_of(path)
    if not replace and LoadBatch.objects.filter(dataset=dataset, file_sha256=digest, status=LoadBatch.OK).exists():
        return {"dataset": dataset, "status": "SKIPPED_UNCHANGED"}

    batch = LoadBatch.objects.create(
        dataset=dataset, source_file=path.name, source_version=source_version, file_sha256=digest,
    )
    gaps = Collector(batch)
    try:
        with transaction.atomic():
            if replace:
                clear()
            stats = loader(batch, path, gaps)
            gaps.flush()
    except Exception as exc:
        batch.status = LoadBatch.FAILED
        batch.finished_at = timezone.now()
        batch.save(update_fields=["status", "finished_at"])
        GapEntry.objects.create(
            dataset=dataset, load_batch=batch, category=GapEntry.SERVICE_ERROR, severity=GapEntry.HIGH,
            reason_code=type(exc).__name__[:64], source_ref=path.name, message=str(exc)[:2000],
        )
        raise

    batch.rows_read = stats["read"]
    batch.rows_loaded = stats["loaded"]
    batch.rows_rejected = stats["rejected"]
    batch.status = LoadBatch.OK
    batch.finished_at = timezone.now()
    batch.save()
    return {"dataset": dataset, "status": "OK", "batch_id": batch.id, **stats}


def load_all(data_dir, replace=False):
    """Load every packet file found under data_dir. Returns one result dict per dataset."""
    results = []
    for dataset, path, loader, version, clear in _plan(Path(data_dir)):
        results.append(_run(dataset, path, loader, version, clear, replace))
    return results
