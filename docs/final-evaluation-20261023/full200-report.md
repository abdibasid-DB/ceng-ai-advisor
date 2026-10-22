# Full 200-Question CENG AI Advisor Evaluation

Generated at: `2026-10-22T20:33:35+00:00`
Complete: `True`
Dataset: `docs\semantic-coverage-200-questions.json`

## Procedure

Official 200-question semantic coverage dataset; current backend query-resolution/session logic; current RAGPipeline, KB, Chroma collection, and Ollama model; evaluation-only scoring with citation-label validity and claim/evidence lexical support checks.

The scoring is stricter than citation-format checking: answered cases require valid citation labels, no built-in unsupported-generation warning, expected-topic evidence, and a lexical claim/evidence support check. It remains an automated evaluation and should not be represented as human proof of every factual claim.

## Aggregate Results

- correct_evidence_supported: 94/200 (47.0%)
- correct_insufficient_information: 33/200 (16.5%)
- incorrect_refusal_evidence_exists: 43/200 (21.5%)
- unsupported_incorrect_or_misleading: 30/200 (15.0%)
- runtime_error: 0/200 (0.0%)
- Answered cases with valid citation labels: 124/124 (100.0%)
- Answered cases passing evidence-support checks: 94/124 (75.8%)
- Mean latency: 28.41s

## Results By Student-Question Category

| Category | Total | Supported | Correct insuff. | Incorrect refusal | Unsupported/misleading | Runtime errors |
|---|---:|---:|---:|---:|---:|---:|
| ai_future | 14 | 10 | 0 | 3 | 1 | 0 |
| career_employment | 28 | 12 | 3 | 9 | 4 | 0 |
| complex | 12 | 7 | 0 | 4 | 1 | 0 |
| curriculum | 14 | 9 | 0 | 3 | 2 | 0 |
| cybersecurity | 12 | 9 | 0 | 2 | 1 | 0 |
| fundamentals | 12 | 10 | 0 | 0 | 2 | 0 |
| hardware_networks | 12 | 7 | 0 | 4 | 1 | 0 |
| mathematics | 12 | 5 | 0 | 5 | 2 | 0 |
| multi_turn | 22 | 10 | 1 | 3 | 8 | 0 |
| out_of_scope | 13 | 0 | 13 | 0 | 0 | 0 |
| programming_software | 18 | 11 | 0 | 3 | 4 | 0 |
| student_local | 18 | 4 | 3 | 7 | 4 | 0 |
| unsupported | 13 | 0 | 13 | 0 | 0 | 0 |

## Most Common Systematic Failures

- 18: cited_passages_do_not_support_claim_terms
- 15: false_refusal: generated answer did not address the question's distinctive topic terms
- 14: false_refusal: unsupported claim could not be matched to retrieved evidence
- 12: unsupported_generation: generated answer did not address the question's distinctive topic terms
- 4: false_refusal: cited passage does not support one or more answer claims
- 3: false_refusal: retrieved evidence does not compare the requested learning order or prerequisites
- 2: false_refusal: generated answer gave cybersecurity pathway advice beyond the retrieved framework evidence
- 1: false_refusal: retrieved evidence does not address the requested learning alternatives
- 1: false_refusal: retrieved evidence has too little overlap with the question terms: ['agreements', 'erasmus']
- 1: false_refusal: retrieved evidence does not contain salary evidence for Computer Engineering graduates or job outcomes
- 1: false_refusal: generated answer made a definite AI replacement claim without direct replacement evidence
- 1: false_refusal: retrieved evidence does not address required question terms: ['hard']

## Files

- Structured results: `full200-results.json`
- Report: `full200-report.md`
