"""Offline test of a claim-level NLI (entailment) check on saved answers.

For every answer sentence that cites [S#] labels, the sentence (citations and
"according to [S1]"-style framing removed) is the hypothesis. Premises come
from the cited passages; the best entailment probability across cited labels
and premises is the sentence's score. A sentence is kept when the score is at
or above the threshold, and removed otherwise.

Premises (--premises):
  sentence  each passage sentence
  pairs     each passage sentence and each pair of neighbouring sentences
  passage   the whole passage as one premise (in addition to sentences)

Context (--context):
  none        hypothesis is the sentence alone
  hypothesis  if the sentence opens with a pronoun or connector ("This",
              "They", "Additionally", ...), the previous answer sentence is
              prepended to the hypothesis

Two modes:
  key mode     compare with a sentence-level answer key
               (docs/semantic-rescue-rerun-20261019/sentence-key.json)
  replay mode  no key: report how many answers would lose a sentence or be
               left empty (refused), with examples of removed sentences

No pipeline code is changed and Ollama is not called.

Usage:
    python scripts/evaluate_nli_claims.py RESULTS_JSON [--key KEY_JSON]
        [--model NAME] [--premises sentence|pairs|passage] [--context none|hypothesis]
        [--thresholds 0.3 0.5 0.7] [--output OUT_JSON]
"""

from __future__ import annotations

import argparse
import json
import random
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
DEPENDENT_OPENING = re.compile(
    r"^\W*(?:it|its|this|that|these|those|they|their|them|such|also|additionally|moreover|furthermore|"
    r"however|therefore|thus|hence|then|lastly|finally|in addition|as a result|for example|for instance)\b",
    re.I,
)


def answer_sentences(answer: str) -> list[str]:
    return [s.strip() for line in answer.splitlines() if line.strip() for s in re.split(SENTENCE_SPLIT, line.strip()) if s.strip()]


PRONOUN_OPENING = re.compile(r"^\W*(?:it|its|this|that|these|those|they|their|them|such)\b", re.I)
LEADING_CONNECTOR = re.compile(
    r"^\W*(?:also|additionally|moreover|furthermore|however|therefore|thus|hence|then|lastly|finally|"
    r"in addition|as a result|for example|for instance)\b,?\s*",
    re.I,
)
SOURCE_REFERENCE = re.compile(r",?\s*as (?:mentioned|stated|noted|described|indicated|stipulated) in (?:the )?(?:source|document|context)?\s*(?=[.,]|$)", re.I)


def clean_claim(sentence: str, *, strip_connectors: bool = False) -> str:
    text = " ".join(rp.strip_citation_text(sentence).split())
    text = re.sub(r"^\s*,\s*", "", text)
    if strip_connectors:
        text = SOURCE_REFERENCE.sub("", text)
        text = LEADING_CONNECTOR.sub("", text)
    stripped = FRAMING.sub("", text)
    return (stripped[:1].upper() + stripped[1:]) if len(stripped.split()) >= 3 else text


def split_passage(passage: str, bullets: bool) -> list[str]:
    if not bullets:
        return rp.passage_sentences(passage)
    parts = []
    for chunk in re.split(r"\s*[•▪●]\s*|\s+x\s+(?=[A-Z])", passage or ""):
        parts += rp.passage_sentences(chunk) if chunk.strip() else []
    return parts or rp.passage_sentences(passage)


def premises(passage: str, mode: str, bullets: bool = False) -> list[str]:
    sentences = split_passage(passage, bullets)
    result = list(sentences)
    if mode in {"pairs", "passage"}:
        result += [f"{first} {second}" for first, second in zip(sentences, sentences[1:])]
    if mode == "passage" and passage.strip():
        result.append(" ".join(passage.split()))
    return list(dict.fromkeys(result))


def score_case(case: dict, model: CrossEncoder, entail: int, args, timings: list) -> list[dict]:
    context = {item.get("label"): item for item in case.get("retrieved_context") or []}
    sentences = answer_sentences(case.get("answer") or "")
    rows = []
    for index, sentence in enumerate(sentences):
        labels = [label for label in rp.extract_citation_labels(sentence) if label in context]
        hypothesis = clean_claim(sentence, strip_connectors=args.clean)
        opening = PRONOUN_OPENING if args.context == "pronoun" else DEPENDENT_OPENING
        with_context = args.context != "none" and index > 0 and opening.match(rp.strip_citation_text(sentence))
        if with_context:
            hypothesis = f"{clean_claim(sentences[index - 1], strip_connectors=args.clean)} {hypothesis}"
        row = {"id": case["id"], "index": index, "sentence": sentence, "hypothesis": hypothesis, "context_added": bool(with_context)}
        if EXEMPT.match(rp.strip_citation_text(sentence)) or not labels:
            row.update(score=None, note="exempt" if labels else "no citation")
            rows.append(row)
            continue
        pairs = [
            (premise, hypothesis)
            for label in labels
            for premise in premises(str(context[label].get("passage") or ""), args.premises, bullets=args.clean)
        ]
        started = time.perf_counter()
        probs = model.predict(pairs, apply_softmax=True, batch_size=16, show_progress_bar=False)
        timings.append((time.perf_counter() - started, len(pairs)))
        best = max(range(len(pairs)), key=lambda i: probs[i][entail])
        row.update(score=float(probs[best][entail]), best_premise=pairs[best][0][:300])
        rows.append(row)
    return rows


def kept(row: dict, threshold: float) -> bool:
    return row["score"] is None or row["score"] >= threshold


