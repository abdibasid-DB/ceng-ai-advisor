"""Pydantic models for safe public source metadata."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PublicSource(BaseModel):
    source_id: str
    title: str
    source_name: str
    source_type: str
    url: str | None = None
    publication_date: str | None = None
    date_added: str | None = None
    category: str
    language: str
    indexed_in_rag: bool = False


class SourcesResponse(BaseModel):
    count: int
    indexed_count: int = 0
    categories: list[str] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)
    sources: list[PublicSource] = Field(default_factory=list)
