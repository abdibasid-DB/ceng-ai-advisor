# AI-Powered Computer Engineering Student Advisor

## Project Purpose

AI-Powered Computer Engineering Student Advisor is a university project that helps students ask source-grounded questions about Computer Engineering education, curriculum, skills, careers, internships, AI, cybersecurity, and future technologies.

The system uses Retrieval-Augmented Generation (RAG) with a locally deployed open-source model through Ollama. It does not use commercial cloud LLM APIs such as OpenAI, Gemini, Claude, Azure OpenAI, Cohere, Perplexity, or similar services for answer generation.

## Architecture

```text
React + Vite
  -> FastAPI
  -> RAG pipeline
  -> ChromaDB vector store
  -> Ollama
  -> qwen2.5:3b
```

The frontend communicates with FastAPI only:

- Chat: `POST /api/v1/chat`
- Readiness: `GET /api/v1/readiness`
- Source registry metadata: `GET /api/v1/sources`

## Website Sections

- Home
- AI Advisor
- Computer Engineering
- Sources
- About Project

The AI Advisor page contains the working chatbot with current-session visible history, example questions, readiness status, loading feedback, citations, source cards, supporting passages, New Conversation, insufficient-information handling, out-of-scope handling, and controlled backend/network errors.

## Technology Stack

- Frontend: React + Vite
- Backend: FastAPI
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
- Vector database: ChromaDB
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
- Node.js 18 or newer. The current frontend lockfile supports Node.js `>=18.0.0`.
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

If this variable is not set, the frontend uses `http://127.0.0.1:8000`.

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

The current backend does not read runtime `.env` variables. Its local AI and retrieval settings are defined in code:

- Ollama base URL: `http://127.0.0.1:11434`
- Ollama model: `qwen2.5:3b`
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- ChromaDB path: `knowledge_base/vector_store/chroma/`
- Collection name: `ceng_advisor_chunks`

Relevant files:

- `backend/app/core/llm_config.py`
- `backend/app/core/retrieval_config.py`

Do not document or add fake backend environment variables unless the code is updated to support them.

## Installation

Run all commands from the cloned project directory unless a command says otherwise.

### 1. Backend dependencies

Create and activate a Python virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. Frontend dependencies

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
4. Install frontend dependencies with `pnpm install --frozen-lockfile`.
5. Pull the local model with `ollama pull qwen2.5:3b`.
6. Start Ollama on the target machine.
7. Start FastAPI with a production process manager or a supervised `uvicorn` command.
8. Build the frontend with `pnpm run build`.
9. Serve `frontend/dist/` using a static web server.
10. Set `VITE_API_BASE_URL` before building the frontend if the backend URL is not `http://127.0.0.1:8000`.

The deployed application must continue to use the locally hosted open-source Ollama model integrated with the RAG pipeline. Do not replace the local model with a commercial LLM API.

Docker and Docker Compose are encouraged by the WEX428 guideline, but they are optional for this project and are not required to run the current implementation.

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

Confirm Ollama is installed, running, and listening locally. The backend currently expects Ollama at `http://127.0.0.1:11434`; this is defined in `backend/app/core/llm_config.py`.

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
