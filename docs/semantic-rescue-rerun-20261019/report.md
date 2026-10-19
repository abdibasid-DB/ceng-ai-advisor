# Full 200-Question CENG AI Advisor Evaluation

Generated at: `2026-10-19T16:17:27+00:00`
Complete: `True`
Dataset: `docs\semantic-coverage-200-questions.json`

## Procedure

Official 200-question semantic coverage dataset; current backend query-resolution/session logic; current RAGPipeline, KB, Chroma collection, and Ollama model; evaluation-only scoring with citation-label validity and claim/evidence lexical support checks.

The scoring is stricter than citation-format checking: answered cases require valid citation labels, no built-in unsupported-generation warning, expected-topic evidence, and a lexical claim/evidence support check. It remains an automated evaluation and should not be represented as human proof of every factual claim.

## Aggregate Results

- correct_evidence_supported: 11/43 (25.6%)
- correct_insufficient_information: 0/43 (0.0%)
- incorrect_refusal_evidence_exists: 22/43 (51.2%)
- unsupported_incorrect_or_misleading: 10/43 (23.3%)
- runtime_error: 0/43 (0.0%)
- Answered cases with valid citation labels: 21/21 (100.0%)
- Answered cases passing evidence-support checks: 11/21 (52.4%)
- Mean latency: 60.43s

## Results By Student-Question Category

| Category | Total | Supported | Correct insuff. | Incorrect refusal | Unsupported/misleading | Runtime errors |
|---|---:|---:|---:|---:|---:|---:|
| ai_future | 6 | 1 | 0 | 5 | 0 | 0 |
| career_employment | 9 | 1 | 0 | 6 | 2 | 0 |
| complex | 3 | 1 | 0 | 2 | 0 | 0 |
| curriculum | 4 | 1 | 0 | 3 | 0 | 0 |
| cybersecurity | 1 | 1 | 0 | 0 | 0 | 0 |
| fundamentals | 1 | 1 | 0 | 0 | 0 | 0 |
| hardware_networks | 3 | 1 | 0 | 1 | 1 | 0 |
| mathematics | 4 | 1 | 0 | 1 | 2 | 0 |
| multi_turn | 4 | 0 | 0 | 1 | 3 | 0 |
| programming_software | 2 | 1 | 0 | 1 | 0 | 0 |
| student_local | 6 | 2 | 0 | 2 | 2 | 0 |

## Most Common Systematic Failures

- 10: false_refusal: unsupported claim could not be matched to retrieved evidence
- 9: false_refusal: generated answer did not address the question's distinctive topic terms
- 5: unsupported_generation: generated answer did not address the question's distinctive topic terms
- 5: cited_passages_do_not_support_claim_terms
- 2: false_refusal: cited passage does not support one or more answer claims
- 1: false_refusal: generated answer attributed broad technology roles to Computer Engineering graduates without direct role evidence

## Files

- Structured results: `results.json`
- Report: `report.md`
