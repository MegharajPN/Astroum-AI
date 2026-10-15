"""End-to-end trace (Module C): one prescription + one question -> one JSON object.

Thin on purpose. It composes the rail and the grounded Q&A and records every version used.
"""
import datetime as dt
import uuid

from django.conf import settings

from . import qa, rail


def build_trace(prescription, question=None, as_of=None):
    safety = rail.run_rail(prescription, as_of=as_of)
    normalization = [
        {
            "line_no": item["line_no"],
            "written_product": item["written_product"],
            "resolution": item["resolution"],
            "brand_name": item["brand_name"],
            "product_id": item["product_id"],
            "candidates": item.get("candidates", []),
            "detail": item["detail"],
        }
        for item in safety["items"]
    ]
    return {
        "trace_id": uuid.uuid4().hex,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "unresolved_inputs": [n["line_no"] for n in normalization if n["resolution"] != "RESOLVED"],
        "normalization": normalization,
        "safety": safety,
        "grounded_answer": qa.answer(question) if question else None,
        "versions": {
            "rail_rule": settings.RAIL_RULE_VERSION,
            "qa_rule": settings.QA_RULE_VERSION,
            "data": safety["data_versions"],
            "model": None,
        },
    }
