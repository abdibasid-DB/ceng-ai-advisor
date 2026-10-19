"""Compare this full-200 run with the previous official run, case by case.

Usage: python docs/full-200-evaluation-20261018-reliability/compare.py [new-results.json]
Writes comparison.json and comparison.md next to this script.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE = ROOT / "docs" / "full-200-ceng-ai-advisor-evaluation-after-kb-ollama-20261013-202801" / "results.json"
NEW = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "results.json"

LABELS = (
    "correct_evidence_supported",
    "correct_insufficient_information",
    "incorrect_refusal_evidence_exists",
    "unsupported_incorrect_or_misleading",
    "runtime_error",
)
GOOD = {"correct_evidence_supported", "correct_insufficient_information"}


def load(path: Path) -> dict[str, dict]:
    return {row["id"]: row for row in json.loads(path.read_text(encoding="utf-8"))["results"]}


def main() -> None:
    before, after = load(BASELINE), load(NEW)
    shared = sorted(set(before) & set(after))
    counts_before = Counter(before[i]["evaluation_label"] for i in shared)
    counts_after = Counter(after[i]["evaluation_label"] for i in shared)
    transitions = Counter((before[i]["evaluation_label"], after[i]["evaluation_label"]) for i in shared)
    categories = sorted({before[i]["group"] for i in shared})
    by_category = {}
    for category in categories:
        ids = [i for i in shared if before[i]["group"] == category]
        by_category[category] = {
            "total": len(ids),
            "good_before": sum(before[i]["evaluation_label"] in GOOD for i in ids),
            "good_after": sum(after[i]["evaluation_label"] in GOOD for i in ids),
        }
    regressions = [
        {"id": i, "question": after[i]["question"], "before": before[i]["evaluation_label"], "after": after[i]["evaluation_label"]}
        for i in shared
        if before[i]["evaluation_label"] in GOOD and after[i]["evaluation_label"] not in GOOD
    ]
    answered_after = [after[i] for i in shared if (after[i].get("diagnostics") or {}).get("status") == "answered"]
    latency = [after[i].get("elapsed_wall_seconds") or 0 for i in shared]
    output = {
        "baseline": str(BASELINE.relative_to(ROOT)),
        "new": str(NEW),
        "case_count": len(shared),
        "labels_before": {label: counts_before.get(label, 0) for label in LABELS},
        "labels_after": {label: counts_after.get(label, 0) for label in LABELS},
        "transitions": {f"{a} -> {b}": n for (a, b), n in transitions.most_common()},
        "by_category": by_category,
        "regressions": regressions,
        "answered_after": len(answered_after),
        "mean_latency_after_seconds": round(sum(latency) / max(len(latency), 1), 2),
    }
    (HERE / "comparison.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Full 200-question evaluation: before vs after reliability fixes",
        "",
        f"Baseline: `{output['baseline']}` (generated 2026-10-16). Same dataset, runner and automated classifier.",
        "",
        "| Label | Before | After | Change |",
        "|---|---:|---:|---:|",
    ]
    for label in LABELS:
        b, a = output["labels_before"][label], output["labels_after"][label]
        lines.append(f"| {label} | {b} | {a} | {a - b:+d} |")
    lines += ["", "## By category (correct = supported answer or correct refusal)", "", "| Category | Total | Before | After |", "|---|---:|---:|---:|"]
    for category, row in by_category.items():
        lines.append(f"| {category} | {row['total']} | {row['good_before']} | {row['good_after']} |")
    lines += ["", f"## Regressions ({len(regressions)})", ""]
    lines += [f"- {r['id']}: {r['question']} ({r['before']} -> {r['after']})" for r in regressions] or ["- none"]
    lines += ["", "## Label transitions", ""]
    lines += [f"- {key}: {n}" for key, n in output["transitions"].items()]
    lines += ["", f"Mean wall-clock latency after: {output['mean_latency_after_seconds']} s per case."]
    (HERE / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
