"""Module A.7: run the rail over the 10 seeded prescriptions and fill the template's output columns.

Writes:
  --csv-out   the template with candidate_rail_output_state and candidate_evidence_note completed
  --json-out  full rail results per prescription (all checks, evidence, versions)
"""
import csv
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from brahmo import rail


class Command(BaseCommand):
    help = "Run the safety rail over the seeded prescription template and write the completed outputs."

    def add_arguments(self, parser):
        parser.add_argument("--input", default=str(settings.DATA_DIR / "seed_prescriptions_template.csv"))
        parser.add_argument("--csv-out", default=str(settings.DATA_DIR / "seed_prescriptions_completed.csv"))
        parser.add_argument("--json-out", default=str(settings.REPO_ROOT / "outputs" / "seed_rail_results.json"))

    def handle(self, *args, **opts):
        src = Path(opts["input"])
        if not src.exists():
            raise CommandError(f"Seed template not found: {src}")
        with open(src, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        by_rx = {}
        for row in rows:
            by_rx.setdefault(row["rx_id"], []).append(row)

        results = {}
        for rx_id, group in by_rx.items():
            prescription = [{
                "line_no": int(r["item_no"]),
                "written_product": r["written_product"],
                "strength_as_written": r["strength_as_written"],
                "dose_frequency": r["dose_frequency"],
            } for r in group]
            results[rx_id] = rail.run_rail(prescription)
            self.stdout.write(f"{rx_id}: {results[rx_id]['overall_state']}")

        for row in rows:
            result = results[row["rx_id"]]
            item = next(i for i in result["items"] if i["line_no"] == int(row["item_no"]))
            row["candidate_rail_output_state"] = item["state"]
            row["candidate_evidence_note"] = _note(item, result)

        out_csv = Path(opts["csv_out"])
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        out_json = Path(opts["json_out"])
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Wrote {out_csv} and {out_json}"))


def _note(item, result):
    relevant = []
    for group in result["checks"].values():
        for entry in group:
            if item["line_no"] in entry.get("lines", []) and entry["state"] != rail.CHECKED_NO_HIT:
                relevant.append(f"{entry['state']}: {entry.get('detail') or entry.get('ingredient', '')}")
    head = item["detail"] or item["state"]
    tail = "; ".join(relevant[:3])
    return f"{head} | {tail} | Rx overall: {result['overall_state']}".strip(" |")
