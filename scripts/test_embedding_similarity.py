"""Lightweight local similarity tester for Stage 11 validation.

This utility embeds a question locally and compares it with the saved Stage 11
embedding matrix. It does not create a vector database or production retrieval
service.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = PROJECT_ROOT / "knowledge_base" / "chunks" / "chunks.jsonl"
EMBEDDINGS_PATH = PROJECT_ROOT / "knowledge_base" / "embeddings" / "embeddings.npy"
METADATA_PATH = PROJECT_ROOT / "knowledge_base" / "embeddings" / "embedding_metadata.jsonl"
MANIFEST_PATH = PROJECT_ROOT / "knowledge_base" / "embeddings" / "embedding_manifest.json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_jsonl_by_chunk_id(path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            record = json.loads(line)
            records[record["chunk_id"]] = record
    return records


def load_metadata(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            records.append(json.loads(line))
    return sorted(records, key=lambda item: item["embedding_index"])


STAGE11_TEST_QUERIES = [
    "What programming languages should a Computer Engineering student learn?",
    "What courses are taught in Computer Engineering?",
    "Can Computer Engineers work in cybersecurity?",
    "What career opportunities are available after graduation?",
    "How is artificial intelligence affecting computing jobs?",
    "Are internships important for students?",
]


def top_k_results(query: str, top_k: int) -> list[dict[str, Any]]:
    manifest = load_json(MANIFEST_PATH)
    embeddings = np.load(EMBEDDINGS_PATH)
    metadata = load_metadata(METADATA_PATH)
    chunks_by_id = load_jsonl_by_chunk_id(CHUNKS_PATH)

    if embeddings.shape[0] != len(metadata):
        raise ValueError("Embedding row count does not match metadata record count.")

    model = SentenceTransformer(manifest["model_name"])
    query_embedding = model.encode(
        [query],
        normalize_embeddings=manifest["normalization_setting"],
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype(np.float32, copy=False)[0]

    if query_embedding.shape[0] != embeddings.shape[1]:
        raise ValueError(
            f"Query embedding dimension {query_embedding.shape[0]} does not match matrix dimension {embeddings.shape[1]}."
        )

    scores = embeddings @ query_embedding
    top_indices = np.argsort(scores)[::-1][:top_k]

    results: list[dict[str, Any]] = []
    for rank, index in enumerate(top_indices, start=1):
        item = metadata[int(index)]
        chunk = chunks_by_id[item["chunk_id"]]
        results.append(
            {
                "rank": rank,
                "score": float(scores[int(index)]),
                "chunk_id": item["chunk_id"],
                "source_id": item["source_id"],
                "title": item.get("title"),
                "category": item.get("category"),
                "url": item.get("url"),
                "text_preview": " ".join(chunk["text"].split())[:500],
            }
        )

    return results


def run_queries(queries: list[str], top_k: int) -> list[dict[str, Any]]:
    return [{"query": query, "results": top_k_results(query, top_k)} for query in queries]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local Top-K embedding similarity test.")
    parser.add_argument("query", nargs="?", help="Question/query to embed and compare against local chunk embeddings.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return.")
    parser.add_argument("--preset-stage11", action="store_true", help="Run the Stage 11 representative query set.")
    args = parser.parse_args()

    if args.preset_stage11:
        print(json.dumps(run_queries(STAGE11_TEST_QUERIES, args.top_k), indent=2, ensure_ascii=False))
        return

    if not args.query:
        parser.error("query is required unless --preset-stage11 is used")

    print(json.dumps(top_k_results(args.query, args.top_k), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
