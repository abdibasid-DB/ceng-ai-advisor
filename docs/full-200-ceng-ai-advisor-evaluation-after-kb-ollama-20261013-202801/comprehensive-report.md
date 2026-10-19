# CENG AI Advisor: 200-question evaluation after KB expansion

## Completion and scope

The existing run was resumed from its 187-result checkpoint. The original process had stopped; the checkpoint contained exactly `F001` through `T187`, with no duplicate or out-of-order IDs. The unchanged runner skipped those records and processed `T188` through `T200` through the real local Ollama and RAG pipeline. The final `results.json` has `complete: true`, 200 unique dataset IDs, and no blocker. Four questions returned runtime errors after Ollama request timeouts, so 196/200 produced a non-error status. The errors are measured outcomes, not missing or fabricated results.

This is an evaluation-only artifact. No production code, model setting, embeddings, Chroma collection, or source material was changed during this continuation. The before and after runs used byte-identical evaluation scripts and the same 200-case dataset. The current project files have no edit timestamp later than the first run for the production modules and vector manifest inspected. Local model output and runtime conditions can still vary between runs.

## Automated before and after

The labels below are the runner's automated classifications. They are not verified factual-accuracy grades.

| Classification | Before | After | Change |
|---|---:|---:|---:|
| Evidence-supported answer, automated | 2 (1.0%) | 1 (0.5%) | -1 |
| Correct insufficient/out-of-scope response, automated | 35 (17.5%) | 34 (17.0%) | -1 |
| Potential incorrect refusal with topic evidence | 40 (20.0%) | 55 (27.5%) | +15 |
| Unsupported, incorrect, or misleading, automated | 123 (61.5%) | 106 (53.0%) | -17 |
| Runtime error | 0 | 4 (2.0%) | +4 |

Backend statuses changed from 125 answered, 58 insufficient, 17 out-of-scope, and 0 errors to 107 answered, 72 insufficient, 17 out-of-scope, and 4 errors. In paired cases, 30 previously answered questions became insufficient; 15 previously insufficient questions became answered. The apparent 17-case drop in the broad unsupported label is therefore **not** a demonstrated 17-case accuracy gain. Many cases moved into refusal or error classifications. The two previously supported answers did not retain that label, while one different answer gained it.

The runner's expected-topic evidence indicator was positive for 178/200 before and 179/200 after. This indicator checks category/topic signals and may count passages that are too broad to answer the actual question. It differs from the separate retrieval-only audit, which reported 194/200 and 196/200 relevant cases using its own criteria. Neither metric proves evidence sufficiency or final-answer correctness.

Answered cases with valid citation *labels* were 125/125 before and 107/107 after. Only 2/125 before and 1/107 after passed all automated evidence-support checks. All 106 after-run answers assigned the broad unsupported label had at least one sentence without an inline citation under the runner's sentence splitting rule; ten also had cited-claim word-overlap failures. This is a reliable warning about citation placement, but the label alone cannot tell whether the answer is factually wrong. Conversely, a valid label does not establish that a cited passage entails the claim.

Mean reported pipeline latency increased from 35.56 to 63.24 seconds among cases with timing data. The after run had four Ollama timeouts (`F002`, `A070`, `T187`, `T190`). `T187` took 1,474.9 seconds of wall time including retries before returning a timeout. Latency differences between these local runs should not be attributed solely to the KB expansion.

## Category comparison

Each cell is before -> after. `Supported` is the strict automated label; `refusal` is the potential incorrect-refusal label; `unsupported` is the broad answer-failure label.

