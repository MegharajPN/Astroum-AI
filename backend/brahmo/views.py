import datetime as dt
import itertools

from django.conf import settings
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import ValidationError

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
from .serializers import (
    GapEntrySerializer,
    JanAushadhiItemSerializer,
    LoadBatchSerializer,
    NLEMEntrySerializer,
    PharmacyStockItemSerializer,
    ProductSerializer,
    ProtocolDocumentSerializer,
    ProtocolUnitSerializer,
    RegulatoryEventSerializer,
    SevereInteractionSerializer,
)


def _flag(params, name):
    value = params.get(name)
    if value in ("true", "1"):
        return True
    if value in ("false", "0"):
        return False
    return None


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Drug master. ?q= brand/strength, ?ingredient= salt, ?dose_form=, ?fdc=true|false, ?manufacturer="""
    serializer_class = ProductSerializer

    def get_queryset(self):
        p = self.request.query_params
        qs = Product.objects.select_related("load_batch").prefetch_related("ingredients")
        if p.get("q"):
            qs = qs.filter(Q(brand_name__icontains=p["q"]) | Q(strength_text__icontains=p["q"]))
        if p.get("ingredient"):
            qs = qs.filter(ingredients__ingredient_name__icontains=p["ingredient"]).distinct()
        if p.get("dose_form"):
            qs = qs.filter(dose_form__iexact=p["dose_form"])
        if p.get("manufacturer"):
            qs = qs.filter(manufacturer__icontains=p["manufacturer"])
        fdc = _flag(p, "fdc")
        if fdc is not None:
            qs = qs.filter(is_fdc=fdc)
        return qs.order_by("brand_name", "product_id")


class NLEMViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NLEMEntrySerializer

    def get_queryset(self):
        qs = NLEMEntry.objects.all()
        p = self.request.query_params
        if p.get("q"):
            qs = qs.filter(medicine__icontains=p["q"])
        if p.get("care_level"):
            qs = qs.filter(care_levels__contains=p["care_level"])
        return qs


class JanAushadhiViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = JanAushadhiItemSerializer

    def get_queryset(self):
        qs = JanAushadhiItem.objects.all()
        if self.request.query_params.get("q"):
            qs = qs.filter(generic_name__icontains=self.request.query_params["q"])
        return qs


class RegulatoryEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Event log. Status is derived from these events, never stored as a boolean."""
    serializer_class = RegulatoryEventSerializer

    def get_queryset(self):
        p = self.request.query_params
        qs = RegulatoryEvent.objects.all()
        if p.get("target"):
            qs = qs.filter(target_description__icontains=p["target"])
        if p.get("action"):
            qs = qs.filter(action=p["action"].upper())
        if p.get("as_of"):
            qs = qs.filter(effective_date__lte=p["as_of"])
        return qs


class PharmacyStockViewSet(viewsets.ReadOnlyModelViewSet):
    """Untrusted clinic stock lines. ?match_status=, ?q=, ?expiring=1 (within configured window)."""
    serializer_class = PharmacyStockItemSerializer

    def get_queryset(self):
        p = self.request.query_params
        qs = PharmacyStockItem.objects.select_related("matched_product")
        if p.get("q"):
            qs = qs.filter(item_name_as_billed__icontains=p["q"])
        if p.get("match_status"):
            qs = qs.filter(match_status=p["match_status"].upper())
        if _flag(p, "expiring"):
            today = dt.date.today()
            limit = today + dt.timedelta(days=settings.BRAHMO["STOCK_EXPIRY_WARN_DAYS"])
            qs = qs.filter(expiry_date__gte=today, expiry_date__lte=limit)
        return qs


class ProtocolDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProtocolDocumentSerializer

    def get_queryset(self):
        p = self.request.query_params
        qs = ProtocolDocument.objects.all()
        if p.get("source_kind"):
            qs = qs.filter(source_kind=p["source_kind"].upper())
        if p.get("specialty"):
            qs = qs.filter(specialty__icontains=p["specialty"])
        return qs


class ProtocolUnitViewSet(viewsets.ReadOnlyModelViewSet):
    """Decision units for Module B retrieval. Lexical search for now; see DESIGN.md D-006."""
    serializer_class = ProtocolUnitSerializer

    def get_queryset(self):
        p = self.request.query_params
        qs = ProtocolUnit.objects.select_related("document")
        if p.get("q"):
            qs = qs.filter(Q(text__icontains=p["q"]) | Q(section__icontains=p["q"]))
        if p.get("specialty"):
            qs = qs.filter(document__specialty__icontains=p["specialty"])
        if p.get("source_kind"):
            qs = qs.filter(document__source_kind=p["source_kind"].upper())
        if p.get("unit_type"):
            qs = qs.filter(unit_type=p["unit_type"].upper())
        if p.get("document"):
            qs = qs.filter(document__code__iexact=p["document"])
        if p.get("version"):
            qs = qs.filter(document__version=p["version"])
        return qs.order_by("document__specialty", "document__code", "-document__version", "page_no", "ordinal")


class GapEntryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                      mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Gaps register. Create = manual log; update = resolve/accept with a note."""
    serializer_class = GapEntrySerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        p = self.request.query_params
        qs = GapEntry.objects.all()
        for field in ("category", "status", "severity", "dataset"):
            if p.get(field):
                qs = qs.filter(**{field: p[field].upper() if field != "dataset" else p[field]})
        return qs

    def create(self, request, *args, **kwargs):
        required = ("dataset", "category", "reason_code", "message")
        missing = [f for f in required if not request.data.get(f)]
        if missing:
            raise ValidationError({f: "required" for f in missing})
        entry = GapEntry.objects.create(
            dataset=request.data["dataset"],
            category=request.data["category"],
            severity=request.data.get("severity", GapEntry.MEDIUM),
            reason_code=request.data["reason_code"][:64],
            source_ref=request.data.get("source_ref", "")[:255],
            message=request.data["message"],
            details=request.data.get("details", {}),
        )
        return Response(GapEntrySerializer(entry).data, status=201)

    def perform_update(self, serializer):
        new_status = serializer.validated_data.get("status")
        extra = {}
        if new_status in (GapEntry.RESOLVED, GapEntry.ACCEPTED):
            extra["resolved_at"] = timezone.now()
        serializer.save(**extra)


class LoadBatchViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LoadBatchSerializer
    queryset = LoadBatch.objects.all()


class InteractionListView(ListAPIView):
    serializer_class = SevereInteractionSerializer

    def get_queryset(self):
        qs = SevereInteraction.objects.all()
        if self.request.query_params.get("ingredient"):
            term = self.request.query_params["ingredient"].lower()
            qs = qs.filter(Q(ingredient_a__icontains=term) | Q(ingredient_b__icontains=term))
        return qs


class InteractionCheckView(APIView):
    """Pure lookup, no model call (law 4). Pairwise over ?ingredients=a,b,c.

    HIT = pair found in the seed list.
    PARTIAL_COVERAGE = pair not in the seed list. The seed list has 15 pairs, so
    absence is NOT evidence of safety and is never reported as CHECKED_NO_HIT.
    """

    def get(self, request):
        raw = request.query_params.get("ingredients", "")
        names = sorted({n.strip().lower() for n in raw.split(",") if n.strip()})
        if len(names) < 2:
            return Response(
                {"status": "UNVERIFIED_INPUT",
                 "detail": "Provide at least two ingredient names separated by commas."},
                status=400,
            )
        pairs = list(itertools.combinations(names, 2))
        keys = [f"{a}|{b}" for a, b in pairs]
        hits = {row.pair_key: row for row in SevereInteraction.objects.filter(pair_key__in=keys)}
        results = []
        for (a, b), key in zip(pairs, keys):
            row = hits.get(key)
            if row:
                results.append({
                    "pair": [a, b], "status": "HIT", "severity": row.severity,
                    "evidence": {"note": row.note, "source_tag": row.source_tag,
                                 "seed_row_id": row.id, "load_batch": row.load_batch_id},
                })
            else:
                results.append({
                    "pair": [a, b], "status": "PARTIAL_COVERAGE",
                    "detail": "Pair not in the severe-interaction seed list. Not evidence of safety.",
                })
        return Response({
            "seed_list_pairs": SevereInteraction.objects.count(),
            "results": results,
        })


class StockSummaryView(APIView):
    def get(self, request):
        today = dt.date.today()
        warn_days = settings.BRAHMO["STOCK_EXPIRY_WARN_DAYS"]
        limit = today + dt.timedelta(days=warn_days)
        qs = PharmacyStockItem.objects.all()
        value_expr = ExpressionWrapper(F("qty_units") * F("mrp_inr"),
                                       output_field=DecimalField(max_digits=24, decimal_places=2))
        return Response({
            "lines": qs.count(),
            "by_match_status": list(qs.values("match_status").annotate(n=Count("id"))),
            "expired": qs.filter(expiry_date__lt=today).count(),
            "expiring_within_window": qs.filter(expiry_date__gte=today, expiry_date__lte=limit).count(),
            "window_days": warn_days,
            "expiry_unparsed": qs.filter(expiry_date__isnull=True).count(),
            "billed_value_inr": qs.aggregate(total=Sum(value_expr))["total"],
            "note": "Billed MRP x units as written by the clinic. Not normalised to any price list.",
        })


class DashboardView(APIView):
    def get(self, request):
        counts = {
            "products": Product.objects.count(),
            "fdc_products": Product.objects.filter(is_fdc=True).count(),
            "product_ingredients": ProductIngredient.objects.count(),
            "nlem_entries": NLEMEntry.objects.count(),
            "jan_aushadhi_items": JanAushadhiItem.objects.count(),
            "regulatory_events": RegulatoryEvent.objects.count(),
            "severe_interaction_pairs": SevereInteraction.objects.count(),
            "stock_lines": PharmacyStockItem.objects.count(),
            "protocol_documents": ProtocolDocument.objects.count(),
            "protocol_units": ProtocolUnit.objects.count(),
        }
        open_gaps = dict(
            GapEntry.objects.filter(status=GapEntry.OPEN).values_list("severity").annotate(n=Count("id"))
        )
        latest = {}
        for batch in LoadBatch.objects.order_by("dataset", "-started_at"):
            latest.setdefault(batch.dataset, LoadBatchSerializer(batch).data)
        return Response({"counts": counts, "open_gaps_by_severity": open_gaps, "latest_batches": latest})
