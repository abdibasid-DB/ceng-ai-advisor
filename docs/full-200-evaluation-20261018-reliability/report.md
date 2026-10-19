# Full 200-Question CENG AI Advisor Evaluation

Generated at: `2026-10-17T19:56:24+00:00`
Complete: `False`
Dataset: `docs\semantic-coverage-200-questions.json`

## Procedure

Official 200-question semantic coverage dataset; current backend query-resolution/session logic; current RAGPipeline, KB, Chroma collection, and Ollama model; evaluation-only scoring with citation-label validity and claim/evidence lexical support checks.

The scoring is stricter than citation-format checking: answered cases require valid citation labels, no built-in unsupported-generation warning, expected-topic evidence, and a lexical claim/evidence support check. It remains an automated evaluation and should not be represented as human proof of every factual claim.

## Aggregate Results

- correct_evidence_supported: 90/193 (46.6%)
- correct_insufficient_information: 34/193 (17.6%)
- incorrect_refusal_evidence_exists: 50/193 (25.9%)
- unsupported_incorrect_or_misleading: 19/193 (9.8%)
- runtime_error: 0/193 (0.0%)
- Answered cases with valid citation labels: 109/109 (100.0%)
- Answered cases passing evidence-support checks: 90/109 (82.6%)
- Mean latency: 26.55s

## Results By Student-Question Category

| Category | Total | Supported | Correct insuff. | Incorrect refusal | Unsupported/misleading | Runtime errors |
|---|---:|---:|---:|---:|---:|---:|
| ai_future | 14 | 7 | 0 | 6 | 1 | 0 |
| career_employment | 28 | 10 | 2 | 12 | 4 | 0 |
| complex | 12 | 6 | 1 | 4 | 1 | 0 |
| curriculum | 14 | 8 | 0 | 4 | 2 | 0 |
| cybersecurity | 12 | 9 | 0 | 1 | 2 | 0 |
| fundamentals | 12 | 9 | 0 | 1 | 2 | 0 |
| hardware_networks | 12 | 8 | 0 | 4 | 0 | 0 |
| mathematics | 12 | 8 | 0 | 4 | 0 | 0 |
| multi_turn | 15 | 6 | 1 | 4 | 4 | 0 |
| out_of_scope | 13 | 0 | 13 | 0 | 0 | 0 |
| programming_software | 18 | 13 | 0 | 3 | 2 | 0 |
| student_local | 18 | 6 | 4 | 7 | 1 | 0 |
| unsupported | 13 | 0 | 13 | 0 | 0 | 0 |

## Most Common Systematic Failures

- 22: false_refusal: generated answer did not address the question's distinctive topic terms
- 18: false_refusal: unsupported claim could not be matched to retrieved evidence
- 11: cited_passages_do_not_support_claim_terms
- 8: unsupported_generation: generated answer did not address the question's distinctive topic terms
- 3: false_refusal: cited passage does not support one or more answer claims
- 2: false_refusal: retrieved evidence does not compare the requested learning order or prerequisites
- 1: false_refusal: retrieved evidence does not address the requested learning alternatives
- 1: false_refusal: retrieved evidence does not directly address hackathons or student coding competitions
- 1: false_refusal: retrieved evidence has too little overlap with the question terms: ['long', 'until']
- 1: false_refusal: retrieved evidence has too little overlap with the question terms: ['freelancing', 'start', 'studying']
- 1: false_refusal: retrieved evidence has too little overlap with the question terms: ['exams', 'explains', 'grading', 'official', 'regulation']

## Files

- Structured results: `results.json`
- Report: `report.md`
