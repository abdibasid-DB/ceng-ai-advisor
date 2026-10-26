"""Simulation A: ignore generic words when the topic-term check counts the question's topic terms.

Reads replay_topic_check.json (written by replay_topic_check.py) and reports which of the
25 topic-check refusals would pass. The 0.70 question-answer similarity fallback of the
check is kept.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
GENERIC = {"my", "mine", "your", "one", "but", "while", "until", "between", "too", "only", "next",
           "get", "take", "make", "makes", "mean", "include", "includes", "difference", "different"}

out = json.loads((HERE / "replay_topic_check.json").read_text(encoding="utf-8"))
passed = []
for row in out["refused"]:
    focus = set(row["focus"]) - GENERIC
    covered = set(row["covered_after_pruning"]) - GENERIC
    need = 2 if len(focus) >= 3 else 1
    ok = not focus or len(covered) >= need or (row["sim_after"] or 0) >= 0.70
    print(f"{row['id']:5} focus {sorted(focus)} covered {sorted(covered)} need {need} -> {'PASS' if ok else 'still refused'}")
    if ok:
        passed.append(row)
print(f"\n{len(passed)} of {len(out['refused'])} would pass")
for row in passed:
    print(f"\n{row['id']} {row['question']}\n  {row['final'][:400]}")
