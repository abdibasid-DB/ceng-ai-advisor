# Spec-question fixes (2026-10-23)

This report covers the four spec questions, the refused mathematics, programming, Linux and OSTİM cases, and the T182/T187 follow-up rewrites. Every change is general: the code has no rule for a specific question and no hand-written answer. No sources were added, and the full 200-question evaluation was not rerun.

## 1. Which gate refused what

| Case | Gate that refused | Usable evidence retrieved? | Cause |
|---|---|---|---|
| SPEC1 Will AI replace computer engineers? | citation validation | yes (OECD S1: jobs not likely to be entirely substituted, up/re-skilling; WEF S3: enhance vs substitute) | "Future of Jobs Report **2025**" (the source title) was read as an unsupported number; the uncited "Therefore …" conclusion left too little |
| SPEC2 Is Computer Engineering still worth studying? | generated-answer check (topic) after pruning | no outlook evidence before; after the expansion, CE2016 chunk_079 (great potential, 17.7% growth) and O*NET Bright Outlook | the ethics sentence was cited to the wrong label; the only focus term "worth" was never matched by an outlook answer |
| SPEC4 Not good at maths, can I succeed? | generated-answer check after pruning | partly (CE2016 chunk_077: "up to each program to decide the quantity and level of mathematics") | the on-topic sentence was dropped because of the title year "2016" and because "required" (used as a noun modifier) counted as a requirement claim |
| A076, S135 | citation validation | yes | title years, mis-labelled citations (both now answered) |
| M027, M035 | citation validation | yes | correct rejection: the model invented "18 credits" (the passage has 21 credits of mathematics and 18 of humanities) |
| M028, M033 | citation validation | partly | M033: the model emitted INSUFFICIENT and then speculated |
| P041 (C++) | citation validation | no | irrelevant evidence |
| S127, S128 (clubs) | citation validation | no | src_112 (Turkish) is not retrieved; src_122 has 0 chunks (extraction failed) |
| S136 | generated-answer check | no | src_005 "Our Difference" was not retrieved |
| P054, X148, R111, U153 | claim gate | no | correct refusals: no ordering or ranking evidence |
| Y089, T187 (Linux) | answered weakly / generation | no | there is no Linux-for-security evidence |

No case was refused by the evidence threshold, answerability, specific-fact or category gates. All refusals happened after generation.

## 2. SPEC3: why the employment sources were not retrieved

All of them are indexed: src_095 BLS (3 chunks), src_096 ShiftDelete/Önceki Yazılımcı (3), src_097 Haber Gazetesi/Kariyer.net (5) and src_103 TÜİK/Ekonomi Gazetesi (5).

- **BLS src_095:** the table headers are in chunk_001, among navigation text, and the chunk_002 "Software developers" row has no column names. It ranks 225th by vector search.
- **TÜİK src_103_chunk_003** ("ICT graduates find a first job in 11.4 months") is in Turkish. It ranks 122nd by vector search and gets a BM25 score of 0 for an English question.
- **Salary sources:** they are about pay, not finding a job, and they include junk chunks (liquor prices, navigation).

With the new retrieval expansion ("find a job", "worth studying" → outlook/employment terms), SPEC3 now retrieves the O*NET Bright Outlook and projected-growth chunks and CE2016 chunk_080.

## 3. Changes (general)

**Citation validation and pruning** ([rag_pipeline.py](../../backend/app/rag/rag_pipeline.py))

Loosened where evidence existed:
- Years and course codes in a source's own title or name are no longer treated as numeric claims.
- A sentence cited to the wrong label is re-labelled to a passage that supports it (only labels in the retrieved context).
- A connective ("Additionally,") is removed when the sentence before it was pruned, instead of dropping the sentence.
- A cited partial answer behind `[INSUFFICIENT_INFORMATION]` is kept. Bracket noise and author-date wrappers ("(WEF, Not specified [S3])") are cleaned.
- "required" used as a noun modifier ("the mathematics required for graduates") is no longer a requirement claim.
- The topic check matches word prefixes and no longer treats modal or degree words (will, can, should, not, very…) as topic terms.
- Aliases were added for "worth" (outlook, demand, growth…) and "succeed" (success…).

Tightened so the loosening does not let invented claims through:
- A number must appear in the passage next to the same words as in the claim ("18 credits of mathematics" ≠ "18 credits of humanities").
- A comparison ("more important than") needs a comparison in the passage.
- A requirement or strong claim needs the passage's strong word to be about the same subject ("a professional **must** be a good communicator" does not support "mathematics is a fundamental requirement").
- A trailing inference clause (", which indicates …", ", making …") is cut unless supported.
- A model conclusion ("Therefore …", "These steps …") gets no automatic citation, and a sentence referring back to a pruned one is dropped.
- In "<conclusion>, as/since/because <reason>", the conclusion itself must be semantically supported ("You can still succeed, as the curriculum does not fix the amount of mathematics" is rejected).

