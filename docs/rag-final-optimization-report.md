# Stage 15C - Final RAG Grounding Quality and Latency Optimization

Date: 2026-09-16

## Scope

Stage 15C focused only on final grounding quality and latency optimization for the existing local RAG pipeline. It did not add API routes, frontend chatbot features, preprocessing, chunking, embeddings, ChromaDB rebuilds, or any commercial cloud LLM API.

The local model remains:

- Ollama model: `qwen2.5:3b`
- Commercial LLM APIs: not used
- Maximum citation correction retries: 1

## Stage 15B Baseline

The Stage 15B live validation showed correct citation mechanics but exposed two remaining issues:

- Valid citation labels did not always guarantee claim-level grounding.
- Average answered-case LLM generation latency was 39.781 seconds.

## Changes Made

### Prompt and Output Control

The grounded-answer prompt was tightened so the model must:

- use only supplied context
- avoid outside knowledge
- avoid invented facts, statistics, policies, course names, career claims, source IDs, or URLs
- cite the exact label whose passage directly states the fact
- answer only the supported part of a question
- prefer short supported answers over speculative answers
- return `INSUFFICIENT_INFORMATION` when context does not directly support the answer

The answer format was constrained to 1-3 short bullets.

### Latency Settings

The default Stage 15C generation/context settings are:

- `MAX_CONTEXT_CHARACTERS = 3000`
- `MAX_PASSAGE_CHARACTERS = 700`
- `RAG_NUM_PREDICT = 140`
- `LLM_KEEP_ALIVE = "10m"`

This keeps responses shorter than Stage 15B while avoiding mid-answer truncation seen with a 120-token generation cap.

### Context Selection

Two context-selection refinements were added:

- Curriculum questions prefer official curriculum and course-description sources.
- Non-curriculum questions prefer unique source IDs first and omit duplicate same-source chunks when at least three unique sources are available.

This reduced adjacent same-report citation confusion, especially in career answers.

### Insufficient-Information Guards

Additional pre-LLM safety guards were added for cases where retrieved evidence is superficially similar but not strong enough:

- AI replacement questions require direct replacement/displacement evidence.
- GPA/projects/internships comparison questions require directly comparative evidence.
- Existing unsupported tuition and weak cybersecurity behavior was preserved.

Natural local-model refusals such as "I don't have enough reliable information..." are now normalized to the pipeline's `insufficient_information` status.

## Live Validation

Final live results are stored in:

- `docs/rag-final-optimization-results.json`

Supporting small-batch files:

- `docs/rag-final-optimization-results-a.json`
- `docs/rag-final-optimization-results-b.json`
- `docs/rag-final-optimization-results-career.json`
- `docs/rag-final-optimization-results-ai.json`
- `docs/rag-final-optimization-results-multitopic.json`
- `docs/rag-final-optimization-results-safety.json`

Curriculum experiments are stored in:

- `docs/rag-final-optimization-experiments-curriculum.json`

## Final Live Results Summary

Representative cases tested: 9

- Answered: 4
- Insufficient information: 4
- Out of scope: 1
- Errors: 0
- LLM called: 4
- LLM skipped: 5

Covered cases:

- curriculum
- programming paraphrase
- careers
- AI replacement weak-evidence case
- internships
- multi-source/multi-topic weak-evidence case
- cybersecurity weak-evidence case
- unsupported in-domain tuition case
- out-of-scope cake recipe case

## Citation Reliability

- Initial citation reliability for answered cases: 4/4
- Cases requiring retry: 0
- Retry successes: 0
- Final citation reliability for answered cases: 4/4
- Final citation failures: 0

The one-correction-retry rule remains in place, but no final Stage 15C live case needed retry.

## Latency

Stage 15B answered-case average LLM generation latency:

- 39.781 seconds

Stage 15C answered-case average LLM generation latency:

- 19.465 seconds

Stage 15C answered-case generation latency range:

- Minimum: 5.440 seconds
- Maximum: 25.993 seconds

Stage 15C answered-case average total latency:

- 19.674 seconds

Average total latency across all 9 representative cases:

- 8.905 seconds

Approximate answered-generation latency improvement over Stage 15B:

- 51.1%

## Regression Tests

Complete regression suite:

```powershell
python -m unittest tests.test_rag_pipeline tests.test_retriever tests.test_llm_service
```

Result:

- 43 tests passed

## JSON Validation

Validated successfully:

- `docs/rag-final-optimization-results.json`
- `docs/rag-final-optimization-experiments-curriculum.json`

## Remaining Limitations

- Programming-language answers are limited by currently retrieved evidence. The system can cite Python strongly, but broader language recommendations need better source coverage.
- AI replacement questions are intentionally conservative. Without direct evidence about replacement/displacement, the pipeline now returns insufficient information.
- Some local Ollama generations still vary in latency, although answered-case latency is much lower than Stage 15B.
- The system is ready for API/chatbot integration, but final user-facing UX should display unsupported reasons and source context clearly.

## Final Decision

A. CORE RAG PIPELINE READY FOR API/CHATBOT INTEGRATION
