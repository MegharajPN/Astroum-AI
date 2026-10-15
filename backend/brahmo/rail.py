"""Deterministic prescription safety rail (Module A.6).

Pure lookup over versioned rows. There is no model call anywhere in this module (law 4).

Checks:
  (a) duplicate active ingredient across products
  (b) prohibited / restricted FDC, derived from effective-dated gazette events (law 7)
  (c) severe interactions against the seed list
  (d) cumulative same-ingredient exposure per day across the whole prescription

Every state comes from the 8-state vocabulary (law 5). When states combine, the most
cautious one wins, so an unknown is never reported as safe.
"""
import datetime as dt
import itertools
import re
from collections import defaultdict
from decimal import Decimal

from django.conf import settings

from .ingest import _brand_key
from .models import LoadBatch, Product, RegulatoryEvent, SevereInteraction

HIT = "HIT"
CHECKED_NO_HIT = "CHECKED_NO_HIT"
PARTIAL_COVERAGE = "PARTIAL_COVERAGE"
UNVERIFIED_INPUT = "UNVERIFIED_INPUT"
NOT_CHECKED = "NOT_CHECKED"
DATA_EXPIRED = "DATA_EXPIRED"
SOURCE_CONFLICT = "SOURCE_CONFLICT"
SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

# Lower rank = more cautious. The combined state is the minimum rank.
STATE_RANK = {
    SERVICE_UNAVAILABLE: 0,
    HIT: 1,
    SOURCE_CONFLICT: 2,
    UNVERIFIED_INPUT: 3,
    NOT_CHECKED: 4,
    DATA_EXPIRED: 5,
    PARTIAL_COVERAGE: 6,
    CHECKED_NO_HIT: 7,
}

FREQ_RE = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)\s*(?:x\s*(\d+)\s*d)?\s*$", re.IGNORECASE)
STRENGTH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(mcg|µg|mg|ml|g)\b", re.IGNORECASE)
DATA_DATASETS = [
    "cdci", "nlem", "jan_aushadhi", "regulatory_gazette", "severe_interactions",
    "pharmacy_stock", "stw_corpus", "local_protocol",
]


def worst_state(states):
    return min(states, key=STATE_RANK.__getitem__) if states else UNVERIFIED_INPUT


def parse_frequency(text):
    """'1-0-1 x 5d' -> (2 units/day, 5 days). Anything else -> (None, None): unknown, never assumed."""
    match = FREQ_RE.match(text or "")
    if not match:
        return None, None
    units_per_day = sum(int(match.group(i)) for i in (1, 2, 3))
    days = int(match.group(4)) if match.group(4) else None
    return units_per_day, days


def target_terms(description):
    """'Nimesulide + Paracetamol (all strengths)' -> frozenset({'nimesulide', 'paracetamol'})."""
    base = re.sub(r"\(.*?\)", "", description).strip()
    return frozenset(t.strip().lower() for t in base.split("+") if t.strip())


def scope_qualifier(description):
    match = re.search(r"\((.*?)\)", description)
    return match.group(1).strip() if match else ""


def derive_status(events):
    """Active event = not superseded by another event in the list. Latest effective wins.

    Callers pass only events effective on or before the as-of date, so a future
    supersession does not hide a current event.
    """
    events = list(events)
    superseded = {e.supersedes_event_code for e in events if e.supersedes_event_code}
    active = [e for e in events if e.event_id not in superseded]
    return max(active, key=lambda e: (e.effective_date, e.event_id)) if active else None


def data_versions():
    versions = {}
    for dataset in DATA_DATASETS:
        batch = LoadBatch.objects.filter(dataset=dataset, status=LoadBatch.OK).order_by("-started_at").first()
        versions[dataset] = (
            f"{batch.source_version or batch.source_file}@{batch.file_sha256[:12]}" if batch else "NOT_LOADED"
        )
    return versions


def _product_index():
    index = defaultdict(list)
    for product in Product.objects.prefetch_related("ingredients"):
        index[_brand_key(product.brand_name)].append(product)
    return index


def _resolve_item(raw, index):
    written = (raw.get("written_product") or "").strip()
    units_per_day, course_days = parse_frequency(raw.get("dose_frequency"))
    item = {
        "line_no": raw.get("line_no"),
        "written_product": written,
        "dose_frequency": raw.get("dose_frequency") or "",
        "strength_as_written": raw.get("strength_as_written") or "",
        "units_per_day": units_per_day,
        "course_days": course_days,
        "resolution": None,
        "product_id": None,
        "brand_name": None,
        "ingredients": [],
        "state": None,
        "detail": "",
        "_product": None,
    }
    candidates = index.get(_brand_key(written), []) if written else []
    if len(candidates) == 1:
        product = candidates[0]
        item.update(resolution="RESOLVED", product_id=product.id, brand_name=product.brand_name, _product=product)
        item["ingredients"] = [
            {"name": i.ingredient_name, "strength_mg": float(i.strength_mg) if i.strength_mg is not None else None}
            for i in product.ingredients.all()
        ]
    elif len(candidates) > 1:
        item.update(resolution="AMBIGUOUS", detail=f"{len(candidates)} CDCI products share this brand; not linked")
        item["candidates"] = [{"product_id": p.id, "strength_text": p.strength_text} for p in candidates]
    else:
        item.update(resolution="UNMATCHED", detail="No CDCI brand match; item not checked")
    return item