**Retrieval** ([retriever.py](../../backend/app/rag/retriever.py)): "worth studying / worth it" and "find a job / job after" questions are expanded with career-outlook and graduate-employment terms.

**Query understanding** ([query_understanding.py](../../backend/app/query_understanding.py)): a specific maths question ("discrete math for algorithms") is no longer rewritten into the generic "How much mathematics is required".

## 4. T182 and T187: the follow-up rewrite changed the meaning

- **T182** "How can I prepare before first year?" (after "I am weak at math") was rewritten to "… considering MATH 101 and MATH 202?". The course codes came from the advisor's answer, and the student's concern was lost.
- **T187** "Is Linux important too?" (after "I want cybersecurity") was rewritten to "What role does Linux play in cybersecurity?". The word "important" was dropped, which changes the question.

**Fix** ([follow_up_rewriter.py](../../backend/app/services/follow_up_rewriter.py)): a rewrite is rejected, and the rule-based resolution is used instead, when it:
- leaves the question unchanged;
- drops a content word of the student's question; or
- adds numbers that never appeared in the student's turns.

On the 22 multi-turn cases, only T182, T187 and T195 are rejected, and faithful paraphrases (T184, T186, T194) are kept.

- T182 becomes "How can I prepare before first year? Regarding I am weak at math in Computer Engineering." and is now answered with support.
- T187 becomes "Is linux important too? Regarding I want cybersecurity in Computer Engineering." It is refused, which is correct because the knowledge base has no Linux-in-security evidence.

## 5. Before and after numbers

### Live run (qwen2.5:3b, temperature 0.2)

- **Before:** the rows for the same IDs from the final evaluation, and a paraphrase run of the exported HEAD (338a340).
- **After:** a live run of the changed code: [results/cases-after.json](results/cases-after.json) and [results/paraphrase-after.json](results/paraphrase-after.json).
- **Labels:** both sides are labelled by the current official classifier, because that classifier calls the pipeline's topic check, which this change touches.

| Group | n | Supported | Correct refusal | Incorrect refusal | Unsupported |
|---|---:|---:|---:|---:|---:|
| ai_future | 14 | 10 → 11 | 0 → 0 | 3 → 1 | 1 → 2 |
| mathematics | 12 | 5 → 9 | 0 → 0 | 5 → 3 | 2 → 0 |
| career_employment | 28 | 12 → 14 | 3 → 3 | 9 → 7 | 4 → 4 |
| student_local | 18 | 4 → 6 | 3 → 3 | 7 → 5 | 4 → 4 |
| programming_software | 18 | 11 → 13 | 0 → 0 | 3 → 2 | 4 → 3 |
| multi_turn | 22 | 11 → 7 | 1 → 1 | 3 → 7 | 7 → 7 |
| out_of_scope | 13 | 0 → 0 | 13 → 13 | 0 → 0 | 0 → 0 |
| unsupported | 13 | 0 → 0 | 13 → 13 | 0 → 0 | 0 → 0 |
| paraphrase | 20 | 16 → 15 | 0 → 0 | 3 → 3 | 1 → 2 |
| **All** | 158 | **69 → 75** | 33 → 33 | **33 → 28** | **23 → 22** |

- **Out-of-scope and unsupported refusals:** unchanged at 13/13 each.
- **Unsupported answers overall:** 23 → 22.
- **Runtime errors:** 0.

The full case list is in [results/comparison.md](results/comparison.md).

**Multi-turn got worse in this run (4 more refusals), but not because of the gates.** T179, T188, T189 and T197 still use the same rewrite, and replaying their new generations through the unchanged HEAD code refuses them too. These are new generations at temperature 0.2. The rewrite guard changes only T182, T187 and T195.

The live "after" run used the code before the last three tightenings: the strong-claim subject check, the causal-conclusion check, and the modal-word exclusion. Their effect was measured by replay (below).

### Offline replay of the saved final-evaluation generations

This is deterministic: no LLM call. Each saved generation is passed through the post-generation validation of HEAD and of the final code, and labelled by the current classifier. See [results/replay-final-eval-generations.txt](results/replay-final-eval-generations.txt).

| Label | HEAD | Final code |
|---|---:|---:|
| Supported | 97 | 108 |
| Incorrect refusal | 43 | 37 |
| Unsupported | 27 | 22 |
| Correct refusal (incl. out_of_scope 13/13, unsupported 13/13) | 33 | 33 |

Known regressions in the replay:
- **T184, T194** (multi-turn): refusal → unsupported.
- **C023** (curriculum): supported → unsupported.
- **Y089:** supported → unsupported.
- **T192:** supported → refusal.

## 6. The four spec answers (committed code, live run)

From [results/spec4-committed.json](results/spec4-committed.json). The runner labels these four with "evidence exists = false" because spec cases have no expected topics, so its labels are not meaningful. The answers below were judged by hand.