def key_summary(cases: list[dict], rows: list[dict], key: dict, threshold: float) -> dict:
    good_kept = flawed_fixed = ok_lost_flawed = bad_total = bad_removed = 0
    failures = {"good_answers_damaged": [], "flawed_answers_not_fixed": []}
    for case in cases:
        verdict = key["verdicts"].get(case["id"])
        tags = key["sentences"].get(case["id"], {})
        case_rows = [r for r in rows if r["id"] == case["id"]]
        tag = lambda r: next((name for name, ids in tags.items() if r["index"] in ids), "ok")  # noqa: E731
        ok_rows = [r for r in case_rows if tag(r) == "ok"]
        bad_rows = [r for r in case_rows if tag(r) == "bad"]
        if verdict == "good":
            if all(kept(r, threshold) for r in ok_rows):
                good_kept += 1
            else:
                failures["good_answers_damaged"].append(case["id"])
        if verdict == "flawed":
            bad_total += len(bad_rows)
            bad_removed += sum(not kept(r, threshold) for r in bad_rows)
            ok_lost_flawed += sum(not kept(r, threshold) for r in ok_rows)
            if bad_rows and not any(kept(r, threshold) for r in bad_rows):
                flawed_fixed += 1
            else:
                failures["flawed_answers_not_fixed"].append(case["id"])
    return {
        "good_answers_fully_kept": f"{good_kept}/{sum(v == 'good' for v in key['verdicts'].values())}",
        "flawed_answers_fixed": f"{flawed_fixed}/{sum(v == 'flawed' for v in key['verdicts'].values())}",
        "bad_sentences_removed": f"{bad_removed}/{bad_total}",
        "ok_sentences_lost_in_flawed": ok_lost_flawed,
        **failures,
    }


def replay_summary(cases: list[dict], rows: list[dict], threshold: float) -> dict:
    lost = emptied = 0
    removed_examples = []
    for case in cases:
        case_rows = [r for r in rows if r["id"] == case["id"]]
        removed = [r for r in case_rows if not kept(r, threshold)]
        claims_left = [r for r in case_rows if kept(r, threshold) and r.get("note") != "exempt"]
        if removed:
            lost += 1
            removed_examples += [{"id": case["id"], "question": case["question"], **r} for r in removed]
        if case_rows and not claims_left:
            emptied += 1
    return {
        "answered_cases": len(cases),
        "answers_losing_a_sentence": lost,
        "answers_left_empty_refused": emptied,
        "sentences_scored": sum(r["score"] is not None for r in rows),
        "sentences_removed": sum(not kept(r, threshold) for r in rows),
        "removed": removed_examples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results", type=Path)
    parser.add_argument("--key", type=Path)
    parser.add_argument("--model", default="cross-encoder/nli-deberta-v3-small")
    parser.add_argument("--premises", choices=["sentence", "pairs", "passage"], default="pairs")
    parser.add_argument("--context", choices=["none", "hypothesis", "pronoun"], default="hypothesis",
                        help="prepend the previous answer sentence after any pronoun/connector opening (hypothesis), "
                             "only after a pronoun opening (pronoun), or never (none)")
    parser.add_argument("--clean", action="store_true",
                        help="strip leading connectors and 'as mentioned in the source' from hypotheses, and split "
                             "bulleted passages into separate premises")
    parser.add_argument("--thresholds", type=float, nargs="+", default=[0.3, 0.5, 0.7])
    parser.add_argument("--examples", type=int, default=5, help="removed-sentence examples to print in replay mode")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cases = [c for c in json.loads(args.results.read_text(encoding="utf-8"))["results"] if c["diagnostics"]["status"] == "answered"]
    key = json.loads(args.key.read_text(encoding="utf-8")) if args.key else None

    model = CrossEncoder(args.model, device="cpu")
    entail = next(i for i, name in model.model.config.id2label.items() if name.lower() == "entailment")
    model.predict([("Warm-up premise.", "Warm-up hypothesis.")])

    timings: list = []
    rows = [row for case in cases for row in score_case(case, model, entail, args, timings)]
    seconds = sum(t for t, _ in timings)
    print(f"model {args.model} | premises={args.premises} context={args.context} | {len(timings)} sentences | "
          f"{seconds / max(len(timings), 1):.3f} s/sentence | {seconds * 1000 / max(sum(n for _, n in timings), 1):.0f} ms/pair")

    summaries = {}
    for threshold in args.thresholds:
        if key:
            summaries[threshold] = key_summary(cases, rows, key, threshold)
            s = summaries[threshold]
            print(f"t={threshold}: good kept {s['good_answers_fully_kept']} | flawed fixed {s['flawed_answers_fixed']} | "
                  f"bad removed {s['bad_sentences_removed']} | ok lost in flawed {s['ok_sentences_lost_in_flawed']} | "
                  f"damaged {s['good_answers_damaged']} | not fixed {s['flawed_answers_not_fixed']}")
        else:
            summaries[threshold] = replay_summary(cases, rows, threshold)
            s = summaries[threshold]
            print(f"t={threshold}: {s['answers_losing_a_sentence']}/{s['answered_cases']} answers lose a sentence | "
                  f"{s['answers_left_empty_refused']} left empty (refused) | "
                  f"{s['sentences_removed']}/{s['sentences_scored']} sentences removed")

    if not key and args.examples:
        removed = summaries[args.thresholds[0]]["removed"]
        for example in random.Random(7).sample(removed, min(args.examples, len(removed))):
            print(f"\n[{example['id']}] Q: {example['question']}\n  removed (score {example['score']:.2f}): {example['sentence']}\n"
                  f"  best premise: {example['best_premise']}")

    if args.output:
        args.output.write_text(json.dumps({"rows": rows, "summaries": summaries}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