| Category | N | Supported | Potential refusal | Unsupported | Correct insuff. | Errors after |
|---|---:|---:|---:|---:|---:|---:|
| Fundamentals | 12 | 0 -> 0 | 0 -> 2 | 12 -> 9 | 0 -> 0 | 1 |
| Curriculum | 14 | 0 -> 0 | 3 -> 5 | 11 -> 9 | 0 -> 0 | 0 |
| Mathematics | 12 | 0 -> 0 | 2 -> 4 | 10 -> 8 | 0 -> 0 | 0 |
| Programming/software | 18 | 0 -> 0 | 5 -> 7 | 13 -> 11 | 0 -> 0 | 0 |
| Hardware/networks | 12 | 0 -> 0 | 2 -> 3 | 10 -> 9 | 0 -> 0 | 0 |
| AI/future | 14 | 0 -> 0 | 2 -> 4 | 12 -> 9 | 0 -> 0 | 1 |
| Cybersecurity | 12 | 1 -> 0 | 4 -> 5 | 7 -> 7 | 0 -> 0 | 0 |
| Career/employment | 28 | 1 -> 1 | 6 -> 7 | 18 -> 18 | 3 -> 2 | 0 |
| Student/local | 18 | 0 -> 0 | 4 -> 6 | 11 -> 9 | 3 -> 3 | 0 |
| Complex | 12 | 0 -> 0 | 7 -> 4 | 4 -> 7 | 1 -> 1 | 0 |
| Multi-turn | 22 | 0 -> 0 | 5 -> 8 | 15 -> 10 | 2 -> 2 | 2 |
| Unsupported | 13 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 13 -> 13 | 0 |
| Out of scope | 13 | 0 -> 0 | 0 -> 0 | 0 -> 0 | 13 -> 13 | 0 |

The 26 explicit unsupported/out-of-scope category questions retained their automated correct-refusal classifications. Multi-turn questions produced 10 broad unsupported labels, eight potential false refusals, two correct insufficiency labels, and two timeouts. Eight of 22 follow-ups were classified by query understanding as standalone; several of these rely on the previous turn for the student's preference or referent.

## Manual review of representative cases

The following checks compare the actual answer with the question and the retrieved passages. They validate or qualify the automated labels; they are not a manual audit of all 200 answers.

| ID | Observation | Root cause / scoring note |
|---|---|---|
| `F001` | Definition of CENG is plausible and relevant, but its first factual sentence has no inline citation. | Real citation traceability failure; the broad "incorrect or misleading" label overstates what was established. |
| `C019` | Refused electronics/digital-logic question. The three captured passages did not directly mention either subject. | The evaluator's topic/category match makes this a questionable "incorrect refusal". Retrieval or sufficiency should be reviewed before blaming the guard. |
| `P045` | Refused whether Linux is worth learning for embedded systems. Retrieved evidence mentions Linux in an operating-systems course and hardware elsewhere, but does not establish the embedded-Linux connection. | Potential retrieval/content gap, with guard rejection; the automated false-refusal label is not proven. |
| `M032` | Gives supportive math advice and names OSTIM courses, but puts citations only after several separate claims. | Mostly a citation-placement issue; individual institutional claims still require source checking. |
| `H063` | Asked whether a student weaker at hardware can manage CENG; the answer pivots to career sustainability and unrelated labor/environment sources. | Question-understanding, retrieval selection, and generation relevance failure beyond citation formatting. |
| `Y088` | Gives reasonable cybersecurity pathway guidance but leaves the actionable first sentence uncited. | Automated failure is justified for traceability, not proof that the advice is false. |
| `R108` | Sole automated "supported" answer describes sectors and a hardware-engineer occupation, but never says whether CENG graduates can work abroad or explains country-specific conditions. | Clear evaluator false positive: overlap and valid citations do not measure answer completeness. |
| `S126` | Presents OSTIM student life as "dynamic," "supportive," and centered on projects based mainly on department, admissions, and course material. | Unsupported extrapolation about lived experience, plus paragraph-end citations that do not map to claims. |
| `X141` | Says a student who dislikes electronics should still choose CENG and should start cybersecurity before AI. The cited cybersecurity sources do not justify that personal degree choice or learning order. | Material unsupported advice/hallucination risk, not just citation format. |
| `T184` | Previous turn was "I prefer hardware," yet the resolver treated "What projects should I build?" as standalone and the system refused. | Lost preference in follow-up resolution, weak project retrieval, and guard rejection. |
| `T188` | Correctly resolved CENG-vs-CS context and retrieved comparison sources, then refused after a missing-inline-citation guard. | Stronger candidate for a true avoidable refusal; answer generation/citation validation is implicated. |
| `T189` | The previous portfolio-project goal was dropped; the answer gives no usable team-vs-solo recommendation and includes uncited concluding claims. | Follow-up resolution and answer completeness failure. |
| `T193` | Declined a salary follow-up because retrieved passages lacked salary evidence. | A prudent refusal in this trace, though it does not establish that the entire KB lacks salary data. |
| `T200` | Resolved a student-club follow-up, but retrieved passages were about the department and coursework, not where to find clubs. | Retrieval/knowledge gap; the refusal is more defensible than a blanket "false refusal" count would suggest. |

