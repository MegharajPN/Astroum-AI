"""Safety, Q&A and trace endpoints (kept apart from the reference-data views)."""
import datetime as dt

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import qa, rail
from .trace import build_trace


def _prescription_from(data):
    items = data.get("prescription")
    if not isinstance(items, list) or not items:
        raise ValidationError({"prescription": "Provide a non-empty list of items."})
    cleaned = []
    for index, raw in enumerate(items, start=1):
        if not isinstance(raw, dict) or not str(raw.get("written_product", "")).strip():
            raise ValidationError({"prescription": f"Item {index} needs written_product."})
        cleaned.append({
            "line_no": raw.get("line_no", index),
            "written_product": str(raw["written_product"]),
            "dose_frequency": raw.get("dose_frequency", ""),
            "strength_as_written": raw.get("strength_as_written", ""),
        })
    return cleaned


def _as_of(data):
    if not data.get("as_of"):
        return None
    try:
        return dt.date.fromisoformat(data["as_of"])
    except ValueError as exc:
        raise ValidationError({"as_of": "Use YYYY-MM-DD."}) from exc


class RailCheckView(APIView):
    """POST {prescription: [...], as_of?: YYYY-MM-DD} -> rail result with 8-state vocabulary."""

    def post(self, request):
        return Response(rail.run_rail(_prescription_from(request.data), as_of=_as_of(request.data)))


class GroundedQAView(APIView):
    """GET ?q= -> cited answer or explicit abstention."""

    def get(self, request):
        question = request.query_params.get("q", "").strip()
        if not question:
            raise ValidationError({"q": "Provide a question."})
        return Response(qa.answer(question))


class TraceView(APIView):
    """POST {prescription: [...], question?: str, as_of?: date} -> single JSON trace."""

    def post(self, request):
        question = (request.data.get("question") or "").strip() or None
        return Response(build_trace(_prescription_from(request.data), question, as_of=_as_of(request.data)))
