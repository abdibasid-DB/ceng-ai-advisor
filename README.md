# AI-Powered Computer Engineering Student Advisor

## Project Purpose

AI-Powered Computer Engineering Student Advisor is a university project that helps students ask source-grounded questions about Computer Engineering education, curriculum, skills, careers, internships, AI, cybersecurity, and future technologies.

The system uses Retrieval-Augmented Generation (RAG) with a locally deployed open-source model through Ollama. It does not use commercial cloud LLM APIs such as OpenAI, Gemini, Claude, Azure OpenAI, Cohere, Perplexity, or similar services for answer generation.

## Architecture

```text
React + Vite
  -> FastAPI
  -> RAG pipeline
  -> hybrid retrieval: ChromaDB (bge-m3 vectors) + BM25, reciprocal rank fusion
  -> Ollama
  -> qwen2.5:3b
```

The frontend communicates with FastAPI only:

- Chat: `POST /api/v1/chat`
- Streaming chat (NDJSON metadata, token, and final events): `POST /api/v1/chat/stream`
- Readiness: `GET /api/v1/readiness`
- Source registry metadata: `GET /api/v1/sources`
- Health: `GET /health`
- API information: `GET /`
- OpenAPI schema: `GET /openapi.json`; interactive docs: `GET /docs` and `GET /redoc`

## Website Sections

- Home
- AI Advisor
- Computer Engineering
- Sources
- About Project

The AI Advisor keeps conversations in this browser tab's session storage, listed by their first question. New Conversation preserves earlier chats, and reopening one reuses its backend session ID. History survives a page reload and is limited to this browser session. The backend keeps the last 8 turns per session in process memory to understand follow-up questions; restarting the backend clears that memory.

Answers render as Markdown with clickable citation badges, supporting passages, publication dates when available from the source registry, similarity scores, and a copy button. Retrieval progress comes from streaming metadata. Home sample questions open a new Advisor conversation and send the selected question. Source counts come from the live registry. The theme follows the system by default, with Light and Dark overrides remembered in this browser.

## Technology Stack

- Frontend: React + Vite
- Backend: FastAPI
- Embeddings: `BAAI/bge-m3` (dense, 1024 dimensions, 512-token input) on ~180-word chunks
- Vector database: ChromaDB, fused with BM25 keyword search (`rank_bm25`) by reciprocal rank fusion
- Local LLM runtime: Ollama
- Local LLM: `qwen2.5:3b`
- Package manager: pnpm

## Project Structure

- `backend/`: FastAPI application, API routes, Pydantic models, RAG pipeline, retriever, and local Ollama service integration.
- `frontend/`: React/Vite website source, dependency manifests, environment example, and production build scripts.
- `knowledge_base/`: source registry, raw and processed source material, chunks, embeddings, and prepared local vector-store artifacts.
- `scripts/`: acquisition, preprocessing, chunking, embedding, vector-store, retrieval, LLM, and RAG evaluation utilities.
- `tests/`: backend API, retrieval, RAG pipeline, LLM service, and evaluation-case validation tests.
- `docs/`: stage reports, evaluation results, source audits, and project evidence.

## Prerequisites

Install these before running the project:

- Python 3.12 recommended. The current project has been verified with Python 3.12.
- Node.js 22.12 or newer (Node.js 24 recommended for the Vite 7 frontend).
- pnpm, for frontend dependency installation and Vite commands.
- Ollama, running locally.
- The Ollama model `qwen2.5:3b`.

The project does not require API keys for commercial LLM providers.

## Project Data Required At Runtime

The local RAG system expects these project artifacts to exist:

- `knowledge_base/sources.json`
- `knowledge_base/chunks/chunks.jsonl`
- `knowledge_base/embeddings/embeddings.npy`
- `knowledge_base/vector_store/chroma/`
- `knowledge_base/vector_store/vector_store_manifest.json`

These artifacts are already part of the prepared project workspace. Normal local running does not require rerunning preprocessing, embedding generation, ChromaDB indexing, or the 80-case RAG evaluation.

## Environment Configuration

### Frontend

The frontend supports one Vite environment variable:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

If this variable is not set, the frontend uses `http://127.0.0.1:8000`. Set it to `/` for a same-origin reverse proxy, as used by the frontend Docker image. Vite embeds this value at build time.

An example file is provided at:

```text
frontend/.env.example
```

To customize the frontend API URL:

```powershell
cd frontend
Copy-Item .env.example .env.local
```

Then edit `frontend/.env.local`.

### Backend

The backend reads these process environment variables at startup, with local defaults:

- `OLLAMA_BASE_URL`: default `http://127.0.0.1:11434`
- `OLLAMA_MODEL`: default `qwen2.5:3b`
- `LLM_TEMPERATURE`: default `0`; `LLM_SEED`: default `42`. Every generation, including the follow-up rewrite, uses them.
- `LLM_RESET_PROMPT_CACHE`: default `1`. A one-token request before each generation gives every prompt the same starting cache state; set `0` to skip it.

