"""Public source-registry endpoint for the website references page."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from ..models.sources import PublicSource, SourcesResponse


router = APIRouter(prefix="/api/v1", tags=["source-registry"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCES_REGISTRY_PATH = PROJECT_ROOT / "knowledge_base" / "sources.json"
CHUNKS_PATH = PROJECT_ROOT / "knowledge_base" / "chunks" / "chunks.jsonl"
SAFE_SOURCE_FIELDS = {
    "source_id",
    "title",
    "source_name",
    "source_type",
    "url",
    "publication_date",
    "date_added",
    "category",
    "language",
    "indexed_in_rag",
}


@router.get("/sources", response_model=SourcesResponse)
def list_sources() -> SourcesResponse:
    """Return safe public metadata from the approved source registry."""
    try:
        registry = load_source_registry(SOURCES_REGISTRY_PATH)
        indexed_source_ids = load_indexed_source_ids(CHUNKS_PATH)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="The source registry is currently unavailable.") from exc

    sources = [PublicSource(**safe_source_fields(source, indexed_source_ids)) for source in registry]
    categories = sorted({source.category for source in sources})
    source_types = sorted({source.source_type for source in sources})
    indexed_count = sum(1 for source in sources if source.indexed_in_rag)
    return SourcesResponse(
        count=len(sources),
        indexed_count=indexed_count,
        categories=categories,
        source_types=source_types,
        sources=sources,
    )


def load_source_registry(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    sources = data.get("sources")
    if not isinstance(sources, list):
        raise ValueError("Source registry must contain a sources list.")
    return sources


def load_indexed_source_ids(path: Path) -> set[str]:
    indexed_source_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            record = json.loads(line)
            source_id = record.get("source_id")
            if source_id:
                indexed_source_ids.add(source_id)
    return indexed_source_ids


def safe_source_fields(source: dict[str, Any], indexed_source_ids: set[str]) -> dict[str, Any]:
    fields = {field: source.get(field) for field in SAFE_SOURCE_FIELDS}
    fields["date_added"] = source.get("date_accessed")
    fields["indexed_in_rag"] = source.get("source_id") in indexed_source_ids
    return fields
