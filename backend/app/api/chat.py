"""FastAPI routes exposing the existing local RAG pipeline."""

from __future__ import annotations

import json
import re
from collections import deque
from dataclasses import dataclass
from collections.abc import Iterator
from threading import Lock
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from ..models.chat import ChatRequest, ChatResponse, RetrievedContextResponse, SourceResponse
from ..query_understanding import (
    QueryResolution,
    previous_turn_has_domain_context,
    refers_to_previous_answer,
    resolve_query,
)
from ..rag.rag_pipeline import ANSWERED, ERROR, INSUFFICIENT_INFORMATION, OUT_OF_SCOPE, RAGPipeline
from ..services.llm_service import LocalLLMError


router = APIRouter(prefix="/api/v1", tags=["rag-chat"])
_pipeline_lock = Lock()
_pipeline: RAGPipeline | None = None
_session_lock = Lock()
_sessions: dict[str, deque["ConversationTurn"]] = {}
MAX_SESSION_TURNS = 8
CONTEXT_TURNS = 3


@dataclass(frozen=True)
class ConversationTurn:
    question: str
    status: str
    answer: str = ""
    sources: tuple[dict[str, Any], ...] = ()
    retrieved_context: tuple[dict[str, Any], ...] = ()
    citation_metadata: dict[str, Any] | None = None


def get_rag_pipeline() -> RAGPipeline:
    """Reuse expensive local RAG components across API requests."""
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                _pipeline = RAGPipeline()
    return _pipeline


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, pipeline: RAGPipeline = Depends(get_rag_pipeline)):
    """Answer a student-advisor question using the local Stage 15C RAG pipeline."""
    session_id = prepare_session(request.session_id, reset=request.reset_session)
    previous_turn = last_context_turn(session_id)
    resolution = resolve_query(request.question, previous_turn)

    if resolution.kind == "source_follow_up" and latest_turn_was_unsourced(session_id):
        result = unsourced_previous_turn_response(request.question)
        response = build_chat_response(attach_resolution_metadata(result, resolution), session_id=session_id)
        record_turn(session_id, result)
        return response

    if resolution.kind == "source_follow_up" and last_answered_turn(session_id):
        result = previous_source_response(request.question, last_answered_turn(session_id))
        result = attach_resolution_metadata(result, resolution)
        response = build_chat_response(result, session_id=session_id)
        record_turn(session_id, result)
        return response

    if resolution.kind == "source_follow_up":
        result = unresolved_follow_up_response(request.question, "I do not have a previous sourced answer in this session to cite.")
        return build_chat_response(attach_resolution_metadata(result, resolution), session_id=session_id)

    if resolution.kind == "vague_no_referent":
        result = unresolved_follow_up_response(
            request.question,
            "I am not sure which previous topic or information you are referring to. Please ask a complete question about Computer Engineering.",
        )
        result = attach_resolution_metadata(result, resolution)
        response = build_chat_response(result, session_id=session_id)
        record_turn(session_id, result)
        return response

    if resolution.kind == "out_of_scope_persona_meta":
        result = out_of_scope_response(request.question)
        result = attach_resolution_metadata(result, resolution)
        response = build_chat_response(result, session_id=session_id)
        record_turn(session_id, result)
        return response

    conversation_context = build_resolution_context(resolution)
    try:
        result = pipeline.answer(
            request.question,
            conversation_context=conversation_context,
            resolved_question=resolution.resolved_question,
        )
        result = attach_resolution_metadata(result, resolution)
    except LocalLLMError:
        result = service_error_response(request.question, "Local LLM service is unavailable or timed out.")
    except Exception:
        result = service_error_response(request.question, "The local RAG service could not process the request.")

    record_turn(session_id, result)
    response = build_chat_response(result, session_id=session_id)
    if response.status == ERROR:
        return JSONResponse(status_code=503, content=response.model_dump(mode="json"))
    return response