With these defaults the same question gives the same answer, provided the Ollama server is started with `LLAMA_ARG_CACHE_RAM=0`. Without it, Ollama's llama-server restores the closest of its recently cached prompts, and the answer can depend on what was asked before. The `docker-compose.yml` Ollama service already sets it. For a local Ollama:

- Windows: run `setx LLAMA_ARG_CACHE_RAM 0`, then quit Ollama completely (tray icon → Quit Ollama, or end both `ollama app.exe` and `ollama.exe` in Task Manager) and start it again. Reopening the app while the old server still runs keeps the old server and its settings, because the app logs "existing instance found, exiting".
- macOS/Linux: start the server with `LLAMA_ARG_CACHE_RAM=0 ollama serve`, or set it in the systemd unit (`Environment="LLAMA_ARG_CACHE_RAM=0"`).

To check, send one request and look in the server log (`%LOCALAPPDATA%\Ollama\server.log` on Windows). It must say `prompt cache is disabled`, not `prompt cache is enabled, size limit: 8192 MiB`.

For example, in PowerShell before starting the backend:

```powershell
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434"
$env:OLLAMA_MODEL = "qwen2.5:3b"
```

On macOS/Linux, use `export OLLAMA_BASE_URL=http://127.0.0.1:11434` and `export OLLAMA_MODEL=qwen2.5:3b`.
The backend does not automatically load `.env` files. Retrieval settings remain defined in code:

- Embedding model: `BAAI/bge-m3` (`max_seq_length` 512)
- Hybrid search: BM25 over `knowledge_base/chunks/chunks.jsonl`, fused by reciprocal rank fusion (`HYBRID_SEARCH_ENABLED`)
- ChromaDB path: `knowledge_base/vector_store/chroma/`
- Collection name: `ceng_advisor_chunks`

Relevant files:

- `backend/app/core/llm_config.py`
- `backend/app/core/retrieval_config.py`

## Run With Docker Compose

Install Docker Engine with Compose v2 or Docker Desktop using Linux containers. Run these commands from the project root. The prepared knowledge-base files listed above must be present before building.

```bash
docker compose config --quiet
docker compose build
docker compose up -d
docker compose logs -f ollama backend
```

Open `http://localhost:8080` for the website and `http://127.0.0.1:8000/docs` for API documentation. Check `http://127.0.0.1:8000/api/v1/readiness` before asking a question.

Compose runs three services:

- `ollama`: the `ollama/ollama` image, with models persisted in the `ollama_models` volume. It starts the server, pulls `qwen2.5:3b` when missing, and becomes healthy once the model is available. Later starts reuse the downloaded model.
- `backend`: Python 3.12, CPU PyTorch, and `requirements.txt`, with the prepared `knowledge_base` copied into the image. The embedding model `BAAI/bge-m3` (about 2.3 GB) downloads at build time and loads from the image cache at runtime; the backend container needs roughly 3 GB of RAM for it. It uses `OLLAMA_BASE_URL=http://ollama:11434` and `OLLAMA_MODEL=qwen2.5:3b`.
- `frontend`: a pnpm build served by nginx on port 8080. nginx proxies `/api/` to the backend with response buffering disabled for streaming answers.

The first build and model pull require internet access and several GB of free disk space; CPU inference can take time. Compose waits for the Ollama model health check before starting the backend, and for backend health before starting the frontend. Ollama is reachable within the Compose network; the backend's direct port is bound to loopback.

To stop the services while preserving the model download:

```bash
docker compose down
```

Rebuild after source or knowledge-base changes with `docker compose build`, then recreate services with `docker compose up -d`. The source tree is copied into the images; the containers do not modify the workspace knowledge base.

## Installation

Run all commands from the cloned project directory unless a command says otherwise.

### 1. Backend dependencies

Create and activate a Python virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"
```

On macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"
```

### 2. Frontend dependencies

The embedding download above (about 2.3 GB) is a one-time setup step; runtime retrieval uses the cached model offline.

```powershell
cd frontend
pnpm install --frozen-lockfile
cd ..
```

If `pnpm` is not installed globally, install it using your Node.js package manager before running the command above.

### 3. Ollama and local model

Install Ollama from the official Ollama distribution for your operating system, then pull the project model:

```powershell
ollama pull qwen2.5:3b
```

Verify that Ollama can see the model:

```powershell
ollama list
```

## Local Run Instructions

Use three terminals.

### Terminal 1: Start or verify Ollama

Ollama usually runs as a local background service. Verify it is available:

```powershell
ollama list
```

The list should include `qwen2.5:3b`.

### Terminal 2: Start the backend

From the project root:

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

On macOS/Linux:

```bash
source .venv/bin/activate
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Backend URLs:

- API root: `http://127.0.0.1:8000/`
- Health check: `http://127.0.0.1:8000/health`
- Readiness check: `http://127.0.0.1:8000/api/v1/readiness`
- Swagger docs: `http://127.0.0.1:8000/docs`

