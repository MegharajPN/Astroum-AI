import datetime as dt
import tempfile
from pathlib import Path

from django.test import TestCase
from django.urls import reverse

from . import ingest
from .models import GapEntry, LoadBatch, PharmacyStockItem, Product, ProtocolUnit, SevereInteraction


class PureHelperTests(TestCase):
    """Parsing helpers. These run inside TestCase only for the test-runner harness; no fixtures needed."""

    def test_billed_name_splits_pack_tokens(self):
        key, packs = ingest.normalize_billed_name("DUTAS-PLUS CAP 10'S")
        self.assertEqual(key, "DUTAS PLUS")
        self.assertEqual(packs, "CAP 10'S")

    def test_billed_name_keeps_strength_numbers(self):
        key, _ = ingest.normalize_billed_name("DOLO 650 TAB 15'S")
        self.assertEqual(key, "DOLO 650")

    def test_expiry_is_last_day_of_month(self):
        self.assertEqual(ingest._expiry("2026-02"), dt.date(2026, 2, 28))
        self.assertEqual(ingest._expiry("2028-12"), dt.date(2028, 12, 31))

    def test_expiry_rejects_bad_month(self):
        self.assertIsNone(ingest._expiry("2026-13"))
        self.assertIsNone(ingest._expiry(""))

    def test_section_drives_unit_type(self):
        self.assertEqual(ingest._unit_type_for_section("RED FLAGS — REFER"), ProtocolUnit.REFERRAL)
        self.assertEqual(ingest._unit_type_for_section("DO NOT"), ProtocolUnit.CONTRAINDICATION)
        self.assertEqual(ingest._unit_type_for_section("FIRST-LINE MANAGEMENT (CURRENT)"),
                         ProtocolUnit.RECOMMENDATION)
        self.assertEqual(ingest._unit_type_for_section("TARGETS"), ProtocolUnit.MONITORING)

    def test_stw_page_parser_extracts_meta_and_bullets(self):
        text = (
            "STANDARD TREATMENT WORKFLOW\n"
            "Hypertension — Initial Management (Adult)\n"
            "Code: STW-GP-02\n"
            "Version: 2025.2 · Effective: 2025-06-01\n"
            "Supersedes: STW-GP-02 v2021.1\n"
            "FIRST-LINE MANAGEMENT (CURRENT)\n"
            "• Start Amlodipine 5 mg once daily OR Telmisartan 40 mg once daily\n"
            "SYNTHETIC ASSESSMENT DOCUMENT — modeled on the ICMR STW one-page format.\n"
        )
        meta, title, units = ingest._parse_stw_text(text)
        self.assertEqual(meta["code"], "STW-GP-02")
        self.assertEqual(meta["version"], "2025.2")
        self.assertEqual(meta["effective"], "2025-06-01")
        self.assertEqual(title, "Hypertension — Initial Management (Adult)")
        self.assertEqual(len(units), 1)
        self.assertTrue(units[0][1].startswith("Start Amlodipine 5 mg"))


