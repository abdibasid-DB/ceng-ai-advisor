"""Local Ollama configuration for Stage 14."""

import os

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_GENERATE_ENDPOINT = "/api/generate"
OLLAMA_TAGS_ENDPOINT = "/api/tags"
OLLAMA_VERSION_ENDPOINT = "/api/version"

SELECTED_LLM_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
LLM_REQUEST_TIMEOUT_SECONDS = 120
# Temperature 0 and a fixed seed make answers reproducible: the same question
# and retrieved evidence give the same answer on every run.
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0"))
LLM_SEED = int(os.environ.get("LLM_SEED", "42"))
# Ollama reuses the cached prompt prefix of the previous request; how much it
# reuses changes the floating-point results of long prompts, so the same
# prompt gave different answers depending on what ran before. A one-token
# request before each generation leaves the same cache state every time.
# Ollama's llama-server also keeps a host-memory cache of recent prompts and
# restores the closest one, which the client cannot switch off; for identical
# answers start the Ollama server with LLAMA_ARG_CACHE_RAM=0.
LLM_RESET_PROMPT_CACHE = os.environ.get("LLM_RESET_PROMPT_CACHE", "1") != "0"
LLM_NUM_CTX = 4096
LLM_NUM_PREDICT = 256
LLM_KEEP_ALIVE = "2h"

# Follow-up questions are rewritten into one standalone question by the local
# LLM before retrieval (backend/app/services/follow_up_rewriter.py).
FOLLOW_UP_REWRITE_ENABLED = True
FOLLOW_UP_REWRITE_NUM_PREDICT = 60
FOLLOW_UP_REWRITE_NUM_CTX = 2048
