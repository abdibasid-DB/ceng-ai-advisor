# Removing hand-written passages and answer templates (Part 2)

Before: rag_pipeline.py with the six hand-written passage functions (augment_context_results) and the bounded_* answer templates, on the option-f index. After: those functions deleted; the passages that retrieval did not find on its own were added as curated verbatim source notes (src_126-src_131, build_curated_notes.py) and indexed. Both runs send the same 113 test questions (questions.json: every test-set question that triggered one of the removed functions) through POST /api/v1/chat with the local qwen2.5:3b; the follow-up rewrite is off in both. Answer texts are in before.json and after.json.

## Rule check: is the right passage in the top 5 without the function?

| Function | Triggering questions | Top-5 hit, index without notes | Decision | Top-5 hit with curated note |
|---|---:|---:|---|---:|
| `programming_languages_passage()` | 5 | 0/5 | curated note src_126, then deleted | 2/5 |
| `gpa_screening_passage()` | 9 | 3/9 | curated note src_127, then deleted | 9/9 |
| `computer_engineering_definition_passage()` | 15 | 6/15 | curated note src_128, then deleted | 8/15 |
| `future_technologies_passage()` | 2 | 0/2 | curated note src_129, then deleted | 2/2 |
| `linux_operating_system_passage()` | 12 | 3/12 | curated note src_130, then deleted | 8/12 |
| `specialization_areas_passage()` | 18 | 11/18 | curated note src_131, then deleted | 11/18 |

Every function failed the rule on at least one triggering question, so each became a curated note. Some triggering questions are false triggers of the old keyword detectors (for example salary questions for the definition function); they count as misses here.

The `bounded_*` templates (`bounded_verified_partial_answer`, `bounded_ai_replacement_answer`, `bounded_programming_language_answer`, `bounded_prior_programming_answer`, `bounded_git_github_answer`, `bounded_cybersecurity_pathway_answer`, `bounded_career_jobs_answer`, and the future-technology template inside `bounded_fallback_answer`) wrote fixed answer sentences around a retrieved label. They only fired when their evidence passage was already retrieved, so no source note was needed; they were deleted and the fallback is now only `extractive_partial_answer`, which quotes one retrieved sentence verbatim.

## Live pipeline before and after

| Built for | n | Answered before → after | Refused before → after | Answer replaced by fallback before → after | Mean s before → after |
|---|---:|---:|---:|---:|---:|
| **All 113 questions** | 113 | 83 → 83 | 30 → 30 | 10 → 9 | 26.9 → 23.0 |
| `bounded_ai_replacement_answer` | 2 | 1 → 2 | 1 → 0 | 0 → 1 | 60.9 → 29.8 |
| `bounded_career_jobs_answer` | 35 | 21 → 23 | 14 → 12 | 3 → 3 | 27.2 → 23.8 |
| `bounded_cybersecurity_pathway_answer` | 7 | 4 → 4 | 3 → 3 | 0 → 0 | 33.2 → 21.6 |
| `bounded_git_github_answer` | 6 | 5 → 5 | 1 → 1 | 0 → 0 | 20.9 → 15.7 |
| `bounded_prior_programming_answer` | 4 | 4 → 4 | 0 → 0 | 1 → 0 | 27.9 → 27.1 |
| `bounded_programming_language_answer` | 5 | 5 → 5 | 0 → 0 | 3 → 1 | 21.6 → 21.0 |
| `bounded_verified_partial_answer` | 12 | 12 → 11 | 0 → 1 | 1 → 3 | 26.3 → 24.7 |
| `computer_engineering_definition_passage` | 15 | 11 → 11 | 4 → 4 | 1 → 1 | 24.2 → 20.5 |
| `future_technologies_passage` | 2 | 0 → 0 | 2 → 2 | 0 → 0 | 48.5 → 46.0 |
| `gpa_screening_passage` | 9 | 9 → 9 | 0 → 0 | 0 → 1 | 27.7 → 27.4 |
| `linux_operating_system_passage` | 12 | 11 → 8 | 1 → 4 | 2 → 1 | 21.8 → 16.9 |
| `programming_languages_passage` | 5 | 5 → 5 | 0 → 0 | 3 → 1 | 21.6 → 21.0 |
| `specialization_areas_passage` | 18 | 11 → 11 | 7 → 7 | 1 → 0 | 22.8 → 20.1 |

"Answer replaced by fallback" counts answers where the LLM output was discarded and a template (before) or the extractive quote (after) was returned.

## Questions whose status changed (14)

| Question | Built for | Before | After |
|---|---|---|---|
| What network skills are useful for cybersecurity? | bounded_cybersecurity_pathway_answer | answered | insufficient_information |
| What skills should I build for cybersecurity? | bounded_cybersecurity_pathway_answer | insufficient_information | answered |
| Can I learn security without doing illegal hacking? | bounded_cybersecurity_pathway_answer | answered | insufficient_information |
| Does it include Linux? | linux_operating_system_passage | answered | insufficient_information |
| Will AI replace software engineers and computer engineers? | bounded_ai_replacement_answer | insufficient_information | answered |
| Is the Computer Engineering job market becoming saturated? | bounded_career_jobs_answer | insufficient_information | answered |
| Which field of Computer Engineering is right for me? | specialization_areas_passage | insufficient_information | answered |
| How do I discover which specialization I enjoy the most? | specialization_areas_passage | insufficient_information | answered |
| Which specialization is expected to grow the fastest in the future? | specialization_areas_passage | answered | insufficient_information |
| Would a Computer Engineering degree be a route into an AI engineering career? | bounded_career_jobs_answer | insufficient_information | answered |
| Can I becme a cybersecurity specialist with a Computer Engineering degree? | bounded_cybersecurity_pathway_answer | insufficient_information | answered |
| How useful is Linux knowledge for someone studying Computer Engineering? | linux_operating_system_passage | answered | insufficient_information |
| Is learing Linux important for Computer Engineering students? | linux_operating_system_passage, bounded_verified_partial_answer | answered | insufficient_information |
| How can I choose the Computer Engineering area that best matches my interests and strengths? | specialization_areas_passage | answered | insufficient_information |

## Reading

- Overall the removal is neutral on these 113 questions: the same number is answered (83) and refused (30), and fewer answers are replaced by a fallback (10 → 9). Mean answer time fell from 26.9 s to 23.0 s; the "after" run also used the new 2-hour model keep-alive (Part 4), so part of that is less model reloading.
- The status changes go both ways (7 refused → answered, 7 answered → refused). The LLM samples at temperature 0.2, so a single run cannot separate the code change from generation noise for individual questions.
- The clearest loss is Linux: 3 of 12 Linux questions that were answered before are now refused, including "Does it include Linux?" and two paraphrases of q039. Before, `augment_context_results` injected the CENG 303 "Linux or Windows" sentence at the top of the context; now the curated note `src_130` is retrieved for 8/12 Linux questions but not for those q039 paraphrases.
- Answers that were template text before are now either the model's own grounded answer or a verbatim source quote: no answer text is written by hand in the code any more.