class DatasetLoadTests(TestCase):
    """Loads small fixtures through the real loader path (LoadBatch, gaps, idempotency)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "regulatory_gazette_events.csv").write_text(
            "event_id,notification_id,date_published,effective_date,action,target_type,target_description,"
            "supersedes_event_id,note\n"
            "EV001,GSR 704(E),2018-09-07,2018-09-12,PROHIBITED,FDC,Nimesulide + Paracetamol,,Prohibition\n"
            "EV999,GSR X,2020-01-01,2020-01-02,BOGUS,FDC,Something,,bad action\n",
            encoding="utf-8",
        )
        (self.tmp / "severe_interaction_seed.csv").write_text(
            "ingredient_a,ingredient_b,severity,note,source_tag\n"
            "Warfarin,Aspirin,SEVERE,Additive bleeding risk,public-high-priority-2026\n"
            "Aspirin,Warfarin,SEVERE,duplicate in other order,public-high-priority-2026\n",
            encoding="utf-8",
        )

    def test_gazette_rejects_unknown_action_and_logs_it(self):
        result = ingest._run("regulatory_gazette", self.tmp / "regulatory_gazette_events.csv",
                             ingest.load_gazette, "", lambda: None, replace=False)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["rejected"], 1)
        self.assertTrue(GapEntry.objects.filter(reason_code="UNKNOWN_ACTION_OR_TARGET").exists())

    def test_unchanged_file_is_skipped(self):
        path = self.tmp / "regulatory_gazette_events.csv"
        ingest._run("regulatory_gazette", path, ingest.load_gazette, "", lambda: None, replace=False)
        again = ingest._run("regulatory_gazette", path, ingest.load_gazette, "", lambda: None, replace=False)
        self.assertEqual(again["status"], "SKIPPED_UNCHANGED")
        self.assertEqual(LoadBatch.objects.filter(dataset="regulatory_gazette").count(), 1)

    def test_duplicate_interaction_pair_is_rejected_order_independent(self):
        ingest._run("severe_interactions", self.tmp / "severe_interaction_seed.csv",
                    ingest.load_interactions, "", lambda: None, replace=False)
        self.assertEqual(SevereInteraction.objects.count(), 1)
        self.assertEqual(SevereInteraction.objects.get().pair_key, "aspirin|warfarin")

    def test_interaction_check_hit_and_partial_coverage(self):
        ingest._run("severe_interactions", self.tmp / "severe_interaction_seed.csv",
                    ingest.load_interactions, "", lambda: None, replace=False)
        response = self.client.get(reverse("interaction-check"), {"ingredients": "Aspirin,Warfarin,Metformin"})
        self.assertEqual(response.status_code, 200)
        statuses = {tuple(r["pair"]): r["status"] for r in response.json()["results"]}
        self.assertEqual(statuses[("aspirin", "warfarin")], "HIT")
        self.assertEqual(statuses[("aspirin", "metformin")], "PARTIAL_COVERAGE")
        self.assertEqual(statuses[("metformin", "warfarin")], "PARTIAL_COVERAGE")

    def test_interaction_check_requires_two_ingredients(self):
        response = self.client.get(reverse("interaction-check"), {"ingredients": "Aspirin"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "UNVERIFIED_INPUT")


class StockMatchingTests(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        batch = LoadBatch.objects.create(dataset="cdci", source_file="x", file_sha256="0" * 64, status="OK")
        Product.objects.create(product_id="T1", brand_name="Dutas-Plus", strength_text="Atenolol 500 mg",
                               source="s", load_batch=batch)
        for pid in ("T2", "T3"):
            Product.objects.create(product_id=pid, brand_name="Suzith Forte", strength_text="x",
                                   source="s", load_batch=batch)
        (self.tmp / "pharmacy_stock.csv").write_text(
            "item_name_as_billed,qty_units,mrp_inr,batch,expiry\n"
            "DUTAS-PLUS CAP 10'S,20,97.95,B9520,2028-06\n"
            "SUZITH FORTE TAB 10'S,15,469.92,B4608,2028-03\n"
            "MYSTERY STRIP,1,10.00,B1,not-a-date\n"
            "NOBRAND,x,y,B2,2027-01\n",
            encoding="utf-8",
        )

    def test_exact_unique_ambiguous_and_unmatched_are_never_conflated(self):
        ingest._run("pharmacy_stock", self.tmp / "pharmacy_stock.csv", ingest.load_stock, "", lambda: None,
                    replace=False)
        by_name = {s.item_name_as_billed: s for s in PharmacyStockItem.objects.all()}
        self.assertEqual(by_name["DUTAS-PLUS CAP 10'S"].match_status, PharmacyStockItem.EXACT_UNIQUE)
        self.assertIsNotNone(by_name["DUTAS-PLUS CAP 10'S"].matched_product_id)
        self.assertEqual(by_name["SUZITH FORTE TAB 10'S"].match_status, PharmacyStockItem.AMBIGUOUS)
        self.assertIsNone(by_name["SUZITH FORTE TAB 10'S"].matched_product_id)
        self.assertEqual(by_name["MYSTERY STRIP"].match_status, PharmacyStockItem.UNMATCHED)
        self.assertEqual(by_name["MYSTERY STRIP"].parse_status, "PARTIAL")
        self.assertIsNone(by_name["MYSTERY STRIP"].expiry_date)
        self.assertTrue(GapEntry.objects.filter(reason_code="BRAND_NAME_NOT_UNIQUE").exists())
