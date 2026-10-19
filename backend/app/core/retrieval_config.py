"""Configuration for the Stage 13 retrieval layer."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHROMA_PATH = PROJECT_ROOT / "knowledge_base" / "vector_store" / "chroma"
VECTOR_STORE_MANIFEST_PATH = PROJECT_ROOT / "knowledge_base" / "vector_store" / "vector_store_manifest.json"
COLLECTION_NAME = "ceng_advisor_chunks"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

DEFAULT_TOP_K = 5
CANDIDATE_TOP_K = 12
CATEGORY_CANDIDATES_PER_CATEGORY = 3
MIN_SIMILARITY_THRESHOLD = 0.30
MIN_RESULTS_ABOVE_THRESHOLD = 2
MAX_RESULTS_PER_SOURCE = 3

# Semantic grounding checks (cosine similarity with the retrieval embedding
# model). Chosen by replaying the 2026-10-18 full-200 run offline; see
# scripts/evaluate_semantic_thresholds.py.
QUESTION_ANSWER_SIMILARITY_THRESHOLD = 0.65
SENTENCE_PASSAGE_SIMILARITY_THRESHOLD = 0.70

CATEGORY_BOOST = 0.08
OFFICIAL_SOURCE_BOOST = 0.05
TITLE_KEYWORD_BOOST = 0.02
