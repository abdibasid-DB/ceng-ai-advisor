# Stage 15 - Core RAG Pipeline Integration Report

## Scope

Stage 15 integrates the existing retrieval layer with the existing local Ollama LLM service. This stage does not add FastAPI chatbot endpoints, React chatbot UI, chat history, deployment, preprocessing, chunking, embeddings, or vector-store rebuilding.

Commercial cloud LLM APIs are not used. The pipeline uses the local Ollama model selected in Stage 14: `qwen2.5:3b`.

## Files Created or Modified

- `backend/app/rag/rag_pipeline.py`: core RAG orchestration module.
- `scripts/test_rag_pipeline.py`: command-line runner for one question or selected representative test cases.
- `tests/rag_test_cases.json`: representative Stage 15 RAG test dataset.
- `tests/test_rag_pipeline.py`: mocked unit tests for pipeline behavior and safety controls.
- `docs/rag-live-test-results.json`: saved live local RAG validation output.
- `docs/rag-pipeline-report.md`: this report.
- `README.md`: updated with Stage 15 RAG test commands.

## Pipeline Architecture

The pipeline flow is:

1. Normalize the user question.
2. Retrieve candidate chunks through the existing `Retriever`.
3. Check retrieval sufficiency and out-of-scope status before generation.
4. Apply conservative unsupported-evidence guards for high-risk exact facts and weak topic coverage.
5. Build a deterministic context using source labels `[S1]`, `[S2]`, etc.
6. Send a grounded prompt to the local Ollama LLM only when evidence is acceptable.
7. Validate the model response for placeholder output and required inline evidence labels.
8. Return a structured result containing status, answer, sources, retrieved context, retrieval metadata, timing, model information, and error information.

## Retrieval and Context Settings

- Retriever Top-K: `5`
- Candidate Top-K: `12`
- Similarity threshold: `0.30`
- Minimum relevant retrieved chunks: inherited from the existing retriever configuration
- Context character budget: `4500`
- Per-passage character budget: `900`
- LLM output budget: `num_predict=180`

The context budget is character-based and deterministic. No tokenizer dependency was added.

## Prompt Strategy

The prompt instructs the model to:

- Use only supplied context.
- Avoid outside knowledge.
- Avoid invented facts, statistics, salaries, policies, course names, career claims, source IDs, or URLs.
- Return `INSUFFICIENT_INFORMATION` when the supplied context does not directly support an answer.
- Keep output concise.
- Include inline source labels such as `[S1]` or `[S2]`.

Source attribution is produced and validated in Python. The source list is deduplicated by source ID and URL, while preserving supporting chunk IDs and evidence labels.

## Supported Statuses

- `answered`: retrieval was sufficient, the LLM was called, and the generated answer passed safety validation.
- `insufficient_information`: the question is in scope but the available retrieved evidence is not strong enough.
- `out_of_scope`: the question is outside the Computer Engineering advisor domain.
- `error`: retrieval, context construction, local LLM generation, or answer validation failed.

## Safety Controls

The pipeline now blocks LLM generation when:

- Retrieval evidence is insufficient.
- The query is out of scope.
- A high-risk exact fact is requested but matching evidence terms are missing, such as tuition, deadlines, quotas, scholarships, or salaries.
- A cybersecurity question retrieves no cybersecurity-category evidence.

The pipeline also rejects LLM output when:

- It contains copied placeholder text such as `answer text`.
- It does not include required inline evidence labels.

These controls deliberately favor conservative refusal over unsupported answers.

## Live Integration Results

The final saved live run used `qwen2.5:3b` through Ollama and the existing local ChromaDB collection. Results are saved in `docs/rag-live-test-results.json`.

| Test Case | Status | LLM Called | Retrieval Time | LLM Time | Total Time | Notes |
|---|---:|---:|---:|---:|---:|---|
| `curriculum_supported` | `answered` | Yes | 0.494s | 3.523s | 4.018s | Returned cited curriculum items. |
| `cybersecurity_supported` | `insufficient_information` | No | 0.069s | 0.000s | 0.069s | Blocked because retrieved evidence lacked a cybersecurity-category source. |
| `unsupported_in_domain` | `insufficient_information` | No | 0.057s | 0.000s | 0.057s | Blocked exact tuition question because no tuition/fee evidence was retrieved. |
| `out_of_scope_football` | `out_of_scope` | No | 0.033s | 0.000s | 0.033s | Blocked before LLM generation. |

Earlier exploratory live runs showed that broader department and programming questions can retrieve useful evidence, but `qwen2.5:3b` sometimes omitted inline citations or produced loosely grounded statements. The final pipeline therefore treats missing inline citations as an error instead of accepting the answer.

## Unit and Validation Results

Commands run:

```powershell
python -m py_compile backend/app/rag/rag_pipeline.py scripts/test_rag_pipeline.py tests/test_rag_pipeline.py
```

```powershell
python -m unittest tests.test_rag_pipeline
```

Result:

- `14` mocked RAG pipeline tests passed.

Combined regression command:

```powershell
python -m unittest tests.test_rag_pipeline tests.test_retriever tests.test_llm_service
```

Result:

- `29` tests passed across RAG pipeline, retriever, and local LLM service tests.

JSON validation:

- `tests/rag_test_cases.json`: valid JSON.
- `docs/rag-live-test-results.json`: valid JSON.

## Commands for Local RAG Testing

Run one question:

```powershell
python scripts\test_rag_pipeline.py "What courses are taught in Computer Engineering?"
```

Run selected representative cases:

```powershell
python scripts\test_rag_pipeline.py --preset --ids curriculum_supported cybersecurity_supported unsupported_in_domain out_of_scope_football
```

Run the full Stage 15 preset dataset:

```powershell
python scripts\test_rag_pipeline.py --preset
```

## Remaining Weaknesses

- The small local model can be inconsistent with citation formatting.
- Broad questions may retrieve mixed sources, such as curriculum and general programming-advising material together.
- Some cybersecurity questions need stronger category-specific retrieval evidence before the system should answer them.
- Some generated answers may be too narrow because the context budget only includes top retrieved chunks.
- Live generation latency can vary from a few seconds to much longer depending on the prompt and local Ollama state.

## Readiness Decision

Decision: **B - not ready to proceed directly to API/chatbot integration yet.**

The core RAG pipeline is implemented and safety behavior is substantially improved, but the live tests revealed answer-quality and citation-compliance issues from the local LLM. The pipeline now fails closed when citations are missing or evidence is weak, which is safe, but the next step should be a focused Stage 15B refinement pass on retrieval targeting and prompt/answer validation before exposing this through FastAPI or the React frontend.
