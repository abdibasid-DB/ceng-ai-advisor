# Stage 15B - RAG Grounding and Citation Refinement Report

## Scope

Stage 15B refined the existing core RAG pipeline only. It did not add FastAPI chatbot endpoints, React chatbot UI, chat history, source cards, deployment work, preprocessing, chunking, embeddings, ChromaDB rebuilding, or corpus changes.

The pipeline remains local-only:

- Retriever: existing ChromaDB collection `ceng_advisor_chunks`
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- LLM: local Ollama `qwen2.5:3b`
- Commercial cloud LLM APIs: not used

## Stage 15 Problem

Stage 15 showed that the local model could retrieve useful context but did not reliably follow citation instructions. Some generated answers omitted inline `[S#]` citations or placed source labels only in a final source summary. One stricter prompt also caused the model to copy placeholder wording such as `answer text`.

Because source attribution is essential for a university RAG system, Stage 15B focused on citation validation, controlled retry, and fail-closed behavior.

## Actual Citation Failure Modes Observed

Observed during Stage 15 and Stage 15B live testing:

- Missing inline citations even when the answer text was relevant.
- A final source summary instead of claim-level inline citations.
- Prompt-copy behavior after an overly template-like instruction.
- `USED_SOURCES` appearing as answer text in one live run before parsing was improved.
- Valid citation labels attached to answers that still contained weakly grounded or overly broad claims.

Not observed in the final Stage 15B live set:

- Invented nonexistent labels such as `[S8]`.
- Commercial/cloud model usage.
- Out-of-scope questions reaching the LLM.

## Prompt Changes

The prompt was shortened and simplified for `qwen2.5:3b`.

The current prompt tells the model to:

- Use only supplied context.
- Avoid outside knowledge.
- Avoid invented facts, statistics, salaries, policies, source IDs, URLs, and career claims.
- Return `INSUFFICIENT_INFORMATION` if context does not directly support the answer.
- Cite only supplied labels such as `[S1]`.
- Return two simple sections: `ANSWER` and `USED_SOURCES`.

The prompt no longer includes a concrete sample answer that the model can copy.

## Structured Output Decision

Decision: use a simple two-section text format, not JSON.

Chosen format:

```text
ANSWER:
- answer sentence [S1]

USED_SOURCES:
S1
```

Reason: a small local model is more reliable with a simple format than with strict JSON. Python still treats retrieval metadata as authoritative; model text is never trusted for URLs, titles, source IDs, or chunk IDs.

## Citation Validation

Python now validates citations after generation.

Rules:

- At least one valid `[S#]` citation is required for answered responses.
- Every cited label must exist in the current retrieved context.
- Labels must map to actual retrieved chunks.
- Retrieved chunks must map to source IDs.
- `USED_SOURCES` labels, when present, must also exist in the current context.
- Nonexistent labels are rejected.
- Missing citations are rejected.
- Placeholder-style output is rejected.
- Python does not attach or fabricate citations after generation.

## Citation Normalization

Safe normalization is limited to unambiguous source-label formatting:

- `[S 1]` becomes `[S1]`.
- `[S1.]` becomes `[S1]`.

The pipeline does not convert `[1]` into `[S1]`, because that would infer attribution.

## Retry Strategy

Maximum generations per question: `2`

- Initial generation: `1`
- Citation-correction retry: at most `1`

The retry is used only when retrieval evidence is sufficient and the model output fails citation validation. The retry asks the model to rewrite using only the supplied context and valid labels. If retry still fails, the pipeline returns a safe error instead of exposing an ungrounded answer.

## Fail-Closed Behavior

The pipeline still refuses before generation when:

- Retrieval evidence is insufficient.
- The question is out of scope.
- A high-risk exact fact such as tuition/fees lacks matching evidence.
- A cybersecurity question lacks cybersecurity-category evidence.

The pipeline returns a controlled non-success result when:

- Citations remain invalid after the permitted retry.
- The model produces placeholder or copied prompt text.
- The model fails or times out.

## Live Test Results

Final merged live results are saved in:

`docs/rag-grounding-test-results.json`

Batch files preserved:

- `docs/rag-grounding-test-results-supported-a.json`
- `docs/rag-grounding-test-results-supported-b.json`
- `docs/rag-grounding-test-results-guards.json`

| Case | Status | LLM Called | Citation Valid | Retry | Total Time |
|---|---:|---:|---:|---:|---:|
| curriculum_supported | answered | yes | yes | no | 28.044s |
| programming_supported | answered | yes | yes | no | 40.433s |
| career_supported | answered | yes | yes | no | 41.721s |
| programming_paraphrase | answered | yes | yes | no | 51.559s |
| ai_supported | answered | yes | yes | no | 47.301s |
| internship_supported | answered | yes | yes | no | 34.494s |
| multi_topic | answered | yes | yes | no | 36.293s |
| cybersecurity_supported | insufficient_information | no | n/a | no | 0.535s |
| unsupported_in_domain | insufficient_information | no | n/a | no | 0.064s |
| out_of_scope_cake | out_of_scope | no | n/a | no | 0.032s |
| out_of_scope_football | out_of_scope | no | n/a | no | 0.028s |
| out_of_scope_washing_machine | out_of_scope | no | n/a | no | 0.031s |

