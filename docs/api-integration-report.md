# Stage 16 - FastAPI Backend / RAG API Integration

Date: 2026-09-16

## Objective

Stage 16 exposes the completed Stage 15C local RAG pipeline through a FastAPI REST API. This stage is backend/API only. It does not implement the React chatbot UI, rebuild embeddings, rebuild ChromaDB, alter retrieval thresholds, or add any commercial cloud LLM API.

## Architecture

Request flow:

```text
Client
  -> FastAPI
  -> cached RAGPipeline
  -> Retriever
  -> local ChromaDB collection: ceng_advisor_chunks
  -> local Ollama
  -> qwen2.5:3b
  -> structured JSON answer
```

The API reuses the existing Stage 15C pipeline from `backend/app/rag/rag_pipeline.py`.

## Endpoint

- Method: `POST`
- Path: `/api/v1/chat`
- Request content type: `application/json`
- Response model: `ChatResponse`

Example request:

```json
{
  "question": "What is Computer Engineering?"
}
```

## Request Schema

Model: `ChatRequest`

- `question`: required string
- Empty and whitespace-only questions are rejected.
- Maximum question length: 500 characters.

The 500-character limit is used to prevent very large arbitrary prompts from being sent to the local model during a university demo.

## Response Schema

Model: `ChatResponse`

Main fields:

- `question`
- `status`
- `answer`
- `llm_called`
- `sources`
- `retrieved_context`
- `retrieval_metadata`
- `timing`
- `citation_metadata`
- `answer_warnings`
- `model`
- `error`

## Source Schema

Model: `SourceResponse`

Fields:

- `source_id`
- `title`
- `source_name`
- `source_type`
- `url`
- `category`
- `best_similarity_score`
- `similarity_score`
- `supporting_chunk_ids`
- `evidence_labels`
- `section_headings`
- `supporting_passages`

The API does not ask Qwen to generate source metadata. Source metadata comes from the existing retrieval and RAG result.

## Answer Statuses

Supported statuses are preserved from Stage 15C:

- `answered`
- `insufficient_information`
- `out_of_scope`
- `error`

`insufficient_information` and `out_of_scope` are not converted into normal generated answers.

## HTTP Status Behavior

- Valid processed request with `answered`: HTTP 200
- Valid processed request with `insufficient_information`: HTTP 200
- Valid processed request with `out_of_scope`: HTTP 200
- Invalid request body or validation failure: HTTP 422 from FastAPI/Pydantic
- Internal RAG/local service error: HTTP 503 with controlled JSON response and `status: "error"`

Normal insufficient evidence is not treated as HTTP 500.

## RAG Lifecycle and Reuse

The API uses a cached `get_rag_pipeline()` dependency with `lru_cache(maxsize=1)`.

This reuses:

- `RAGPipeline`
- `Retriever`
- ChromaDB persistent client/collection
- local LLM service object

The embedding model remains lazy-loaded by the retriever when the first retrieval happens.

## Blocking Inference Handling

The chat endpoint is implemented as a regular synchronous `def` endpoint. FastAPI runs synchronous route work in its threadpool, which is appropriate for the existing blocking local retrieval and Ollama calls.

No task queue was added in Stage 16.

## Timeout and Error Handling

The API preserves the existing local Ollama timeout and error handling from `LocalLLMService`.

The API returns controlled service errors instead of exposing:

- Python tracebacks
- local filesystem details
- internal prompts
- secrets

During Stage 16 validation, a live answer truncation issue was discovered. A narrow validation fix was added so every answer bullet must have a citation and must end cleanly. This prevents visibly incomplete answers from being served as successful responses.

## CORS

Development CORS is configured for the expected Vite frontend origins:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

Wildcard origins are not used.

## Health and Readiness

Existing endpoint preserved:

- `GET /health`

Returns:

```json
{
  "status": "healthy"
}
```

New lightweight readiness endpoint:

- `GET /api/v1/readiness`

It checks:

- backend status
- vector-store collection availability/count
- local Ollama model availability

It does not run full RAG generation.

## Swagger

FastAPI Swagger is available at:

```text
http://127.0.0.1:8000/docs
```

The request and response models are visible in the generated documentation.

## Tests

API unit tests:

```powershell
python -m unittest tests.test_api
```

Result:

- 13 API tests passed

Full regression suite:

```powershell
python -m unittest tests.test_rag_pipeline tests.test_retriever tests.test_llm_service tests.test_api
```

Result:

- 59 tests passed

## Live Integration Results

Live results are stored in:

- `docs/api-live-integration-results.json`

Questions tested:

1. Supported: `What is Computer Engineering?`
2. Curriculum: `What courses are taught in Computer Engineering?`
3. Out of scope: `What is the best chocolate cake recipe?`

Final live results:

| Case | HTTP | RAG status | LLM called | Latency |
|---|---:|---|---|---:|
| Supported | 200 | `answered` | true | 24.634s |
| Curriculum | 200 | `answered` | true | 23.827s |
| Out of scope | 200 | `out_of_scope` | false | 0.055s |

Average live latency across the three checks:

- 16.172s

## Security and Input Hygiene

Implemented:

- bounded question length
- empty/whitespace validation
- FastAPI malformed JSON handling
- controlled internal error response
- no authentication, because this is a local university project stage

## Dependencies

No new dependency was added. Existing dependencies were sufficient:

- FastAPI
- Uvicorn
- Sentence Transformers
- ChromaDB
- local Ollama through standard-library HTTP calls

## Limitations

- Local inference can still take 20-25 seconds for answered questions.
- Readiness checks Ollama availability but does not generate an answer.
- No frontend chatbot UI is implemented in this stage.
- No authentication is implemented.

## Final Decision

A. FASTAPI RAG BACKEND READY FOR FRONTEND INTEGRATION
