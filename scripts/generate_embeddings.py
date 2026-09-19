"""Generate local embeddings for Stage 11.

This script reads chunk records and writes local embedding artifacts only. It
does not create ChromaDB collections, retrieval APIs, Ollama integration, RAG,
chatbot logic, or frontend/backend features.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = PROJECT_ROOT / "knowledge_base" / "chunks" / "chunks.jsonl"
CHUNKING_MANIFEST_PATH = PROJECT_ROOT / "knowledge_base" / "chunks" / "chunking_manifest.json"
OUTPUT_DIR = PROJECT_ROOT / "knowledge_base" / "embeddings"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 32
NORMALIZE_EMBEDDINGS = True
SIMILARITY_METRIC = "cosine"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_chunks(path: Path) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    required_fields = {"chunk_id", "source_id", "chunk_index", "text"}
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            record = json.loads(line)
            missing = sorted(field for field in required_fields if record.get(field) in (None, ""))
            if missing:
                raise ValueError(f"Chunk record on line {line_number} is missing required fields: {missing}")
            if not isinstance(record["text"], str) or not record["text"].strip():
                raise ValueError(f"Chunk record on line {line_number} has empty text")
            chunks.append(record)
    return sorted(chunks, key=lambda item: (item["source_id"], item["chunk_index"], item["chunk_id"]))


def validate_embeddings(embeddings: np.ndarray, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    if embeddings.ndim != 2:
        raise ValueError(f"Expected a 2D embedding matrix, got shape {embeddings.shape}")

    invalid_nan = int(np.isnan(embeddings).sum())
    invalid_inf = int(np.isinf(embeddings).sum())
    row_count, dimension = embeddings.shape
    norms = np.linalg.norm(embeddings, axis=1)
    finite_norms = norms[np.isfinite(norms)]
    duplicate_chunk_ids = len(chunks) - len({chunk["chunk_id"] for chunk in chunks})

    return {
        "total_chunks": len(chunks),
        "total_embeddings": int(row_count),
        "embedding_dimension": int(dimension),
        "embedding_count_matches_chunks": row_count == len(chunks),
        "nan_value_count": invalid_nan,
        "infinite_value_count": invalid_inf,
        "duplicate_chunk_id_count": duplicate_chunk_ids,
        "minimum_vector_norm": float(finite_norms.min()) if len(finite_norms) else math.nan,
        "maximum_vector_norm": float(finite_norms.max()) if len(finite_norms) else math.nan,
    }


def write_metadata(chunks: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for index, chunk in enumerate(chunks):
            metadata = {
                "embedding_index": index,
                "chunk_id": chunk["chunk_id"],
                "source_id": chunk["source_id"],
                "chunk_index": chunk["chunk_index"],
                "title": chunk.get("title"),
                "source_name": chunk.get("source_name"),
                "source_type": chunk.get("source_type"),
                "url": chunk.get("url"),
                "category": chunk.get("category"),
                "language": chunk.get("language"),
                "processed_file_path": chunk.get("processed_file_path"),
                "chunk_record_path": str(CHUNKS_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            }
            file.write(json.dumps(metadata, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate local embeddings for chunk records.")
    parser.add_argument("--model", default=MODEL_NAME, help="Sentence Transformers model name.")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Batch size for local encoding.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Embedding artifact output directory.")
    args = parser.parse_args()

    chunks = load_chunks(CHUNKS_PATH)
    chunking_manifest = load_json(CHUNKING_MANIFEST_PATH)
    texts = [chunk["text"] for chunk in chunks]

    start_time = time.perf_counter()
    model = SentenceTransformer(args.model)
    embeddings = model.encode(
        texts,
        batch_size=args.batch_size,
        normalize_embeddings=NORMALIZE_EMBEDDINGS,
        convert_to_numpy=True,
        show_progress_bar=True,
    )
    elapsed_seconds = round(time.perf_counter() - start_time, 2)
    embeddings = embeddings.astype(np.float32, copy=False)

    validation = validate_embeddings(embeddings, chunks)
    device = str(getattr(model, "device", "unknown"))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    embeddings_path = args.output_dir / "embeddings.npy"
    metadata_path = args.output_dir / "embedding_metadata.jsonl"
    manifest_path = args.output_dir / "embedding_manifest.json"

    np.save(embeddings_path, embeddings)
    write_metadata(chunks, metadata_path)

    manifest = {
        "schema_version": "1.0",
        "stage": "Stage 11 - Embedding Model Design and Testing",
        "generation_timestamp": utc_now(),
        "model_name": args.model,
        "model_provider_repository": "Hugging Face / Sentence Transformers",
        "model_type": "sentence-transformers dense embedding model",
        "embedding_dimension": validation["embedding_dimension"],
        "total_chunks": len(chunks),
        "total_embeddings": validation["total_embeddings"],
        "normalization_setting": NORMALIZE_EMBEDDINGS,
        "similarity_metric_intended": SIMILARITY_METRIC,
        "batch_size": args.batch_size,
        "device_used": device,
        "generation_time_seconds": elapsed_seconds,
        "input_files": {
            "chunks": str(CHUNKS_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "chunking_manifest": str(CHUNKING_MANIFEST_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        },
        "output_files": {
            "embeddings": str(embeddings_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "metadata": str(metadata_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "manifest": str(manifest_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        },
        "chunking_manifest_total_chunks": chunking_manifest.get("total_chunk_count"),
        "validation_results": validation,
    }

    with manifest_path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
