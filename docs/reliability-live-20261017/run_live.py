"""Resumable live check through the browser streaming endpoint.

Every turn is sent to POST /api/v1/chat/stream exactly as the frontend does,
with real per-session conversation state and the local qwen2.5:3b Ollama model.
Storage follows backend/app/core/storage_config.py: the Chroma copy, temp files
and full results live on the data drive (D:), the run stops if C: runs low, and
only the finished results file is copied into this docs folder.

Usage: python docs/reliability-live-20261017/run_live.py [results-name] [ids,...]
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.api.chat import clear_all_sessions_for_tests, get_rag_pipeline  # noqa: E402
from backend.app.core.storage_config import (  # noqa: E402
    ensure_disk_space,
    evaluation_chroma_path,
    prepare_evaluation_storage,
)
from backend.app.main import app  # noqa: E402
from backend.app.rag.rag_pipeline import RAGPipeline  # noqa: E402
from backend.app.rag.retriever import Retriever  # noqa: E402

RESULTS_NAME = sys.argv[1] if len(sys.argv) > 1 else "results.json"
RESULTS = prepare_evaluation_storage("reliability-live") / RESULTS_NAME
ONLY = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None

# Each conversation is a list of turns sharing one session.
# expect: "answer" (evidence exists), "insufficient", "out_of_scope", "clarify".
CONVERSATIONS = [
    ("F001", [("What is Computer Engineering?", "answer")]),
    ("C019", [("Do students take electronics and digital logic?", "answer")]),
    ("C020", [("How much lab work is there in computer engineering?", "answer")]),
    ("M032", [("math scary, should i quit ceng?", "answer")]),
    ("P056", [("How important is command line usage?", "answer")]),
    ("A075", [("AI taking jobs, should I still study CENG?", "answer")]),
    ("R108", [("Can CENG graduates work abroad?", "answer")]),
    ("R120", [("What are entry-level computer engineering job titles?", "answer")]),
    ("S129", [("Which official regulation explains exams and grading?", "answer")]),
    ("X141", [("I like AI and cybersecurity but hate electronics; is CENG still a good choice and what should I learn first?", "answer")]),
    ("N002", [("Can I build an FPGA project before taking digital logic?", "answer")]),
    ("N004", [("What can a first-year student put in a GitHub portfolio for internships?", "answer")]),
    ("U153", [("What is the exact job placement rate of OSTIM CENG graduates in 2026?", "insufficient")]),
    ("N005", [("Does OSTIM Technical University guarantee a remote job abroad after graduation?", "insufficient")]),
    ("O166", [("How do I bake sourdough bread?", "out_of_scope")]),
    # Unseen informal / misspelled questions.
    ("Q01", [("wats the diffrence between computer enginering and software enginering?", "answer")]),
    ("Q02", [("hw do i get an internshp as a 2nd year ceng student", "answer")]),
    ("Q03", [("bro is data structures rly that important or nah", "answer")]),
    ("Q04", [("which programing languges shud i learn first for ceng", "answer")]),
    # Multi-turn follow-ups, including references to the previous answer.
    ("T184", [("I prefer hardware.", "answer"), ("What projects should I build?", "answer")]),
    ("T187", [("I want cybersecurity.", "answer"), ("Is Linux important too?", "answer")]),
    ("T188", [("Computer Engineering vs Computer Science?", "answer"), ("Which one has more hardware?", "answer")]),
    ("MT1", [
        ("What skills do I need for a career in embedded systems?", "answer"),
        ("can you explain the first one in more detail?", "answer"),
        ("what sources did you use for that?", "answer"),
    ]),
    ("MT2", [("Tell me about machine learning in computer engineering.", "answer"), ("what jobs use it?", "answer")]),
    ("V01", [("what about that thing you said?", "clarify")]),
    # Unseen questions written after the fixes, used only for verification.
    ("U01", [("is it ok if im bad at physics, does ceng need alot of it?", "answer")]),
    ("U02", [("What does a computer engineer do on a normal day at work?", "answer")]),
    ("U03", [("how do operating systems relate to what we learn in ceng", "answer")]),
    ("U04", [("Whats the tuition fee for CENG at OSTIM next year?", "insufficient")]),
    ("U05", [("Can you write my Python homework for me?", "out_of_scope")]),
    ("U06", [("What is a microcontroller and why do CENG students learn it?", "answer"), ("give me a project idea using it", "answer")]),
    ("U07", [("which is better for me, ai or cybersecurity?", "answer"), ("what sources did you use?", "answer")]),
    ("U08", [("does ceng have lots of coding or is it mostly theory", "answer")]),
    ("U09", [("Do I need a powerful laptop for computer engineering?", "answer")]),
]


def stream_turn(client: TestClient, question: str, session_id: str | None) -> tuple[dict, list[str], float]:
    started = time.perf_counter()
    events: list[str] = []
    final: dict = {}
    with client.stream("POST", "/api/v1/chat/stream", json={"question": question, "session_id": session_id}) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.strip():
                continue
            event = json.loads(line)
            events.append(event["event"])
            if event["event"] == "final":
                final = event["data"]
    return final, events, round(time.perf_counter() - started, 2)


def save(records: list[dict], complete: bool) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "complete": complete,
        "turn_count": len(records),
        "status_counts": {},
        "results": records,
    }
    for record in records:
        payload["status_counts"][record["status"]] = payload["status_counts"].get(record["status"], 0) + 1
    tmp = RESULTS.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(RESULTS)


def main() -> None:
    pipeline = RAGPipeline(retriever=Retriever(chroma_path=evaluation_chroma_path()))
    app.dependency_overrides[get_rag_pipeline] = lambda: pipeline
    clear_all_sessions_for_tests()
    client = TestClient(app)
    records = json.loads(RESULTS.read_text(encoding="utf-8"))["results"] if RESULTS.exists() else []
    done = {record["conversation"] for record in records}
    for conv_id, turns in CONVERSATIONS:
        if conv_id in done or (ONLY and conv_id not in ONLY):
            continue
        ensure_disk_space()
        session_id = f"live-{conv_id}-{int(time.time())}"
        conv_records = []
        for turn_index, (question, expect) in enumerate(turns, start=1):
            print(f"{conv_id} turn {turn_index}: {question}", flush=True)
            try:
                final, events, seconds = stream_turn(client, question, session_id)
            except Exception as exc:  # keep the run going and record the failure
                final, events, seconds = {"status": "runtime_error", "error": repr(exc)}, [], 0.0
            metadata = final.get("retrieval_metadata") or {}
            conv_records.append({
                "conversation": conv_id,
                "turn": turn_index,
                "question": question,
                "expect": expect,
                "status": final.get("status"),
                "answer": final.get("answer"),
                "error": final.get("error"),
                "events": events,
                "seconds": seconds,
                "query_kind": metadata.get("query_kind"),
                "resolved_question": metadata.get("resolved_question"),
                "unsupported_reason": metadata.get("unsupported_reason"),
                "answer_warnings": final.get("answer_warnings"),
                "cited_labels": (final.get("citation_metadata") or {}).get("cited_labels"),
                "sources": [s.get("title") for s in final.get("sources") or []],
                "context": [
                    {"label": c.get("label"), "title": c.get("title"), "section": c.get("section_heading"),
                     "passage": (c.get("passage") or "")[:700]}
                    for c in final.get("retrieved_context") or []
                ],
            })
            print(f"  -> {final.get('status')} ({seconds}s): {(final.get('answer') or '')[:160]}", flush=True)
        records.extend(conv_records)
        save(records, complete=False)
    save(records, complete=True)
    # The finished results file is small; keep a copy next to this script.
    (HERE / RESULTS_NAME).write_text(RESULTS.read_text(encoding="utf-8"), encoding="utf-8")
    print("done", flush=True)


if __name__ == "__main__":
    main()
