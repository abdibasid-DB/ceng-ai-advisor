# Curated English notes (2026-10-26)

**Result: reverted.** The knowledge base, code and index stay at tag `frozen-20261025` (3daff49). Main has no knowledge-base change since that tag.

The rule was to keep the notes only if the spec answers and the OSTİM topics improved and none of the 10 demo questions got worse. The spec answers did not improve, and demo question S127 got worse.

## What was tested

There were 13 curated English notes, in the style of src_126–src_132. Each note covers one topic and states only facts from its source: exact quotes for English sources, and a labelled, non-official translation for Turkish sources. Each note gives the source title, URL and date, and none contains advice. The note texts are in [notes/](notes/), and the registry entries come from [build_notes.py](build_notes.py).

| Note | From | Topic | Chunks |
|---|---|---|---:|
| src_137 | src_134 (BLS) | AI impacts in BLS employment projections | 2 |
| src_138 | src_135 (BLS) | AI, IT and employment 2024–34 | 2 |
| src_139 | src_136 (BLS OOH) | Computer and IT occupations: outlook, openings, wages | 2 |
| src_140 | src_133 (Stack Overflow) | Developers' views on AI and their jobs | 2 |
| src_141 | src_001, 002, 003, 005 | Department aims and program facts | 2 |
| src_142 | src_107 | English prep school: levels, exemption, maximum duration | 3 |
| src_143 | src_104 | Scholarships and discounts | 3 |
| src_144 | src_105, src_106 | Double major and minor eligibility | 4 |
| src_145 | src_122, src_112 | Student clubs: list and how to join | 3 |
| src_146 | src_116 | Academic advising | 2 |
| src_147 | src_114 | Computer labs | 2 |
| src_148 | src_110, 109, 003, 004 | Applied workplace courses instead of a compulsory internship | 3 |
| src_149 | src_111, src_088 | Master's programs | 2 |

How the test was built:
- The original pages src_133–136 were registered as sources. The raw BLS pages src_134–136 were excluded from chunking, so only their notes were indexed; src_133 was indexed as a full page (8 chunks).
- No existing chunk changed. Excluded sources do not feed the shared-navigation cleaning, so the 2026-10-25 side effect did not recur.
- Embedding used `--reuse`: 2844 vectors were reused unchanged and 40 were encoded, giving 2844 → 2884 chunks.
- All of this was done in a git worktree on D:, not in the live repository.

The evaluation pipeline was the same as the final evaluation: temperature 0, seed 42, and Ollama with the prompt cache disabled (confirmed in server.log).

## Retrieval (top 5, live retriever)

- **OSTİM topics:** the notes rank 1–3 for all nine OSTİM topic questions. For "compulsory internship", "scholarships" and "prep exemption", no relevant OSTİM passage was in the top 5 before.
- **SPEC2 and SPEC3:** now retrieve src_139 and src_137.
- **SPEC1 and SPEC4:** top 5 unchanged.

## Results

| Question | Before (frozen) | With notes |
|---|---|---|
| SPEC1 Will AI replace computer engineers? | refused | refused (identical) |
| SPEC2 Is Computer Engineering still worth studying? | unsupported | unsupported (new text, sources src_067 and src_014; no note cited) |
| SPEC3 Can I find a job after graduation? | unsupported | identical |
| SPEC4 Not good at maths… | unsupported | identical |

**10 demo questions:**
- Six answers are identical: F001, F007, C026, A073, Y086 and O166.
- **S127** changed from supported to **unsupported**. The new answer adds "These clubs offer opportunities for students interested in software development, AI, cybersecurity…", which src_122 does not say.
- **R102** is still labelled supported but became weaker: a quote followed by "The retrieved evidence does not establish the rest".
- **T186** (does the curriculum include Linux?) is still labelled supported, but it lost the OSTİM CENG 303 Linux answer and now cites only a generic language list from src_067.
- A082 now also cites src_137 and is still supported.

**Unseen cases, four topic areas** (sup = supported, wrong-ref = wrongly refused, unsup = unsupported, ref-noev = refused without relevant evidence):

| Topic | n | Before: sup / wrong-ref / unsup / ref-noev | With notes |
|---|---:|---|---|
| department_itself | 10 | 1 / 4 / 2 / 3 | 1 / 3 / 2 / 4 |
| student_life | 10 | 1 / 4 / 2 / 3 | 0 / 5 / 1 / 4 |
| common_concerns | 10 | 3 / 3 / 1 / 3 | 4 / 2 / 0 / 4 |
| employment_prospects | 10 | 3 / 1 / 1 / 5 | identical |

Changed cases:
- **Better:** department_itself_010 (entrepreneurship space) and common_concerns_003 (failing the prep year) became supported. department_itself_006, student_life_005, student_life_006 and common_concerns_002 went from an unsupported answer to a refusal.
- **Worse:** department_itself_001 (OSTİM industrial zone) and student_life_010 (first-year university-life course) went from supported to wrongly refused. department_itself_008 (prep-school score) and student_life_003 (sports facilities) went from refused to unsupported answers.

The paraphrase retrieval test (`evaluate_retrieval_paraphrases.py --options live`) was not run. The decision was already fixed by the spec and demo results.

## Why it did not help

- The notes are retrieved, but the bottleneck is the generation and validation stages, not retrieval.
- SPEC1 and SPEC4 still retrieve the same passages.
- For SPEC2 and SPEC3, the model does not use the BLS note figures in a validated sentence.
- For OSTİM questions, the new passages change what the model writes. This helps some answers and hurts others, for example S127, student_life_010 and T186.

The worktree with the full test build, including the index, is kept at `D:/ceng-ai-advisor-data/wt-curated-20261026` (branch `curated-notes-20261026`, not pushed).
