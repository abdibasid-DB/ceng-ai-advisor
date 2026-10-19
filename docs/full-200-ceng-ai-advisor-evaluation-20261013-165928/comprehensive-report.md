# Comprehensive 200-Question CENG AI Advisor Evaluation Report

Generated from `results.json` after the completed real-Ollama run.

## Completion Status

- Evaluation status: complete
- Questions evaluated: 200/200
- Dataset: `docs/semantic-coverage-200-questions.json`
- Evaluation artifact directory: `docs/full-200-ceng-ai-advisor-evaluation-20261013-165928`
- Final results generated at: `2026-10-13T16:12:22+00:00`
- Runtime errors in final run: 0
- Production code, KB files, Chroma database, and RAG behavior were not intentionally modified during the measurement run.

## Automated Overall Metrics

These are automated labels from the evaluation harness. They are stricter than citation-format checking and should not be presented as human factual grading of every claim.

| Label | Count | Percent |
|---|---:|---:|
| Correct, evidence-supported answers | 2 | 1.0% |
| Correct insufficient-information / out-of-scope responses | 35 | 17.5% |
| Incorrect refusals where KB evidence appeared to exist | 40 | 20.0% |
| Unsupported, incorrect, or misleading answers | 123 | 61.5% |
| Runtime errors | 0 | 0.0% |

Backend status distribution:

| Status | Count | Percent |
|---|---:|---:|
| `answered` | 125 | 62.5% |
| `insufficient_information` | 58 | 29.0% |
| `out_of_scope` | 17 | 8.5% |

## Performance By Question Category

| Category | N | Answered | Insufficient | Out of scope | Eval evidence found | Supported | False refusal | Unsupported/misleading | Correct insufficient |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ai_future | 14 | 12 | 2 | 0 | 13 | 0 | 2 | 12 | 0 |
| career_employment | 28 | 19 | 9 | 0 | 26 | 1 | 6 | 18 | 3 |
| complex | 12 | 4 | 8 | 0 | 11 | 0 | 7 | 4 | 1 |
| curriculum | 14 | 11 | 3 | 0 | 14 | 0 | 3 | 11 | 0 |
| cybersecurity | 12 | 8 | 4 | 0 | 12 | 1 | 4 | 7 | 0 |
| fundamentals | 12 | 12 | 0 | 0 | 12 | 0 | 0 | 12 | 0 |
| hardware_networks | 12 | 10 | 2 | 0 | 12 | 0 | 2 | 10 | 0 |
| mathematics | 12 | 10 | 2 | 0 | 12 | 0 | 2 | 10 | 0 |
| multi_turn | 22 | 15 | 7 | 0 | 21 | 0 | 5 | 15 | 2 |
| out_of_scope | 13 | 0 | 0 | 13 | 0 | 0 | 0 | 0 | 13 |
| programming_software | 18 | 13 | 5 | 0 | 18 | 0 | 5 | 13 | 0 |
| student_local | 18 | 11 | 7 | 0 | 18 | 0 | 4 | 11 | 3 |
| unsupported | 13 | 0 | 9 | 4 | 9 | 0 | 0 | 0 | 13 |

## Retrieval Quality And Answer Relevance

Automated evidence detection found expected-category/topic evidence in 178/200 cases. This suggests retrieval often returned plausible material, but the generation and gating layers did not reliably turn that evidence into acceptable answers.

Important distinction:

- `Eval evidence found` means the evaluation harness found retrieved context with matching expected category/topic signals.
- It does not prove full semantic sufficiency for every answer.
- Conversely, `incorrect_refusal_evidence_exists` means the harness found likely relevant evidence while the system still returned `insufficient_information`.

The strongest retrieval-related failure pattern was false refusal: 40 cases returned `insufficient_information` even though the harness found likely supporting evidence. Common causes were unsupported-claim guard rejection, missing citation handling, and overly strict comparison/prerequisite guards.

## Hallucination And Citation Reliability

Citation-label validity looked perfect at the surface level:

| Metric | Result |
|---|---:|
| Answered cases | 125 |
| Answered cases with valid citation labels | 125/125, 100.0% |
| Answered cases passing strict evidence-support checks | 2/125, 1.6% |
| Answered cases with uncited claims by automated checker | 121 |
| Answered cases with cited claim/evidence term-overlap failure | 12 |
| Answered cases without expected evidence by evaluation category/topic check | 2 |

This is the central quality finding: citation formatting is reliable, but claim-level grounding is not yet reliable under the automated checker. The project should not claim that answers are correct merely because citations are syntactically valid.

## Multi-Turn Conversation Performance

Multi-turn cases: 22.

