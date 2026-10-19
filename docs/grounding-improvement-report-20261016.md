# CENG AI Advisor grounding improvement and 30-case verification

Date: 2026-10-16 (Africa/Nairobi)

## Scope and evidence

This phase used the completed post-expansion 200-question results and its comprehensive report as the baseline. It changed only `backend/app/rag/rag_pipeline.py` and focused tests in `tests/test_rag_pipeline.py`. The existing dirty worktree, 200-question results, knowledge base, Chroma index, and local Ollama model were preserved. No commit or push was made.

The live checks used the real local Ollama model and the same backend question-resolution/RAG path as the 200-case runner. The 30 selected cases comprise 24 prior cases and six unseen questions. Each result was saved incrementally with answer, source labels, retrieved passages, citation diagnostics, status, and timing:

- First 30-case diagnostic pass: `docs/grounding-30-evaluation-20261016-171338/results.json`
- Second complete 30-case pass after targeted corrections: `docs/grounding-30-final-20261016-180507/results.json`
- Eleven-case recheck after the final overclaim guards: `docs/grounding-focused-final-20261016-183110/results.json`
- One additional live command-line recheck: `docs/grounding-focused-final-20261016-183110/p056-recheck.json`

The second complete pass recorded 30/30 unique cases with no runtime errors: nine automated "supported" answers, 16 potential incorrect refusals, and five correct insufficiency/out-of-scope responses. The first pass recorded five automated supported answers, 18 potential refusals, five correct insufficiency/out-of-scope responses, one broad answer failure, and one Ollama timeout. These are automated labels, not verified accuracy rates. The final overclaim guards were checked on 11 affected cases (eight automated supported, two potential refusals, one correct insufficiency), and `P056` was checked separately. There has **not** been another complete 30-case run after the final small guard and formatting edits. The focused results below identify which later observations supersede the second-pass records.

## What was fixed

1. The grounded prompt now asks for a direct first sentence, one checkable claim per sentence, and a citation attached to that sentence. It warns against inferring degree choices, prerequisites, program-wide totals, and entry-level roles from merely related text.
2. Citation validation now splits paragraphs into sentences. It repairs an uncited sentence only when the existing passage-match test finds support; otherwise the model receives a controlled rewrite request and the answer is withheld if still unsupported. Citation-only tails are removed when the answer itself is already cited. This fixes the line-level loophole that allowed several uncited factual sentences before a single paragraph-end citation.
3. Existing extractive fallbacks were given sentence-level citations. New bounded partial answers use specific retrieved evidence for lab work, FPGA/digital logic, AI math foundations, Linux, CENG-versus-CS hardware, operating systems versus databases, cloud security, and command-line uses. They state the unsupported part as a limit rather than inventing it.
4. Narrow generation guards now reject the observed overclaims: sample course hours generalized to a program total; occupation pages relabeled as entry-level jobs; curriculum topics turned into an FPGA prerequisite; an OSTIM course mention turned into a field-wide Linux requirement; ML math foundations turned into an OSTIM requirement; and a CENG definition turned into an unsupported ranking among disciplines. The generic career fallback no longer answers work-abroad or entry-level questions with unrelated sector facts. Mixed AI/cybersecurity/electronics degree-choice questions no longer receive a generic cybersecurity pathway as a complete answer.
5. The streaming path now applies bounded fallback and returns a safe insufficiency result on final validation failure, matching the non-streaming path more closely. It still emits provisional tokens before final validation; see remaining risks.

The repair remains deliberately conservative. A citation label's existence and word overlap still cannot prove semantic entailment. The evaluation report's `R108` false pass, and new false passes in the first two 30-case runs, are direct evidence of that limitation.

## Manual audit of the 30 cases

The latest observation for cases in the focused recheck supersedes the second complete pass. `P056` uses its later one-case recheck. "Bounded" means the answer states only the supported part and explicitly notes the gap. "Refused" is not automatically correct: the manual note explains whether the retrieved excerpts looked sufficient.

