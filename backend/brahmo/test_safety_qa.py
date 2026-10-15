"""Rail and grounded-Q&A tests.

Fixtures are real packet rows: the CDCI excerpt (18 rows used by the seeds), the 12 gazette events,
the 15 interaction seeds. The protocol units are transcribed verbatim from the STW one-pagers
and the clinic protocol, so Q&A is exercised without the PDF binaries.
"""
from pathlib import Path

from django.test import TestCase
from django.urls import reverse

from . import ingest, qa, rail
from .models import ProtocolDocument, ProtocolUnit

FIX = Path(__file__).parent / "fixtures"


def _load_fixtures():
    ingest._run("cdci", FIX / "cdci_excerpt.csv", ingest.load_cdci, "", lambda: None, replace=False)
    ingest._run("regulatory_gazette", FIX / "regulatory_gazette_events.csv", ingest.load_gazette, "",
                lambda: None, replace=False)
    ingest._run("severe_interactions", FIX / "severe_interaction_seed.csv", ingest.load_interactions, "",
                lambda: None, replace=False)


def _seed_rx(rx_id):
    import csv
    with open(FIX / "seed_prescriptions_template.csv", newline="", encoding="utf-8") as f:
        return [{"line_no": int(r["item_no"]), "written_product": r["written_product"],
                 "strength_as_written": r["strength_as_written"], "dose_frequency": r["dose_frequency"]}
                for r in csv.DictReader(f) if r["rx_id"] == rx_id]


def _doc(batch, code, version, kind, title, specialty, effective, units):
    doc = ProtocolDocument.objects.create(
        code=code, version=version, source_kind=kind, title=title, specialty=specialty,
        effective_date=effective, source_file=f"{code}.pdf", load_batch=batch,
    )
    for n, (page, section, utype, text) in enumerate(units, start=1):
        ProtocolUnit.objects.create(
            document=doc, ordinal=n, page_no=page, section=section, unit_type=utype,
            text=text, has_dose_text=bool(ingest.DOSE_RE.search(text)),
        )
    return doc


