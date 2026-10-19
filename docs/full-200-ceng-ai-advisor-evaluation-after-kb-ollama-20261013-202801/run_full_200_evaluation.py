"""Full 200-question CENG AI Advisor evaluation artifact runner.

This runner is intentionally evaluation-only. It loads the official 200-case
semantic coverage dataset, calls the current backend/RAG code as-is, and writes
incremental structured results plus aggregate metrics into this artifact folder.
It does not rebuild or modify the KB, embeddings, Chroma collection, prompts, or
retrieval behavior.
"""

from __future__ import annotations

import json
import re
import sys
import time
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ARTIFACT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ARTIFACT_DIR.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.api.chat import (
    ConversationTurn,
    attach_resolution_metadata,
    build_resolution_context,
    out_of_scope_response,
    previous_source_response,
    unresolved_follow_up_response,
)
from backend.app.query_understanding import resolve_query
from backend.app.rag.rag_pipeline import (
    ANSWERED,
    ERROR,
    INSUFFICIENT_INFORMATION,
    OUT_OF_SCOPE,
    RAGPipeline,
    unsupported_generated_answer_reason,
)


QUESTIONS_PATH = PROJECT_ROOT / "docs" / "semantic-coverage-200-questions.json"
RESULTS_PATH = ARTIFACT_DIR / "results.json"
REPORT_PATH = ARTIFACT_DIR / "report.md"

TERMS_TO_IGNORE = {
    "about",
    "after",
    "also",
    "because",
    "before",
    "being",
    "between",
    "build",
    "computer",
    "could",
    "engineering",
    "engineers",
    "from",
    "have",
    "help",
    "important",
    "include",
    "learn",
    "more",
    "should",
    "student",
    "students",
    "their",
    "there",
    "these",
    "they",
    "what",
    "when",
    "where",
    "which",
    "with",
    "work",
    "would",
}

