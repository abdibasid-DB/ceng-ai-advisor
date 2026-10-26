"""Group the 46 wrong refusals (incorrect_refusal_evidence_exists) of the frozen full-200 run by the stage that refused.

Usage: python docs/refusal-analysis-20261026/group_refusals.py
"""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
rows = json.loads((ROOT / "docs/final-evaluation-20261025/full200-results.json").read_text(encoding="utf-8"))["results"]


def stage(row):
    diagnostics = row["diagnostics"]
    metadata = diagnostics.get("retrieval_metadata") or {}
    reason = metadata.get("unsupported_reason") or ""
    if not metadata.get("evidence_sufficient"):
        return "retrieval evidence gate"
    if not diagnostics["llm_called"]:
        return "answerability guard before generation"
    if "did not address" in reason:
        return "topic-term check after generation"
    if "could not be matched" in reason or "does not support" in reason:
        return "claim-support / citation validation"
    if reason:
        return f"other guard after generation: {reason}"
    return "model wrote INSUFFICIENT_INFORMATION"


for label in ("incorrect_refusal_evidence_exists", "correct_insufficient_information"):
    groups = collections.defaultdict(list)
    for row in rows:
        if row["evaluation_label"] == label:
            groups[stage(row)].append(row["id"])
    print(f"{label}: {sum(len(ids) for ids in groups.values())}")
    for name, ids in sorted(groups.items(), key=lambda item: -len(item[1])):
        print(f"  {len(ids):3} {name}: {' '.join(ids)}")
