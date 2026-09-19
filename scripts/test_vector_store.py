"""Stage 12 ChromaDB Top-K validation utility.

This script queries the local persistent ChromaDB collection. It does not
generate final answers, call an LLM, implement RAG, or expose a production API.
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

import chromadb
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VECTOR_STORE_ROOT = PROJECT_ROOT / "knowledge_base" / "vector_store"
CHROMA_PATH = VECTOR_STORE_ROOT / "chroma"
MANIFEST_PATH = VECTOR_STORE_ROOT / "vector_store_manifest.json"
COLLECTION_NAME = "ceng_advisor_chunks"

STAGE12_TEST_QUERIES = [
    "What courses are taught in Computer Engineering?",
    "What programming languages should a Computer Engineering student learn?",
    "What jobs can I do after graduating from Computer Engineering?",
    "Will artificial intelligence replace Computer Engineers?",
    "Can Computer Engineers work in cybersecurity?",
    "How important are internships for Computer Engineering students?",
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def distance_to_similarity(distance: float) -> float:
    """For Chroma cosine distance, smaller is better and similarity is 1 - distance."""
    return 1.0 - distance


def query_vector_store(
    query: str,
    top_k: int,
    *,
    model: SentenceTransformer | None = None,
    collection: Any | None = None,
    manifest: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if manifest is None:
        manifest = load_json(MANIFEST_PATH)
    if model is None:
        model = SentenceTransformer(manifest["embedding_model"])
    if collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        collection = client.get_collection(COLLECTION_NAME)

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )[0]

    results = collection.query(
        query_embeddings=[query_embedding.astype(float).tolist()],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    rows: list[dict[str, Any]] = []
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for rank, (chunk_id, document, metadata, distance) in enumerate(
        zip(ids, documents, metadatas, distances), start=1
    ):
        rows.append(
            {
                "rank": rank,
                "chunk_id": chunk_id,
                "source_id": metadata.get("source_id"),
                "title": metadata.get("title"),
                "category": metadata.get("category"),
                "distance": float(distance),
                "cosine_similarity": distance_to_similarity(float(distance)),
                "url": metadata.get("url"),
                "text_preview": " ".join(document.split())[:500],
            }
        )

    return rows


def run_queries(queries: list[str], top_k: int) -> list[dict[str, Any]]:
    manifest = load_json(MANIFEST_PATH)
    model = SentenceTransformer(manifest["embedding_model"])
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_collection(COLLECTION_NAME)
    return [
        {
            "query": query,
            "results": query_vector_store(query, top_k, model=model, collection=collection, manifest=manifest),
        }
        for query in queries
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Stage 12 ChromaDB Top-K query test.")
    parser.add_argument("query", nargs="?", help="Question/query to embed and search in ChromaDB.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return.")
    parser.add_argument("--preset-stage12", action="store_true", help="Run the Stage 12 representative query set.")
    args = parser.parse_args()

    if args.preset_stage12:
        print(json.dumps(run_queries(STAGE12_TEST_QUERIES, args.top_k), indent=2, ensure_ascii=False))
        return

    if not args.query:
        parser.error("query is required unless --preset-stage12 is used")

    print(json.dumps(query_vector_store(args.query, args.top_k), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