TOPIC_SYNONYMS = {
    "academic_regulations": ("regulation", "exam", "grading", "attendance", "transfer"),
    "ai": ("ai", "artificial intelligence", "machine learning", "generative"),
    "career": ("career", "job", "employ", "work", "industry"),
    "computer_engineering": ("computer engineering", "ceng", "computing discipline"),
    "curriculum": ("course", "curriculum", "semester", "class"),
    "cybersecurity": ("cyber", "security", "cryptography", "cloud security"),
    "gpa": ("gpa", "grade"),
    "graduate_studies": ("master", "graduate", "academia"),
    "hardware": ("hardware", "embedded", "microcontroller", "architecture", "electronics", "fpga", "iot"),
    "internships": ("internship", "staj", "workplace", "erasmus"),
    "mathematics": ("math", "calculus", "algebra", "discrete", "statistics", "linear algebra"),
    "networks": ("network", "protocol", "cloud"),
    "operating_systems": ("linux", "operating system", "unix", "command line"),
    "projects": ("project", "portfolio", "github", "open source"),
    "remote_work": ("remote", "abroad"),
    "salary": ("salary", "pay"),
    "software": ("software", "backend", "frontend", "database", "web", "testing"),
    "student_life": ("club", "community", "hackathon", "competition", "student life"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_cases() -> list[dict[str, Any]]:
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    cases = list(data["cases"])
    if len(cases) != 200:
        raise RuntimeError(f"Official dataset should contain 200 cases, found {len(cases)}.")
    return cases


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def previous_turn_from_result(question: str, result: dict[str, Any] | None) -> ConversationTurn | None:
    if not result:
        return None
    return ConversationTurn(
        question=question,
        status=result.get("status") or ANSWERED,
        answer=result.get("answer") or "",
        sources=tuple(result.get("sources") or ()),
        retrieved_context=tuple(result.get("retrieved_context") or ()),
        citation_metadata=result.get("citation_metadata") or {},
    )


def run_backend_question(
    pipeline: RAGPipeline,
    question: str,
    previous_turn: ConversationTurn | None,
) -> tuple[dict[str, Any], Any]:
    resolution = resolve_query(question, previous_turn)
    if resolution.kind == "source_follow_up":
        result = previous_source_response(question, previous_turn) if previous_turn else unresolved_follow_up_response(
            question,
            "I am not sure which previous topic or information you are referring to. Please ask a complete question about Computer Engineering.",
        )
    elif resolution.kind == "vague_no_referent":
        result = unresolved_follow_up_response(
            question,
            "I am not sure which previous topic or information you are referring to. Please ask a complete question about Computer Engineering.",
        )
    elif resolution.kind == "out_of_scope_persona_meta":
        result = out_of_scope_response(question)
    else:
        result = pipeline.answer(
            question,
            conversation_context=build_resolution_context(resolution),
            resolved_question=resolution.resolved_question,
        )
    return attach_resolution_metadata(result, resolution), resolution


def compact_context(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compacted = []
    for item in items:
        passage = item.get("passage") or item.get("text") or item.get("passage_preview") or ""
        compacted.append(
            {
                "label": item.get("label"),
                "chunk_id": item.get("chunk_id"),
                "source_id": item.get("source_id"),
                "title": item.get("title"),
                "category": item.get("category"),
                "similarity_score": item.get("similarity_score"),
                "url": item.get("url"),
                "passage": passage,
            }
        )
    return compacted


def context_relevant(case: dict[str, Any], context: list[dict[str, Any]], metadata: dict[str, Any]) -> bool:
    expected = case.get("expected_behavior")
    if expected in {"out_of_scope", "insufficient", "source_follow_up"}:
        return bool(metadata.get("evidence_sufficient"))
    if not context:
        return False
    expected_categories = set(case.get("expected_categories") or ())
    categories = {item.get("category") for item in context[:5]}
    if expected_categories and expected_categories & categories:
        return True
    haystack = " ".join(
        " ".join(
            str(part or "")
            for part in (
                item.get("category"),
                item.get("title"),
                item.get("source_id"),
                item.get("passage", "")[:700],
            )
        )
        for item in context[:5]
    ).lower()
    return any(
        any(term in haystack for term in TOPIC_SYNONYMS.get(topic, (topic,)))
        for topic in case.get("expected_topics") or ()
    )


def answer_sentences(answer: str) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+|\n+", answer or "")
    return [piece.strip(" -\t") for piece in pieces if piece.strip(" -\t")]


def content_terms(text: str) -> set[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+.#-]{2,}", normalize_text(text))
    return {token for token in tokens if token not in TERMS_TO_IGNORE}


def citation_labels(text: str) -> list[str]:
    return re.findall(r"\[(S\d+)\]", text or "")


def label_to_passage(context: list[dict[str, Any]]) -> dict[str, str]:
    return {item.get("label"): item.get("passage") or "" for item in context if item.get("label")}


def claim_support_checks(answer: str, context: list[dict[str, Any]]) -> dict[str, Any]:
    passages = label_to_passage(context)
    checks = []
    unsupported = []
    uncited = []
    for sentence in answer_sentences(answer):
        labels = citation_labels(sentence)
        terms = content_terms(re.sub(r"\[(S\d+)\]", "", sentence))
        if not labels:
            uncited.append(sentence)
            checks.append({"claim": sentence, "labels": [], "supported": False, "reason": "missing inline citation"})
            continue
        cited_text = " ".join(passages.get(label, "") for label in labels).lower()
        if not terms:
            supported = True
            overlap = []
        else:
            overlap = sorted(term for term in terms if term.lower() in cited_text)
            required = 1 if len(terms) <= 3 else max(2, min(4, len(terms) // 3))
            supported = len(overlap) >= required
        record = {"claim": sentence, "labels": labels, "supported": supported, "overlap_terms": overlap[:12]}
        checks.append(record)
        if not supported:
            unsupported.append(record)
    return {
        "all_claims_cited": not uncited,
        "all_cited_claims_supported_by_overlap": not unsupported,
        "unsupported_claim_count": len(unsupported),
        "uncited_claim_count": len(uncited),
        "checks": checks,
    }


def classify_case(case: dict[str, Any], result: dict[str, Any], resolution: Any) -> tuple[str, dict[str, Any]]:
    status = result.get("status")
    expected = case.get("expected_behavior")
    context = compact_context(result.get("retrieved_context") or [])
    metadata = result.get("retrieval_metadata") or {}
    citations = result.get("citation_metadata") or {}
    citation_valid = bool(citations.get("valid", True)) and not citations.get("invalid_labels")
    evidence_exists = context_relevant(case, context, metadata)
    support = claim_support_checks(result.get("answer") or "", context) if status == ANSWERED else {
        "all_claims_cited": True,
        "all_cited_claims_supported_by_overlap": True,
        "unsupported_claim_count": 0,
        "uncited_claim_count": 0,
        "checks": [],
    }
    unsupported_reason = None
    if status == ANSWERED:
        try:
            unsupported_reason = unsupported_generated_answer_reason(case["question"], result.get("answer") or "", context)
        except Exception as exc:
            unsupported_reason = f"support-check-error: {exc!r}"

    if status == ERROR:
        label = "runtime_error"
    elif expected in {"out_of_scope", "insufficient"} and status in {OUT_OF_SCOPE, INSUFFICIENT_INFORMATION}:
        label = "correct_insufficient_information"
    elif status in {OUT_OF_SCOPE, INSUFFICIENT_INFORMATION}:
        label = "incorrect_refusal_evidence_exists" if evidence_exists else "correct_insufficient_information"
    elif expected in {"out_of_scope", "insufficient"} and status == ANSWERED:
        label = "unsupported_incorrect_or_misleading"
    elif status == ANSWERED and citation_valid and support["all_claims_cited"] and support["all_cited_claims_supported_by_overlap"] and not unsupported_reason and evidence_exists:
        label = "correct_evidence_supported"
    else:
        label = "unsupported_incorrect_or_misleading"

    diagnostics = {
        "query_kind": resolution.kind,
        "resolved_question": resolution.resolved_question,
        "status": status,
        "llm_called": result.get("llm_called"),
        "evidence_exists_by_eval": evidence_exists,
        "citation_valid": citation_valid,
        "citation_metadata": citations,
        "support_check": support,
        "unsupported_generated_answer_reason": unsupported_reason,
        "retrieval_metadata": metadata,
        "timing": result.get("timing") or {},
        "model": result.get("model"),
        "error": result.get("error"),
    }
    return label, diagnostics


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    label_counts = Counter(row["evaluation_label"] for row in results)
    status_counts = Counter(row["diagnostics"]["status"] for row in results)
    group_counts: dict[str, Counter[str]] = defaultdict(Counter)
    group_total = Counter()
    citation_applicable = 0
    citation_valid = 0
    evidence_supported = 0
    latencies = []
    for row in results:
        group = row["group"]
        group_total[group] += 1
        group_counts[group][row["evaluation_label"]] += 1
        if row["diagnostics"]["status"] == ANSWERED:
            citation_applicable += 1
            if row["diagnostics"]["citation_valid"]:
                citation_valid += 1
            if row["evaluation_label"] == "correct_evidence_supported":
                evidence_supported += 1
        total_seconds = row["diagnostics"].get("timing", {}).get("total_seconds")
        if isinstance(total_seconds, (int, float)):
            latencies.append(float(total_seconds))

    by_group = {}
    for group, total in sorted(group_total.items()):
        labels = dict(group_counts[group])
        by_group[group] = {
            "total": total,
            "labels": labels,
            "correct_evidence_supported_pct": round(100 * labels.get("correct_evidence_supported", 0) / total, 1),
            "correct_insufficient_information_pct": round(100 * labels.get("correct_insufficient_information", 0) / total, 1),
            "incorrect_refusal_evidence_exists_pct": round(100 * labels.get("incorrect_refusal_evidence_exists", 0) / total, 1),
            "unsupported_incorrect_or_misleading_pct": round(100 * labels.get("unsupported_incorrect_or_misleading", 0) / total, 1),
            "runtime_error_pct": round(100 * labels.get("runtime_error", 0) / total, 1),
        }

    return {
        "case_count": len(results),
        "evaluation_label_counts": dict(label_counts),
        "evaluation_label_percentages": {
            key: round(100 * value / len(results), 1) for key, value in sorted(label_counts.items())
        }
        if results
        else {},
        "status_counts": dict(status_counts),
        "answered_cases": citation_applicable,
        "answered_cases_with_valid_citations": citation_valid,
        "answered_cases_with_valid_citations_pct": round(100 * citation_valid / citation_applicable, 1)
        if citation_applicable
        else 0.0,
        "answered_cases_evidence_supported": evidence_supported,
        "answered_cases_evidence_supported_pct": round(100 * evidence_supported / citation_applicable, 1)
        if citation_applicable
        else 0.0,
        "by_group": by_group,
        "latency_seconds": {
            "mean": round(sum(latencies) / len(latencies), 2) if latencies else None,
            "max": round(max(latencies), 2) if latencies else None,
            "min": round(min(latencies), 2) if latencies else None,
        },
        "systematic_failure_counts": systematic_failures(results),
    }


def systematic_failures(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in results:
        label = row["evaluation_label"]
        diag = row["diagnostics"]
        if label == "incorrect_refusal_evidence_exists":
            reason = (diag["retrieval_metadata"] or {}).get("unsupported_reason") or diag.get("query_kind") or "refusal"
            counts[f"false_refusal: {reason}"] += 1
        elif label == "unsupported_incorrect_or_misleading":
            if not diag.get("citation_valid"):
                counts["answered_with_invalid_citations"] += 1
            elif diag.get("unsupported_generated_answer_reason"):
                counts[f"unsupported_generation: {diag['unsupported_generated_answer_reason']}"] += 1
            elif not diag.get("support_check", {}).get("all_claims_cited", True):
                counts["answered_with_uncited_claims"] += 1
            elif not diag.get("support_check", {}).get("all_cited_claims_supported_by_overlap", True):
                counts["cited_passages_do_not_support_claim_terms"] += 1
            elif not diag.get("evidence_exists_by_eval"):
                counts["answered_without_relevant_expected_evidence"] += 1
            else:
                counts["other_unsupported_or_misleading"] += 1
        elif label == "runtime_error":
            counts[f"runtime_error: {diag.get('error') or 'unknown'}"] += 1
    return dict(counts.most_common())


def write_output(results: list[dict[str, Any]], complete: bool, blocker: str | None = None) -> None:
    output = {
        "artifact": "full-200-ceng-ai-advisor-evaluation",
        "generated_at": utc_now(),
        "complete": complete,
        "blocker": blocker,
        "dataset": str(QUESTIONS_PATH.relative_to(PROJECT_ROOT)),
        "procedure": (
            "Official 200-question semantic coverage dataset; current backend query-resolution/session logic; "
            "current RAGPipeline, KB, Chroma collection, and Ollama model; evaluation-only scoring with citation-label "
            "validity and claim/evidence lexical support checks."
        ),
        "case_count": len(results),
        "summary": summarize(results),
        "results": results,
    }
    RESULTS_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(render_report(output), encoding="utf-8")


def pct(count: int, total: int) -> str:
    return f"{count}/{total} ({(100 * count / total if total else 0):.1f}%)"


def render_report(output: dict[str, Any]) -> str:
    summary = output["summary"]
    total = summary["case_count"]
    lines = [
        "# Full 200-Question CENG AI Advisor Evaluation",
        "",
        f"Generated at: `{output['generated_at']}`",
        f"Complete: `{output['complete']}`",
        f"Dataset: `{output['dataset']}`",
        "",
        "## Procedure",
        "",
        output["procedure"],
        "",
        "The scoring is stricter than citation-format checking: answered cases require valid citation labels, no built-in unsupported-generation warning, expected-topic evidence, and a lexical claim/evidence support check. It remains an automated evaluation and should not be represented as human proof of every factual claim.",
        "",
        "## Aggregate Results",
        "",
    ]
    counts = summary["evaluation_label_counts"]
    for label in (
        "correct_evidence_supported",
        "correct_insufficient_information",
        "incorrect_refusal_evidence_exists",
        "unsupported_incorrect_or_misleading",
        "runtime_error",
    ):
        lines.append(f"- {label}: {pct(counts.get(label, 0), total)}")
    lines.extend(
        [
            f"- Answered cases with valid citation labels: {pct(summary['answered_cases_with_valid_citations'], summary['answered_cases'])}",
            f"- Answered cases passing evidence-support checks: {pct(summary['answered_cases_evidence_supported'], summary['answered_cases'])}",
            f"- Mean latency: {summary['latency_seconds']['mean']}s",
            "",
            "## Results By Student-Question Category",
            "",
            "| Category | Total | Supported | Correct insuff. | Incorrect refusal | Unsupported/misleading | Runtime errors |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for group, record in summary["by_group"].items():
        labels = record["labels"]
        lines.append(
            "| "
            + " | ".join(
                [
                    group,
                    str(record["total"]),
                    str(labels.get("correct_evidence_supported", 0)),
                    str(labels.get("correct_insufficient_information", 0)),
                    str(labels.get("incorrect_refusal_evidence_exists", 0)),
                    str(labels.get("unsupported_incorrect_or_misleading", 0)),
                    str(labels.get("runtime_error", 0)),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Most Common Systematic Failures", ""])
    failures = summary["systematic_failure_counts"]
    if failures:
        for name, count in list(failures.items())[:12]:
            lines.append(f"- {count}: {name}")
    else:
        lines.append("- None detected.")
    if output.get("blocker"):
        lines.extend(["", "## Blocker", "", output["blocker"]])
    lines.extend(["", "## Files", "", f"- Structured results: `{RESULTS_PATH.name}`", f"- Report: `{REPORT_PATH.name}`"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full official 200-question evaluation.")
    parser.add_argument("--no-resume", action="store_true", help="Discard saved results and rerun all 200 cases.")
    args = parser.parse_args()
    cases = load_cases()
    existing = (
        {"results": []}
        if args.no_resume or not RESULTS_PATH.exists()
        else json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    )
    results = list(existing.get("results") or [])
    done = {row["id"] for row in results}
    pipeline = RAGPipeline()

    try:
        for index, case in enumerate(cases, start=1):
            if case["id"] in done:
                continue
            print(f"case {index:03d}/200 {case['id']} {case['group']}", flush=True)
            started = time.perf_counter()
            previous_result = None
            previous_turn = None
            if case.get("previous_question"):
                previous_result, _ = run_backend_question(pipeline, case["previous_question"], None)
                previous_turn = previous_turn_from_result(case["previous_question"], previous_result)
            try:
                result, resolution = run_backend_question(pipeline, case["question"], previous_turn)
                label, diagnostics = classify_case(case, result, resolution)
                record = {
                    **case,
                    "evaluation_label": label,
                    "elapsed_wall_seconds": round(time.perf_counter() - started, 3),
                    "diagnostics": diagnostics,
                    "answer": result.get("answer"),
                    "sources": result.get("sources") or [],
                    "retrieved_context": compact_context(result.get("retrieved_context") or []),
                    "previous_turn_setup": None
                    if not previous_result
                    else {
                        "question": case.get("previous_question"),
                        "status": previous_result.get("status"),
                        "answer": previous_result.get("answer"),
                        "sources": previous_result.get("sources") or [],
                    },
                }
            except Exception as exc:
                record = {
                    **case,
                    "evaluation_label": "runtime_error",
                    "elapsed_wall_seconds": round(time.perf_counter() - started, 3),
                    "diagnostics": {
                        "query_kind": None,
                        "resolved_question": None,
                        "status": ERROR,
                        "llm_called": None,
                        "evidence_exists_by_eval": False,
                        "citation_valid": False,
                        "citation_metadata": {},
                        "support_check": {},
                        "unsupported_generated_answer_reason": None,
                        "retrieval_metadata": {},
                        "timing": {},
                        "model": None,
                        "error": repr(exc),
                    },
                    "answer": None,
                    "sources": [],
                    "retrieved_context": [],
                    "previous_turn_setup": None,
                }
            results.append(record)
            write_output(results, complete=False)
        write_output(results, complete=True)
    except KeyboardInterrupt:
        write_output(results, complete=False, blocker="Interrupted by user.")
        raise
    except Exception as exc:
        write_output(results, complete=False, blocker=repr(exc))
        raise

    print(json.dumps(summarize(results), ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
