"""Run comprehensive WEX428 RAG quality evaluation.

This extends the existing local RAG evaluation workflow. It uses the production
RAGPipeline as-is and records retrieval quality separately from generated-answer
quality. The answer-quality rubric is an automated preliminary assessment; it is
not a substitute for manual factual review of every claim.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.rag_pipeline import ANSWERED, ERROR, INSUFFICIENT_INFORMATION, OUT_OF_SCOPE, RAGPipeline


CASES_PATH = PROJECT_ROOT / "tests" / "rag_comprehensive_evaluation_cases.json"
RESULTS_PATH = PROJECT_ROOT / "docs" / "rag-comprehensive-evaluation-results.json"
REPORT_PATH = PROJECT_ROOT / "docs" / "rag-comprehensive-evaluation-report.md"
RECLASSIFIED_RESULTS_PATH = PROJECT_ROOT / "docs" / "rag-category-normalization-recheck.json"
RECLASSIFIED_REPORT_PATH = PROJECT_ROOT / "docs" / "rag-category-normalization-recheck.md"

ANSWER_QUALITY_VALUES = (
    "Correct / well-supported",
    "Partially correct / partially supported",
    "Unsupported or incorrect",
    "Appropriate refusal / insufficient information",
)

# Evaluation-only category compatibility map.
#
# These aliases normalize evaluation labels against the actual category names
# stored in chunk metadata. They intentionally do not affect production
# retrieval, similarity scores, thresholds, embeddings, ChromaDB, prompts, or
# generated answers.
CATEGORY_COMPATIBILITY: dict[str, tuple[str, ...]] = {
    "AI": ("artificial_intelligence",),
    "cybersecurity": ("specializations",),
    "employment": ("career_opportunities",),
    "local_job_market": ("employment",),
    "mathematics": ("curriculum",),
    "programming": ("skills_and_technologies",),
    "remote_work": ("work_life_balance",),
    "skills": ("skills_and_technologies",),
}

CATEGORY_COMPATIBILITY_JUSTIFICATIONS: dict[str, str] = {
    "AI -> artificial_intelligence": "The evaluation shorthand `AI` refers to the indexed `artificial_intelligence` category.",
    "cybersecurity -> specializations": "Cybersecurity appears as a computing specialization/subdiscipline in advising evidence.",
    "employment -> career_opportunities": "`career_opportunities` is an employment-focused indexed category for job/role evidence.",
    "local_job_market -> employment": "Local job-market evidence is stored under the broader indexed `employment` category.",
    "mathematics -> curriculum": "Math requirements are represented in curriculum/course evidence rather than a separate indexed math category.",
    "programming -> skills_and_technologies": "Programming-language/tool evidence is a technical-skills subset in the indexed corpus.",
    "remote_work -> work_life_balance": "Remote/hybrid work evidence overlaps with work-life balance sources when evaluating work-style questions.",
    "skills -> skills_and_technologies": "The evaluation label `skills` maps to the indexed technical/professional skills category.",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def load_existing_results(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = load_json(path)
    return {item["id"]: item for item in data.get("cases", [])}


def compatible_actual_categories(expected_category: str) -> set[str]:
    return {expected_category, *CATEGORY_COMPATIBILITY.get(expected_category, ())}


def category_matches(actual_category: str | None, expected_categories: list[str]) -> bool:
    if not actual_category:
        return False
    return any(actual_category in compatible_actual_categories(expected) for expected in expected_categories)


def count_matching_categories(categories: list[str | None], expected_categories: list[str]) -> int:
    return sum(1 for category in categories if category_matches(category, expected_categories))


def classify_retrieval(
    retrieved_context: list[dict[str, Any]],
    retrieval_metadata: dict[str, Any],
    expected_categories: list[str],
    expected_behavior: str,
) -> str:
    out_of_scope = bool(retrieval_metadata.get("out_of_scope"))
    evidence_sufficient = bool(retrieval_metadata.get("evidence_sufficient"))
    top_similarity = float(retrieval_metadata.get("top_similarity_score") or 0.0)
    categories = [item.get("category") for item in retrieved_context]
    matched = count_matching_categories(categories, expected_categories)

    if expected_behavior == "out_of_scope":
        return "Correctly rejected" if out_of_scope else "False positive"
    if matched >= 2 and evidence_sufficient and top_similarity >= 0.45:
        return "Highly relevant"
    if matched >= 1 and evidence_sufficient:
        return "Relevant"
    if matched >= 1:
        return "Partially relevant"
    return "Irrelevant"


def assess_answer_quality(result: dict[str, Any], retrieval_label: str, expected_behavior: str) -> tuple[str, str]:
    status = result.get("status")
    citation_metadata = result.get("citation_metadata") or {}
    citation_valid = bool(citation_metadata.get("valid"))

    if expected_behavior == "out_of_scope":
        if status == OUT_OF_SCOPE:
            return "Appropriate refusal / insufficient information", "Out-of-scope query was refused before generation."
        return "Unsupported or incorrect", "Out-of-scope query was not refused."

    if status in {INSUFFICIENT_INFORMATION, OUT_OF_SCOPE}:
        if expected_behavior in {"answer_or_refuse_if_evidence_insufficient", "insufficient_ok"}:
            return "Appropriate refusal / insufficient information", "Pipeline refused because retrieved evidence was insufficient."
        return "Partially correct / partially supported", "Pipeline refused; manual review should decide whether available evidence should have supported an answer."

    if status == ERROR:
        return "Unsupported or incorrect", result.get("error") or "Pipeline returned an error."

    if status == ANSWERED and citation_valid:
        if retrieval_label in {"Highly relevant", "Relevant"}:
            return "Correct / well-supported", "Automated proxy: relevant retrieval plus valid citations; manual claim-level review still required."
        if retrieval_label == "Partially relevant":
            return "Partially correct / partially supported", "Automated proxy: citations are valid but retrieval was only partially relevant."
        return "Unsupported or incorrect", "Answered with valid citation format, but retrieved categories did not match expectations."

    if status == ANSWERED:
        return "Unsupported or incorrect", "Answered response did not pass citation validation."

    return "Unsupported or incorrect", "Unexpected answer status."


def compact_case_result(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    retrieved_context = result.get("retrieved_context") or []
    retrieval_metadata = result.get("retrieval_metadata") or {}
    retrieval_label = classify_retrieval(
        retrieved_context,
        retrieval_metadata,
        case.get("expected_categories", []),
        case.get("expected_behavior", "answer"),
    )
    answer_quality, notes = assess_answer_quality(result, retrieval_label, case.get("expected_behavior", "answer"))
    citation_metadata = result.get("citation_metadata") or {}
    retrieved_passages = [
        {
            "label": item.get("label"),
            "chunk_id": item.get("chunk_id"),
            "source_id": item.get("source_id"),
            "title": item.get("title"),
            "category": item.get("category"),
            "similarity_score": item.get("similarity_score"),
            "url": item.get("url"),
            "passage_preview": (item.get("passage") or item.get("text") or "")[:700],
        }
        for item in retrieved_context
    ]

    return {
        "id": case["id"],
        "question_number": case.get("question_number"),
        "question": case["question"],
        "case_kind": case["case_kind"],
        "expected_topic": case["expected_topic"],
        "expected_categories": case.get("expected_categories", []),
        "expected_behavior": case.get("expected_behavior", "answer"),
        "retrieval": {
            "label": retrieval_label,
            "evidence_sufficient": retrieval_metadata.get("evidence_sufficient"),
            "out_of_scope": retrieval_metadata.get("out_of_scope"),
            "top_similarity_score": retrieval_metadata.get("top_similarity_score"),
            "results_above_threshold": retrieval_metadata.get("results_above_threshold"),
            "retrieved_sources": [
                {
                    "source_id": item.get("source_id"),
                    "title": item.get("title"),
                    "category": item.get("category"),
                    "similarity_score": item.get("similarity_score"),
                }
                for item in retrieved_context
            ],
            "retrieved_passages": retrieved_passages,
        },
        "generation": {
            "status": result.get("status"),
            "answer": result.get("answer"),
            "llm_called": result.get("llm_called"),
            "sources": result.get("sources") or [],
            "citations": citation_metadata.get("cited_labels", []),
            "citation_valid": citation_metadata.get("valid", False),
            "citation_metadata": citation_metadata,
            "answer_quality_assessment": answer_quality,
            "assessment_method": "automatic rubric based on retrieval relevance, answer status, and citation validation; manual factual review is still required",
            "notes": notes,
            "error": result.get("error"),
        },
        "timing": result.get("timing") or {},
    }


def summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    def count_by(path: tuple[str, ...]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in cases:
            current: Any = item
            for key in path:
                current = current.get(key, {}) if isinstance(current, dict) else {}
            label = str(current)
            counts[label] = counts.get(label, 0) + 1
        return dict(sorted(counts.items()))

    original_count = sum(1 for item in cases if item["case_kind"] == "original")
    paraphrase_count = sum(1 for item in cases if item["case_kind"] == "paraphrased_unseen")
    citation_applicable = [item for item in cases if item["generation"]["status"] == ANSWERED]
    citation_valid_count = sum(1 for item in citation_applicable if item["generation"]["citation_valid"])
    appropriate_refusals = sum(
        1
        for item in cases
        if item["generation"]["answer_quality_assessment"] == "Appropriate refusal / insufficient information"
    )
    return {
        "total_cases": len(cases),
        "original_questions_tested": original_count,
        "paraphrased_unseen_questions_tested": paraphrase_count,
        "retrieval_label_counts": count_by(("retrieval", "label")),
        "answer_status_counts": count_by(("generation", "status")),
        "answer_quality_counts": count_by(("generation", "answer_quality_assessment")),
        "answered_cases_with_valid_citations": citation_valid_count,
        "answered_cases": len(citation_applicable),
        "appropriate_refusal_count": appropriate_refusals,
        "weak_or_failing_topics": weak_topics(cases),
    }


def weak_topics(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    weak: dict[str, dict[str, Any]] = {}
    for item in cases:
        retrieval_label = item["retrieval"]["label"]
        answer_quality = item["generation"]["answer_quality_assessment"]
        if retrieval_label in {"Irrelevant", "False positive"} or answer_quality in {
            "Partially correct / partially supported",
            "Unsupported or incorrect",
        }:
            topic = item["expected_topic"]
            record = weak.setdefault(topic, {"topic": topic, "case_count": 0, "case_ids": []})
            record["case_count"] += 1
            record["case_ids"].append(item["id"])
    return sorted(weak.values(), key=lambda item: (-item["case_count"], item["topic"]))


def render_report(output: dict[str, Any]) -> str:
    summary = output["summary"]
    cases = output["cases"]
    successes = [
        item
        for item in cases
        if item["retrieval"]["label"] in {"Highly relevant", "Relevant"}
        and item["generation"]["answer_quality_assessment"] == "Correct / well-supported"
    ][:5]
    failures = [
        item
        for item in cases
        if item["retrieval"]["label"] in {"Irrelevant", "False positive"}
        or item["generation"]["answer_quality_assessment"] in {"Partially correct / partially supported", "Unsupported or incorrect"}
    ][:8]

    lines = [
        "# WEX428 Comprehensive RAG Evaluation Report",
        "",
        f"Generated at: `{output['generated_at']}`",
        "",
        "## Scope",
        "",
        "This evaluation runs the existing local RAG pipeline against all 60 representative questions from `ceng-questions.pdf` plus paraphrased/unseen questions across major categories. It does not modify production retrieval, embeddings, the vector database, the LLM, or prompts.",
        "",
        "Answer-quality labels are an automated preliminary rubric based on retrieval relevance, answer status, and citation validation. They are useful for project evaluation, but they do not replace manual claim-level factual review.",
        "",
        "## Summary",
        "",
        f"- Total cases: {summary['total_cases']}",
        f"- Original questions tested: {summary['original_questions_tested']}",
        f"- Paraphrased/unseen questions tested: {summary['paraphrased_unseen_questions_tested']}",
        f"- Answered cases with valid citations: {summary['answered_cases_with_valid_citations']}/{summary['answered_cases']}",
        f"- Appropriate refusals: {summary['appropriate_refusal_count']}",
        "",
        "## Retrieval Quality Results",
        "",
    ]
    lines.extend(markdown_counts(summary["retrieval_label_counts"]))
    lines.extend(["", "## Answer Status Results", ""])
    lines.extend(markdown_counts(summary["answer_status_counts"]))
    lines.extend(["", "## Answer-Quality Results", ""])
    lines.extend(markdown_counts(summary["answer_quality_counts"]))
    lines.extend(["", "## Weak Categories / Topics", ""])
    if summary["weak_or_failing_topics"]:
        for item in summary["weak_or_failing_topics"]:
            lines.append(f"- {item['topic']}: {item['case_count']} case(s) - {', '.join(item['case_ids'][:10])}")
    else:
        lines.append("- None identified by the automated rubric.")
    lines.extend(["", "## Representative Successful Examples", ""])
    for item in successes:
        lines.append(
            f"- `{item['id']}` ({item['expected_topic']}): retrieval `{item['retrieval']['label']}`, answer `{item['generation']['answer_quality_assessment']}`."
        )
    if not successes:
        lines.append("- None classified as fully successful by the automated rubric.")
    lines.extend(["", "## Representative Failure / Caution Examples", ""])
    for item in failures:
        lines.append(
            f"- `{item['id']}` ({item['expected_topic']}): retrieval `{item['retrieval']['label']}`, answer `{item['generation']['answer_quality_assessment']}`. Note: {item['generation']['notes']}"
        )
    if not failures:
        lines.append("- None classified as failing by the automated rubric.")
    lines.extend(
        [
            "",
            "## Evaluation Limitations",
            "",
            "- Automated citation validation confirms citation format and label availability, not full factual entailment.",
            "- Some advisory questions legitimately require cautious or insufficient-information responses.",
            "- Local LLM outputs may vary between runs.",
            "- The evaluation records passage previews and sources, but final grading should manually review representative answers before defense.",
            "",
            "## Files",
            "",
            f"- Structured results: `{RESULTS_PATH.as_posix()}`",
            f"- Case set: `{CASES_PATH.as_posix()}`",
        ]
    )
    return "\n".join(lines) + "\n"


def markdown_counts(counts: dict[str, int]) -> list[str]:
    lines = ["| Label | Count |", "|---|---:|"]
    for label, count in counts.items():
        lines.append(f"| {label} | {count} |")
    return lines


def load_indexed_category_counts() -> dict[str, int]:
    chunks_path = PROJECT_ROOT / "knowledge_base" / "chunks" / "chunks.jsonl"
    counts: dict[str, int] = {}
    with chunks_path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            category = json.loads(line).get("category")
            counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items()))


def evaluation_category_counts(cases: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        for category in case.get("expected_categories", []):
            counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items()))


def reclassify_saved_retrieval_results(
    *,
    input_path: Path = RESULTS_PATH,
    output_path: Path = RECLASSIFIED_RESULTS_PATH,
    report_path: Path = RECLASSIFIED_REPORT_PATH,
) -> dict[str, Any]:
    case_data = load_json(CASES_PATH)
    cases_by_id = {case["id"]: case for case in case_data["cases"]}
    saved = load_json(input_path)
    old_cases = saved["cases"]
    reclassified_cases: list[dict[str, Any]] = []
    changed_cases: list[dict[str, Any]] = []

    for saved_case in old_cases:
        case = cases_by_id[saved_case["id"]]
        retrieval = saved_case["retrieval"]
        retrieved_sources = retrieval.get("retrieved_sources") or []
        retrieval_metadata = {
            "evidence_sufficient": retrieval.get("evidence_sufficient"),
            "out_of_scope": retrieval.get("out_of_scope"),
            "top_similarity_score": retrieval.get("top_similarity_score"),
            "results_above_threshold": retrieval.get("results_above_threshold"),
        }
        old_label = retrieval.get("label")
        new_label = classify_retrieval(
            retrieved_sources,
            retrieval_metadata,
            case.get("expected_categories", []),
            case.get("expected_behavior", "answer"),
        )
        actual_categories = [source.get("category") for source in retrieved_sources]
        matched_categories = [
            category for category in actual_categories if category_matches(category, case.get("expected_categories", []))
        ]
        record = {
            "id": saved_case["id"],
            "question": saved_case["question"],
            "case_kind": saved_case["case_kind"],
            "expected_topic": saved_case["expected_topic"],
            "expected_categories": case.get("expected_categories", []),
            "actual_retrieved_categories": actual_categories,
            "matched_categories_after_normalization": matched_categories,
            "old_retrieval_label": old_label,
            "corrected_retrieval_label": new_label,
            "answer_quality_unchanged": saved_case["generation"]["answer_quality_assessment"],
            "generation_status": saved_case["generation"]["status"],
        }
        reclassified_cases.append(record)
        if old_label != new_label:
            changed_cases.append(record)

    output = {
        "stage": "WEX428 Retrieval Category Normalization Recheck",
        "generated_at": utc_now(),
        "source_results": str(input_path.relative_to(PROJECT_ROOT)),
        "note": "Reclassifies retrieval-quality labels from saved retrieval evidence only. It does not rerun retrieval, regenerate answers, alter answer quality, or touch production RAG artifacts.",
        "actual_indexed_category_counts": load_indexed_category_counts(),
        "evaluation_expected_category_counts": evaluation_category_counts(case_data["cases"]),
        "category_compatibility": {
            expected: list(actuals) for expected, actuals in sorted(CATEGORY_COMPATIBILITY.items())
        },
        "category_compatibility_justifications": CATEGORY_COMPATIBILITY_JUSTIFICATIONS,
        "old_retrieval_label_counts": summarize_retrieval_labels(
            [{"retrieval_label": item["old_retrieval_label"]} for item in reclassified_cases],
            key="retrieval_label",
        ),
        "corrected_retrieval_label_counts": summarize_retrieval_labels(
            [{"retrieval_label": item["corrected_retrieval_label"]} for item in reclassified_cases],
            key="retrieval_label",
        ),
        "changed_case_count": len(changed_cases),
        "changed_cases": changed_cases,
        "remaining_irrelevant_cases": [
            item for item in reclassified_cases if item["corrected_retrieval_label"] == "Irrelevant"
        ],
        "cases": reclassified_cases,
    }
    write_json(output_path, output)
    report_path.write_text(render_reclassification_report(output), encoding="utf-8", newline="\n")
    return output


def summarize_retrieval_labels(items: list[dict[str, Any]], *, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        label = item[key]
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))


def render_reclassification_report(output: dict[str, Any]) -> str:
    lines = [
        "# WEX428 Retrieval Category Normalization Recheck",
        "",
        f"Generated at: `{output['generated_at']}`",
        "",
        "This report reclassifies retrieval-quality labels from the saved comprehensive evaluation retrieval evidence only. It does not rerun retrieval, regenerate LLM answers, change answer-quality labels, or modify production RAG behavior.",
        "",
        "## Category Compatibility Map",
        "",
    ]
    for key, reason in sorted(output["category_compatibility_justifications"].items()):
        lines.append(f"- `{key}`: {reason}")

    lines.extend(["", "## Old Retrieval Totals", ""])
    lines.extend(markdown_counts(output["old_retrieval_label_counts"]))
    lines.extend(["", "## Corrected Retrieval Totals", ""])
    lines.extend(markdown_counts(output["corrected_retrieval_label_counts"]))
    lines.extend(["", "## Changed Cases", ""])
    if output["changed_cases"]:
        for item in output["changed_cases"]:
            lines.append(
                f"- `{item['id']}`: `{item['old_retrieval_label']}` -> `{item['corrected_retrieval_label']}`; matched categories: {', '.join(item['matched_categories_after_normalization']) or 'none'}"
            )
    else:
        lines.append("- No cases changed classification.")

    lines.extend(["", "## Remaining Irrelevant Retrieval Cases", ""])
    for item in output["remaining_irrelevant_cases"]:
        lines.append(
            f"- `{item['id']}` ({item['expected_topic']}): expected {item['expected_categories']}; retrieved {item['actual_retrieved_categories'][:5]}"
        )
    return "\n".join(lines) + "\n"


def evaluate_cases(
    *,
    limit: int | None = None,
    ids: set[str] | None = None,
    resume: bool = True,
    output_path: Path = RESULTS_PATH,
    report_path: Path = REPORT_PATH,
) -> dict[str, Any]:
    case_data = load_json(CASES_PATH)
    cases = case_data["cases"]
    if ids:
        cases = [case for case in cases if case["id"] in ids]
    if limit is not None:
        cases = cases[:limit]

    existing_by_id = load_existing_results(output_path) if resume else {}
    results_by_id = dict(existing_by_id)
    pipeline = RAGPipeline()

    for case in cases:
        if resume and case["id"] in results_by_id:
            continue
        result = pipeline.answer(case["question"])
        results_by_id[case["id"]] = compact_case_result(case, result)
        interim_cases = [results_by_id[item["id"]] for item in cases if item["id"] in results_by_id]
        write_json(
            output_path,
            {
                "stage": "WEX428 Comprehensive RAG Evaluation",
                "generated_at": utc_now(),
                "case_source": str(CASES_PATH.relative_to(PROJECT_ROOT)),
                "case_count": len(interim_cases),
                "summary": summarize(interim_cases),
                "rubric": {
                    "answer_quality_values": list(ANSWER_QUALITY_VALUES),
                    "note": "Automated preliminary rubric; manual factual review still required for final defense claims.",
                },
                "cases": interim_cases,
            },
        )

    final_cases = [results_by_id[item["id"]] for item in cases if item["id"] in results_by_id]
    output = {
        "stage": "WEX428 Comprehensive RAG Evaluation",
        "generated_at": utc_now(),
        "case_source": str(CASES_PATH.relative_to(PROJECT_ROOT)),
        "case_count": len(final_cases),
        "summary": summarize(final_cases),
        "rubric": {
            "answer_quality_values": list(ANSWER_QUALITY_VALUES),
            "note": "Automated preliminary rubric; manual factual review still required for final defense claims.",
        },
        "cases": final_cases,
    }
    write_json(output_path, output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(output), encoding="utf-8", newline="\n")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Run WEX428 comprehensive RAG quality evaluation.")
    parser.add_argument("--limit", type=int, default=None, help="Limit cases for smoke testing.")
    parser.add_argument("--ids", nargs="*", default=None, help="Run only selected case IDs.")
    parser.add_argument("--no-resume", action="store_true", help="Ignore existing result file and rerun selected cases.")
    parser.add_argument("--output", default=str(RESULTS_PATH), help="Structured JSON output path.")
    parser.add_argument("--report", default=str(REPORT_PATH), help="Markdown report output path.")
    parser.add_argument(
        "--reclassify-existing",
        action="store_true",
        help="Recalculate retrieval labels from saved retrieval evidence without rerunning RAG or LLM generation.",
    )
    args = parser.parse_args()

    if args.reclassify_existing:
        output = reclassify_saved_retrieval_results(input_path=Path(args.output))
        print(
            json.dumps(
                {
                    "old_retrieval_label_counts": output["old_retrieval_label_counts"],
                    "corrected_retrieval_label_counts": output["corrected_retrieval_label_counts"],
                    "changed_case_count": output["changed_case_count"],
                    "remaining_irrelevant_count": len(output["remaining_irrelevant_cases"]),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    output = evaluate_cases(
        limit=args.limit,
        ids=set(args.ids) if args.ids else None,
        resume=not args.no_resume,
        output_path=Path(args.output),
        report_path=Path(args.report),
    )
    print(json.dumps(output["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
