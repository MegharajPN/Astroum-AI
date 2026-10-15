"""Grounded clinical Q&A slice (Module B). Extractive and deterministic.

No model writes any text. The answer is verbatim decision-unit text with its source,
edition and page anchor. If nothing in the corpus shares enough terms with the
question, the system abstains and says what is missing (law 2).
"""
import re
from collections import defaultdict

from django.conf import settings
from django.db.models import Q

from .models import ProtocolDocument, ProtocolUnit

TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SUFFIXES = ("ing", "ed", "es", "s")
NATIONAL = ProtocolDocument.NATIONAL
LOCAL = ProtocolDocument.LOCAL


def _stem(word):
    for suffix in SUFFIXES:
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def query_terms(question):
    stop = set(settings.BRAHMO["QA_STOPWORDS"])
    terms = []
    for token in TOKEN_RE.findall(question.lower()):
        if token in stop or len(token) < 3:
            continue
        stem = _stem(token)
        if stem not in terms:
            terms.append(stem)
    return terms


def _sources_for(question):
    """A question that names the clinic gets the clinic protocol; one that names national guidance
    gets the national pack. A question that names both (or neither) gets both, shown side by side."""
    ql = question.lower()
    if "clinic" in ql and "national" not in ql:
        return [LOCAL]
    if "national" in ql and "clinic" not in ql:
        return [NATIONAL]
    return [NATIONAL, LOCAL]


def _hits(word, haystack):
    return re.search(r"\b" + re.escape(word), haystack) is not None


def _term_matches(term, haystack, synonyms):
    return _hits(term, haystack) or any(_hits(s, haystack) for s in synonyms.get(term, []))


def _matched(unit, terms):
    haystack = " ".join([unit.document.title, unit.section, unit.text]).lower()
    synonyms = settings.BRAHMO["QA_SYNONYMS"]
    return [t for t in terms if _term_matches(t, haystack, synonyms)]


def _content_coverage(matched, terms):
    """Share of the question's content terms (not generic) that the unit matches."""
    generic = set(settings.BRAHMO["QA_GENERIC_TERMS"])
    content = [t for t in terms if t not in generic]
    if not content:
        return 1.0
    return len([t for t in content if t in matched]) / len(content)


def _citation(unit, matched):
    doc = unit.document
    return {
        "unit_id": unit.id,
        "text": unit.text,
        "source_ref": unit.source_ref,
        "source_kind": doc.source_kind,
        "label": ("CLINIC PROTOCOL (not national guidance)" if doc.source_kind == LOCAL
                  else "National STW"),
        "edition": f"{doc.code} v{doc.version}",
        "effective_date": doc.effective_date.isoformat() if doc.effective_date else None,
        "matched_terms": matched,
        "has_dose_text": unit.has_dose_text,
    }


def answer(question, top_k=None, min_distinct=None):
    cfg = settings.BRAHMO
    top_k = top_k or cfg["QA_TOP_K"]
    min_distinct = min_distinct or cfg["QA_MIN_DISTINCT_TERMS"]
    sources = _sources_for(question)
    terms = query_terms(question)
    base = {
        "question": question,
        "qa_rule_version": settings.QA_RULE_VERSION,
        "sources_searched": sources,
        "terms": terms,
        "number_policy": "Every number shown is quoted verbatim from a cited unit. None is computed.",
        "model_calls": 0,
    }
    if not terms:
        return {**base, "status": "ABSTAINED", "citations": [], "conflicts": [],
                "abstain_reason": "The question has no searchable clinical terms."}

    query = Q()
    for term in terms:
        query |= (Q(text__icontains=term) | Q(section__icontains=term)
                  | Q(document__title__icontains=term) | Q(document__specialty__icontains=term))
    candidates = list(
        ProtocolUnit.objects.select_related("document")
        .filter(query, document__source_kind__in=sources)
        .order_by("id")[: cfg["QA_CANDIDATE_LIMIT"]]
    )

    min_coverage = cfg["QA_MIN_CONTENT_COVERAGE"]
    scored, seen_terms = [], set()
    for unit in candidates:
        matched = _matched(unit, terms)
        seen_terms.update(matched)
        if len(matched) >= min_distinct and _content_coverage(matched, terms) >= min_coverage:
            scored.append((len(matched), unit, matched))
    # Stable multi-pass sort: score desc, then code asc, then newest edition first.
    scored.sort(key=lambda row: _version_key(row[1].document.version), reverse=True)
    scored.sort(key=lambda row: row[1].document.code)
    scored.sort(key=lambda row: row[0], reverse=True)
    top = scored[:top_k]

    if not top:
        missing = [t for t in terms if t not in seen_terms]
        return {**base, "status": "ABSTAINED", "citations": [], "conflicts": [],
                "coverage": {s: False for s in sources},
                "abstain_reason": (f"No decision unit in the searched sources shares at least {min_distinct} "
                                   f"terms with the question. Terms with no match anywhere in those sources: "
                                   f"{missing or terms}. The corpus does not cover this question."),
                "missing": missing or terms}

    citations = [_citation(unit, matched) for _, unit, matched in top]
    return {
        **base,
        "status": "ANSWERED",
        "citations": citations,
        "conflicts": _conflicts(citations),
        "coverage": {s: any(c["source_kind"] == s for c in citations) for s in sources},
        "abstain_reason": None,
        "missing": [t for t in terms if t not in seen_terms],
    }


def _version_key(version):
    return tuple(int(p) if p.isdigit() else 0 for p in version.split("."))


def _conflicts(citations):
    """Two editions of the same national code both returned = conflict, shown with dates, never merged."""
    editions = defaultdict(dict)
    for c in citations:
        if c["source_kind"] == NATIONAL:
            editions[c["edition"].split(" v")[0]].setdefault(c["edition"], c)
    conflicts = []
    for code, versions in editions.items():
        if len(versions) > 1:
            conflicts.append({
                "kind": "EDITION_CONFLICT",
                "code": code,
                "detail": "Multiple editions of this workflow matched. Both are shown with their dates; "
                          "they are not merged and no recommendation is chosen between them.",
                "editions": [{"edition": ed, "effective_date": c["effective_date"],
                              "text": c["text"], "source_ref": c["source_ref"]}
                             for ed, c in versions.items()],
            })
    kinds = {c["source_kind"] for c in citations}
    if kinds == {NATIONAL, LOCAL}:
        conflicts.append({
            "kind": "DIVERGENCE_SHOWN",
            "detail": "The national pack and the clinic protocol both matched. Both are shown, labelled, "
                      "and neither is merged into the other.",
        })
    return conflicts