| Label | Count | Percent |
|---|---:|---:|
| Correct, evidence-supported answers | 0 | 0.0% |
| Correct insufficient-information responses | 2 | 9.1% |
| Incorrect refusals where evidence appeared to exist | 5 | 22.7% |
| Unsupported, incorrect, or misleading answers | 15 | 68.2% |
| Runtime errors | 0 | 0.0% |

The system did run the multi-turn cases without crashing, but the quality is weak. The follow-up resolver often reached an answer path, yet generated answers still failed grounding checks or the guard layer refused when likely evidence existed.

## Out-Of-Scope And Unsupported Handling

Out-of-scope handling was the best-performing part of the system.

- Out-of-scope category: 13/13 correct refusals.
- Unsupported category: 13/13 correct insufficient-information or out-of-scope responses.
- Combined unsupported/out-of-scope: 26/26 correct handling under the automated rubric.

This is suitable to highlight in a university submission: the system is cautious with unsupported or unrelated questions. The limitation is that it is also too weak at grounded answer generation for supported student-advising questions.

## Failed Questions And Causes

Correct evidence-supported cases:

- `Y088`
- `R095`

Incorrect refusals where evidence appeared to exist:

- `C019`, `C021`, `C025`, `M032`, `M037`, `P045`, `P046`, `P053`, `P054`, `P056`, `H063`, `H065`, `A075`, `A077`, `Y083`, `Y085`, `Y086`, `Y091`, `R100`, `R105`, `R106`, `R117`, `R121`, `R122`, `S126`, `S127`, `S128`, `S129`, `X141`, `X142`, `X143`, `X147`, `X148`, `X151`, `X152`, `T184`, `T187`, `T188`, `T197`, `T199`

Most common systematic failure causes:

| Cause | Count | Example IDs |
|---|---:|---|
| Answered with uncited claims | 121 | `F001`, `F002`, `F003`, `F004`, `F005`, `F006`, `F007`, `F008`, `F009`, `F010`, `F011`, `F012` |
| False refusal: unsupported claim could not be matched to retrieved evidence | 24 | `M032`, `P045`, `P046`, `P053`, `A075`, `A077`, `Y083`, `Y085`, `Y086`, `Y091`, `R105`, `R106` |
| False refusal: incomplete or truncated generated answer | 2 | `C021`, `H063` |
| False refusal: missing inline citation | 2 | `R100`, `S127` |
| False refusal: missing inline citation on one or more answer paragraphs/bullets | 2 | `T188`, `T199` |
| False refusal: overly strict comparison/prerequisite evidence requirement | 2 | `P054`, `X151` |
| Answered without relevant expected evidence | 1 | `R096` |
| Cited passages did not support claim terms | 1 | `R120` |

## Interpretation

Automatically measured:

- The run completed all 200 cases using the real local Ollama path.
- No final-run runtime errors occurred.
- The system is strong at refusing unsupported and out-of-scope questions.
- The system frequently answers supported questions, but most generated answers fail the strict automated grounding checks.
- Citation labels are syntactically valid in answered cases, but that does not establish that the cited passages support every claim.

Subjective/estimated from the pattern of failures:

- The current system is not yet reliable enough to claim high answer accuracy in an academic defense.
- The highest-risk issue is not retrieval alone; it is the mismatch between generated prose, inline citation discipline, and evidence support.
- Some false refusals appear to come from guard logic that rejects usable retrieved evidence after generation or citation validation.

## Five Highest-Impact Remaining Problems

1. Generated answers often include claims without inline citations, causing 121 answered cases to fail strict support checks.
2. The answerability/unsupported-claim guard is too brittle and creates false refusals even when likely KB evidence exists.
3. Citation validity checks confirm label syntax, but they do not ensure claim-level entailment.
4. Multi-turn follow-up behavior works mechanically but does not produce reliably grounded answers.
5. Some answers appear incomplete, over-broad, or weakly matched to the expected category/topic even when retrieval returns plausible context.

## Essential Recommendations For A Strong University Submission

1. Fix answer formatting so every factual sentence or bullet has an inline citation, then rerun a smaller verification suite.
2. Add a claim-level grounding check or stricter extractive answer style before returning `answered`.
3. Tune false-refusal guards using the 40 listed false-refusal cases, especially comparison, prerequisite, and missing-citation paths.
4. Improve multi-turn resolution with targeted tests for the 22 follow-up cases.
5. In the final report/defense, present the system honestly: emphasize local RAG architecture, source-grounded design, strong refusal behavior, and the measured limitations in answer grounding.

Do not present this evaluation as proof that all answered questions are correct. It is evidence that the current implementation can run end-to-end and refuse unsupported questions well, but still needs focused grounding and citation improvements before it can be described as highly reliable.
