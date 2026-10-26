# Wrong-refusal analysis (2026-10-26)

**Result: no change kept.** This was an analysis only. The code, knowledge base and index stay as they are on main, and the fallback remains tag `frozen-20261025`. The experiment branch `exp-fewer-refusals` was deleted without any commits.

**Question.** In the frozen full-200 evaluation ([final-evaluation-20261025](../final-evaluation-20261025/report.md)), 46 of 200 questions were labelled `incorrect_refusal_evidence_exists`: the advisor refused although the knowledge base had evidence. Why were they refused, and is there one small, general change that would answer more of them without adding unsupported answers?

**Method.** Everything below comes from the stored results in `full200-results.json`: the model output, the retrieved passages and the diagnostics. The pipeline's own validation functions were replayed on that data, with the bge-m3 encoder for the similarity checks. The LLM was not called and nothing was re-generated, so the numbers show what the validators decide. They are not new evaluation labels.

## The 46 wrong refusals by reason

| Stage that refused | Count | Cases |
|---|---:|---|
| Topic-term check after generation ("generated answer did not address the question's distinctive topic terms") | **25** | F012 C019 C022 C025 M032 M033 P040 P041 P046 H059 Y092 R097 R100 R105 R112 R113 R116 R122 S124 S135 S136 S140 X141 T184 T192 |
| Claim-support / citation validation ("unsupported claim could not be matched to retrieved evidence") | 13 | P049 H061 A071 Y094 R096 R109 R115 R117 R120 S139 X143 T179 T200 |
| Answerability guard before generation (no LLM call) | 7 | M031 P054 H065 X146 X148 X151 T195 |
| AI-replacement claim guard after generation | 1 | T194 |
| Retrieval evidence gate | 0 | |

The 32 correct refusals came from three stages: 17 from the retrieval evidence gate, 14 from answerability guards before generation, and 1 from claim-support validation. **None came from the topic-term check**, so loosening that check would not have turned any of these 32 into answers. Output: [group_refusals.txt](group_refusals.txt).

## Why the topic-term check refuses: pruned sentences

The topic-term check was replayed on the 25 cases ([replay_topic_check.txt](replay_topic_check.txt)). It reproduces the frozen refusal for 24 of them. For T192, citation validation already fails in the replay.

- **Pruning:** in 21 of the 25, `pruned_unverified_sentences` removed sentences before the topic check ran.
- **Raw answers were on topic:** in 21 of the 25, the model's raw, unpruned answer would have passed the topic check. 19 cases are in both groups.
- **So:** the model usually did write about the question. The on-topic sentences were removed, and the remaining verified sentences were about something else.

Why the sentences were removed: there were 156 sentences across the 38 topic-check and claim-support cases ([why_pruned.txt](why_pruned.txt)).

| Sentence outcome | Sentences |
|---|---:|
| No citation label | 114 |
| Verified | 19 |
| Too little overlap with the cited passage | 16 |
| Strong-claim, relation or causal guard | 5 |
| Speculative wording | 1 |
| Number guard | 1 |

The "no citation label" case arises because the model often cites once at the end of a paragraph or under `USED_SOURCES`. Citation repair attaches that label to an uncited sentence only if its word overlap with the passage is at least 0.5 (`claim_supported_by_context`). A sentence the model cites inline passes with 0.25 overlap, or 0.72 sentence similarity, after the guards in `cited_claim_supported`. Unlabelled sentences are then pruned.

## Two small, general changes simulated

### A. Ignore generic words in the topic-term check

The check counts "topic terms" from the question. These include words no answer repeats, such as "my", "but", "between", "include", "get" and "take". Simulation A removes 20 such words before counting, and keeps the 0.70 question–answer similarity fallback.

**Result: 5 of 25 would pass** (F012, R105, S136, S140, T192). [simulate_generic_words.txt](simulate_generic_words.txt)

Assessment:
- **S136** (what makes OSTİM CENG different) is a good answer.
- **F012** answers only the Computer Engineering half of "IT vs Computer Engineering".
- **R105** (first internship) is one generic sentence.
- **S140** only says the sources do not mention study abroad.
- **T192** fails citation validation in the replay.

Expected gain: about 1–3 supported answers, with a risk of 1–2 new unsupported ones.

### B. Attach the model's own end labels under the inline-citation standard

In citation repair, the model's own paragraph-end or `USED_SOURCES` labels would be attached to an uncited sentence when `cited_claim_supported` accepts it, which is the same standard as an inline citation. Other label sources are unchanged.

**Result: 12 of 46 would be answered** (P040, H059, Y092, R109, R113, R115, R116, S139, S140, X141, T192, T200). R120 and T179 would move on to a later guard and still be refused. [simulate_label_repair.txt](simulate_label_repair.txt)

Assessment: most of these answers now carry the model's own conclusions under a label. Examples:
- "Cryptography is not overly math heavy for a Computer Engineering student" (Y092);
- "Employers will value both the institution's reputation and the practical skills" (R113);
- "Starting with Python can provide a solid foundation", cited to a UC Berkeley CS 61A passage (P040).

Three more answers (S139, S140 and T200) only say that the sources do not contain the information. B would very likely raise the number of unsupported answers.

## Why neither was kept

The keep rule was: keep a change only if wrong refusals fall and unsupported answers do not rise in the full-200 run.

- **A:** too small a gain to clear that rule reliably. Of its 5 extra answers only one is clearly good.
- **B:** would very likely break the rule's second half.
- **Topic-term check:** mostly working as intended. The sentences it loses are not verified by the passages.

The larger lever is to make the model cite every sentence, for example through a prompt change. That changes every generation, including the 10 frozen demo answers, so it was out of scope for a small change. Neither A nor B was implemented, and no evaluation run was made.

## Files

- **Scripts:** run them from the repository root, for example `python docs/refusal-analysis-20261026/group_refusals.py`. Each `.txt` file is the output of the script with the same name.

| File | Purpose |
|---|---|
| [group_refusals.py](group_refusals.py) | Groups the wrong and correct refusals by refusal stage. |
| [replay_topic_check.py](replay_topic_check.py) | Replays citation validation and the topic-term check on the 25 cases. Also writes [replay_topic_check.json](replay_topic_check.json), with term coverage and similarity before and after pruning, and the same numbers for the answered cases. |
| [why_pruned.py](why_pruned.py) | Shows which guard drops each sentence. |
| [simulate_generic_words.py](simulate_generic_words.py) | Simulation A. Reads `replay_topic_check.json`. |
| [simulate_label_repair.py](simulate_label_repair.py) | Simulation B. Patches the repair function in memory only, not in the code. |
