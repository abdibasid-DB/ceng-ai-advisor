"""Before/after tables for the spec-question fixes.

Before: docs/final-evaluation-20261023 (full200 rows of the same groups, spec4)
and the paraphrase run of the exported previous commit. After: the runs of
run_spec_fix.py. Both sides are labelled again with the official classifier of
the working tree, because that classifier calls the pipeline's topic check,
which this change touches; the label recorded at run time is kept as
`recorded_label`.

Usage: python docs/spec-fix-20261023/compare.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.core.storage_config import prepare_evaluation_storage  # noqa: E402

DATA = prepare_evaluation_storage("spec-fix-20261023")
LABELS = [
    "correct_evidence_supported",
    "correct_insufficient_information",
    "incorrect_refusal_evidence_exists",
    "unsupported_incorrect_or_misleading",
    "runtime_error",
]
SHORT = ["Supported", "Correct refusal", "Incorrect refusal", "Unsupported", "Error"]
GROUPS = ["ai_future", "mathematics", "career_employment", "student_local", "programming_software", "multi_turn", "out_of_scope", "unsupported", "paraphrase"]

spec = importlib.util.spec_from_file_location("runner", ROOT / "docs/full-200-ceng-ai-advisor-evaluation-after-kb-ollama-20261013-202801/run_full_200_evaluation.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class Resolution:
    def __init__(self, kind, question):
        self.kind, self.resolved_question = kind, question


def relabel(row: dict) -> str:
    diagnostics = row["diagnostics"]
    result = {
        "status": diagnostics["status"],
        "answer": row.get("answer"),
        "retrieved_context": row.get("retrieved_context") or [],
        "retrieval_metadata": diagnostics.get("retrieval_metadata") or {},
        "citation_metadata": diagnostics.get("citation_metadata") or {},
    }
    if diagnostics["status"] == "error":
        return "runtime_error"
    return runner.classify_case(row, result, Resolution(diagnostics.get("query_kind"), diagnostics.get("resolved_question")))[0]


def load(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["results"] if isinstance(data, dict) else data


def main() -> None:
    after = load(DATA / "cases-after.json") + load(DATA / "paraphrase-after.json")
    after_ids = {row["id"] for row in after}
    before = [row for row in load(ROOT / "docs/final-evaluation-20261023/full200-results.json") if row["id"] in after_ids]
    before += load(DATA / "paraphrase-before.json")
    for row in before + after:
        row["recorded_label"] = row["evaluation_label"]
        row["evaluation_label"] = relabel(row)

    def counts(rows: list[dict], group: str) -> Counter:
        return Counter(row["evaluation_label"] for row in rows if group == "ALL" or row["group"] == group)

    lines = ["| Group | n | " + " | ".join(SHORT[:4]) + " |", "|---|---:|" + "---:|" * 4]
    for group in GROUPS + ["ALL"]:
        b, a = counts(before, group), counts(after, group)
        n = sum(a.values())
        cells = " | ".join(f"{b[label]} → {a[label]}" for label in LABELS[:4])
        lines.append(f"| {'**All**' if group == 'ALL' else group} | {n} | {cells} |")
    errors = counts(after, "ALL")["runtime_error"]
    lines.append("")
    lines.append(f"Runtime errors after: {errors}.")
    changes = ["", "| Case | Group | Before | After |", "|---|---|---|---|"]
    before_by_id = {row["id"]: row for row in before}
    for row in sorted(after, key=lambda row: row["id"]):
        old = before_by_id.get(row["id"])
        if old and old["evaluation_label"] != row["evaluation_label"]:
            changes.append(f"| {row['id']} | {row['group']} | {old['evaluation_label']} | {row['evaluation_label']} |")
    output = "\n".join(lines + changes)
    (DATA / "comparison.md").write_text(output, encoding="utf-8")
    (DATA / "relabelled.json").write_text(json.dumps({"before": before, "after": after}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
