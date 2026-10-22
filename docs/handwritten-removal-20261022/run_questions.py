"""Run the questions the hand-written passages and answer templates were built for through the live API.

Questions: every test-set question (see check_passages.test_questions) that
triggers one of the removed passage functions or bounded_* answer templates.
Multi-turn cases from the 200-question set first send their previous question
in the same session. Each answer is sent through POST /api/v1/chat in-process,
so query understanding, retrieval, the local LLM and grounding all run.

Results are written to the evaluation data directory and copied here.

Usage: python docs/handwritten-removal-20261022/run_questions.py before|after
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(HERE)]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.core.storage_config import ensure_disk_space, prepare_evaluation_storage  # noqa: E402
from backend.app.main import app  # noqa: E402
from check_passages import test_questions  # noqa: E402

# Detectors copied from rag_pipeline.py before the removal, so the "after" run uses the same question list.
PASSAGE_TRIGGERS = {
    "programming_languages_passage": ("is_programming_language_question",),
    "gpa_screening_passage": ("is_gpa_project_question",),
    "computer_engineering_definition_passage": ("is_computer_engineering_definition_question",),
    "future_technologies_passage": ("is_future_technology_question",),
    "linux_operating_system_passage": ("is_linux_operating_system_question",),
    "specialization_areas_passage": ("is_specialization_question",),
}
QUESTIONS_PATH = HERE / "questions.json"


def select_questions() -> list[dict]:
    """Built once (before the removal) and then frozen in questions.json."""
    if QUESTIONS_PATH.exists():
        return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    from backend.app.rag import rag_pipeline as rp

    contains = rp.contains_any_term

    def verified_partial(q: str) -> bool:
        return bool(
            contains(q, ("what is computer engineering", "what is ceng"))
            or contains(q, ("how much lab work", "how many lab hours"))
            or ("fpga" in q and "digital logic" in q)
            or "which one has more hardware" in q
            or ("databases" in q and "operating systems" in q)
            or ("ai" in q and "linear algebra" in q and "probability" in q)
            or "cloud security" in q
            or (contains(q, ("command line", "command-line")) and "important" in q)
            or ("linux" in q and "important" in q)
        )

    triggers = {name: getattr(rp, detector) for name, (detector,) in PASSAGE_TRIGGERS.items()}
    triggers.update(
        {
            "bounded_verified_partial_answer": lambda q: verified_partial(q.lower()),
            "bounded_ai_replacement_answer": lambda q: "replace" in q.lower() and contains(q.lower(), ("ai", "artificial intelligence", "automation", "generative ai")),
            "bounded_programming_language_answer": rp.is_programming_language_question,
            "bounded_prior_programming_answer": rp.is_prior_programming_experience_question,
            "bounded_git_github_answer": rp.is_git_github_learning_question,
            "bounded_cybersecurity_pathway_answer": rp.cybersecurity_pathway_question,
            "bounded_career_jobs_answer": rp.is_career_jobs_question,
        }
    )
    previous = {
        case["id"]: case["previous_question"]
        for case in json.loads((ROOT / "docs" / "semantic-coverage-200-questions.json").read_text(encoding="utf-8"))["cases"]
    }
    selected = []
    for item in test_questions():
        names = [name for name, trigger in triggers.items() if trigger(item["question"])]
        if names:
            selected.append({**item, "previous_question": previous.get(item["id"]) if item["set"] == "full_200" else None, "built_for": names})
    QUESTIONS_PATH.write_text(json.dumps(selected, ensure_ascii=False, indent=1), encoding="utf-8")
    return selected


def ask(client: TestClient, question: str, session_id: str | None = None) -> dict:
    start = time.perf_counter()
    response = client.post("/api/v1/chat", json={"question": question, "session_id": session_id})
    body = response.json()
    body["_seconds"] = round(time.perf_counter() - start, 2)
    return body


def main() -> int:
    label = sys.argv[1]
    if label not in {"before", "after"}:
        raise SystemExit("usage: run_questions.py before|after")
    questions = select_questions()
    output_dir = prepare_evaluation_storage("handwritten-removal-20261022")
    output_path = output_dir / f"{label}.json"
    done = {}
    if output_path.exists():
        done = {row["key"]: row for row in json.loads(output_path.read_text(encoding="utf-8"))}

    # Part 2 compares the removal alone; the follow-up rewrite (Part 3) is evaluated separately.
    import backend.app.api.chat as chat_api

    chat_api.FOLLOW_UP_REWRITE_ENABLED = False
    client = TestClient(app)
    for index, item in enumerate(questions, start=1):
        key = f"{item['set']}|{item['id']}"
        if key in done:
            continue
        session_id = None
        if item.get("previous_question"):
            session_id = ask(client, item["previous_question"]).get("session_id")
        body = ask(client, item["question"], session_id)
        warnings = body.get("answer_warnings") or []
        done[key] = {
            "key": key,
            **item,
            "status": body.get("status"),
            "answer": body.get("answer"),
            "source_ids": [source.get("source_id") for source in body.get("sources") or []],
            "retrieved_chunk_ids": [item.get("chunk_id") for item in body.get("retrieved_context") or []],
            "answer_warnings": warnings,
            "fallback_used": any("replaced_with_" in warning for warning in warnings),
            "seconds": body["_seconds"],
        }
        output_path.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{index}/{len(questions)} {key} {done[key]['status']} {body['_seconds']}s", flush=True)
        ensure_disk_space()
    shutil.copy2(output_path, HERE / f"{label}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
