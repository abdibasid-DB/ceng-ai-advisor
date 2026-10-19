"""Offline test of a claim-level NLI (entailment) check on saved answers.

For every answer sentence that cites [S#] labels, the sentence (citations and
"according to [S1]"-style framing removed) is the hypothesis. Each sentence of
the cited passage is a premise, and the best entailment probability across
cited labels and passage sentences is the sentence's score. The whole passage
is also scored as a premise, because answers often merge two passage
sentences. A sentence is accepted when the score is at or above the threshold.

Results are compared with a sentence-level answer key (see
docs/semantic-rescue-rerun-20261019/sentence-key.json). No pipeline code is
changed and Ollama is not called.

Usage:
    python scripts/evaluate_nli_claims.py RESULTS_JSON KEY_JSON [--model NAME] [--thresholds 0.3 0.5 0.7] [--output OUT_JSON]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sentence_transformers import CrossEncoder  # noqa: E402

from backend.app.rag import rag_pipeline as rp  # noqa: E402

# Same splitter as rp.prune_unverified_sentences, so sentences match what the
# pipeline would judge.
SENTENCE_SPLIT = r"(?<=[.!?\]])\s+(?=[A-Z\-*•\d(]|\[(?!S\d+\]))"
EXEMPT = re.compile(r"\s*(?:the )?(?:retrieved evidence|source|excerpt|syllabus) does not (?:establish|justify|prove|state|rank|quantify)", re.I)
FRAMING = re.compile(
    r"^\s*(?:additionally|also|lastly|however|moreover|furthermore|for example|for instance|therefore)?,?\s*"
    r"(?:(?:the )?(?:context|report|source|sources|document|curated note[^,]*?|retrieved source)\s*(?:from\s*)?)?"
    r"(?:indicates?|mentions?|states?|suggests?|highlights?|notes?|emphasizes?|stresses?|shows?)\s+(?:that\s+)?",
    re.I,
)


def answer_sentences(answer: str) -> list[str]:
    return [s.strip() for line in answer.splitlines() if line.strip() for s in re.split(SENTENCE_SPLIT, line.strip()) if s.strip()]


def hypothesis(sentence: str) -> str:
    text = " ".join(rp.strip_citation_text(sentence).split())
    text = re.sub(r"^\s*,\s*", "", text)
    stripped = FRAMING.sub("", text)
    return (stripped[:1].upper() + stripped[1:]) if len(stripped.split()) >= 3 else text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results", type=Path)
    parser.add_argument("key", type=Path)
    parser.add_argument("--model", default="cross-encoder/nli-deberta-v3-small")
    parser.add_argument("--thresholds", type=float, nargs="+", default=[0.3, 0.5, 0.7])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    key = json.loads(args.key.read_text(encoding="utf-8"))
    cases = [c for c in json.loads(args.results.read_text(encoding="utf-8"))["results"] if c["diagnostics"]["status"] == "answered"]

    model = CrossEncoder(args.model, device="cpu")
    entail = next(i for i, name in model.model.config.id2label.items() if name.lower() == "entailment")
    model.predict([("Warm-up premise.", "Warm-up hypothesis.")])

    rows = []
    timings = []
    for case in cases:
        context = {item.get("label"): item for item in case.get("retrieved_context") or []}
        tags = key["sentences"].get(case["id"], {})
        for index, sentence in enumerate(answer_sentences(case["answer"])):
            tag = next((name for name, ids in tags.items() if index in ids), "ok")
            labels = [label for label in rp.extract_citation_labels(sentence) if label in context]
            row = {"id": case["id"], "index": index, "tag": tag, "sentence": sentence, "hypothesis": hypothesis(sentence)}
            if EXEMPT.match(rp.strip_citation_text(sentence)) or not labels:
                row.update(sentence_score=None, passage_score=None, note="exempt" if labels else "no citation")
                rows.append(row)
                continue
            pairs, kinds = [], []
            for label in labels:
                passage = str(context[label].get("passage") or "")
                for premise in rp.passage_sentences(passage):
                    pairs.append((premise, row["hypothesis"]))
                    kinds.append("sentence")
                pairs.append((passage, row["hypothesis"]))
                kinds.append("passage")
            started = time.perf_counter()
            probs = model.predict(pairs, apply_softmax=True, batch_size=16, show_progress_bar=False)
            timings.append((time.perf_counter() - started, len(pairs)))
            entailment = [float(p[entail]) for p in probs]
            row["sentence_score"] = max(e for e, k in zip(entailment, kinds) if k == "sentence")
            row["passage_score"] = max(entailment)
            rows.append(row)

    total_time = sum(t for t, _ in timings)
    total_pairs = sum(n for _, n in timings)
    summary = {
        "model": args.model,
        "scored_sentences": len(timings),
        "seconds_per_sentence": total_time / max(len(timings), 1),
        "seconds_per_pair": total_time / max(total_pairs, 1),
        "thresholds": {},
    }

    def accepted(row, threshold, mode):
        score = row[f"{mode}_score"]
        return True if score is None else score >= threshold

    for mode in ("sentence", "passage"):
        for t in args.thresholds:
            good_kept = flawed_fixed = ok_lost_in_flawed = bad_total = bad_removed = 0
            per_case = {}
            for case in cases:
                verdict = key["verdicts"].get(case["id"])
                case_rows = [r for r in rows if r["id"] == case["id"]]
                ok_rows = [r for r in case_rows if r["tag"] == "ok"]
                bad_rows = [r for r in case_rows if r["tag"] == "bad"]
                remaining = [r for r in case_rows if accepted(r, t, mode) and r["tag"] != "exempt"]
                per_case[case["id"]] = {
                    "kept": [r["index"] for r in case_rows if accepted(r, t, mode)],
                    "removed": [r["index"] for r in case_rows if not accepted(r, t, mode)],
                    "answer_left": bool(remaining),
                }
                if verdict == "good" and all(accepted(r, t, mode) for r in ok_rows):
                    good_kept += 1
                if verdict == "flawed":
                    bad_total += len(bad_rows)
                    bad_removed += sum(not accepted(r, t, mode) for r in bad_rows)
                    ok_lost_in_flawed += sum(not accepted(r, t, mode) for r in ok_rows)
                    if bad_rows and all(not accepted(r, t, mode) for r in bad_rows):
                        flawed_fixed += 1
            summary["thresholds"][f"{mode}@{t}"] = {
                "good_answers_fully_kept": good_kept,
                "flawed_answers_all_bad_removed": flawed_fixed,
                "bad_sentences_removed": f"{bad_removed}/{bad_total}",
                "ok_sentences_lost_in_flawed": ok_lost_in_flawed,
                "per_case": per_case,
            }

    if args.output:
        args.output.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"model {args.model}: {summary['scored_sentences']} sentences, "
          f"{summary['seconds_per_sentence']:.3f} s/sentence, {summary['seconds_per_pair'] * 1000:.0f} ms/pair")
    for name, s in summary["thresholds"].items():
        print(f"{name}: good kept {s['good_answers_fully_kept']}/8 | flawed fixed {s['flawed_answers_all_bad_removed']}/11 | "
              f"bad removed {s['bad_sentences_removed']} | ok lost in flawed {s['ok_sentences_lost_in_flawed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
