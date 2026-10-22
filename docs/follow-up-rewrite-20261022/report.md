# LLM follow-up rewriting (Part 3)

## What changed

`backend/app/services/follow_up_rewriter.py`, called from both chat endpoints through `backend/app/api/chat.py: apply_follow_up_rewrite`.

**When the rewrite runs:** there must be an earlier turn with domain context, and either:
- `query_understanding` classifies the question as `contextual_follow_up`, or
- a domain question contains "it", "that", "those", "what about" or "the first one".

**The call:** the local `qwen2.5:3b` gets a short prompt with the last two turns (previous answers trimmed to 400 characters, citation labels removed) and the new question. It is asked only for one standalone question, with temperature 0, `num_predict` 60 and `num_ctx` 2048.

**Using the output:**
- The first line is cleaned, and the rewrite is rejected if it is empty, contains INSUFFICIENT or a citation, is longer than 40 words, or has more than one sentence.
- Otherwise it replaces the rule-based resolution: retrieval uses it, and the answer prompt answers it.
- If the rewrite fails, the rule-based resolver's question is used.
- Both versions, the raw output and the time taken are stored in `retrieval_metadata.follow_up_rewrite`.
- The switch is `FOLLOW_UP_REWRITE_ENABLED` in `backend/app/core/llm_config.py`.

## Test

**Script:** `run_multi_turn.py`. It runs all 22 cases from the 200-question set that have a previous question (T179–T200, including T184 and T189). It uses the official 200-question runner's backend path and classifier, once with the rewrite off and once on. Per-case results, including both resolutions, are in `off.json` and `on.json`.

| Automated label (22 multi-turn cases) | Rewrite off | Rewrite on |
|---|---:|---:|
| correct_evidence_supported | 9 | **12** |
| correct_insufficient_information | 1 | 1 |
| incorrect_refusal_evidence_exists | 8 | **4** |
| unsupported_incorrect_or_misleading | 4 | 5 |
| answered / refused | 13 / 9 | 17 / 5 |

- **Rewrite used:** the LLM rewrite was used in 18 of the 22 cases. In the other 4 (T180, T181, T190, T196) the question was not a follow-up by the rule above. Those 4 changed only through generation noise (temperature 0.2).
- **Single-turn cases:** the rewrite fired on 0 of the 178. They have no earlier turn, so their results cannot be changed by this feature.
- **T184** ("What projects should I build?" after "I prefer hardware.") became "What projects should I build if I prefer hardware?". It was answered both times but labelled an incorrect refusal with the rewrite on.
- **T189** became "Should the portfolio projects be team projects or solo?" and was answered with support both times.

**Decision (rule: keep it if multi-turn results improve and single-turn results do not get worse):** multi-turn results improved, with 3 more supported answers and 4 fewer wrong refusals, and single-turn results are unaffected. The rewrite stays **on**.

## Weak rewrites seen

- **T195** "Is it hard?" after "What is CENG 303?" was rewritten to "What is CENG 303?", which drops the new question.
  - After the test, a guard was added: a rewrite that only repeats an earlier question is rejected, and the rule-based resolution is used.
  - Unit test: `tests/test_follow_up_rewriter.py`. This guard was not part of the evaluated run.
- **T182** "How can I prepare before first year?" after "I am weak at math." was rewritten with course names taken from the previous answer ("MATH 202", "third year"). The previous answer text leaked into the question.
- **T187** "Is Linux important too?" after "I want cybersecurity." became a question about other technologies besides Linux, which changes the meaning.

The small model sometimes over-interprets. The rule-based fallback only covers empty or invalid output, not rewrites that read well but are wrong.