@router.post("/chat/stream")
def chat_stream(request: ChatRequest, pipeline: RAGPipeline = Depends(get_rag_pipeline)):
    """Stream a RAG answer as real Ollama generation chunks plus final metadata."""
    session_id = prepare_session(request.session_id, reset=request.reset_session)

    def events() -> Iterator[str]:
        previous_turn = last_context_turn(session_id)
        resolution = resolve_query(request.question, previous_turn)

        if resolution.kind == "source_follow_up" and latest_turn_was_unsourced(session_id):
            result = unsourced_previous_turn_response(request.question)
            response = build_chat_response(attach_resolution_metadata(result, resolution), session_id=session_id)
            record_turn(session_id, result)
            yield encode_stream_event("final", response.model_dump(mode="json"))
            return

        if resolution.kind == "source_follow_up" and last_answered_turn(session_id):
            result = previous_source_response(request.question, last_answered_turn(session_id))
            result = attach_resolution_metadata(result, resolution)
            response = build_chat_response(result, session_id=session_id)
            record_turn(session_id, result)
            yield encode_stream_event("final", response.model_dump(mode="json"))
            return

        if resolution.kind == "source_follow_up":
            result = unresolved_follow_up_response(request.question, "I do not have a previous sourced answer in this session to cite.")
            response = build_chat_response(attach_resolution_metadata(result, resolution), session_id=session_id)
            yield encode_stream_event("final", response.model_dump(mode="json"))
            return

        if resolution.kind == "vague_no_referent":
            result = unresolved_follow_up_response(
                request.question,
                "I am not sure which previous topic or information you are referring to. Please ask a complete question about Computer Engineering.",
            )
            result = attach_resolution_metadata(result, resolution)
            response = build_chat_response(result, session_id=session_id)
            record_turn(session_id, result)
            yield encode_stream_event("final", response.model_dump(mode="json"))
            return

        if resolution.kind == "out_of_scope_persona_meta":
            result = out_of_scope_response(request.question)
            result = attach_resolution_metadata(result, resolution)
            response = build_chat_response(result, session_id=session_id)
            record_turn(session_id, result)
            yield encode_stream_event("final", response.model_dump(mode="json"))
            return

        conversation_context = build_resolution_context(resolution)
        try:
            for event in pipeline.answer_stream(
                request.question,
                conversation_context=conversation_context,
                resolved_question=resolution.resolved_question,
            ):
                event_type = event.get("event")
                if event_type == "final":
                    result = event.get("result") or service_error_response(
                        request.question,
                        "The local RAG stream did not produce a final result.",
                    )
                    result = attach_resolution_metadata(result, resolution)
                    response = build_chat_response(result, session_id=session_id)
                    if response.status != ERROR:
                        record_turn(session_id, result)
                    yield encode_stream_event("final", response.model_dump(mode="json"))
                    return
                if event_type == "token":
                    yield encode_stream_event("token", {"text": event.get("text") or ""})
                elif event_type == "metadata":
                    yield encode_stream_event(
                        "metadata",
                        {
                            "session_id": session_id,
                            "retrieval_metadata": event.get("retrieval_metadata") or {},
                            "retrieved_context": event.get("retrieved_context") or [],
                            "llm_called": bool(event.get("llm_called")),
                        },
                    )
        except GeneratorExit:
            return
        except LocalLLMError:
            result = service_error_response(request.question, "Local LLM service is unavailable or timed out.")
            response = build_chat_response(result, session_id=session_id)
            yield encode_stream_event("final", response.model_dump(mode="json"))
        except Exception:
            result = service_error_response(request.question, "The local RAG service could not process the streaming request.")
            response = build_chat_response(result, session_id=session_id)
            yield encode_stream_event("final", response.model_dump(mode="json"))

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/readiness")
def readiness(pipeline: RAGPipeline = Depends(get_rag_pipeline)) -> dict[str, Any]:
    """Lightweight component check that avoids full RAG generation."""
    vector_store = {"available": False, "collection_count": None, "error": None}
    ollama = {"available": False, "model": getattr(pipeline.llm_service, "model", None), "error": None}

    try:
        vector_store["collection_count"] = pipeline.retriever.collection_count
        vector_store["available"] = True
    except Exception:
        vector_store["error"] = "Vector store is not available."

    try:
        ollama["available"] = pipeline.llm_service.model_available()
    except Exception:
        ollama["error"] = "Local Ollama service is not available."

    return {
        "status": "ready" if vector_store["available"] and ollama["available"] else "degraded",
        "backend": "healthy",
        "vector_store": vector_store,
        "ollama": ollama,
    }


def prepare_session(session_id: str | None, *, reset: bool = False) -> str:
    active_session_id = session_id or uuid4().hex
    with _session_lock:
        if reset or active_session_id not in _sessions:
            _sessions[active_session_id] = deque(maxlen=MAX_SESSION_TURNS)
    return active_session_id


def build_conversation_context(session_id: str) -> str | None:
    with _session_lock:
        turns = list(_sessions.get(session_id, ()))
    relevant_turns = [turn for turn in turns if turn.status != ERROR][-CONTEXT_TURNS:]
    if not relevant_turns:
        return None
    rendered = []
    for index, turn in enumerate(relevant_turns, start=1):
        rendered.append(f"Previous user question {index}: {turn.question} (previous status: {turn.status})")
        if turn.answer:
            rendered.append(f"Previous assistant answer {index}: {turn.answer}")
    return "\n".join(rendered)


