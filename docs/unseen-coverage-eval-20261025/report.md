# Unseen student questions, end to end (2026-10-25)

Evaluation only; no code was changed. The 120 cases of tests/unseen_coverage_cases.json (116 "answer", 4 "insufficient") were run through the live pipeline of the frozen system (tag `frozen-20261025`) and labelled with the official full-200 classifier. Each case's `expected_categories` are the registry categories of its expected sources (see [run_unseen.py](run_unseen.py)).

## Answer cases (116)

| Result | Count |
|---|---:|
| Answered with support | 42 (36.2%) |
| Wrongly refused (evidence exists) | 22 (19.0%) |
| Unsupported answer | 16 (13.8%) |
| Refused, no relevant evidence retrieved (counted as correct refusal by the classifier) | 36 (31.0%) |
| Runtime errors | 0 |
| An expected source among the retrieved passages | 56 (48.3%) |
| Mean time per question | 36.3 s |

## Insufficient cases (4)

Correctly refused: 2 of 4; answered: 2. Mean time 32.6 s.

## By topic area (answer cases)

| Topic area | n | Supported | Wrongly refused | Unsupported | Refused, no evidence | Expected source retrieved | Mean s |
|---|---:|---:|---:|---:|---:|---:|---:|
| academic_curriculum | 10 | 5 | 2 | 0 | 3 | 4 | 38.4 |
| artificial_intelligence | 10 | 5 | 0 | 2 | 3 | 6 | 37.7 |
| career_opportunities | 9 | 3 | 3 | 2 | 1 | 7 | 43.9 |
| common_concerns | 10 | 3 | 3 | 1 | 3 | 6 | 41.2 |
| department_itself | 10 | 1 | 4 | 2 | 3 | 4 | 58.8 |
| employment_prospects | 9 | 3 | 1 | 0 | 5 | 4 | 26.1 |
| future_technologies | 9 | 3 | 0 | 0 | 6 | 2 | 25.5 |
| graduate_studies | 10 | 5 | 1 | 1 | 3 | 4 | 28.6 |
| internships | 10 | 4 | 4 | 0 | 2 | 6 | 46.1 |
| programming | 10 | 4 | 0 | 2 | 4 | 3 | 29.0 |
| specialization_areas | 10 | 5 | 0 | 4 | 1 | 7 | 36.3 |
| student_life | 9 | 1 | 4 | 2 | 2 | 3 | 20.7 |

## Wrongly refused questions (22)

By gate: citation / claim validation after generation 10, generated-answer topic check 7, answerability guard (before the LLM) 5.

