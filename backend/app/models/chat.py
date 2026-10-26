"""Pydantic models for the Stage 16 RAG chat API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


MAX_QUESTION_LENGTH = 500
MAX_SESSION_ID_LENGTH = 80

AnswerStatus = Literal["answered", "help", "insufficient_information", "out_of_scope", "error"]


class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=MAX_QUESTION_LENGTH,
        description="Computer Engineering student-advisor question.",
        examples=["What is Computer Engineering?"],
    )
    session_id: str | None = Field(
        default=None,
        max_length=MAX_SESSION_ID_LENGTH,
        description="Optional current chat session ID. Omit to start a backend session.",
    )
    reset_session: bool = Field(
        default=False,
        description="When true, clear the supplied session or start a fresh one before answering.",
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Question must not be empty or whitespace only.")
        return cleaned

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        return cleaned


class SourceResponse(BaseModel):
    source_id: str | None = None
    title: str | None = None
    source_name: str | None = None
    source_type: str | None = None
    url: str | None = None
    category: str | None = None
    best_similarity_score: float | None = None
    similarity_score: float | None = None
    supporting_chunk_ids: list[str | None] = Field(default_factory=list)
    evidence_labels: list[str | None] = Field(default_factory=list)
    section_headings: list[str | None] = Field(default_factory=list)
    supporting_passages: list[str] = Field(default_factory=list)


class RetrievedContextResponse(BaseModel):
    label: str | None = None
    chunk_id: str | None = None
    source_id: str | None = None
    title: str | None = None
    source_name: str | None = None
    source_type: str | None = None
    url: str | None = None
    category: str | None = None
    section_heading: str | None = None
    similarity_score: float | None = None
    distance: float | None = None
    passage: str | None = None
    passage_preview: str | None = None


class ChatResponse(BaseModel):
    session_id: str | None = None
    question: str
    status: AnswerStatus
    answer: str
    llm_called: bool = False
    example_questions: list[str] = Field(default_factory=list)
    answered_as: str | None = None
    sources: list[SourceResponse] = Field(default_factory=list)
    retrieved_context: list[RetrievedContextResponse] = Field(default_factory=list)
    retrieval_metadata: dict[str, Any] = Field(default_factory=dict)
    timing: dict[str, Any] = Field(default_factory=dict)
    citation_metadata: dict[str, Any] = Field(default_factory=dict)
    answer_warnings: list[str] = Field(default_factory=list)
    model: str | None = None
    error: str | None = None
