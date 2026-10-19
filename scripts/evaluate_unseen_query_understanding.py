"""Evaluate query understanding on unseen student-advisor scenarios."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.query_understanding import understand_query


CASES: list[dict[str, Any]] = [
    {
        "id": "cv_first_year",
        "question": "what should I put on my CV as a first year student",
        "expected_kind": "standalone_domain_question",
        "required_topics": ["cv"],
    },
    {
        "id": "laptop",
        "question": "should i buy a laptop before starting computer engineering",
        "expected_kind": "standalone_domain_question",
        "required_topics": ["laptop", "computer_engineering"],
    },
    {
        "id": "erasmus",
        "question": "can computer engineering students do erasmus",
        "expected_kind": "standalone_domain_question",
        "required_topics": ["computer_engineering", "erasmus"],
    },
    {
        "id": "ai_cybersecurity_electives",
        "question": "what electives should I choose if I like cybersecurity and AI?",
        "expected_kind": "standalone_domain_question",
        "required_topics": ["electives", "cybersecurity", "ai"],
    },
    {
        "id": "internship_gpa_projects",
        "question": "my GPA is low but I have projects, can I still get an internship?",
        "expected_kind": "standalone_domain_question",
        "required_topics": ["gpa", "projects", "internships"],
        "required_constraints": ["low_gpa"],
    },
    {
        "id": "interview_prep",
        "question": "how can I prepare for interviews as a computer engineering student",
        "expected_kind": "standalone_domain_question",
        "required_topics": ["interviews", "computer_engineering"],
    },
    {
        "id": "typo_definition",
        "question": "what is computer engneering",
        "expected_kind": "standalone_domain_question",
        "required_topics": ["computer_engineering", "definition"],
    },
    {
        "id": "informal_ai_language",
        "question": "which programing language good for ai",
        "expected_kind": "standalone_domain_question",
        "required_topics": ["programming", "ai"],
    },
    {
        "id": "bad_grammar_no_internship",
        "question": "i dont have internship what should i do",
        "expected_kind": "standalone_domain_question",
        "required_topics": ["internships"],
    },
    {
        "id": "vague_no_referent",
        "question": "what about that",
        "expected_kind": "vague_no_referent",
        "required_topics": [],
    },
    {
        "id": "football",
        "question": "football transfer news",
        "expected_kind": "out_of_scope_persona_meta",
        "required_topics": [],
    },
    {
        "id": "weather",
        "question": "what is the weather today",
        "expected_kind": "out_of_scope_persona_meta",
        "required_topics": [],
    },
]


def evaluate() -> dict[str, Any]:
    failures = []
    cases = []
    for case in CASES:
        understanding = understand_query(case["question"])
        topics = {topic.name for topic in understanding.topics}
        missing_topics = sorted(set(case.get("required_topics", [])) - topics)
        missing_constraints = sorted(set(case.get("required_constraints", [])) - set(understanding.constraints))
        passed = (
            understanding.kind == case["expected_kind"]
            and not missing_topics
            and not missing_constraints
        )
        record = {
            "id": case["id"],
            "question": case["question"],
            "expected_kind": case["expected_kind"],
            "actual_kind": understanding.kind,
            "topics": sorted(topics),
            "missing_topics": missing_topics,
            "constraints": list(understanding.constraints),
            "missing_constraints": missing_constraints,
            "retrieval_question": understanding.retrieval_question,
            "passed": passed,
        }
        cases.append(record)
        if not passed:
            failures.append(record)
    return {
        "tested": len(CASES),
        "passed": len(CASES) - len(failures),
        "success_rate": round((len(CASES) - len(failures)) / len(CASES), 3),
        "failures": failures,
        "cases": cases,
    }


def main() -> None:
    print(json.dumps(evaluate(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