def _unit_conflict(item):
    written = STRENGTH_RE.search(item["strength_as_written"])
    source = STRENGTH_RE.search(item["_product"].strength_text) if item["_product"] else None
    if written and source and written.group(2).lower() != source.group(2).lower():
        return (f"Written unit '{written.group(2)}' differs from source unit '{source.group(2)}' "
                f"('{item['_product'].strength_text}'); not converted")
    return ""


def _set_item_state(item):
    conflict = _unit_conflict(item) if item["resolution"] == "RESOLVED" else ""
    if item["resolution"] == "UNMATCHED":
        item["state"] = NOT_CHECKED
    elif item["resolution"] == "AMBIGUOUS":
        item["state"] = UNVERIFIED_INPUT
    elif conflict:
        item["state"] = SOURCE_CONFLICT
        item["detail"] = conflict
    else:
        item["state"] = PARTIAL_COVERAGE
        item["detail"] = "Resolved to one CDCI product; checks ran against the loaded registers only"


def _cumulative_and_duplicates(resolved, max_daily):
    """Per-ingredient daily totals (d) and duplicate-salt hits (a)."""
    presence = defaultdict(set)
    brands = defaultdict(set)
    names = {}
    known = defaultdict(Decimal)
    unknown = defaultdict(list)
    contributions = defaultdict(list)
    lines = defaultdict(set)

    for item in resolved:
        for ing in item["ingredients"]:
            key = ing["name"].lower()
            names.setdefault(key, ing["name"])
            presence[key].add(item["product_id"])
            brands[key].add(item["brand_name"])
            lines[key].add(item["line_no"])
            if ing["strength_mg"] is None:
                unknown[key].append({"line_no": item["line_no"], "reason": "STRENGTH_MISSING"})
            elif item["units_per_day"] is None:
                unknown[key].append({"line_no": item["line_no"], "reason": "FREQUENCY_UNPARSED",
                                     "dose_frequency": item["dose_frequency"]})
            else:
                mg = Decimal(str(ing["strength_mg"])) * item["units_per_day"]
                known[key] += mg
                contributions[key].append({"line_no": item["line_no"], "brand": item["brand_name"],
                                           "mg_per_day": float(mg)})

    cumulative, duplicates = [], []
    for key in sorted(names):
        total = float(known[key])
        ceiling = max_daily.get(key)
        if ceiling and total > ceiling["max_mg"]:
            state = HIT
        elif unknown[key]:
            state = PARTIAL_COVERAGE
        elif ceiling:
            state = CHECKED_NO_HIT
        else:
            state = NOT_CHECKED
        entry = {
            "ingredient": names[key], "state": state, "daily_mg_known": round(total, 3),
            "lower_bound": bool(unknown[key]), "lines": sorted(lines[key]),
            "contributions": contributions[key], "unknown_contributions": unknown[key],
            "max_daily_mg": ceiling["max_mg"] if ceiling else None,
            "max_daily_mg_source": ceiling["source"] if ceiling else None,
            "detail": _cumulative_detail(state, names[key], ceiling, bool(unknown[key])),
        }
        cumulative.append(entry)
        if len(presence[key]) >= 2:
            duplicates.append({
                "ingredient": names[key], "state": HIT,
                "severity": "HIGH" if state == HIT else settings.BRAHMO["DUPLICATE_SEVERITY"],
                "products": sorted(brands[key]),
                "lines": sorted(lines[key]),
                "aggregate": {"daily_mg_known": entry["daily_mg_known"], "lower_bound": entry["lower_bound"]},
                "detail": f"{names[key]} appears in {len(presence[key])} products on this prescription",
            })
    return cumulative, duplicates


def _cumulative_detail(state, name, ceiling, has_unknown):
    if state == HIT:
        return f"Known daily total of {name} exceeds the documented ceiling."
    if state == PARTIAL_COVERAGE:
        return (f"Known daily total of {name} is a lower bound; some items have no usable "
                "strength or frequency.")
    if state == CHECKED_NO_HIT:
        return f"Total of {name} is within the documented ceiling."
    return f"No documented daily ceiling configured for {name}; aggregate shown as evidence only."