| ID | Latest observation | Manual finding |
|---|---|---|
| `F001` | Answered, focused recheck | Improved. ACM guidance supports the processor-based hardware/software/communications definition; Computing Curricula 2020 supports the hardware-boundary wording. The prior uncited definition was fixed. A redundant label-only tail observed in the recheck is removed by the final formatting test. |
| `C019` | Refused | Unresolved retrieval/sufficiency issue. The captured excerpts do not directly mention electronics or digital logic despite the automated "incorrect refusal" label. |
| `C020` | Bounded answer, focused recheck | Improved. CE2016 says laboratory experiences are crucial; it does not establish a program-wide lab-hour total. Earlier output falsely treated one sample course's 28 lab hours as a whole-program amount. |
| `M032` | Refused | Usability regression. The old answer offered relevant math advice but left several claims uncited; the stricter validator now withholds it. A supported, empathetic partial answer is still needed. |
| `P045` | Refused | Still unresolved. OS course text mentions Linux and hardware separately but does not establish why Linux matters specifically for embedded systems. The automated false-refusal label overstates the evidence. |
| `P056` | Bounded answer, one-case recheck | Improved. MIT's *Missing Semester: The Shell* supports file navigation, running programs, automation, logs, and remote machines; the answer avoids calling the skill mandatory for every CENG path. |
| `H063` | Refused | Safer than the old off-topic answer about career sustainability, but it does not help a student anxious about hardware difficulty. |
| `A075` | Refused | Still unresolved. The retrieved career/AI material does not directly decide the student's personal degree choice; useful bounded counseling remains absent. |
| `Y088` | Answered | Citation grounding improved. NICCS/CISA supports exploring cybersecurity roles, tasks, knowledge, and skills. It is still only a partial career path from CENG. |
| `Y090` | Bounded answer, focused recheck | Improved. NICCS/CISA lists cloud security among cybersecurity paths; the answer does not promise a job after CENG. The earlier generic cybersecurity response missed "cloud." |
| `R108` | Refused | Safer than the old automated "supported" answer, which never answered work abroad. The retrieved sector and occupation excerpts do not establish overseas eligibility. The current automated false-refusal label is questionable. |
| `R120` | Refused, focused recheck | Improved factual caution. O*NET and BLS describe occupations, not verified entry-level CENG job titles. The first 30-case pass had a false "supported" answer calling data scientist entry-level. |
| `S126` | Refused | Avoids the previous invented claims about OSTIM student life being dynamic/supportive. Department and admissions material does not establish lived student experience. |
| `S129` | Refused | Retrieval gap. Top passages are generic ACM/CE2016 material, not the requested official exams/grading regulation. |
| `X141` | Refused, focused recheck | Safer than recommending CENG despite disliked electronics and prescribing cybersecurity before AI without evidence. The personalized choice remains unanswered. |
| `X151` | Refused | The retrieved reports do not directly compare backend versus ML as a route to a quick job; the learning-order guard remains appropriate. |
| `T184` | Refused | Multi-turn failure remains: the resolver classified "What projects should I build?" as standalone and dropped the prior hardware preference. |
| `T187` | Bounded answer, focused recheck | Improved from the old timeout and the second pass's field-wide Linux overclaim. OSTIM's CENG 303 excerpt supports practical Linux/Windows work, not a universal requirement. |
| `T188` | Bounded answer, focused recheck | Improved from refusal and the second pass's unsupported CENG>CS hardware ranking. ACM explicitly includes hardware in CENG; these excerpts do not quantify CS hardware content. |
| `T189` | Refused | Multi-turn failure remains: the portfolio-project context was treated as standalone, and no team-versus-solo recommendation was grounded. |
| `T193` | Refused | Correctly cautious in this trace: no salary evidence for the requested CENG graduate outcomes appeared in the retrieved passages. |
| `T200` | Refused | Correctly cautious in this trace: retrieved department/course excerpts do not say where to find student clubs. |
| `U153` | Refused | Correct refusal: no exact 2026 OSTIM CENG graduate placement rate was retrieved. |
| `O166` | Out of scope | Correct response to a sourdough-bread question. |
| `N001` | Bounded answer, focused recheck | New question. OSTIM CENG 303 supports the operating-systems part; the retrieved excerpts did not establish the databases part. |
| `N002` | Bounded answer, focused recheck | New question. Altera explains FPGA digital hardware; no cited source states a digital-logic course prerequisite. The first pass incorrectly said an FPGA project was "not recommended" before that course. |
| `N003` | Bounded answer, focused recheck | New question. DeepLearning.AI identifies linear algebra and probability as ML foundations; it does not set OSTIM CENG degree requirements. The second pass's "likely requires" claim was rejected. |
| `N004` | Refused | New question. Top results discuss general readiness and portfolio tools but do not give concrete first-year GitHub project examples for internships. |
| `N005` | Refused | Correct negative control: the university cannot guarantee a remote job abroad. |
| `N006` | Refused | New question. Retrieved sensor-network and occupation excerpts do not directly support advice on explaining an individual's team contribution to employers. |

## Verification and remaining work

- `python -m unittest tests.test_rag_pipeline`: **122 tests passed** after the final code edits. New tests cover per-sentence citations, unsupported lab totals, FPGA prerequisites, AI math requirements, CENG/CS hardware rankings, Linux overreach, command-line partial answers, work-abroad protection, and streaming final insufficiency.
- `git diff --check` for the two edited files: passed; Git noted only its normal LF/CRLF conversion warning.
- An isolated FastAPI `TestClient` streaming test stalled before a result and was interrupted. This is an unverified API integration path, not a passing test.
- The old 200-question result remains a baseline, not a post-fix score. The 30-case selection is small and deliberately failure-heavy; its automated percentages must not be presented as overall advisor accuracy.

**Priority before 2026-11-02:**

1. Improve retrieval and source selection for direct student questions such as official grading rules, embedded Linux, project examples, and individual portfolio contributions. Several "false refusal" labels are actually inadequate passages.
2. Add supported partial-answer behavior for math anxiety and mixed degree/career-choice questions. The stricter citation rule currently turns some previously helpful but uncited prose into refusals.
3. Fix multi-turn resolution for preferences and referents (`T184`, `T189`), then test actual API sessions.
4. Replace lexical support as the sole grounding proxy with a manually calibrated claim-level entailment and question-completeness rubric. No current result establishes that hallucinations are eliminated.
5. Investigate Ollama timeouts and the streaming UI's provisional display of tokens before validation. The first 30-case pass timed out once; the second passed without timeouts, so reliability is not yet established. Re-run the full 200 only after those issues are addressed, preserving this baseline.

The advisor is safer on the verified overclaims and correct negative controls remained intact, but the remaining refusal rate, unanswered follow-ups, and unverified claim support mean it is not yet defensible to call it fully reliable for a WEX428 submission.
