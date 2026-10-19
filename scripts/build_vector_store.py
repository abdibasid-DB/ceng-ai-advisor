"""Build the local ChromaDB vector store for Stage 12.

This script indexes existing chunk embeddings into a persistent local ChromaDB
collection. It does not regenerate document embeddings, create RAG logic,
integrate Ollama, or implement chatbot/API/frontend features.
"""

from __future__ import annotations

import json
import shutil
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = PROJECT_ROOT / "knowledge_base" / "chunks" / "chunks.jsonl"
EMBEDDINGS_PATH = PROJECT_ROOT / "knowledge_base" / "embeddings" / "embeddings.npy"
EMBEDDING_METADATA_PATH = PROJECT_ROOT / "knowledge_base" / "embeddings" / "embedding_metadata.jsonl"
EMBEDDING_MANIFEST_PATH = PROJECT_ROOT / "knowledge_base" / "embeddings" / "embedding_manifest.json"
SOURCES_PATH = PROJECT_ROOT / "knowledge_base" / "sources.json"
VECTOR_STORE_ROOT = PROJECT_ROOT / "knowledge_base" / "vector_store"
CHROMA_PATH = VECTOR_STORE_ROOT / "chroma"
MANIFEST_PATH = VECTOR_STORE_ROOT / "vector_store_manifest.json"

COLLECTION_NAME = "ceng_advisor_chunks"
DISTANCE_METRIC = "cosine"
EXPECTED_DIMENSION = 384
BATCH_SIZE = 200

METADATA_FIELDS = [
    "source_id",
    "chunk_index",
    "title",
    "source_name",
    "source_type",
    "url",
    "publication_date",
    "category",
    "language",
    "processed_file_path",
    "section_heading",
    "word_count",
    "character_count",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def safe_metadata_value(value: Any) -> str | int | float | bool:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, ensure_ascii=False)


def build_metadata(chunk: dict[str, Any]) -> dict[str, str | int | float | bool]:
    return {field: safe_metadata_value(chunk.get(field)) for field in METADATA_FIELDS}


def validate_inputs(
    chunks: list[dict[str, Any]],
    embeddings: np.ndarray,
    embedding_metadata: list[dict[str, Any]],
    approved_source_ids: set[str],
    expected_chunks: int,
    expected_dimension: int,
) -> dict[str, Any]:
    sorted_chunks = sorted(chunks, key=lambda item: (item["source_id"], item["chunk_index"], item["chunk_id"]))
    chunk_ids = [chunk["chunk_id"] for chunk in sorted_chunks]
    metadata_chunk_ids = [item["chunk_id"] for item in sorted(embedding_metadata, key=lambda item: item["embedding_index"])]
    source_ids = {chunk["source_id"] for chunk in sorted_chunks}

    validation = {
        "chunk_count": len(sorted_chunks),
        "embedding_count": int(embeddings.shape[0]) if embeddings.ndim == 2 else 0,
        "embedding_dimension": int(embeddings.shape[1]) if embeddings.ndim == 2 else 0,
        "metadata_count": len(embedding_metadata),
        "chunk_id_duplicates": len(chunk_ids) - len(set(chunk_ids)),
        "mapping_order_matches": chunk_ids == metadata_chunk_ids,
        "all_sources_approved": source_ids.issubset(approved_source_ids),
        "unknown_source_ids": sorted(source_ids - approved_source_ids),
        "nan_value_count": int(np.isnan(embeddings).sum()) if embeddings.ndim == 2 else None,
        "infinite_value_count": int(np.isinf(embeddings).sum()) if embeddings.ndim == 2 else None,
    }

    problems = []
    if validation["chunk_count"] != expected_chunks:
        problems.append(f"expected {expected_chunks} chunks, found {validation['chunk_count']}")
    if validation["embedding_count"] != expected_chunks:
        problems.append(f"expected {expected_chunks} embeddings, found {validation['embedding_count']}")
    if validation["metadata_count"] != expected_chunks:
        problems.append(f"expected {expected_chunks} metadata records, found {validation['metadata_count']}")
    if validation["embedding_dimension"] != expected_dimension:
        problems.append(f"expected embedding dimension {expected_dimension}, found {validation['embedding_dimension']}")
    if validation["chunk_id_duplicates"]:
        problems.append("duplicate chunk IDs found")
    if not validation["mapping_order_matches"]:
        problems.append("embedding metadata order does not match deterministic chunk order")
    if not validation["all_sources_approved"]:
        problems.append("one or more chunks use unknown source IDs")
    if validation["nan_value_count"]:
        problems.append("embedding matrix contains NaN values")
    if validation["infinite_value_count"]:
        problems.append("embedding matrix contains infinite values")

    if problems:
        raise ValueError("Input validation failed: " + "; ".join(problems))

    return validation


