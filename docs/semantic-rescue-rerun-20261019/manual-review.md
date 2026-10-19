# Semantic rescue re-run: manual review

Date: 2026-10-19

## What was run

The 43 cases from the 2026-10-18 full-200 run that were labelled `incorrect_refusal_evidence_exists` **and** had called the LLM were re-run live with `qwen2.5:3b`. The pipeline now has the semantic grounding checks:

- question–answer similarity of at least 0.65 rescues the topic-term check
- sentence–passage similarity of at least 0.70 supports cited sentences, and attaches labels to uncited sentences when the existing guards also pass

The 7 refusals made before the LLM was called were not re-run, because the new checks cannot affect them. Runner: `run_rescue_rerun.py`. Automated labels: `report.md` and `results.json`. The classifier ran with the semantic encoder disabled, so its labels use the same word-overlap standard as the baseline run.

## Outcome

| Outcome | Cases |
|---|---:|
| Now answered | 21 |
| Still refused | 22 (raw model output now saved in `retrieval_metadata.discarded_generation`) |
| Automated label `correct_evidence_supported` | 11 |
| Automated label `unsupported_incorrect_or_misleading` | 10 |

## Attribution

Answers that were only lightly repaired, not discarded, have no saved raw generation, so the same text cannot be replayed with and without the new checks. Re-validating each **final** answer with the semantic encoder disabled gives this:

- **S136 and T191** pass only because of the question–answer check (a). Both answers are acceptable (see below).
- The other 19 final answers also pass the old word-overlap checks. Their acceptance may come from the new label-repair step, or simply from a different generation this time (temperature 0.2). This run cannot separate the two. A controlled run that replays identical generations with the checks on and off would be needed.

## Manual verdicts (all 21 answered cases)

Verdicts come from reading each answer against the cited passages stored in `results.json`.

| ID | Automated label | Manual verdict | Note |
|---|---|---|---|
| P046 | correct | **Supported** | SWEBOK note and CE2016 debugger outcome support both claims. |
| R103 | unsupported | **Supported (bounded)** | Quotes the career-readiness note and states the gap. |
| R106 | correct | **Supported** | Erasmus internship call 2025–2026. Opens with a dangling "One such source". |
| R118 | unsupported | **Supported** | NACE GPA/internship passage and career-readiness note match the claims. |
| S135 | correct | **Supported** | Applied-education model and WEX 428 factory training. |
| S136 | unsupported | **Supported** | Restates the department aims (src_001). Rescued by (a). |
| T183 | unsupported | **Supported** | OSTIM cluster internship in Ankara factories (src_004). |
| T191 | unsupported | **Mostly supported** | Department aims are supported. "Strong emphasis" from the CENG 303 syllabus is an inference. Rescued by (a). |
| H066 | correct | Supported but **does not answer** | Never explains the OS–hardware connection. |
| M035 | unsupported | **Content-free** | "The courses are detailed in [S1] and [S2]." |
| F007 | correct | **Contains a wrong claim** | Attributes the passage's statement about *computer scientists* (theory) to computer engineers. Its opening claim cites a passage that does not state it. |
| C021 | correct | **Partly unsupported** | Adds AI/robotics/cybernetics electives that S2 does not list. Cites a UC Berkeley CS 10 rule irrelevant to the student. |
| M031 | unsupported | **Garbled / misleading** | "Mathematics is insufficient to produce a competent computer engineer" is presented without context. |
| M034 | correct | **Misattribution** | Cites S1 (Berkeley first-course page) for math topics it does not mention. |
| H059 | unsupported | **Partly unsupported** | The microcontroller definition is not in the passage. |
| A082 | correct | **Misreading** | "86% … generative AI" — the passage's 86% is for "AI and information processing technologies". |
| Y092 | correct | **Partly unsupported** | Says S5 mentions sectors involving cryptography; it does not. Does not answer the question. |
| S132 | correct | **Wrong** | Reverses the passage: says transfers between demanding and non-demanding programs are "likely". |
| S139 | unsupported | **Wrong** | Says there is no department-specific Erasmus information, but the passage lists Computer Engineering agreements. |
| X150 | correct | **Unsupported** | "Connect directly to industry roles" is not in the cited passage. |
| T182 | unsupported | **Partly unsupported** | Misreads a passage about communication requirements as a statement about math courses. |

**Summary:** 8 acceptable, 2 on-topic but unhelpful, 11 containing at least one wrong or unsupported claim.

The automated label agreed with the manual verdict in only about half the cases. It marked 7 flawed answers as correct and 5 sound answers as unsupported.

## Implications

- The two answers confirmed as rescued by the semantic checks (S136, T191) are acceptable.
- Most errors are misattributions and misreadings that share many words with the passage. The existing lexical checks also let these through. Raising the answer rate on hard questions surfaces this weakness; it was not created by the new similarity checks.
- A controlled replay of identical generations is needed before claiming a net effect of the semantic checks. Claim-level checking (natural-language inference, or a stricter "statement must appear in the passage" rule) is needed to catch misattribution.