class RailTests(TestCase):
    def setUp(self):
        from .models import LoadBatch
        self.batch = LoadBatch.objects.create(dataset="x", source_file="x", file_sha256="0" * 64, status="OK")
        _load_fixtures()

    def _item(self, rx, line):
        return next(i for i in rail.run_rail(_seed_rx(rx))["items"] if i["line_no"] == line)

    def test_fdc_prohibition_is_derived_from_latest_active_event(self):
        result = rail.run_rail(_seed_rx("RX02"))
        hit = [c for c in result["checks"]["prohibited_fdc"] if c["state"] == rail.HIT]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["evidence"]["notification_id"], "GSR 411(E)")  # EV003 supersedes stay EV002
        self.assertEqual(result["overall_state"], rail.HIT)

    def test_duplicate_salt_across_brands_carries_cumulative_aggregate(self):
        result = rail.run_rail(_seed_rx("RX01"))
        dup = [d for d in result["checks"]["duplicate_ingredient"] if d["ingredient"] == "Paracetamol"]
        self.assertEqual(len(dup), 1)
        self.assertEqual(dup[0]["state"], rail.HIT)
        self.assertEqual(dup[0]["aggregate"]["daily_mg_known"], 2300.0)  # 650x2 + 500x2
        cum = [c for c in result["checks"]["cumulative_exposure"] if c["ingredient"] == "Paracetamol"][0]
        self.assertEqual(cum["state"], rail.CHECKED_NO_HIT)  # under the 3000 mg ceiling

    def test_unknown_frequency_makes_total_a_lower_bound_not_a_pass(self):
        cum = [c for c in rail.run_rail(_seed_rx("RX07"))["checks"]["cumulative_exposure"]
               if c["ingredient"] == "Paracetamol"][0]
        self.assertEqual(cum["daily_mg_known"], 1950.0)
        self.assertTrue(cum["lower_bound"])
        self.assertEqual(cum["state"], rail.PARTIAL_COVERAGE)

    def test_severe_interaction_hit(self):
        result = rail.run_rail(_seed_rx("RX03"))
        hits = [s for s in result["checks"]["severe_interaction"] if s["state"] == rail.HIT]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["severity"], "SEVERE")

    def test_unmatched_brand_is_not_checked_never_safe(self):
        item = self._item("RX04", 1)
        self.assertEqual(item["resolution"], "UNMATCHED")
        self.assertEqual(item["state"], rail.NOT_CHECKED)
        self.assertNotEqual(rail.run_rail(_seed_rx("RX04"))["overall_state"], rail.CHECKED_NO_HIT)

    def test_written_unit_mismatch_is_source_conflict(self):
        item = self._item("RX10", 2)
        self.assertEqual(item["state"], rail.SOURCE_CONFLICT)
        self.assertIn("mcg", item["detail"])

    def test_duplicate_telmisartan_across_fixed_combo_and_single(self):
        result = rail.run_rail(_seed_rx("RX09"))
        self.assertTrue(any(d["ingredient"] == "Telmisartan" for d in result["checks"]["duplicate_ingredient"]))

    def test_ambiguous_brand_is_queued_not_linked(self):
        from .models import Product
        batch = self.batch
        for pid in ("Z1", "Z2"):
            Product.objects.create(product_id=pid, brand_name="Dup Brand", strength_text="Atenolol 50 mg",
                                   source="s", load_batch=batch)
        result = rail.run_rail([{"line_no": 1, "written_product": "Dup Brand", "dose_frequency": "1-0-0"}])
        self.assertEqual(result["items"][0]["resolution"], "AMBIGUOUS")
        self.assertIsNone(result["items"][0]["product_id"])
        self.assertEqual(result["items"][0]["state"], rail.UNVERIFIED_INPUT)

    def test_api_rejects_empty_prescription(self):
        response = self.client.post(reverse("rail-check"), {"prescription": []}, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_trace_contains_every_version_and_no_model_call(self):
        response = self.client.post(
            reverse("trace"),
            {"prescription": _seed_rx("RX02"), "question": "What is the first-line antibiotic for otitis media?"},
            content_type="application/json",
        )
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(body["versions"]["model"])
        self.assertIn("cdci", body["versions"]["data"])
        self.assertEqual(body["safety"]["overall_state"], rail.HIT)


class QATests(TestCase):
    def setUp(self):
        from .models import LoadBatch
        batch = LoadBatch.objects.create(dataset="stw_corpus", source_file="t", file_sha256="1" * 64, status="OK")
        import datetime as dt
        hyp_title = "Hypertension — Initial Management (Adult)"
        _doc(batch, "STW-GP-02", "2025.2", ProtocolDocument.NATIONAL, hyp_title, "General Practice",
             dt.date(2025, 6, 1), [
                 (1, "CONFIRM", ProtocolUnit.WORKFLOW_STEP, "Two readings, two occasions"),
                 (1, "FIRST-LINE MANAGEMENT (CURRENT)", ProtocolUnit.RECOMMENDATION,
                  "Start Amlodipine 5 mg once daily OR Telmisartan 40 mg once daily"),
             ])
        _doc(batch, "STW-GP-02", "2021.1", ProtocolDocument.NATIONAL, hyp_title, "General Practice",
             dt.date(2021, 2, 1), [
                 (1, "FIRST-LINE MANAGEMENT (THIS 2021 EDITION)", ProtocolUnit.RECOMMENDATION,
                  "Start Atenolol 50 mg once daily as initial monotherapy"),
             ])
        _doc(batch, "STW-GP-04", "2024.2", ProtocolDocument.NATIONAL, "Dengue Fever — OPD Management",
             "General Practice", dt.date(2024, 7, 1), [
                 (1, "OPD MANAGEMENT", ProtocolUnit.CONTRAINDICATION,
                  "AVOID Ibuprofen, Diclofenac, Aspirin and all NSAIDs — bleeding risk"),
             ])
        _doc(batch, "SOP-CLIN-014", "2.1", ProtocolDocument.LOCAL,
             "Adult Acute Undifferentiated Fever: Local Treatment Protocol", "Adult general medicine",
             dt.date(2026, 3, 10), [
                 (1, "Step 2", ProtocolUnit.RECOMMENDATION,
                  "Day 2: if fever persists beyond 48 hours without a localizing source, start empirical "
                  "Azithromycin 500 mg once daily for 3 days."),
             ])

    def test_out_of_corpus_question_abstains(self):
        result = qa.answer("What is the first-line prophylactic drug for migraine in adults?")
        self.assertEqual(result["status"], "ABSTAINED")
        self.assertEqual(result["citations"], [])
        self.assertIn("migraine", result["missing"])

    def test_two_editions_are_both_shown_as_conflict(self):
        result = qa.answer("What is the first-line initial drug therapy for newly diagnosed adult hypertension?")
        self.assertEqual(result["status"], "ANSWERED")
        codes = [c["edition"] for c in result["citations"]]
        self.assertIn("STW-GP-02 v2025.2", codes)
        self.assertIn("STW-GP-02 v2021.1", codes)
        conflict = [c for c in result["conflicts"] if c["kind"] == "EDITION_CONFLICT"]
        self.assertEqual(len(conflict), 1)

    def test_suspected_dengue_avoid_class_is_cited(self):
        result = qa.answer("Which analgesic class must be avoided in suspected dengue, and why?")
        self.assertEqual(result["status"], "ANSWERED")
        self.assertTrue(any("AVOID Ibuprofen" in c["text"] for c in result["citations"]))

    def test_clinic_question_is_labelled_and_national_coverage_is_reported(self):
        result = qa.answer("Per the clinic's own protocol, when are empirical antibiotics started in adult "
                           "acute undifferentiated fever?")
        self.assertEqual(result["status"], "ANSWERED")
        self.assertTrue(all(c["label"].startswith("CLINIC PROTOCOL") for c in result["citations"]))
        self.assertTrue(result["sources_searched"] == [ProtocolDocument.LOCAL])

    def test_national_and_clinic_both_searched_and_gap_reported_not_filled(self):
        # The fixture has no national fever workflow, so the national side must report no coverage
        # and no divergence may be invented.
        result = qa.answer("Does the national pack and the clinic protocol agree on antibiotics for fever?")
        self.assertEqual(len(result["sources_searched"]), 2)
        self.assertEqual(result["status"], "ANSWERED")
        self.assertFalse(result["coverage"][ProtocolDocument.NATIONAL])
        self.assertTrue(result["coverage"][ProtocolDocument.LOCAL])
        self.assertFalse(any(c["kind"] == "DIVERGENCE_SHOWN" for c in result["conflicts"]))

    def test_no_model_calls_recorded(self):
        self.assertEqual(qa.answer("dengue avoid analgesic")["model_calls"], 0)