def reset_chroma_storage(path: Path) -> None:
    def clear_readonly_and_retry(function: Any, item_path: str, _exc_info: Any) -> None:
        os.chmod(item_path, stat.S_IWRITE)
        function(item_path)

    if path.exists():
        shutil.rmtree(path, onexc=clear_readonly_and_retry)
    path.mkdir(parents=True, exist_ok=True)


def build_vector_store() -> dict[str, Any]:
    chunks = load_jsonl(CHUNKS_PATH)
    embeddings = np.load(EMBEDDINGS_PATH)
    embedding_metadata = load_jsonl(EMBEDDING_METADATA_PATH)
    embedding_manifest = load_json(EMBEDDING_MANIFEST_PATH)
    sources = load_json(SOURCES_PATH)
    approved_source_ids = {source["source_id"] for source in sources["sources"]}
    expected_chunks = int(embedding_manifest["total_chunks"])
    expected_dimension = int(embedding_manifest["embedding_dimension"])

    input_validation = validate_inputs(
        chunks,
        embeddings,
        embedding_metadata,
        approved_source_ids,
        expected_chunks,
        expected_dimension,
    )
    sorted_chunks = sorted(chunks, key=lambda item: (item["source_id"], item["chunk_index"], item["chunk_id"]))

    reset_chroma_storage(CHROMA_PATH)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": DISTANCE_METRIC},
    )
    collection_count_before = collection.count()

    for start in range(0, len(sorted_chunks), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(sorted_chunks))
        batch_chunks = sorted_chunks[start:end]
        collection.upsert(
            ids=[chunk["chunk_id"] for chunk in batch_chunks],
            documents=[chunk["text"] for chunk in batch_chunks],
            embeddings=embeddings[start:end].astype(float).tolist(),
            metadatas=[build_metadata(chunk) for chunk in batch_chunks],
        )

    indexed_count = collection.count()

    # Reopen the persistent database to verify it is durable.
    reloaded_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    reloaded_collection = reloaded_client.get_collection(COLLECTION_NAME)
    reloaded_count = reloaded_collection.count()
    peek = reloaded_collection.get(limit=5, include=["metadatas", "documents"])

    validation_results = {
        **input_validation,
        "collection_exists": True,
        "collection_count_before_indexing": collection_count_before,
        "indexed_record_count": indexed_count,
        "persistent_reload_record_count": reloaded_count,
        "indexed_count_matches_expected": indexed_count == expected_chunks,
        "persistent_reload_ok": reloaded_count == expected_chunks,
        "sample_documents_present": all(bool(document) for document in peek.get("documents", [])),
        "sample_metadata_present": all(bool(metadata) for metadata in peek.get("metadatas", [])),
    }

    manifest = {
        "schema_version": "1.0",
        "stage": "Stage 12 - ChromaDB Vector Database Integration",
        "database_type": "ChromaDB",
        "chromadb_version": chromadb.__version__,
        "persistence_path": str(CHROMA_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "collection_name": COLLECTION_NAME,
        "embedding_model": embedding_manifest["model_name"],
        "embedding_dimension": expected_dimension,
        "distance_metric": DISTANCE_METRIC,
        "expected_chunk_count": expected_chunks,
        "indexed_record_count": indexed_count,
        "metadata_fields": METADATA_FIELDS,
        "build_timestamp": utc_now(),
        "rebuild_strategy": "Upsert deterministic chunk IDs and precomputed embeddings into the existing persistent Chroma collection.",
        "input_files": {
            "chunks": str(CHUNKS_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "embeddings": str(EMBEDDINGS_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "embedding_metadata": str(EMBEDDING_METADATA_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "embedding_manifest": str(EMBEDDING_MANIFEST_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        },
        "validation_results": validation_results,
    }

    VECTOR_STORE_ROOT.mkdir(parents=True, exist_ok=True)
    tmp_manifest_path = MANIFEST_PATH.with_suffix(".json.tmp")
    with tmp_manifest_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)
        file.write("\n")
    os.replace(tmp_manifest_path, MANIFEST_PATH)

    return manifest


def main() -> None:
    manifest = build_vector_store()
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
