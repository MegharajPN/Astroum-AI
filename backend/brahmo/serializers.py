from rest_framework import serializers

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


class LoadBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoadBatch
        fields = "__all__"


class ProductIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductIngredient
        fields = ["position", "ingredient_name", "strength_mg", "mapping_method", "confidence"]


class ProductSerializer(serializers.ModelSerializer):
    ingredients = ProductIngredientSerializer(many=True, read_only=True)
    source_batch = serializers.IntegerField(source="load_batch_id", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "product_id", "brand_name", "manufacturer", "dose_form", "strength_text",
            "is_fdc", "source", "source_version", "effective_from", "source_batch", "ingredients",
        ]


class NLEMEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = NLEMEntry
        fields = ["id", "medicine", "therapeutic_category", "care_levels", "edition", "load_batch"]


class JanAushadhiItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = JanAushadhiItem
        fields = ["id", "generic_name", "strength", "pack", "mrp_inr", "catalog_version", "load_batch"]


class RegulatoryEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegulatoryEvent
        fields = [
            "id", "event_id", "notification_id", "date_published", "effective_date", "action",
            "target_type", "target_description", "supersedes_event_code", "note", "load_batch",
        ]


class SevereInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SevereInteraction
        fields = ["id", "ingredient_a", "ingredient_b", "severity", "note", "source_tag", "load_batch"]


class PharmacyStockItemSerializer(serializers.ModelSerializer):
    matched_product = serializers.SerializerMethodField()

    class Meta:
        model = PharmacyStockItem
        fields = [
            "id", "line_no", "item_name_as_billed", "billed_brand_key", "pack_tokens", "qty_units",
            "mrp_inr", "batch", "expiry_text", "expiry_date", "parse_status", "match_status",
            "matched_product", "load_batch",
        ]

    def get_matched_product(self, obj):
        if obj.matched_product_id is None:
            return None
        return {"id": obj.matched_product_id, "brand_name": obj.matched_product.brand_name,
                "strength_text": obj.matched_product.strength_text}


class ProtocolDocumentSerializer(serializers.ModelSerializer):
    unit_count = serializers.IntegerField(source="units.count", read_only=True)

    class Meta:
        model = ProtocolDocument
        fields = [
            "id", "code", "version", "source_kind", "title", "specialty", "effective_date",
            "supersedes_text", "status_note", "source_file", "unit_count", "load_batch",
        ]


class ProtocolUnitSerializer(serializers.ModelSerializer):
    document_code = serializers.CharField(source="document.code", read_only=True)
    document_version = serializers.CharField(source="document.version", read_only=True)
    source_kind = serializers.CharField(source="document.source_kind", read_only=True)
    specialty = serializers.CharField(source="document.specialty", read_only=True)
    effective_date = serializers.DateField(source="document.effective_date", read_only=True)
    source_ref = serializers.CharField(read_only=True)

    class Meta:
        model = ProtocolUnit
        fields = [
            "id", "document_code", "document_version", "source_kind", "specialty", "effective_date",
            "page_no", "section", "unit_type", "has_dose_text", "text", "source_ref",
        ]


class GapEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = GapEntry
        fields = [
            "id", "dataset", "load_batch", "category", "severity", "status", "reason_code",
            "source_ref", "message", "details", "resolution_note", "created_at", "resolved_at",
        ]
        read_only_fields = [
            "id", "dataset", "load_batch", "category", "severity", "reason_code", "source_ref",
            "message", "details", "created_at", "resolved_at",
        ]