## Citation Reliability

Measured on the Stage 15B live test set.

- Total live cases: `12`
- LLM-called cases: `7`
- Supported answered cases: `7`
- Initial-generation valid citation count: `7/7`
- Initial-generation valid citation rate: `100%`
- Cases requiring retry: `0`
- Retry successes: `0`
- Final valid citation count: `7/7`
- Final valid citation rate: `100%`
- Final citation failures: `0`

This is a small representative validation set, not a statistical accuracy claim.

## Curriculum Findings

The curriculum question returned valid citations and did not invent nonexistent citation labels. However, the answer was somewhat broad and described source coverage rather than giving a polished course list. It cited OSTIM curriculum chunks correctly, but Brown CS material still appeared in retrieval context. This remains a retrieval-ranking and answer-quality limitation.

## Cybersecurity Findings

Cybersecurity remained safe:

- Status: `insufficient_information`
- LLM called: `false`
- Reason: retrieved evidence did not include a cybersecurity-category source

This should be documented as a knowledge-base or retrieval limitation rather than weakened just to force an answer.

## Paraphrase Findings

The programming paraphrase question returned valid citations without retry. It handled the reworded question, but the answer mixed language evidence with related curriculum evidence. Citation formatting was stable, but answer specificity can still improve.

## Multi-Source Findings

The career and multi-topic cases used multiple retrieved labels successfully. Citation validation passed. The multi-topic answer combined GPA, projects, and internships, but some claims were weakly supported by general career guidance rather than direct Computer Engineering evidence.

## Out-of-Scope Regression

All out-of-scope cases skipped the LLM:

- Chocolate cake recipe: `out_of_scope`
- Football match: `out_of_scope`
- Washing machine repair: `out_of_scope`

No general-knowledge fallback occurred.

## Unsupported In-Domain Regression

The exact tuition question returned:

- Status: `insufficient_information`
- LLM called: `false`

The pipeline correctly treated in-domain wording as not automatically answerable.

## Hallucination and Grounding Review

Citation formatting improved substantially. The remaining problem is not label validity; it is claim-level grounding quality.

Observed remaining risks:

- The AI answer inferred that AI suggests integration rather than replacement. This is plausible from retrieved sources but not directly stated.
- The multi-topic answer included advice-style synthesis from general career sources.
- Programming answers sometimes include related courses and concepts instead of directly listing programming languages.

The system now prevents uncited answers, but it does not yet prove every cited sentence is fully entailed by the cited passage.

## Latency

For answered supported live cases:

- Average initial LLM generation latency: `39.781s`
- Maximum initial LLM generation latency: `50.817s`
- Average total answered-case latency: `39.978s`
- Retry latency in final live set: `0.000s`, because no final live cases required retry

Guarded/refusal cases completed quickly because they skipped the LLM.

Live-demo practicality:

- Safe refusal behavior is fast.
- Generated answers are slow but still possible for a university demo if only a few questions are asked.
- The current local model and prompt are not ideal for a polished low-latency chatbot experience.

## Automated Tests

Expanded RAG unit tests now cover:

- Valid single citation
- Multiple valid citations
- Nonexistent citation rejection
- Malformed `[S 1]` normalization
- Numeric `[1]` rejection
- Missing citation behavior
- Controlled retry success
- Failed retry safe error
- Maximum one retry
- Source mapping
- Structured source integrity
- Out-of-scope skip behavior
- Insufficient-evidence skip behavior
- LLM error safety

Final regression command:

```powershell
python -m unittest tests.test_rag_pipeline tests.test_retriever tests.test_llm_service
```

Result:

- `38` tests passed.

JSON validation:

- `docs/rag-grounding-test-results.json`: valid JSON
- `tests/rag_test_cases.json`: valid JSON

## Dependencies

No dependencies were added.

## Files Created or Modified

- `backend/app/rag/rag_pipeline.py`
- `scripts/test_rag_pipeline.py`
- `tests/test_rag_pipeline.py`
- `docs/rag-grounding-test-results-supported-a.json`
- `docs/rag-grounding-test-results-supported-b.json`
- `docs/rag-grounding-test-results-guards.json`
- `docs/rag-grounding-test-results.json`
- `docs/rag-grounding-refinement-report.md`

## Readiness Decision

Decision: **B - RAG grounding/quality issues still require resolution.**

Stage 15B fixed the citation mechanics enough to avoid uncited answers, fabricated source labels, and general-knowledge fallback. However, live testing still shows claim-level grounding and answer-quality weaknesses. Before API/chatbot integration, the project should add stricter answer-quality controls or improve retrieval/prompting so answers are not merely cited, but also directly supported and useful.
