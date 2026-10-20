"""Step 1.2 retrieval experiment: chunk size, embedding model and hybrid search.

Scores source retrieval (Recall@5 and MRR@10) on the 240 paraphrase cases and
the unseen coverage cases labelled "answer", overall and for questions whose
expected sources are Turkish-language or OSTİM-specific.

Every option is built and queried in its own Chroma store under the
evaluation data directory (see backend/app/core/storage_config.py). The live
collection in knowledge_base/vector_store is only copied, never opened. Each
option's result file is written as soon as the option finishes, and finished
options are skipped on a rerun unless --force is given.

Options:
  baseline  copy of the live index, live settings
  a0        control: current chunking (380/500/60 words), all-MiniLM-L6-v2,
            rebuilt with all chunk-eligible documents
  a         ~180-word chunks with 40-word overlap, header and boilerplate
            stripped, all-MiniLM-L6-v2
  b         option a chunks + BAAI/bge-small-en-v1.5
  c         option a chunks + intfloat/multilingual-e5-small ("query: " /
            "passage: " prefixes)
  d         best of a/b/c (by overall Recall@5, then MRR) + BM25 fused with
            the vector ranking by reciprocal rank fusion
"""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (PROJECT_ROOT, PROJECT_ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import chromadb
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

import chunk_documents as chunking
from backend.app.core.retrieval_config import (
    CANDIDATE_TOP_K,
    CHROMA_PATH,
    COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
)
from backend.app.core.storage_config import ensure_disk_space, prepare_evaluation_storage
from backend.app.rag.retriever import (
    Retriever,
    deduplicate_candidates,
    diversify_results,
    expand_query_for_retrieval,
    infer_query_profile,
    rerank_candidates,
)
from build_vector_store import METADATA_FIELDS, safe_metadata_value


PARAPHRASE_CASES_PATH = PROJECT_ROOT / "tests" / "retrieval_paraphrase_cases.json"
UNSEEN_CASES_PATH = PROJECT_ROOT / "tests" / "unseen_coverage_cases.json"
SOURCES_PATH = PROJECT_ROOT / "knowledge_base" / "sources.json"
PROCESSING_MANIFEST_PATH = PROJECT_ROOT / "knowledge_base" / "processed" / "processing_manifest.json"
LIVE_CHUNKS_PATH = PROJECT_ROOT / "knowledge_base" / "chunks" / "chunks.jsonl"

RECALL_K = 5
MRR_K = 10
RRF_K = 60
BM25_CANDIDATES = CANDIDATE_TOP_K
EMBED_BATCH_SIZE = 32
BOOTSTRAP_SAMPLES = 2000

MINILM = EMBEDDING_MODEL_NAME
BGE = "BAAI/bge-small-en-v1.5"
E5 = "intfloat/multilingual-e5-small"
BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

CURRENT_CHUNKING = {"target_words": chunking.TARGET_WORDS, "max_words": chunking.MAX_WORDS, "overlap_words": chunking.OVERLAP_WORDS, "clean": False}
SMALL_CHUNKING = {"target_words": 180, "max_words": 220, "overlap_words": 40, "clean": True}

OPTIONS: dict[str, dict[str, Any]] = {
    "baseline": {"label": "Baseline (live index)", "chunking": None, "model": MINILM, "query_prefix": "", "passage_prefix": ""},
    "a0": {"label": "Control: current chunking, all docs", "chunking": CURRENT_CHUNKING, "model": MINILM, "query_prefix": "", "passage_prefix": ""},
    "a": {"label": "a: 180w chunks + cleaning, MiniLM", "chunking": SMALL_CHUNKING, "model": MINILM, "query_prefix": "", "passage_prefix": ""},
    "b": {"label": "b: a + bge-small-en-v1.5", "chunking": SMALL_CHUNKING, "model": BGE, "query_prefix": BGE_QUERY_INSTRUCTION, "passage_prefix": ""},
    "c": {"label": "c: a + multilingual-e5-small", "chunking": SMALL_CHUNKING, "model": E5, "query_prefix": "query: ", "passage_prefix": "passage: "},
    "d": {"label": "d: best of a/b/c + BM25 (RRF)", "hybrid": True},
}

# Short digit-free HTML blocks found in the header or footer zone of at least
# this many different HTML documents are treated as navigation/menu
# boilerplate. Table rows (country names, percentages) sit mid-page and stay.
NAV_BLOCK_MAX_WORDS = 12
NAV_BLOCK_MIN_DOCUMENTS = 3
NAV_EDGE_SHARE = 0.2
# Repeated paragraphs inside one HTML page (pages rendered twice) are dropped
# from their second occurrence; short repeated labels such as place names are kept.
REPEATED_BLOCK_MIN_WORDS = 8
COOKIE_BLOCK_MAX_WORDS = 80
COOKIE_RE = re.compile(r"cookie|çerez|kvkk|gdpr|kabul et\b|accept all|strictly necessary", re.IGNORECASE)
PAGE_NUMBER_RE = re.compile(r"^page\s+\d+$", re.IGNORECASE)
SOURCE_ID_HEADER_RE = re.compile(r"^source id:\s*\S+$", re.IGNORECASE)

BM25_STOPWORDS = set(
    "a an and are as at be but by can do does for from how i if in into is it its me my of on or our should so than "
    "that the their them there these they this to was we what when where which who why will with would you your".split()
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")
    tmp_path.replace(path)


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def fold(text: str) -> str:
    """Case- and diacritic-insensitive form, so OSTİM, OSTIM and ostim compare equal."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char)).replace("ı", "i")


def normalize_block(block: str) -> str:
    return " ".join(block.split()).casefold()


# ---------------------------------------------------------------- test cases


def load_cases(sources: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    turkish_ids = {source_id for source_id, source in sources.items() if source.get("language") == "Turkish"}
    ostim_ids = {
        source_id
        for source_id, source in sources.items()
        if "ostim" in fold(f"{source.get('title') or ''} {source.get('source_name') or ''}")
    }

    raw_cases = [dict(case, test_set="paraphrase", cluster=case["original_id"]) for case in load_json(PARAPHRASE_CASES_PATH)]
    unseen = load_json(UNSEEN_CASES_PATH)
    raw_cases += [dict(case, test_set="unseen", cluster=case["id"]) for case in unseen if case.get("expected_behavior") == "answer"]

    cases = []
    for case in raw_cases:
        expected = list(dict.fromkeys(case.get("expected_source_ids") or []))
        if not expected:
            continue
        cases.append(
            {
                "id": case["id"],
                "test_set": case["test_set"],
                "cluster": case["cluster"],
                "question": case["question"],
                "expected_source_ids": expected,
                "turkish_source": any(source_id in turkish_ids for source_id in expected),
                "ostim_specific": any(source_id in ostim_ids for source_id in expected),
            }
        )
    counts = {
        "paraphrase_cases": sum(1 for case in raw_cases if case["test_set"] == "paraphrase"),
        "unseen_answer_cases": sum(1 for case in raw_cases if case["test_set"] == "unseen"),
        "cases_without_expected_sources_skipped": len(raw_cases) - len(cases),
        "scored_cases": len(cases),
        "turkish_source_cases": sum(case["turkish_source"] for case in cases),
        "ostim_specific_cases": sum(case["ostim_specific"] for case in cases),
    }
    return cases, counts


# ------------------------------------------------------------------ chunking


def html_boilerplate_blocks(documents: list[tuple[dict[str, Any], str]]) -> set[str]:
    document_counts: Counter[str] = Counter()
    for record, text in documents:
        if record.get("input_file_type") != "html":
            continue
        blocks = chunking.split_blocks(text)
        edge = max(1, int(len(blocks) * NAV_EDGE_SHARE))
        edge_blocks = {
            normalize_block(block)
            for index, block in enumerate(blocks)
            if (index < edge or index >= len(blocks) - edge)
            and chunking.count_words(block) <= NAV_BLOCK_MAX_WORDS
            and not any(char.isdigit() for char in block)
        }
        document_counts.update(edge_blocks)
    return {block for block, count in document_counts.items() if count >= NAV_BLOCK_MIN_DOCUMENTS}


def clean_document(text: str, file_type: str, boilerplate: set[str]) -> str:
    kept: list[str] = []
    seen_paragraphs: set[str] = set()
    for block in chunking.split_blocks(text):
        lines = [
            line
            for line in block.splitlines()
            if not SOURCE_ID_HEADER_RE.match(line.strip()) and not PAGE_NUMBER_RE.match(line.strip())
        ]
        block = "\n".join(lines).strip()
        if not block:
            continue
        key = normalize_block(block)
        words = chunking.count_words(block)
        if words <= COOKIE_BLOCK_MAX_WORDS and COOKIE_RE.search(block):
            continue
        if file_type == "html":
            if key in boilerplate:
                continue
            if words >= REPEATED_BLOCK_MIN_WORDS:
                if key in seen_paragraphs:
                    continue
                seen_paragraphs.add(key)
        kept.append(block)
    return "\n\n".join(kept) + "\n"


def build_chunks(settings: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = load_json(PROCESSING_MANIFEST_PATH)
    sources = {source["source_id"]: source for source in load_json(SOURCES_PATH)["sources"]}
    records = sorted((record for record in manifest["records"] if record.get("chunking_eligible") is True), key=lambda item: item["source_id"])
    documents = [(record, (PROJECT_ROOT / record["processed_file_path"]).read_text(encoding="utf-8")) for record in records]
    boilerplate = html_boilerplate_blocks(documents) if settings["clean"] else set()

    chunks: list[dict[str, Any]] = []
    words_before = words_after = 0
    for record, text in documents:
        words_before += chunking.count_words(text)
        if settings["clean"]:
            text = clean_document(text, record.get("input_file_type", ""), boilerplate)
        words_after += chunking.count_words(text)
        units = chunking.build_text_units(text)
        pieces = chunking.create_chunks_from_units(
            units,
            target_words=settings["target_words"],
            max_words=settings["max_words"],
            overlap_words=settings["overlap_words"],
        )
        for index, piece in enumerate(pieces, start=1):
            chunks.append(chunking.build_chunk_record(piece, record, sources[record["source_id"]], index))

    word_counts = [chunk["word_count"] for chunk in chunks]
    stats = {
        "settings": settings,
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "average_chunk_words": round(float(np.mean(word_counts)), 1),
        "median_chunk_words": float(np.median(word_counts)),
        "max_chunk_words": int(max(word_counts)),
        "document_words_before_cleaning": words_before,
        "document_words_after_cleaning": words_after,
        "boilerplate_block_patterns": len(boilerplate),
    }
    return chunks, stats


def load_live_chunks() -> list[dict[str, Any]]:
    with LIVE_CHUNKS_PATH.open("r", encoding="utf-8") as file:
        chunks = [json.loads(line) for line in file if line.strip()]
    return sorted(chunks, key=lambda item: (item["source_id"], item["chunk_index"], item["chunk_id"]))


# ----------------------------------------------------------------- embedding


def truncation_stats(model: SentenceTransformer, texts: list[str]) -> dict[str, Any]:
    limit = model.max_seq_length
    lengths = [len(ids) for ids in model.tokenizer(texts, add_special_tokens=True, truncation=False)["input_ids"]]
    over = [length for length in lengths if length > limit]
    return {
        "max_seq_length": limit,
        "mean_tokens": round(float(np.mean(lengths)), 1),
        "chunks_truncated": len(over),
        "chunks_truncated_share": round(len(over) / len(lengths), 4),
        "tokens_never_embedded_share": round(sum(length - limit for length in over) / sum(lengths), 4),
    }


def embed_chunks(model: SentenceTransformer, chunks: list[dict[str, Any]], passage_prefix: str) -> tuple[np.ndarray, dict[str, Any]]:
    texts = [passage_prefix + chunk["text"] for chunk in chunks]
    truncation = truncation_stats(model, texts)
    start = time.perf_counter()
    embeddings = model.encode(texts, batch_size=EMBED_BATCH_SIZE, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    seconds = time.perf_counter() - start
    return embeddings.astype(np.float32), {"embedding_seconds": round(seconds, 1), "chunks_per_second": round(len(texts) / seconds, 1), **truncation}


def build_index(path: Path, chunks: list[dict[str, Any]], embeddings: np.ndarray) -> None:
    if path.exists():
        shutil.rmtree(path)
    client = chromadb.PersistentClient(path=str(path))
    collection = client.create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    for start in range(0, len(chunks), 200):
        batch = chunks[start : start + 200]
        collection.upsert(
            ids=[chunk["chunk_id"] for chunk in batch],
            documents=[chunk["text"] for chunk in batch],
            embeddings=embeddings[start : start + 200].astype(float).tolist(),
            metadatas=[{field: safe_metadata_value(chunk.get(field)) for field in METADATA_FIELDS} for chunk in batch],
        )
    if collection.count() != len(chunks):
        raise RuntimeError(f"{path}: indexed {collection.count()} of {len(chunks)} chunks")


# ----------------------------------------------------------------- retrieval


def bm25_tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"\w+", fold(text)) if len(token) > 1 and token not in BM25_STOPWORDS]


class ExperimentRetriever(Retriever):
    """The live retriever on an experiment index, with model-specific query prefixes and optional BM25 fusion."""

    def __init__(
        self,
        *,
        chroma_path: Path,
        model: SentenceTransformer,
        model_name: str,
        query_prefix: str = "",
        hybrid_chunks: list[dict[str, Any]] | None = None,
        hybrid_embeddings: np.ndarray | None = None,
    ) -> None:
        super().__init__(chroma_path=chroma_path, collection_name=COLLECTION_NAME, model_name=model_name)
        self._model = model
        self.query_prefix = query_prefix
        self.hybrid_chunks = hybrid_chunks
        self.hybrid_embeddings = hybrid_embeddings
        self.bm25 = BM25Okapi([bm25_tokens(chunk["text"]) for chunk in hybrid_chunks]) if hybrid_chunks else None

    def encode_query(self, query: str) -> list[float]:
        embedding = self.get_model().encode(
            [self.query_prefix + self._clean_query(query)],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0]
        return embedding.astype(float).tolist()

    def retrieve(self, query: str, *, top_k: int, candidate_top_k: int = CANDIDATE_TOP_K) -> dict[str, Any]:
        if self.bm25 is None:
            return super().retrieve(query, top_k=top_k, candidate_top_k=candidate_top_k)

        expanded_query = expand_query_for_retrieval(self._clean_query(query))
        query_embedding = self.encode_query(expanded_query)
        profile = infer_query_profile(expanded_query)
        raw = self._collection.query(query_embeddings=[query_embedding], n_results=candidate_top_k, include=["documents", "metadatas", "distances"])
        candidates = self._format_candidates(raw)
        candidates.extend(self._category_supplemental_candidates(query_embedding, profile))
        vector_ranked = rerank_candidates(deduplicate_candidates(candidates), profile)

        scores = self.bm25.get_scores(bm25_tokens(expanded_query))
        bm25_indices = [int(index) for index in np.argsort(-scores)[:BM25_CANDIDATES] if scores[index] > 0]
        query_vector = np.asarray(query_embedding, dtype=np.float32)

        fused: dict[str, dict[str, Any]] = {}
        for rank, candidate in enumerate(vector_ranked, start=1):
            fused[candidate["chunk_id"]] = dict(candidate, rerank_score=1.0 / (RRF_K + rank))
        for rank, index in enumerate(bm25_indices, start=1):
            chunk = self.hybrid_chunks[index]
            entry = fused.get(chunk["chunk_id"])
            if entry is None:
                similarity = float(self.hybrid_embeddings[index] @ query_vector)
                entry = {
                    "chunk_id": chunk["chunk_id"],
                    "source_id": chunk["source_id"],
                    "text": chunk["text"],
                    "title": chunk.get("title") or "",
                    "category": chunk.get("category") or "",
                    "similarity_score": similarity,
                    "rerank_score": 0.0,
                }
                fused[chunk["chunk_id"]] = entry
            entry["rerank_score"] += 1.0 / (RRF_K + rank)

        ranked = sorted(fused.values(), key=lambda item: (item["rerank_score"], item["similarity_score"]), reverse=True)
        return {"query": query, "retrieval_query": expanded_query, "results": diversify_results(ranked, top_k=top_k)}


# ---------------------------------------------------------------- evaluation


def score_case(case: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    expected = set(case["expected_source_ids"])
    ranked_sources = [result["source_id"] for result in results]
    top_sources = set(ranked_sources[:RECALL_K])
    first_rank = next((rank for rank, source_id in enumerate(ranked_sources[:MRR_K], start=1) if source_id in expected), None)
    return {
        "recall_at_5": len(expected & top_sources) / len(expected),
        "hit_at_5": float(bool(expected & top_sources)),
        "reciprocal_rank": 1.0 / first_rank if first_rank else 0.0,
        "first_relevant_rank": first_rank,
        "retrieved": [[result["chunk_id"], result["source_id"]] for result in results],
    }


def aggregate(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    def metrics(selected: list[dict[str, Any]]) -> dict[str, Any]:
        if not selected:
            return {"n": 0}
        return {
            "n": len(selected),
            "recall_at_5": round(float(np.mean([case["recall_at_5"] for case in selected])), 4),
            "mrr_at_10": round(float(np.mean([case["reciprocal_rank"] for case in selected])), 4),
            "hit_at_5": round(float(np.mean([case["hit_at_5"] for case in selected])), 4),
        }

    return {
        "overall": metrics(case_results),
        "turkish_source": metrics([case for case in case_results if case["turkish_source"]]),
        "ostim_specific": metrics([case for case in case_results if case["ostim_specific"]]),
        "paraphrase_set": metrics([case for case in case_results if case["test_set"] == "paraphrase"]),
        "unseen_set": metrics([case for case in case_results if case["test_set"] == "unseen"]),
    }


def evaluate_cases(retriever: Retriever, cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], float]:
    results = []
    start = time.perf_counter()
    for case in cases:
        retrieval = retriever.retrieve(case["question"], top_k=MRR_K)
        results.append({**case, **score_case(case, retrieval["results"])})
    return results, (time.perf_counter() - start) / max(1, len(cases))


def run_vector_option(name: str, option: dict[str, Any], run_dir: Path, cases: list[dict[str, Any]], models: dict[str, SentenceTransformer]) -> dict[str, Any]:
    model = models.setdefault(option["model"], SentenceTransformer(option["model"]))
    index_path = run_dir / "indexes" / name

    if option["chunking"] is None:
        chunks = load_live_chunks()
        chunk_stats = {"settings": "live knowledge_base/chunks/chunks.jsonl", "chunk_count": len(chunks), "average_chunk_words": round(float(np.mean([c["word_count"] for c in chunks])), 1)}
        _, embedding_stats = embed_chunks(model, chunks, option["passage_prefix"])
        embedding_stats["note"] = "Live chunks re-encoded in memory for timing only; queries run on a file copy of the live index."
        if index_path.exists():
            shutil.rmtree(index_path)
        shutil.copytree(CHROMA_PATH, index_path)
    else:
        chunks, chunk_stats = build_chunks(option["chunking"])
        embeddings, embedding_stats = embed_chunks(model, chunks, option["passage_prefix"])
        build_index(index_path, chunks, embeddings)
        np.save(run_dir / "indexes" / f"{name}_embeddings.npy", embeddings)
        with (run_dir / "indexes" / f"{name}_chunks.jsonl").open("w", encoding="utf-8", newline="\n") as file:
            for chunk in chunks:
                file.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    retriever = ExperimentRetriever(chroma_path=index_path, model=model, model_name=option["model"], query_prefix=option["query_prefix"])
    case_results, seconds_per_query = evaluate_cases(retriever, cases)
    return {
        "chunking": chunk_stats,
        "embedding": {"model": option["model"], "query_prefix": option["query_prefix"], "passage_prefix": option["passage_prefix"], **embedding_stats},
        "seconds_per_query": round(seconds_per_query, 4),
        "metrics": aggregate(case_results),
        "cases": case_results,
    }


def pick_best(run_dir: Path) -> str:
    candidates = []
    for name in ("a", "b", "c"):
        path = run_dir / "results" / f"{name}.json"
        if not path.exists():
            raise RuntimeError(f"Option d needs finished results for a, b and c; {path.name} is missing.")
        overall = load_json(path)["metrics"]["overall"]
        candidates.append((overall["recall_at_5"], overall["mrr_at_10"], name))
    return max(candidates)[2]


def run_hybrid_option(run_dir: Path, cases: list[dict[str, Any]], models: dict[str, SentenceTransformer]) -> dict[str, Any]:
    base_name = pick_best(run_dir)
    base = OPTIONS[base_name]
    model = models.setdefault(base["model"], SentenceTransformer(base["model"]))
    with (run_dir / "indexes" / f"{base_name}_chunks.jsonl").open("r", encoding="utf-8") as file:
        chunks = [json.loads(line) for line in file if line.strip()]
    embeddings = np.load(run_dir / "indexes" / f"{base_name}_embeddings.npy")
    base_result = load_json(run_dir / "results" / f"{base_name}.json")

    retriever = ExperimentRetriever(
        chroma_path=run_dir / "indexes" / base_name,
        model=model,
        model_name=base["model"],
        query_prefix=base["query_prefix"],
        hybrid_chunks=chunks,
        hybrid_embeddings=embeddings,
    )
    case_results, seconds_per_query = evaluate_cases(retriever, cases)
    return {
        "base_option": base_name,
        "fusion": {"method": "reciprocal_rank_fusion", "k": RRF_K, "bm25": "rank_bm25.BM25Okapi on folded word tokens of the expanded query", "bm25_candidates": BM25_CANDIDATES},
        "chunking": base_result["chunking"],
        "embedding": {**base_result["embedding"], "note": f"Reuses option {base_name}'s index; BM25 index build is not included."},
        "seconds_per_query": round(seconds_per_query, 4),
        "metrics": aggregate(case_results),
        "cases": case_results,
    }


def paired_bootstrap(results: dict[str, dict[str, Any]], reference: str, metric: str) -> dict[str, Any]:
    """95% interval for (option - reference), resampling original questions so paraphrase variants stay together."""
    reference_cases = {case["id"]: case for case in results[reference]["cases"]}
    clusters = sorted({case["cluster"] for case in reference_cases.values()})
    rng = random.Random(20261020)
    draws = [[rng.choice(clusters) for _ in clusters] for _ in range(BOOTSTRAP_SAMPLES)]
    intervals = {}
    for name, result in results.items():
        if name == reference:
            continue
        by_cluster: dict[str, list[float]] = {}
        for case in result["cases"]:
            by_cluster.setdefault(case["cluster"], []).append(case[metric] - reference_cases[case["id"]][metric])
        sums = {cluster: (sum(values), len(values)) for cluster, values in by_cluster.items()}
        estimates = []
        for draw in draws:
            total = sum(sums[cluster][0] for cluster in draw)
            count = sum(sums[cluster][1] for cluster in draw)
            estimates.append(total / count)
        estimates.sort()
        point = sum(value for value, _ in sums.values()) / sum(count for _, count in sums.values())
        intervals[name] = {
            "difference": round(point, 4),
            "ci95": [round(estimates[int(0.025 * BOOTSTRAP_SAMPLES)], 4), round(estimates[int(0.975 * BOOTSTRAP_SAMPLES) - 1], 4)],
        }
    return intervals


def summary_table(results: dict[str, dict[str, Any]]) -> str:
    lines = [
        "| Option | Recall@5 overall | MRR overall | Recall@5 Turkish | MRR Turkish | Recall@5 OSTİM | MRR OSTİM | Chunks | Embedding time |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, result in results.items():
        metrics = result["metrics"]
        embedding = result["embedding"]
        time_text = f"{embedding['embedding_seconds']} s" if name != "d" else f"{embedding['embedding_seconds']} s (+BM25)"
        lines.append(
            f"| {OPTIONS[name]['label']} | {metrics['overall']['recall_at_5']:.3f} | {metrics['overall']['mrr_at_10']:.3f} | "
            f"{metrics['turkish_source']['recall_at_5']:.3f} | {metrics['turkish_source']['mrr_at_10']:.3f} | "
            f"{metrics['ostim_specific']['recall_at_5']:.3f} | {metrics['ostim_specific']['mrr_at_10']:.3f} | "
            f"{result['chunking']['chunk_count']} | {time_text} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Step 1.2 retrieval experiment on experiment copies of the index.")
    parser.add_argument("--options", default=",".join(OPTIONS), help="Comma-separated options to run, in order.")
    parser.add_argument("--run-name", default="retrieval-paraphrases-step-1-2", help="Folder name under the evaluation output directory.")
    parser.add_argument("--force", action="store_true", help="Rerun options that already have a result file.")
    args = parser.parse_args()

    run_dir = prepare_evaluation_storage(args.run_name)
    sources = {source["source_id"]: source for source in load_json(SOURCES_PATH)["sources"]}
    cases, case_counts = load_cases(sources)
    print(f"Run folder: {run_dir}")
    print(json.dumps(case_counts, indent=2))

    models: dict[str, SentenceTransformer] = {}
    for name in [item.strip() for item in args.options.split(",") if item.strip()]:
        if name not in OPTIONS:
            raise SystemExit(f"Unknown option {name!r}; choose from {', '.join(OPTIONS)}.")
        result_path = run_dir / "results" / f"{name}.json"
        if result_path.exists() and not args.force:
            print(f"{name}: already finished, skipping ({result_path.name})")
            continue
        ensure_disk_space()
        print(f"{name}: running {OPTIONS[name]['label']} ...", flush=True)
        started = time.perf_counter()
        if OPTIONS[name].get("hybrid"):
            result = run_hybrid_option(run_dir, cases, models)
        else:
            result = run_vector_option(name, OPTIONS[name], run_dir, cases, models)
        result = {
            "option": name,
            "label": OPTIONS[name]["label"],
            "generated_at": utc_now(),
            "git_commit": git_commit(),
            "case_counts": case_counts,
            "wall_seconds": round(time.perf_counter() - started, 1),
            **result,
        }
        write_json(result_path, result)
        overall = result["metrics"]["overall"]
        print(f"{name}: Recall@5 {overall['recall_at_5']:.3f}, MRR {overall['mrr_at_10']:.3f}; saved {result_path}", flush=True)

    finished = {name: load_json(run_dir / "results" / f"{name}.json") for name in OPTIONS if (run_dir / "results" / f"{name}.json").exists()}
    if "baseline" in finished:
        comparisons = {
            reference: {metric: paired_bootstrap(finished, reference, metric) for metric in ("recall_at_5", "reciprocal_rank")}
            for reference in ("baseline", "a0")
            if reference in finished
        }
        summary = {
            "generated_at": utc_now(),
            "case_counts": case_counts,
            "metrics": {name: result["metrics"] for name, result in finished.items()},
            "embedding": {name: result["embedding"] for name, result in finished.items()},
            "chunking": {name: result["chunking"] for name, result in finished.items()},
            "seconds_per_query": {name: result["seconds_per_query"] for name, result in finished.items()},
            "paired_bootstrap_vs_reference": comparisons,
        }
        write_json(run_dir / "summary.json", summary)
        table = summary_table(finished)
        (run_dir / "summary.md").write_text(table + "\n", encoding="utf-8", newline="\n")
        print(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
