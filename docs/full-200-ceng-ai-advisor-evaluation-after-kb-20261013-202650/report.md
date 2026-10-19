# Full 200-Question CENG AI Advisor Evaluation

Generated at: `2026-10-13T17:27:46+00:00`
Complete: `True`
Dataset: `docs\semantic-coverage-200-questions.json`

## Procedure

Official 200-question semantic coverage dataset; current backend query-resolution/session logic; current RAGPipeline, KB, Chroma collection, and Ollama model; evaluation-only scoring with citation-label validity and claim/evidence lexical support checks.

The scoring is stricter than citation-format checking: answered cases require valid citation labels, no built-in unsupported-generation warning, expected-topic evidence, and a lexical claim/evidence support check. It remains an automated evaluation and should not be represented as human proof of every factual claim.

## Aggregate Results

- correct_evidence_supported: 0/200 (0.0%)
- correct_insufficient_information: 32/200 (16.0%)
- incorrect_refusal_evidence_exists: 5/200 (2.5%)
- unsupported_incorrect_or_misleading: 1/200 (0.5%)
- runtime_error: 162/200 (81.0%)
- Answered cases with valid citation labels: 1/1 (100.0%)
- Answered cases passing evidence-support checks: 0/1 (0.0%)
- Mean latency: 0.08s

## Results By Student-Question Category

| Category | Total | Supported | Correct insuff. | Incorrect refusal | Unsupported/misleading | Runtime errors |
|---|---:|---:|---:|---:|---:|---:|
| ai_future | 14 | 0 | 0 | 0 | 0 | 14 |
| career_employment | 28 | 0 | 2 | 1 | 0 | 25 |
| complex | 12 | 0 | 1 | 1 | 0 | 10 |
| curriculum | 14 | 0 | 0 | 0 | 0 | 14 |
| cybersecurity | 12 | 0 | 0 | 0 | 0 | 12 |
| fundamentals | 12 | 0 | 0 | 0 | 0 | 12 |
| hardware_networks | 12 | 0 | 0 | 1 | 0 | 11 |
| mathematics | 12 | 0 | 0 | 0 | 0 | 12 |
| multi_turn | 22 | 0 | 1 | 0 | 1 | 20 |
| out_of_scope | 13 | 0 | 13 | 0 | 0 | 0 |
| programming_software | 18 | 0 | 0 | 1 | 0 | 17 |
| student_local | 18 | 0 | 2 | 1 | 0 | 15 |
| unsupported | 13 | 0 | 13 | 0 | 0 | 0 |

## Most Common Systematic Failures

- 162: runtime_error: Local LLM failed: Could not connect to local Ollama at http://127.0.0.1:11434: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions
- 2: false_refusal: retrieved evidence does not compare the requested learning order or prerequisites
- 1: false_refusal: retrieved evidence does not address the requested learning alternatives
- 1: false_refusal: retrieved evidence does not directly address hackathons or student coding competitions
- 1: false_refusal: retrieved evidence has too little overlap with the question terms: ['exams', 'explains', 'grading', 'official', 'regulation']
- 1: answered_with_uncited_claims

## Files

- Structured results: `results.json`
- Report: `report.md`
