"""Write report.md comparing before.json and after.json (run_questions.py) and the passage checks.

Usage: python docs/handwritten-removal-20261022/compare.py
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if hasattr(__import__("sys").stdout, "reconfigure"):
    __import__("sys").stdout.reconfigure(encoding="utf-8")
NOTES = {
    "programming_languages_passage": "src_126",
    "gpa_screening_passage": "src_127",
    "computer_engineering_definition_passage": "src_128",
    "future_technologies_passage": "src_129",
    "linux_operating_system_passage": "src_130",
    "specialization_areas_passage": "src_131",
}


def load(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def main() -> int:
    before = {row["key"]: row for row in load("before.json")}
    after = {row["key"]: row for row in load("after.json")}
    check_before, check_after = load("passage-check.json"), load("passage-check-after-notes.json")
    keys = [key for key in before if key in after]
    functions = sorted({name for key in keys for name in before[key]["built_for"]})

    def fallback(row: dict) -> bool:
        return any("replaced_with_" in warning for warning in row.get("answer_warnings") or [])

    lines = [
        "# Removing hand-written passages and answer templates (Part 2)",
        "",
        "Before: rag_pipeline.py with the six hand-written passage functions (augment_context_results) and the bounded_* answer templates, "
        "on the option-f index. After: those functions deleted; the passages that retrieval did not find on its own were added as curated "
        "verbatim source notes (src_126-src_131, build_curated_notes.py) and indexed. Both runs send the same 113 test questions "
        "(questions.json: every test-set question that triggered one of the removed functions) through POST /api/v1/chat with the "
        "local qwen2.5:3b; the follow-up rewrite is off in both. Answer texts are in before.json and after.json.",
        "",
        "## Rule check: is the right passage in the top 5 without the function?",
        "",
        "| Function | Triggering questions | Top-5 hit, index without notes | Decision | Top-5 hit with curated note |",
        "|---|---:|---:|---|---:|",
    ]
    for name, data in check_before.items():
        lines.append(
            f"| `{name}()` | {data['questions']} | {data['covered']}/{data['questions']} | "
            f"{'deleted' if data['decision'] == 'delete' else 'curated note ' + NOTES[name] + ', then deleted'} | "
            f"{check_after[name]['covered']}/{check_after[name]['questions']} |"
        )
    lines += [
        "",
        "Every function failed the rule on at least one triggering question, so each became a curated note. Some triggering questions are "
        "false triggers of the old keyword detectors (for example salary questions for the definition function); they count as misses here.",
        "",
        "The `bounded_*` templates (`bounded_verified_partial_answer`, `bounded_ai_replacement_answer`, `bounded_programming_language_answer`, "
        "`bounded_prior_programming_answer`, `bounded_git_github_answer`, `bounded_cybersecurity_pathway_answer`, `bounded_career_jobs_answer`, "
        "and the future-technology template inside `bounded_fallback_answer`) wrote fixed answer sentences around a retrieved label. "
        "They only fired when their evidence passage was already retrieved, so no source note was needed; they were deleted and the "
        "fallback is now only `extractive_partial_answer`, which quotes one retrieved sentence verbatim.",
        "",
        "## Live pipeline before and after",
        "",
    ]

    def summary(rows: list[dict]) -> dict:
        statuses = Counter(row["status"] for row in rows)
        return {
            "n": len(rows),
            "answered": statuses.get("answered", 0),
            "refused": statuses.get("insufficient_information", 0) + statuses.get("out_of_scope", 0),
            "template_or_fallback": sum(fallback(row) for row in rows),
            "seconds": round(statistics.mean(row["seconds"] for row in rows), 1),
        }

    lines += ["| Built for | n | Answered before → after | Refused before → after | Answer replaced by fallback before → after | Mean s before → after |", "|---|---:|---:|---:|---:|---:|"]
    for name in ["ALL", *functions]:
        selected = keys if name == "ALL" else [key for key in keys if name in before[key]["built_for"]]
        b, a = summary([before[key] for key in selected]), summary([after[key] for key in selected])
        label = "**All 113 questions**" if name == "ALL" else f"`{name}`"
        lines.append(
            f"| {label} | {b['n']} | {b['answered']} → {a['answered']} | {b['refused']} → {a['refused']} | "
            f"{b['template_or_fallback']} → {a['template_or_fallback']} | {b['seconds']} → {a['seconds']} |"
        )

    changed = [key for key in keys if before[key]["status"] != after[key]["status"]]
    lines += [
        "",
        "\"Answer replaced by fallback\" counts answers where the LLM output was discarded and a template (before) or the extractive quote (after) was returned.",
        "",
        f"## Questions whose status changed ({len(changed)})",
        "",
        "| Question | Built for | Before | After |",
        "|---|---|---|---|",
    ]
    for key in changed:
        b, a = before[key], after[key]
        lines.append(f"| {b['question']} | {', '.join(b['built_for'])} | {b['status']} | {a['status']} |")
    (HERE / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:60]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
