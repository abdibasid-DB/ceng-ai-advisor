"""Configuration for the Stage 13 retrieval layer."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHROMA_PATH = PROJECT_ROOT / "knowledge_base" / "vector_store" / "chroma"
VECTOR_STORE_MANIFEST_PATH = PROJECT_ROOT / "knowledge_base" / "vector_store" / "vector_store_manifest.json"
CHUNKS_PATH = PROJECT_ROOT / "knowledge_base" / "chunks" / "chunks.jsonl"
EMBEDDINGS_PATH = PROJECT_ROOT / "knowledge_base" / "embeddings" / "embeddings.npy"
COLLECTION_NAME = "ceng_advisor_chunks"
# Step 1.2 option f: BAAI/bge-m3 dense embeddings on ~180-word chunks, fused
# with BM25 by reciprocal rank fusion (docs/retrieval-paraphrases-step-1-2/).
EMBEDDING_MODEL_NAME = "BAAI/bge-m3"
EMBEDDING_DIMENSION = 1024
EMBEDDING_MAX_SEQ_LENGTH = 512

# Five passages still fill the prompt's 3000-character context budget with the
# shorter chunks; see docs/retrieval-f-calibration/README.md.
DEFAULT_TOP_K = 5
CANDIDATE_TOP_K = 12
CATEGORY_CANDIDATES_PER_CATEGORY = 3
# Recalibrated for bge-m3 (scripts/calibrate_retrieval_threshold.py): 96.8% of
# in-scope test questions pass; MiniLM's 0.30 does not transfer, because
# bge-m3 gives unrelated text cosine scores of roughly 0.4-0.55.
MIN_SIMILARITY_THRESHOLD = 0.50
MIN_RESULTS_ABOVE_THRESHOLD = 2
MAX_RESULTS_PER_SOURCE = 3

# Hybrid search: BM25 over chunk text fused with the vector ranking.
HYBRID_SEARCH_ENABLED = True
RRF_K = 60
BM25_CANDIDATES = CANDIDATE_TOP_K

# Semantic grounding checks (cosine similarity with the retrieval embedding
# model). Chosen by replaying the 2026-10-18 full-200 run offline with bge-m3
# (scripts/evaluate_semantic_thresholds.py --model): the lowest thresholds that
# accept no more mismatched or unsupported pairs than MiniLM did at 0.65/0.70.
QUESTION_ANSWER_SIMILARITY_THRESHOLD = 0.70
SENTENCE_PASSAGE_SIMILARITY_THRESHOLD = 0.72

CATEGORY_BOOST = 0.08
OFFICIAL_SOURCE_BOOST = 0.05
TITLE_KEYWORD_BOOST = 0.02
