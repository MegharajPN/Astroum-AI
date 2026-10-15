"""Mini-eval for Module B: score the grounded Q&A slice against eval/sample_questions.json.

Scoring follows the brief: correct +1 · correctly abstained 0 · confidently wrong -1.
An answer is correct only if every expected document is cited and the expected phrase
appears verbatim in a cited unit. An abstention on an answerable question is a miss (0), not an error.
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from brahmo import qa, rail

EVAL_FILE = settings.REPO_ROOT / "eval" / "sample_questions.json"
OUT_FILE = settings.REPO_ROOT / "eval" / "results.json"


def score(item, result):
    cited_codes = {c["edition"].split(" v")[0] for c in result["citations"]}
    cited_text = " ".join(c["text"] for c in result["citations"])
    if item["expect"] == "ABSTAIN":
        if result["status"] == "ABSTAINED":
            return "abstained_correctly", 0
        return "wrong", -1
    if result["status"] == "ABSTAINED":
        return "abstained_on_answerable", 0
    docs_ok = all(code in cited_codes for code in item["expected_documents"])
    phrase_ok = item["expected_phrase"] in cited_text
    if docs_ok and phrase_ok:
        return "correct", 1
    return "wrong", -1


class Command(BaseCommand):
    help = "Score the grounded Q&A slice on the 11 sample questions."

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(EVAL_FILE))
        parser.add_argument("--out", default=str(OUT_FILE))

    def handle(self, *args, **opts):
        path = Path(opts["file"])
        if not path.exists():
            raise CommandError(f"Eval file not found: {path}")
        items = json.loads(path.read_text(encoding="utf-8"))["questions"]

        rows, total = [], 0
        for item in items:
            result = qa.answer(item["question"])
            label, points = score(item, result)
            total += points
            rows.append({
                "id": item["id"], "label": label, "points": points,
                "expected": item["expect"], "status": result["status"],
                "cited": [c["edition"] for c in result["citations"]],
                "conflicts": [c["kind"] for c in result["conflicts"]],
                "abstain_reason": result.get("abstain_reason"),
            })
            self.stdout.write(f"Q{item['id']:>2} {label:<24} {points:+d}  cited={rows[-1]['cited']}")

        summary = {
            "questions": len(items),
            "correct": sum(r["label"] == "correct" for r in rows),
            "abstained_correctly": sum(r["label"] == "abstained_correctly" for r in rows),
            "abstained_on_answerable": sum(r["label"] == "abstained_on_answerable" for r in rows),
            "wrong": sum(r["label"] == "wrong" for r in rows),
            "score": total,
            "qa_rule_version": settings.QA_RULE_VERSION,
            "data_versions": rail.data_versions(),
            "rows": rows,
        }
        out = Path(opts["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(
            f"correct={summary['correct']} abstained_correctly={summary['abstained_correctly']} "
            f"abstained_on_answerable={summary['abstained_on_answerable']} wrong={summary['wrong']} "
            f"score={total}"))