def build_resolution_context(resolution: QueryResolution) -> str | None:
    if resolution.kind != "contextual_follow_up" or not resolution.previous_turn:
        return None
    rendered = f"Previous user question: {resolution.previous_turn.question}\n"
    previous_answer = ""
    if refers_to_previous_answer(resolution.question, resolution.previous_turn):
        previous_answer = previous_answer_summary(resolution.previous_turn)
    if previous_answer:
        rendered += f"Previous assistant answer (not evidence): {previous_answer}\n"
    return rendered + f"Resolved current question for retrieval: {resolution.resolved_question}"


def previous_answer_summary(turn: ConversationTurn, max_characters: int = 300) -> str:
    """Trimmed previous answer so the model can resolve "that" or "the first one".

    Citation labels are removed because they refer to the previous turn's
    evidence, not to the passages supplied for the current answer.
    """
    if turn.status != ANSWERED or not turn.answer:
        return ""
    text = " ".join(re.sub(r"\[S\d+\]", "", turn.answer).split())
    if len(text) <= max_characters:
        return text
    return text[: max_characters - 3].rsplit(" ", 1)[0] + "..."


def record_turn(session_id: str, result: dict[str, Any]) -> None:
    cleaned = " ".join((result.get("question") or "").split())
    if not cleaned:
        return
    answer = " ".join((result.get("answer") or "").split())
    with _session_lock:
        _sessions.setdefault(session_id, deque(maxlen=MAX_SESSION_TURNS)).append(
            ConversationTurn(
                question=cleaned,
                status=result.get("status") or ERROR,
                answer=answer,
                sources=tuple(result.get("sources") or ()),
                retrieved_context=tuple(result.get("retrieved_context") or ()),
                citation_metadata=result.get("citation_metadata") or {},
            )
        )


def last_answered_turn(session_id: str) -> ConversationTurn | None:
    with _session_lock:
        turns = list(_sessions.get(session_id, ()))
    for turn in reversed(turns):
        if turn.status == ANSWERED and (turn.sources or turn.retrieved_context):
            return turn
    return None


def latest_turn_was_unsourced(session_id: str) -> bool:
    """True when the most recent reply was a refusal, so "that" has no sources.

    Without this check a source request after a refusal would report the
    sources of an older, unrelated answer.
    """
    with _session_lock:
        turns = [turn for turn in _sessions.get(session_id, ()) if turn.status != ERROR]
    return bool(turns) and turns[-1].status in {INSUFFICIENT_INFORMATION, OUT_OF_SCOPE}


def unsourced_previous_turn_response(question: str) -> dict[str, Any]:
    return unresolved_follow_up_response(
        question,
        "My previous reply did not use any sources, because I did not have enough reliable information in my "
        "knowledge base to answer that question.",
    )


def last_context_turn(session_id: str) -> ConversationTurn | None:
    with _session_lock:
        turns = list(_sessions.get(session_id, ()))
    for turn in reversed(turns):
        if previous_turn_has_domain_context(turn):
            return turn
    return None


def unresolved_follow_up_response(question: str, answer: str) -> dict[str, Any]:
    return {
        "question": " ".join((question or "").split()),
        "status": INSUFFICIENT_INFORMATION,
        "answer": answer,
        "llm_called": False,
        "sources": [],
        "retrieved_context": [],
        "retrieval_metadata": {"unresolved_follow_up": True, "evidence_sufficient": False},
        "timing": {},
        "citation_metadata": {},
        "answer_warnings": [],
        "model": None,
        "error": None,
    }


def out_of_scope_response(question: str) -> dict[str, Any]:
    return {
        "question": " ".join((question or "").split()),
        "status": OUT_OF_SCOPE,
        "answer": (
            "I am a Computer Engineering student advisor. I can help with Computer Engineering education, "
            "curriculum, courses, skills, careers, internships, AI, cybersecurity, programming, and related study paths."
        ),
        "llm_called": False,
        "sources": [],
        "retrieved_context": [],
        "retrieval_metadata": {"classified_out_of_scope": True, "evidence_sufficient": False, "out_of_scope": True},
        "timing": {},
        "citation_metadata": {},
        "answer_warnings": [],
        "model": None,
        "error": None,
    }


def attach_resolution_metadata(result: dict[str, Any], resolution: QueryResolution) -> dict[str, Any]:
    metadata = dict(result.get("retrieval_metadata") or {})
    if resolution.resolved_question:
        metadata["resolved_question"] = resolution.resolved_question
    metadata["query_kind"] = resolution.kind
    if resolution.normalization_metadata:
        metadata["query_normalization"] = resolution.normalization_metadata
    return {**result, "retrieval_metadata": metadata}