**SPEC1: Will AI replace computer engineers?** Refused in this run.

The model answered "there is no direct evidence … However, the [S3] source indicates…" and cited a reference outside the knowledge base ("Lassébie and Quintini, 2022 [44]"). None of its claims could be matched to a passage. The earlier live generation of the same question passes under this code:

> The OECD's Skills for the Digital Age report indicates that while some tasks may be automated, workers in these jobs may need up-skilling and re-skilling as technologies replace workers for several tasks [S1]. Additionally, the World Economic Forum's The Future of Jobs Report 2025 emphasizes that technological development should focus on enhancing rather than substituting human capabilities [S3].

Sources: S1 OECD, *Skills for the digital age* (src_045_chunk_203); S3 WEF, *The Future of Jobs Report 2025* (src_017_chunk_029).

**SPEC2: Is Computer Engineering still worth studying?** Refused in this run, by the topic check: what survived pruning did not address "worth".

The run before it (with the "worth" alias) answered:

> Computer Engineering remains a worthwhile field of study, as evidenced by its continued relevance and growth in various sectors [S2]. The field of computer engineering has expanded and matured, with professionals applying their skills in diverse career sectors including business, industry, government, services, organizations, and other structured entities that utilize computers to automate or enhance their operations [S2].

Source: S2 ACM/IEEE, *Computer Engineering Curricula 2016* (src_067_chunk_079).

**SPEC3: Can I find a job after graduation?** Answered (partial):

> Computer Hardware Engineers have a bright outlook and that the occupation is expected to grow much faster than average (7% or higher) over the projections period (2024-2034) [S5]. The source [S2] suggests that while a degree in Computer Engineering is likely necessary, it is not sufficient for a position.

Sources: S5 O*NET OnLine, *Computer Hardware Engineers 17-2061.00* (src_014_chunk_016); S2 ACM/IEEE, *Computer Engineering Curricula 2016* (src_067_chunk_080).

The answer is correct but narrow: it covers hardware engineers only and has no Türkiye data. See section 7.

**SPEC4: I'm not very good at mathematics. Can I still succeed in Computer Engineering?**

The live run answered with three sentences. The first, "I can still succeed … as the degree credential is not sufficient [S1]", is the model's conclusion, and the final code's causal-conclusion check removes it. The same generation through the committed code gives:

> The 2024 State of Tech Talent Report indicates that relevant hands-on experience is the most crucial aspect employers look for during the hiring process, with 71% of respondents considering it extremely or very important [S3]. While a strong understanding of mathematics is beneficial, it is not the sole requirement for success in computer engineering [S4].

Sources: S3 Linux Foundation, *2024 State of Tech Talent Report* (src_016_chunk_030); S4 ACM/IEEE, *Computer Engineering Curricula 2016* (src_067_chunk_077).

The second sentence is still loose: S4 says each program decides the quantity and level of mathematics.

The 3B model often wraps spec answers in its own conclusions. The gates now remove these instead of refusing the whole answer or letting them through. Whether a spec question is answered still varies from one generation to the next.

## 7. Missing evidence (sources not added yet)

| Question area | What would answer it |
|---|---|
| SPEC3, finding a job in Türkiye | A bilingual or English summary of TÜİK src_103 (ICT graduates: 11.4 months to a first job); TÜİK or YÖK/Kariyer graduate-employment data for *bilgisayar mühendisliği* |
| SPEC3, US outlook | Re-extract BLS src_095 so every table row keeps its column headers |
| SPEC2, degree value | An employment-outcome source for CE graduates (for example the NACE first-destination survey, CE row) |
| SPEC4, weak at maths | A source on maths support or bridging for engineering students (for example OSTİM preparatory or tutoring pages, or a study on maths remediation in engineering) |
| S127, S128 clubs | Fix extraction of src_122 (sks.ostimteknik.edu.tr/ogrenci-topluluklarimiz, 0 chunks); English handling of src_112 |
| Linux in security (Y089, T187) | CyBOK *Operating Systems & Virtualisation Security*, or NICE Framework knowledge statements |
| Other unindexed pages | src_121 Sağlık and src_124 KARPİEM (0 chunks) |

## 8. Reproduce

```
python docs/spec-fix-20261023/run_spec_fix.py cases --groups ai_future,mathematics,career_employment,student_local,programming_software,out_of_scope,unsupported,multi_turn
python docs/spec-fix-20261023/run_spec_fix.py paraphrase
python docs/spec-fix-20261023/run_spec_fix.py paraphrase --code-root <exported HEAD> --name before
python docs/spec-fix-20261023/run_spec_fix.py spec4 --name committed
python docs/spec-fix-20261023/compare.py
```

Outputs go to `D:/ceng-ai-advisor-data/evaluations/spec-fix-20261023/`.