| Case | Topic | Question | Gate that refused | Expected source retrieved |
|---|---|---|---|---|
| unseen_department_itself_004 | department_itself | Who in OSTIM CENG could I email about an interest in computer networks? | generated-answer topic check: generated answer did not address the question's distinctive topic terms | no |
| unseen_department_itself_008 | department_itself | What score would let me skip OSTIM's English prep school? | citation / claim validation after generation: unsupported claim could not be matched to retrieved evidence | yes |
| unseen_department_itself_009 | department_itself | Where are the CENG lecturers' offices at OSTIM if I want to go ask a question? | citation / claim validation after generation: unsupported claim could not be matched to retrieved evidence | no |
| unseen_department_itself_010 | department_itself | If I come up with a product idea at OSTIM, is there somewhere on campus to turn it into a prototype? | citation / claim validation after generation: unsupported claim could not be matched to retrieved evidence | yes |
| unseen_academic_curriculum_002 | academic_curriculum | At OSTIM, does doing a minor give me another degree like a double major does? | citation / claim validation after generation: unsupported claim could not be matched to retrieved evidence | yes |
| unseen_academic_curriculum_005 | academic_curriculum | Do first-year students at OSTIM get physics lab sessions, or is physics all lectures? | answerability guard (before the LLM): retrieved evidence does not compare the requested learning order or prerequisites | no |
| unseen_student_life_001 | student_life | Is there anywhere quiet to study at OSTIM when home is too noisy? | answerability guard (before the LLM): retrieved evidence has too little overlap with the question terms: ['anywhere', 'home', 'noisy', 'quiet', 'study', 'too'] | yes |
| unseen_student_life_004 | student_life | Do student clubs have their own spaces in the Cezeri center? | answerability guard (before the LLM): retrieved evidence has too little overlap with the question terms: ['center', 'cezeri', 'own', 'spaces', 'their'] | no |
| unseen_student_life_008 | student_life | If I get really homesick at OSTIM, how do I book a student counseling session? | answerability guard (before the LLM): retrieved evidence has too little overlap with the question terms: ['book', 'counseling', 'get', 'homesick', 'really', 'session'] | no |
| unseen_student_life_009 | student_life | Are there cafes or places to sit with friends on the OSTIM campus? | answerability guard (before the LLM): retrieved evidence has too little overlap with the question terms: ['cafes', 'campus', 'friends', 'places', 'sit'] | yes |
| unseen_career_opportunities_002 | career_opportunities | Are there software jobs where figuring out what users need is a big part of the work? | generated-answer topic check: generated answer did not address the question's distinctive topic terms | yes |
| unseen_career_opportunities_004 | career_opportunities | Could a CENG graduate work on computers inside cars instead of desktop PCs? | citation / claim validation after generation: unsupported claim could not be matched to retrieved evidence | yes |
| unseen_career_opportunities_005 | career_opportunities | How does Cezeri support a student idea between the first sketch and starting a company? | generated-answer topic check: generated answer did not address the question's distinctive topic terms | yes |
| unseen_internships_002 | internships | In OSTIM's 2025-26 Erasmus call, did students have to find their own internship company? | citation / claim validation after generation: unsupported claim could not be matched to retrieved evidence | yes |
| unseen_internships_003 | internships | Was a company acceptance letter compulsory when applying for OSTIM's 2025-26 Erasmus internship? | generated-answer topic check: generated answer did not address the question's distinctive topic terms | yes |
| unseen_internships_005 | internships | Could a prep exemption exam result be used for OSTIM's 2025-26 Erasmus internship language requirement? | citation / claim validation after generation: unsupported claim could not be matched to retrieved evidence | yes |
| unseen_internships_008 | internships | Exactly how many compulsory summer internship days do OSTIM CENG students have to finish? | citation / claim validation after generation: unsupported claim could not be matched to retrieved evidence | no |
| unseen_graduate_studies_007 | graduate_studies | What ALES score would I need for OSTIM's CENG master's? | generated-answer topic check: generated answer did not address the question's distinctive topic terms | no |
| unseen_employment_prospects_002 | employment_prospects | Would I need to get my diploma or transcript translated before applying for work abroad? | generated-answer topic check: generated answer did not address the question's distinctive topic terms | yes |
| unseen_common_concerns_003 | common_concerns | If I fail OSTIM's English prep year, what exactly happens to my place on the degree? | citation / claim validation after generation: unsupported claim could not be matched to retrieved evidence | yes |
| unseen_common_concerns_004 | common_concerns | I have dyslexia and timed exams worry me; what extra-time arrangements could I get at OSTIM? | generated-answer topic check: generated answer did not address the question's distinctive topic terms | yes |
| unseen_common_concerns_009 | common_concerns | If my first semester feels too much, can I ask my OSTIM advisor about taking fewer credits? | citation / claim validation after generation: unsupported claim could not be matched to retrieved evidence | yes |

## Notes

- **How to read "Refused, no evidence":** the official classifier counts a refusal as correct when none of the top-5 passages has an expected category. The dataset expects an answer for all 116 of these questions, so these 36 cases (31.0%) are also failures, but retrieval failures rather than gate failures. Altogether 58 of the 116 answer cases (50.0%) were refused: 22 by a gate although relevant evidence was retrieved, and 36 because no relevant evidence was retrieved.
- **Expected sources:** at least one was among the retrieved passages in 56 of 116 cases (48.3%), so retrieval of the labelled source is the main limit on coverage.
- **Gates that refused:** the gate is read from the recorded diagnostics (`run_unseen.py`, `refusing_gate`). 17 of the 22 wrong refusals happened after generation: claim validation 10 and the topic check 7. The answerability guards before the LLM refused 5, 4 of them in student_life, where the question words ("quiet", "cafes", "homesick") are not in the retrieved text. The evidence-similarity gate refused none.
- **Insufficient cases:**
  - Correctly refused: dorm cost (student_life_007) and a job guarantee (career_opportunities_010).
  - Answered: current Ankara vacancy counts (employment_prospects_010), with an extractive quote that does not address the question, and the main programming language in 2035 (future_technologies_010), answered with today's Python usage. Both answers count as unsupported.
- **Classifier:** the labels are automated (citation validity, category or topic evidence, and lexical claim support). They are not a human check of each claim.
