"""Local Ollama configuration for Stage 14."""

import os

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_GENERATE_ENDPOINT = "/api/generate"
OLLAMA_TAGS_ENDPOINT = "/api/tags"
OLLAMA_VERSION_ENDPOINT = "/api/version"

SELECTED_LLM_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
LLM_REQUEST_TIMEOUT_SECONDS = 120
LLM_TEMPERATURE = 0.2
LLM_NUM_CTX = 4096
LLM_NUM_PREDICT = 256
LLM_KEEP_ALIVE = "2h"

# Follow-up questions are rewritten into one standalone question by the local
# LLM before retrieval (backend/app/services/follow_up_rewriter.py).
FOLLOW_UP_REWRITE_ENABLED = True
FOLLOW_UP_REWRITE_NUM_PREDICT = 60
FOLLOW_UP_REWRITE_NUM_CTX = 2048