def _interactions(resolved, pair_rows):
    names = {}
    lines = defaultdict(set)
    for item in resolved:
        for ing in item["ingredients"]:
            key = ing["name"].lower()
            names.setdefault(key, ing["name"])
            lines[key].add(item["line_no"])
    results = []
    if len(names) < 2:
        return [{"state": NOT_CHECKED, "detail": "Fewer than two resolved ingredients; no pair to check."}]
    for a, b in itertools.combinations(sorted(names), 2):
        row = pair_rows.get(f"{a}|{b}")
        if row:
            results.append({
                "state": HIT, "severity": row.severity, "pair": [names[a], names[b]],
                "lines": sorted(lines[a] | lines[b]),
                "evidence": {"note": row.note, "source_tag": row.source_tag, "seed_row_id": row.id,
                             "load_batch": row.load_batch_id},
            })
    if not results:
        results.append({
            "state": PARTIAL_COVERAGE,
            "detail": (f"{len(list(itertools.combinations(names, 2)))} pairs checked against a seed list of "
                       f"{len(pair_rows)} pairs. No hit is not evidence of no interaction."),
        })
    return results


def _reg_result(label, events, lines, as_of, n_events):
    active = derive_status(events)
    if active is None:
        return {"state": PARTIAL_COVERAGE, "label": label, "lines": lines,
                "detail": (f"No gazette event in the register for {label} as of {as_of}. The register "
                           f"holds {n_events} events; absence here is not clearance.")}
    evidence = {"event_id": active.event_id, "notification_id": active.notification_id,
                "effective_date": active.effective_date.isoformat(), "action": active.action,
                "target_description": active.target_description, "supersedes": active.supersedes_event_code or None}
    if active.action == "STAY_GRANTED":
        return {"state": SOURCE_CONFLICT, "label": label, "lines": lines, "evidence": evidence,
                "detail": f"A stay ({active.notification_id}) is the active event. Verify before dispensing."}
    qualifier = scope_qualifier(active.target_description)
    severity = settings.BRAHMO["REGULATORY_SEVERITY"].get(active.action, "UNKNOWN")
    if qualifier and not qualifier.lower().startswith("all "):
        return {"state": PARTIAL_COVERAGE, "label": label, "lines": lines, "severity": severity,
                "evidence": evidence,
                "detail": (f"Event applies with scope '{qualifier}'. Applicability to this product and "
                           "patient cannot be confirmed from stock data.")}
    return {"state": HIT, "label": label, "lines": lines, "severity": severity, "evidence": evidence,
            "detail": f"{active.action} by {active.notification_id}, effective {active.effective_date}."}


def _regulatory(resolved, events, as_of):
    fdc_groups, ingredient_groups = defaultdict(list), defaultdict(list)
    for e in events:
        key = target_terms(e.target_description)
        if e.target_type == "FDC":
            fdc_groups[key].append(e)
        elif e.target_type == "INGREDIENT":
            ingredient_groups[key].append(e)

    checks = []
    for item in resolved:
        names = sorted({i["name"].lower() for i in item["ingredients"]})
        if len(names) > 1:
            label = "FDC " + " + ".join(names)
            checks.append(_reg_result(label, fdc_groups.get(frozenset(names), []),
                                      [item["line_no"]], as_of, len(events)))
        for name in names:
            checks.append(_reg_result(f"ingredient {name}", ingredient_groups.get(frozenset({name}), []),
                                      [item["line_no"]], as_of, len(events)))
    return checks


def run_rail(prescription, as_of=None):
    """Run the rail over a list of {line_no, written_product, dose_frequency, strength_as_written}."""
    as_of = as_of or dt.date.today()
    index = _product_index()
    events = list(RegulatoryEvent.objects.filter(effective_date__lte=as_of))
    pair_rows = {r.pair_key: r for r in SevereInteraction.objects.all()}
    max_daily = settings.BRAHMO["DAILY_MAX_MG"]

    items = [_resolve_item(raw, index) for raw in prescription]
    for item in items:
        _set_item_state(item)
    resolved = [i for i in items if i["_product"] is not None]

    cumulative, duplicates = _cumulative_and_duplicates(resolved, max_daily)
    checks = {
        "duplicate_ingredient": duplicates,
        "cumulative_exposure": cumulative,
        "prohibited_fdc": _regulatory(resolved, events, as_of),
        "severe_interaction": _interactions(resolved, pair_rows),
    }

    all_states = [i["state"] for i in items]
    for group in checks.values():
        all_states.extend(entry["state"] for entry in group)

    notes = []
    unresolved = [i["line_no"] for i in items if i["resolution"] != "RESOLVED"]
    if unresolved:
        notes.append(f"Unresolved lines {unresolved}: these were not checked and must not be read as clear.")

    for item in items:
        item.pop("_product", None)

    return {
        "rail_rule_version": settings.RAIL_RULE_VERSION,
        "as_of": as_of.isoformat(),
        "data_versions": data_versions(),
        "items": items,
        "checks": checks,
        "overall_state": worst_state(all_states),
        "states_present": sorted(set(all_states), key=STATE_RANK.__getitem__),
        "notes": notes,
    }