### Terminal 3: Start the frontend

From the project root:

```powershell
cd frontend
pnpm run dev
```

Open:

```text
http://localhost:5173
```

## Verify The System Is Running

1. Open `http://127.0.0.1:8000/health`.
2. Open `http://127.0.0.1:8000/api/v1/readiness`.
3. Confirm readiness reports the backend, vector store, and Ollama status.
4. Open `http://localhost:5173`.
5. Go to the AI Advisor page and ask a supported Computer Engineering question such as:

```text
What is Computer Engineering?
```

The answer should include retrieved source information when the system answers from the knowledge base.

## Production Build

Create a frontend production build:

```powershell
cd frontend
pnpm run build
```

Preview the built frontend locally:

```powershell
pnpm run preview
```

The preview command serves the built frontend only. The FastAPI backend and Ollama service must still be running for chat functionality.

Frontend browser checks use mocked API responses and do not run the RAG pipeline:

```bash
cd frontend
pnpm exec playwright install chromium
pnpm exec playwright test
```

To use installed Microsoft Edge on Windows instead, set `$env:PLAYWRIGHT_CHANNEL = "msedge"` before running `pnpm exec playwright test`. Checks cover 375, 768, and 1280 px widths, browser-session history and session IDs, Markdown citations, copying, theme preferences, metadata progress, and service errors.

## Deployment Readiness Guidance

The final application should be deployable on a machine that can run all required local services:

- FastAPI backend
- Built React/Vite frontend
- ChromaDB vector-store files from `knowledge_base/vector_store/chroma/`
- Ollama with `qwen2.5:3b` available to the backend

For a production-like deployment:

1. Install Python, Node.js, pnpm, and Ollama on the target machine.
2. Copy or clone the project repository, including required knowledge-base artifacts.
3. Install backend dependencies with `python -m pip install -r requirements.txt`.
4. Run `pnpm install --frozen-lockfile` from `frontend/`.
5. Pull the local model with `ollama pull qwen2.5:3b`.
6. Start Ollama on the target machine.
7. Start FastAPI with a production process manager or a supervised `uvicorn` command.
8. Run `pnpm run build` from `frontend/`.
9. Serve `frontend/dist/` using a static web server.
10. Set `VITE_API_BASE_URL` before building the frontend if the backend URL is not `http://127.0.0.1:8000`.

The deployed application must continue to use the locally hosted open-source Ollama model integrated with the RAG pipeline. Do not replace the local model with a commercial LLM API.

For deployment with Docker, use the Compose workflow above. For other deployments, serve API requests through the same origin or use an origin already allowed by the backend.

## Useful Test Commands

Run API tests:

```powershell
python -m unittest tests.test_api
```

Run broader backend regression tests:

```powershell
python -m unittest tests.test_rag_pipeline tests.test_retriever tests.test_llm_service
```

Do not rerun the comprehensive 80-case RAG evaluation unless a later measurement task explicitly requires it.

## Troubleshooting

### Ollama or model is not running

Symptoms:

- Readiness endpoint reports degraded status.
- Chat requests return a local service error.

Checks:

```powershell
ollama list
ollama pull qwen2.5:3b
```

Make sure the backend can reach Ollama at `http://127.0.0.1:11434`.

### Backend cannot connect to Ollama

Confirm Ollama is installed, running, and listening locally. The backend defaults to `http://127.0.0.1:11434`; override it with `OLLAMA_BASE_URL` before starting the backend. In Compose it must use the service address `http://ollama:11434`.

### Missing vector store or knowledge-base artifacts

Symptoms:

- Backend startup or readiness fails.
- Retrieval returns errors before generation.

Check that these paths exist:

- `knowledge_base/sources.json`
- `knowledge_base/chunks/chunks.jsonl`
- `knowledge_base/embeddings/embeddings.npy`
- `knowledge_base/vector_store/chroma/`
- `knowledge_base/vector_store/vector_store_manifest.json`

If they are missing in a fresh clone, restore the prepared artifacts from the project submission package before running the app.

### Frontend cannot reach the backend

By default the frontend calls:

```text
http://127.0.0.1:8000
```

If the backend runs somewhere else, set `VITE_API_BASE_URL` in `frontend/.env.local` before starting or building the frontend.

### Port conflicts

Default ports:

- Backend: `127.0.0.1:8000`
- Frontend dev server: `localhost:5173`
- Ollama: `127.0.0.1:11434`

If port `8000` is already in use, choose another backend port and update `VITE_API_BASE_URL` accordingly.

## Important Data Artifacts

Do not regenerate these artifacts unless a later stage explicitly requires it:

- `knowledge_base/raw/`
- `knowledge_base/processed/`
- `knowledge_base/chunks/`
- `knowledge_base/embeddings/`
- `knowledge_base/vector_store/chroma/`

The source registry page reads safe public metadata from `knowledge_base/sources.json` and does not expose local file paths.
