"""API error handling: unhandled failures are recorded in the gaps register and
returned as an explicit SERVICE_UNAVAILABLE state, never as a quiet 200."""
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .models import GapEntry

log = logging.getLogger(__name__)


def handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        return response

    log.exception("Unhandled API error")
    try:
        GapEntry.objects.create(
            dataset="api",
            category=GapEntry.SERVICE_ERROR,
            severity=GapEntry.HIGH,
            reason_code=type(exc).__name__[:64],
            source_ref=context["request"].path[:255],
            message=str(exc)[:2000],
        )
    except Exception:  # the database may be the thing that failed
        log.exception("Could not persist gap entry for API error")

    return Response(
        {"status": "SERVICE_UNAVAILABLE", "detail": "Internal error recorded in the gaps register."},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
