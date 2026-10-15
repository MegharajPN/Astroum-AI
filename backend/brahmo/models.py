"""Versioned reference data for the drug master, protocols and safety rail inputs.

Provenance rule: every data row carries a ``load_batch`` (source file, SHA-256,
source version, load time), so any answer can be traced to the exact file that
produced it. Anything that could not be parsed or mapped is written to
``GapEntry`` instead of being guessed into a row.
"""
from django.db import models


class LoadBatch(models.Model):
    """One ingestion run of one source file."""

    RUNNING = "RUNNING"
    OK = "OK"
    FAILED = "FAILED"
    STATUS_CHOICES = [(RUNNING, "Running"), (OK, "OK"), (FAILED, "Failed")]

    dataset = models.CharField(max_length=64, db_index=True)
    source_file = models.CharField(max_length=255)
    source_version = models.CharField(max_length=128, blank=True)
    file_sha256 = models.CharField(max_length=64, db_index=True)
    rows_read = models.IntegerField(default=0)
    rows_loaded = models.IntegerField(default=0)
    rows_rejected = models.IntegerField(default=0)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.dataset} <- {self.source_file} [{self.status}]"


class Product(models.Model):
    """A brand / SKU from the CDCI drug-code extract."""

    product_id = models.CharField(max_length=32, unique=True)
    brand_name = models.CharField(max_length=255, db_index=True)
    manufacturer = models.CharField(max_length=255, blank=True)
    dose_form = models.CharField(max_length=64, blank=True)
    strength_text = models.CharField(max_length=512)
    is_fdc = models.BooleanField(default=False, db_index=True)
    source = models.CharField(max_length=64)
    source_version = models.CharField(max_length=64, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    load_batch = models.ForeignKey(LoadBatch, on_delete=models.PROTECT, related_name="products")

    class Meta:
        ordering = ["brand_name", "product_id"]

    def __str__(self):
        return f"{self.brand_name} ({self.product_id})"


class ProductIngredient(models.Model):
    """Decomposition of a product into salts + strengths (FDC = several rows)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="ingredients")
    position = models.PositiveSmallIntegerField()
    ingredient_name = models.CharField(max_length=255, db_index=True)
    strength_mg = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    mapping_method = models.CharField(max_length=32, default="SOURCE_COLUMNS")
    confidence = models.DecimalField(max_digits=4, decimal_places=3, default=1)

    class Meta:
        unique_together = [("product", "position")]
        ordering = ["product_id", "position"]

    def __str__(self):
        return f"{self.ingredient_name} {self.strength_mg}"


class NLEMEntry(models.Model):
    medicine = models.CharField(max_length=255, db_index=True)
    therapeutic_category = models.CharField(max_length=128, blank=True)
    care_levels = models.CharField(max_length=32, blank=True)
    edition = models.CharField(max_length=64)
    load_batch = models.ForeignKey(LoadBatch, on_delete=models.PROTECT, related_name="nlem_entries")

    class Meta:
        ordering = ["medicine"]
        verbose_name_plural = "NLEM entries"

    def __str__(self):
        return self.medicine


class JanAushadhiItem(models.Model):
    generic_name = models.CharField(max_length=255, db_index=True)
    strength = models.CharField(max_length=64)
    pack = models.CharField(max_length=64)
    mrp_inr = models.DecimalField(max_digits=12, decimal_places=2)
    catalog_version = models.CharField(max_length=64)
    load_batch = models.ForeignKey(LoadBatch, on_delete=models.PROTECT, related_name="jan_aushadhi_items")

    class Meta:
        ordering = ["generic_name", "strength"]

    def __str__(self):
        return f"{self.generic_name} {self.strength} ({self.pack})"


class RegulatoryEvent(models.Model):
    """Effective-dated gazette event. Status is derived from events, never stored as a boolean."""

    event_id = models.CharField(max_length=16, unique=True)
    notification_id = models.CharField(max_length=64)
    date_published = models.DateField()
    effective_date = models.DateField(db_index=True)
    action = models.CharField(max_length=32)
    target_type = models.CharField(max_length=32)
    target_description = models.CharField(max_length=512)
    supersedes_event_code = models.CharField(max_length=16, blank=True)
    note = models.CharField(max_length=512, blank=True)
    load_batch = models.ForeignKey(LoadBatch, on_delete=models.PROTECT, related_name="regulatory_events")

    class Meta:
        ordering = ["effective_date", "event_id"]

    def __str__(self):
        return f"{self.event_id} {self.action} {self.notification_id}"


class SevereInteraction(models.Model):
    """Ingredient-level severe interaction seed pair."""

    pair_key = models.CharField(max_length=255, unique=True)  # "a|b", lower-case, sorted
    ingredient_a = models.CharField(max_length=255)
    ingredient_b = models.CharField(max_length=255)
    severity = models.CharField(max_length=16)
    note = models.CharField(max_length=512, blank=True)
    source_tag = models.CharField(max_length=128, blank=True)
    load_batch = models.ForeignKey(LoadBatch, on_delete=models.PROTECT, related_name="interactions")

    class Meta:
        ordering = ["ingredient_a", "ingredient_b"]

    def __str__(self):
        return f"{self.ingredient_a} + {self.ingredient_b} ({self.severity})"


class PharmacyStockItem(models.Model):
    """One billed line from a clinic pharmacy stock file. Untrusted input."""

    EXACT_UNIQUE = "EXACT_UNIQUE"
    AMBIGUOUS = "AMBIGUOUS"
    UNMATCHED = "UNMATCHED"
    MATCH_CHOICES = [
        (EXACT_UNIQUE, "Exact unique brand match"),
        (AMBIGUOUS, "Several CDCI products share this brand"),
        (UNMATCHED, "No CDCI brand match"),
    ]

    line_no = models.PositiveIntegerField()
    item_name_as_billed = models.CharField(max_length=255)
    billed_brand_key = models.CharField(max_length=255, db_index=True)
    pack_tokens = models.CharField(max_length=64, blank=True)
    qty_units = models.IntegerField(null=True, blank=True)
    mrp_inr = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    batch = models.CharField(max_length=64, blank=True)
    expiry_text = models.CharField(max_length=16, blank=True)
    expiry_date = models.DateField(null=True, blank=True, db_index=True)  # last day of expiry month
    parse_status = models.CharField(max_length=16, default="PARSED")
    match_status = models.CharField(max_length=16, choices=MATCH_CHOICES, default=UNMATCHED)
    matched_product = models.ForeignKey(
        Product, null=True, blank=True, on_delete=models.SET_NULL, related_name="stock_lines"
    )
    load_batch = models.ForeignKey(LoadBatch, on_delete=models.PROTECT, related_name="stock_items")

    class Meta:
        ordering = ["line_no"]

    def __str__(self):
        return f"{self.item_name_as_billed} x{self.qty_units}"


class ProtocolDocument(models.Model):
    """A national STW edition or the clinic's own protocol. Edition is part of identity."""

    NATIONAL = "NATIONAL_STW"
    LOCAL = "LOCAL_PROTOCOL"
    SOURCE_CHOICES = [(NATIONAL, "National STW"), (LOCAL, "Clinic protocol (not national guidance)")]

    code = models.CharField(max_length=32)
    version = models.CharField(max_length=32)
    source_kind = models.CharField(max_length=32, choices=SOURCE_CHOICES)
    title = models.CharField(max_length=255)
    specialty = models.CharField(max_length=128)
    effective_date = models.DateField(null=True, blank=True)
    supersedes_text = models.CharField(max_length=255, blank=True)
    status_note = models.CharField(max_length=255, blank=True)
    source_file = models.CharField(max_length=255)
    load_batch = models.ForeignKey(LoadBatch, on_delete=models.PROTECT, related_name="protocol_documents")

    class Meta:
        unique_together = [("code", "version")]
        ordering = ["specialty", "code", "-version"]

    def __str__(self):
        return f"{self.code} v{self.version}"


class ProtocolUnit(models.Model):
    """A decision unit (recommendation, step, referral...) with its page anchor."""

    RECOMMENDATION = "RECOMMENDATION"
    WORKFLOW_STEP = "WORKFLOW_STEP"
    REFERRAL = "REFERRAL"
    CONTRAINDICATION = "CONTRAINDICATION"
    MONITORING = "MONITORING"
    UNIT_TYPE_CHOICES = [
        (RECOMMENDATION, "Recommendation"),
        (WORKFLOW_STEP, "Workflow step"),
        (REFERRAL, "Referral / red flag"),
        (CONTRAINDICATION, "Avoid / do not"),
        (MONITORING, "Monitoring / target"),
    ]

    document = models.ForeignKey(ProtocolDocument, on_delete=models.CASCADE, related_name="units")
    ordinal = models.PositiveSmallIntegerField()
    page_no = models.PositiveSmallIntegerField(default=1)
    section = models.CharField(max_length=128)
    unit_type = models.CharField(max_length=24, choices=UNIT_TYPE_CHOICES)
    text = models.TextField()
    has_dose_text = models.BooleanField(default=False)

    class Meta:
        ordering = ["document_id", "page_no", "ordinal"]

    @property
    def source_ref(self):
        d = self.document
        return f"{d.code} v{d.version}, p.{self.page_no}, §{self.section}"

    def __str__(self):
        return f"{self.source_ref}: {self.text[:60]}"


class GapEntry(models.Model):
    """Gaps register and error log. Missing data and anomalies are recorded here, not hidden."""

    MISSING_DATA = "MISSING_DATA"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    ANOMALY = "ANOMALY"
    PARSE_REJECT = "PARSE_REJECT"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    SERVICE_ERROR = "SERVICE_ERROR"
    CATEGORY_CHOICES = [
        (MISSING_DATA, "Missing data"),
        (AMBIGUOUS_MAPPING, "Ambiguous mapping (queued, not resolved)"),
        (ANOMALY, "Data anomaly"),
        (PARSE_REJECT, "Row rejected at parse"),
        (SOURCE_CONFLICT, "Source conflict"),
        (SERVICE_ERROR, "Service error"),
    ]

    LOW, MEDIUM, HIGH = "LOW", "MEDIUM", "HIGH"
    SEVERITY_CHOICES = [(LOW, "Low"), (MEDIUM, "Medium"), (HIGH, "High")]

    OPEN, RESOLVED, ACCEPTED = "OPEN", "RESOLVED", "ACCEPTED"
    STATUS_CHOICES = [(OPEN, "Open"), (RESOLVED, "Resolved"), (ACCEPTED, "Accepted as limitation")]

    dataset = models.CharField(max_length=64, db_index=True)
    load_batch = models.ForeignKey(
        LoadBatch, null=True, blank=True, on_delete=models.SET_NULL, related_name="gaps"
    )
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, db_index=True)
    severity = models.CharField(max_length=8, choices=SEVERITY_CHOICES, default=MEDIUM)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=OPEN, db_index=True)
    reason_code = models.CharField(max_length=64)
    source_ref = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    resolution_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name_plural = "gap entries"

    def __str__(self):
        return f"[{self.category}] {self.reason_code} @ {self.source_ref}"