def previous_source_response(question: str, previous_turn: ConversationTurn) -> dict[str, Any]:
    cited = set((previous_turn.citation_metadata or {}).get("cited_labels") or ())
    sources = [source for source in previous_turn.sources if not cited or cited.intersection(source.get("evidence_labels") or ())]
    titles = [source.get("title") or source.get("source_name") for source in sources]
    answer = "The previous answer cited " + "; ".join(title for title in titles if title) + "."
    return {
        "question": " ".join((question or "").split()),
        "status": ANSWERED,
        "answer": answer,
        "llm_called": False,
        "sources": sources,
        "retrieved_context": [item for item in previous_turn.retrieved_context if not cited or item.get("label") in cited],
        "retrieval_metadata": {
            "used_previous_answer_sources": True,
            "evidence_sufficient": True,
        },
        "timing": {},
        "citation_metadata": previous_turn.citation_metadata or {},
        "answer_warnings": [],
        "model": None,
        "error": None,
    }


def clear_all_sessions_for_tests() -> None:
    with _session_lock:
        _sessions.clear()


def encode_stream_event(event: str, data: dict[str, Any]) -> str:
    return json.dumps({"event": event, "data": data}, ensure_ascii=False) + "\n"


def build_chat_response(result: dict[str, Any], session_id: str | None = None) -> ChatResponse:
    context_items = normalize_context_items(result.get("retrieved_context", []))
    sources = enrich_sources(result.get("sources", []), context_items)
    return ChatResponse(
        session_id=session_id,
        question=result.get("question") or "",
        status=result.get("status") or ERROR,
        answer=result.get("answer") or "",
        llm_called=bool(result.get("llm_called")),
        sources=sources,
        retrieved_context=[RetrievedContextResponse(**item) for item in context_items],
        retrieval_metadata=result.get("retrieval_metadata") or {},
        timing=result.get("timing") or {},
        citation_metadata=result.get("citation_metadata") or {},
        answer_warnings=result.get("answer_warnings") or [],
        model=result.get("model"),
        error=safe_error_message(result.get("error")),
    )


def normalize_context_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items or []:
        normalized.append(
            {
                "label": item.get("label"),
                "chunk_id": item.get("chunk_id"),
                "source_id": item.get("source_id"),
                "title": item.get("title"),
                "source_name": item.get("source_name"),
                "source_type": item.get("source_type") or item.get("metadata", {}).get("source_type"),
                "url": item.get("url"),
                "category": item.get("category"),
                "section_heading": item.get("section_heading"),
                "similarity_score": item.get("similarity_score"),
                "distance": item.get("distance"),
                "passage": item.get("passage"),
                "passage_preview": item.get("passage_preview"),
            }
        )
    return normalized


def enrich_sources(sources: list[dict[str, Any]], context_items: list[dict[str, Any]]) -> list[SourceResponse]:
    context_by_label = {item.get("label"): item for item in context_items if item.get("label")}
    responses: list[SourceResponse] = []
    for source in sources or []:
        labels = list(source.get("evidence_labels") or [])
        matching_context = [context_by_label[label] for label in labels if label in context_by_label]
        responses.append(
            SourceResponse(
                source_id=source.get("source_id"),
                title=source.get("title"),
                source_name=source.get("source_name"),
                source_type=source.get("source_type"),
                url=source.get("url"),
                category=source.get("category"),
                best_similarity_score=source.get("best_similarity_score"),
                similarity_score=source.get("best_similarity_score"),
                supporting_chunk_ids=list(source.get("supporting_chunk_ids") or []),
                evidence_labels=labels,
                section_headings=[item.get("section_heading") for item in matching_context if item.get("section_heading")],
                supporting_passages=[item.get("passage") for item in matching_context if item.get("passage")],
            )
        )
    return responses


def service_error_response(question: str, message: str) -> dict[str, Any]:
    return {
        "question": question,
        "status": ERROR,
        "answer": "The local RAG pipeline could not complete the request safely.",
        "llm_called": False,
        "sources": [],
        "retrieved_context": [],
        "retrieval_metadata": {},
        "timing": {},
        "citation_metadata": {},
        "answer_warnings": [],
        "model": None,
        "error": message,
    }


def safe_error_message(error: Any) -> str | None:
    if not error:
        return None
    text = str(error)
    if len(text) > 240:
        return text[:237].rstrip() + "..."
    return text
