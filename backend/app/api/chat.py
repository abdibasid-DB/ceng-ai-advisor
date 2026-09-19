"""FastAPI routes exposing the existing local RAG pipeline."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..models.chat import ChatRequest, ChatResponse, RetrievedContextResponse, SourceResponse
from ..rag.rag_pipeline import ERROR, RAGPipeline
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
    conversation_context = build_conversation_context(session_id)
    try:
        result = pipeline.answer(request.question, conversation_context=conversation_context)
    except LocalLLMError:
        result = service_error_response(request.question, "Local LLM service is unavailable or timed out.")
    except Exception:
        result = service_error_response(request.question, "The local RAG service could not process the request.")

    record_turn(session_id, result.get("question") or request.question, result.get("status") or ERROR)
    response = build_chat_response(result, session_id=session_id)
    if response.status == ERROR:
        return JSONResponse(status_code=503, content=response.model_dump(mode="json"))
    return response


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
    rendered = [
        f"Previous user question {index}: {turn.question} (previous status: {turn.status})"
        for index, turn in enumerate(relevant_turns, start=1)
    ]
    return "\n".join(rendered)


def record_turn(session_id: str, question: str, status: str) -> None:
    cleaned = " ".join((question or "").split())
    if not cleaned:
        return
    with _session_lock:
        _sessions.setdefault(session_id, deque(maxlen=MAX_SESSION_TURNS)).append(ConversationTurn(cleaned, status))


def clear_all_sessions_for_tests() -> None:
    with _session_lock:
        _sessions.clear()


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
