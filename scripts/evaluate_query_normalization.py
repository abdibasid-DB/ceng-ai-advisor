"""Evaluate pre-retrieval query normalization against the 60-question set."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.query_understanding import QueryResolution, resolve_query


CASES_PATH = PROJECT_ROOT / "tests" / "rag_comprehensive_evaluation_cases.json"
DOMAIN_KINDS = {"standalone_domain_question", "contextual_follow_up", "source_follow_up"}
NEGATIVES = ["football", "cooking", "weather", "who won the match", "make me a cake"]


def load_original_cases() -> list[dict[str, Any]]:
    with CASES_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return [case for case in data["cases"] if case.get("case_kind") == "original"]


def typo_variant(question: str) -> str:
    replacements = {
        "Engineering": "Engneering",
        "engineering": "engneering",
        "Engineer": "Enginer",
        "engineer": "enginer",
        "Programming": "Programing",
        "programming": "programing",
        "language": "langauge",
        "learn": "lern",
        "mathematics": "math",
        "Mathematics": "Math",
    }
    variant = question
    for source, target in replacements.items():
        if source in variant:
            return variant.replace(source, target, 1)
    return question.lower().rstrip("?")


def informal_variant(question: str) -> str:
    variant = question.lower().rstrip("?")
    variant = variant.replace("computer engineering", "computer eng")
    variant = variant.replace("do i need", "i need")
    variant = variant.replace("should i", "i should")
    variant = variant.replace("can i", "can i")
    return variant


def short_variant(question: str) -> str:
    lowered = question.lower().rstrip("?")
    if "computer engineering" in lowered:
        return lowered.replace("computer engineering", "computer eng")
    if "programming" in lowered:
        return "programming language"
    if "mathematics" in lowered or "math" in lowered:
        return "how much math i need"
    if "ai" in lowered or "artificial intelligence" in lowered:
        return "computer eng ai"
    return lowered


def paraphrase_variant(question: str) -> str:
    lowered = question.lower().rstrip("?")
    if lowered.startswith("what is "):
        return f"can you explain {lowered[8:]}"
    if lowered.startswith("is "):
        return f"can you explain whether {lowered[3:]}"
    if lowered.startswith("what "):
        return f"tell me about {lowered[5:]}"
    if lowered.startswith("how "):
        return f"explain {lowered}"
    if lowered.startswith("can "):
        return f"tell me if {lowered[4:]}"
    return f"can you explain {lowered}"


def classify(question: str) -> QueryResolution:
    return resolve_query(question, previous_turn=None)


def evaluate() -> dict[str, Any]:
    cases = load_original_cases()
    buckets = {
        "original": [(case, case["question"]) for case in cases],
        "typo": [(case, typo_variant(case["question"])) for case in cases],
        "informal": [(case, informal_variant(case["question"])) for case in cases],
        "shorter": [(case, short_variant(case["question"])) for case in cases],
        "paraphrase": [(case, paraphrase_variant(case["question"])) for case in cases],
    }
    results: dict[str, Any] = {}
    for bucket, items in buckets.items():
        failures = []
        for case, question in items:
            resolution = classify(question)
            if resolution.kind not in DOMAIN_KINDS:
                failures.append(
                    {
                        "question_number": case["question_number"],
                        "variant": question,
                        "kind": resolution.kind,
                        "resolved_question": resolution.resolved_question,
                    }
                )
        results[bucket] = {
            "tested": len(items),
            "success": len(items) - len(failures),
            "success_rate": round((len(items) - len(failures)) / len(items), 3),
            "failures": failures,
        }

    false_matches = []
    for question in NEGATIVES:
        resolution = classify(question)
        if resolution.kind in DOMAIN_KINDS:
            false_matches.append(
                {
                    "question": question,
                    "kind": resolution.kind,
                    "resolved_question": resolution.resolved_question,
                }
            )
    results["dangerous_negatives"] = {
        "tested": len(NEGATIVES),
        "false_domain_matches": len(false_matches),
        "false_domain_match_rate": round(len(false_matches) / len(NEGATIVES), 3),
        "false_matches": false_matches,
    }
    return results


def main() -> None:
    print(json.dumps(evaluate(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
