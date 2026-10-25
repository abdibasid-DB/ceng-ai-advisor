# Full 200-Question CENG AI Advisor Evaluation

Generated at: `2026-10-25T16:24:14+00:00`
Complete: `True`
Dataset: `docs\semantic-coverage-200-questions.json`

## Procedure

Official 200-question semantic coverage dataset; current backend query-resolution/session logic; current RAGPipeline, KB, Chroma collection, and Ollama model; evaluation-only scoring with citation-label validity and claim/evidence lexical support checks.

The scoring is stricter than citation-format checking: answered cases require valid citation labels, no built-in unsupported-generation warning, expected-topic evidence, and a lexical claim/evidence support check. It remains an automated evaluation and should not be represented as human proof of every factual claim.

## Aggregate Results

- correct_evidence_supported: 95/200 (47.5%)
- correct_insufficient_information: 32/200 (16.0%)
- incorrect_refusal_evidence_exists: 46/200 (23.0%)
- unsupported_incorrect_or_misleading: 27/200 (13.5%)
- runtime_error: 0/200 (0.0%)
- Answered cases with valid citation labels: 122/122 (100.0%)
- Answered cases passing evidence-support checks: 95/122 (77.9%)
- Mean latency: 35.15s

## Results By Student-Question Category

| Category | Total | Supported | Correct insuff. | Incorrect refusal | Unsupported/misleading | Runtime errors |
|---|---:|---:|---:|---:|---:|---:|
| ai_future | 14 | 11 | 0 | 1 | 2 | 0 |
| career_employment | 28 | 10 | 2 | 12 | 4 | 0 |
| complex | 12 | 4 | 0 | 5 | 3 | 0 |
| curriculum | 14 | 11 | 0 | 3 | 0 | 0 |
| cybersecurity | 12 | 10 | 0 | 2 | 0 | 0 |
| fundamentals | 12 | 8 | 0 | 1 | 3 | 0 |
| hardware_networks | 12 | 9 | 0 | 3 | 0 | 0 |
| mathematics | 12 | 8 | 0 | 3 | 1 | 0 |
| multi_turn | 22 | 8 | 1 | 6 | 7 | 0 |
| out_of_scope | 13 | 0 | 13 | 0 | 0 | 0 |
| programming_software | 18 | 11 | 0 | 5 | 2 | 0 |
| student_local | 18 | 5 | 3 | 5 | 5 | 0 |
| unsupported | 13 | 0 | 13 | 0 | 0 | 0 |

## Most Common Systematic Failures

- 25: false_refusal: generated answer did not address the question's distinctive topic terms
- 16: cited_passages_do_not_support_claim_terms
- 12: false_refusal: unsupported claim could not be matched to retrieved evidence
- 11: unsupported_generation: generated answer did not address the question's distinctive topic terms
- 3: false_refusal: retrieved evidence does not compare the requested learning order or prerequisites
- 1: false_refusal: retrieved evidence does not address required question terms: ['math']
- 1: false_refusal: cited passage does not support one or more answer claims
- 1: false_refusal: retrieved evidence does not address the requested learning alternatives
- 1: false_refusal: retrieved evidence does not contain salary evidence for Computer Engineering graduates or job outcomes
- 1: false_refusal: generated answer made a definite AI replacement claim without direct replacement evidence
- 1: false_refusal: retrieved evidence does not address required question terms: ['hard']

## Files

- Structured results: `full200-results.json`
- Report: `full200-report.md`