## Failure interpretation

1. **Answer content and grounding.** The broad unsupported label covers 106 answers. Some, such as `X141` and `S126`, contain recommendations or claims not justified by the cited passages. Others, such as `F001` and `Y088`, may be substantively reasonable but fail claim-level citation placement. The current score cannot separate these outcomes.
2. **Over-refusal and guard behavior.** Fifty-five refusals were automatically flagged because broad expected-topic evidence was present. Thirty-two have a guard reason of "unsupported claim could not be matched to retrieved evidence" and eight more cite missing-inline-citation variants. `T188` is a concrete avoidable-refusal candidate. `C019` and `P045` show why the whole count cannot be called proven false refusals.
3. **Retrieval and knowledge.** Top passages can be topically related without directly answering the question (`C019`, `P045`, `T200`). The after-run expected-topic evidence indicator improved only one case over baseline; retrieval-only gains did not translate into a demonstrated end-to-end improvement.
4. **Follow-up understanding.** `T184` and `T189` lost prior-turn context, and the multi-turn category had no automated supported answers. Some follow-ups resolved correctly (`T188`, `T193`) but failed later in the pipeline.
5. **Operational reliability.** Four real Ollama calls timed out. They remain errors in the completed 200-case run. The assessment did not silently replace them with inferred answers.
6. **Evaluator calibration.** The support test requires citations on every split sentence and uses lexical term overlap for cited claims. It does not test factual entailment, directness, or completeness. The retrieval-evidence test uses expected categories/topics and a metadata sufficiency flag. `R108` demonstrates a false pass; `C019` demonstrates a questionable false-refusal failure. A manual, claim-level rubric is needed before reporting a defensible accuracy percentage.

## Recommended order of fixes (not implemented)

1. Calibrate the evaluation rubric with a human-reviewed sample: score question coverage, claim support, citation relevance, and justified refusal separately. Keep runtime errors separate from answer quality.
2. Improve answer generation and citation placement so every material claim is tied to its supporting passage, and avoid personalized recommendations unsupported by evidence. Verify on representative failed cases, not only on citation-label syntax.
3. Review refusal/unsupported-claim guards using high-confidence cases such as `T188`; distinguish absent evidence from a repairable citation or wording failure.
4. Improve retrieval relevance and evidence sufficiency for narrow questions, then revisit genuinely missing content. Start with the `C019`, `P045`, `T184`, and `T200` traces.
5. Preserve previous-turn preferences and referents for multi-turn queries; test hardware projects and portfolio team-vs-solo examples.
6. Diagnose Ollama timeout/retry behavior and record per-stage timing so long-running or failed questions can be explained.

`results.json` contains the complete question-level answers, sources, retrieved passages, diagnostics, and timings. `report.md` is the runner's unqualified automated summary. The earlier blocked-socket attempt is preserved separately in `docs/full-200-ceng-ai-advisor-evaluation-after-kb-20261013-202650` and is not included in this comparison.
