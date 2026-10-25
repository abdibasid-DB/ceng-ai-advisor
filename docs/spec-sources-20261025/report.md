# Better sources for the spec questions (2026-10-25)

**Result: reverted.** The knowledge base, code and index stay at tag `frozen-20261025` (3daff49).

The rule was to keep the change only if the spec answers improved and no demo question got worse. Two versions were tested:
- **Stack Overflow only:** changed nothing.
- **All four requested sources:** made two spec answers and one demo answer worse.

## Requested sources

| Source | Acquisition | Chunks |
|---|---|---:|
| src_133 Stack Overflow 2025 Developer Survey press release (2025-07-29) | `scripts/acquire_sources.py` (HTTP 200) | 8 |
| src_134 BLS TED, "AI impacts in BLS employment projections" (2025-03-11) | bls.gov answers automated downloads with "Access Denied", so the page was saved manually in a browser by the project author on 2026-10-25 | 6 |
| src_135 BLS TED, "Artificial intelligence, information technology, and employment, 2024–34" (2026-07-16) | manual browser save, as above | 4 |
| src_136 BLS OOH, Computer and Information Technology Occupations (last modified 2026-08-27) | manual browser save, as above | 3 |

- **Saved pages:** each has the correct page title and no "Access Denied" text, and each passed the integrity and bot-block check of `scripts/acquire_sources.py` (`skipped_existing`, "passed basic integrity checks").
- **Processing:** with the repository scripts; only the new chunks were encoded.
- **Index:** 2844 → 2852 chunks with src_133 only, and 2865 with all four.
- **Side effect:** with three more BLS pages, the chunker's "navigation shared by ≥3 pages" cleaning also dropped navigation words from 5 existing chunks (src_008, src_039, src_068, src_095).

All test indexes were built outside the live repository: at first in the working tree, later in a git worktree at the tag. That way the unseen-question evaluation (Task 2) kept running on the frozen index.

The four raw pages, their processed texts and the registry entries are kept outside the repository in `D:/ceng-ai-advisor-data/sources-pending-20261025/`, so they can be added again without new downloads.

## Mathematics

- **OSTİM "TELAFİ DERSLERİ USUL VE ESASLARI"** (Senate 29.01.2026, in force 22.04.2026; link in [ostim-legislation-index.md](../ostim-legislation-index.md)): **not added**. It only regulates rescheduling lessons that could not be held, for example because of holidays, disasters, a lecturer's illness or technical faults: application, approval, announcement and attendance. It describes no academic or mathematics support.
- **Search for a 2022–2026 source on mathematics support for engineering students: none added.**
  - The most relevant result was Tsui & Khan, "Is mathematics a barrier for engineering?" (International Journal of Mathematical Education in Science and Technology, 2023-10-11, University of Western Australia, CC BY-NC-ND 4.0, doi:10.1080/0020739X.2023.2256319). It is peer-reviewed and on topic, but the publisher blocks automated downloads (HTTP 403). Its full text could not be read to confirm what it says.
  - The other results were from 2018–2021 or not about engineering students.

## Results

Same pipeline as the final evaluation ([run_spec_fix.py](../spec-fix-20261023/run_spec_fix.py), with `--code-root` for the worktree): temperature 0, seed 42, Ollama with `LLAMA_ARG_CACHE_RAM=0`. Each run had the Ollama server to itself.

| Question | Frozen system | + src_133 | + src_133–136 |
|---|---|---|---|
| SPEC1 Will AI replace computer engineers? | refused | refused (identical) | refused |
| SPEC2 Is Computer Engineering still worth studying? | answered, 1 of 4 sentences supported | identical | **refused** (generated-answer topic check) |
| SPEC3 Can I find a job after graduation? | answered, 1 vague sentence | identical | **refused** (claim validation) |
| SPEC4 Not good at maths… | answered, 2 of 3 sentences supported | identical | answered, but opens with an unsupported "Yes, you can still succeed … even if you are not very good at mathematics [S1]" |
| 10 demo questions | 9 supported + 1 correct refusal | all identical | A082 **unsupported**; A073 changed (still labelled supported); the other 8 identical |

Files:
- with src_133: [spec4-with-src133.json](spec4-with-src133.json), [demo-with-src133.json](demo-with-src133.json);
- with all four: [spec4-with-src133-136.json](spec4-with-src133-136.json), [demo-with-src133-136.json](demo-with-src133-136.json).

## Why it did not help

- **src_133 is never retrieved** into the top 5 for any spec question.
- **The new BLS passages do get retrieved, but the answers based on them fail validation.**
  - SPEC2's discarded answer ("Computer Engineering is still worth studying, as evidenced by … the median annual wage of $109,470") does not answer the "worth studying" terms closely enough for the topic check.
  - SPEC3's discarded answer mixes O*NET with a BLS table row for *management analysts* (10.1%) and attributes a 7.3% growth figure to computer hardware engineers. The passage gives that 7.3% for construction laborers, so the claim check correctly rejects it.
- **One BLS chunk crowds out better passages.** src_134_chunk_004 is about personal financial advisors and robo-advisors. It is retrieved for SPEC1, SPEC4, A073 and A082, because it contains "AI can support many tasks involved in architecture and engineering occupations". It displaces passages that supported the previous answers.
- **Navigation text:** BLS page frames ("The .gov means it's official …") end up in src_136_chunk_001. The chart tables come out one cell per line without their column headers; the src_095 table extractor is not applied to these pages, and changing it would be a code change.

**Possible next step (not done; it needs code or curation changes):** a curated English note per BLS page with the key sentences only, in the style of src_126–src_132. For example: software developers +17.9% (2023–33) and +15.8% (2024–34); about 280,000 openings a year in computer and IT occupations; and AI is "expected to primarily affect occupations whose core tasks can be most easily replicated by Generative AI". This would avoid the navigation and financial-advisor text.
