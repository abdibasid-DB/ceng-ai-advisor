"""Core RAG pipeline for Stage 15.

This module connects the existing retriever to the existing local Ollama
service. It does not expose API endpoints, implement chat history, or build a
frontend chatbot.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
import re
from typing import Any

from ..core.retrieval_config import CANDIDATE_TOP_K, DEFAULT_TOP_K
from ..services.llm_service import (
    LocalLLMError,
    LocalLLMService,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)
from .retriever import Retriever


ANSWERED = "answered"
INSUFFICIENT_INFORMATION = "insufficient_information"
OUT_OF_SCOPE = "out_of_scope"
ERROR = "error"

INSUFFICIENT_MESSAGE = "I don't have enough reliable information in the current knowledge base to answer that question."

MAX_CONTEXT_CHARACTERS = 3000
MAX_PASSAGE_CHARACTERS = 700
RAG_NUM_PREDICT = 220


@dataclass(frozen=True)
class RAGPipelineConfig:
    top_k: int = DEFAULT_TOP_K
    candidate_top_k: int = CANDIDATE_TOP_K
    max_context_characters: int = MAX_CONTEXT_CHARACTERS
    max_passage_characters: int = MAX_PASSAGE_CHARACTERS
    max_citation_retries: int = 1


@dataclass(frozen=True)
class CitationValidation:
    valid: bool
    answer: str
    cited_labels: tuple[str, ...]
    invalid_labels: tuple[str, ...]
    available_labels: tuple[str, ...]
    normalized: bool = False
    reason: str | None = None


class RAGPipeline:
    def __init__(
        self,
        *,
        retriever: Retriever | None = None,
        llm_service: LocalLLMService | None = None,
        config: RAGPipelineConfig | None = None,
    ) -> None:
        self.retriever = retriever or Retriever()
        self.llm_service = llm_service or LocalLLMService()
        self.config = config or RAGPipelineConfig()

    def answer(self, question: str, conversation_context: str | None = None) -> dict[str, Any]:
        start_total = time.perf_counter()
        cleaned = " ".join((question or "").split())
        if not cleaned:
            return self._error_result(question or "", "Question must not be empty.", start_total)
        context_hint = normalize_conversation_context(conversation_context)
        retrieval_query = build_contextual_retrieval_query(cleaned, context_hint)

        try:
            retrieval_start = time.perf_counter()
            retrieval = self.retriever.retrieve(
                retrieval_query,
                top_k=self.config.top_k,
                candidate_top_k=self.config.candidate_top_k,
            )
            retrieval_latency = elapsed(retrieval_start)
        except Exception as exc:
            return self._error_result(cleaned, f"Retrieval failed: {friendly_error(exc)}", start_total)

        if not retrieval.get("evidence_sufficient"):
            status = OUT_OF_SCOPE if retrieval.get("out_of_scope") else INSUFFICIENT_INFORMATION
            return {
                "question": cleaned,
                "status": status,
                "answer": INSUFFICIENT_MESSAGE,
                "llm_called": False,
                "sources": [],
                "retrieved_context": retrieval.get("results", []),
                "retrieval_metadata": retrieval_metadata(retrieval),
                "timing": {
                    "retrieval_seconds": retrieval_latency,
                    "context_construction_seconds": 0.0,
                    "llm_generation_seconds": 0.0,
                    "total_seconds": elapsed(start_total),
                },
                "error": None,
            }

        unsupported_reason = unsupported_specific_fact_reason(cleaned, retrieval.get("results", []))
        if unsupported_reason:
            return {
                "question": cleaned,
                "status": INSUFFICIENT_INFORMATION,
                "answer": INSUFFICIENT_MESSAGE,
                "llm_called": False,
                "sources": [],
                "retrieved_context": retrieval.get("results", []),
                "retrieval_metadata": {**retrieval_metadata(retrieval), "unsupported_reason": unsupported_reason},
                "timing": {
                    "retrieval_seconds": retrieval_latency,
                    "context_construction_seconds": 0.0,
                    "llm_generation_seconds": 0.0,
                    "total_seconds": elapsed(start_total),
                },
                "error": None,
            }

        category_reason = unsupported_category_reason(cleaned, retrieval.get("results", []))
        if category_reason:
            return {
                "question": cleaned,
                "status": INSUFFICIENT_INFORMATION,
                "answer": INSUFFICIENT_MESSAGE,
                "llm_called": False,
                "sources": [],
                "retrieved_context": retrieval.get("results", []),
                "retrieval_metadata": {**retrieval_metadata(retrieval), "unsupported_reason": category_reason},
                "timing": {
                    "retrieval_seconds": retrieval_latency,
                    "context_construction_seconds": 0.0,
                    "llm_generation_seconds": 0.0,
                    "total_seconds": elapsed(start_total),
                },
                "error": None,
            }

        claim_reason = unsupported_claim_reason(cleaned, retrieval.get("results", []))
        if claim_reason:
            return {
                "question": cleaned,
                "status": INSUFFICIENT_INFORMATION,
                "answer": INSUFFICIENT_MESSAGE,
                "llm_called": False,
                "sources": [],
                "retrieved_context": retrieval.get("results", []),
                "retrieval_metadata": {**retrieval_metadata(retrieval), "unsupported_reason": claim_reason},
                "timing": {
                    "retrieval_seconds": retrieval_latency,
                    "context_construction_seconds": 0.0,
                    "llm_generation_seconds": 0.0,
                    "total_seconds": elapsed(start_total),
                },
                "error": None,
            }

        try:
            context_start = time.perf_counter()
            context_results = select_context_results(cleaned, retrieval["results"])
            context_items, context_text = build_context(
                context_results,
                max_context_characters=self.config.max_context_characters,
                max_passage_characters=self.config.max_passage_characters,
            )
            prompt = build_grounded_prompt(cleaned, context_text)
            if context_hint:
                prompt = build_grounded_prompt(cleaned, context_text, conversation_context=context_hint)
            context_latency = elapsed(context_start)
        except Exception as exc:
            return self._error_result(cleaned, f"Context construction failed: {friendly_error(exc)}", start_total, retrieval)

        try:
            llm_start = time.perf_counter()
            llm_response = self.llm_service.generate(prompt, num_predict=RAG_NUM_PREDICT)
            llm_latency = elapsed(llm_start)
            initial_llm_latency = llm_latency
            retry_llm_latency = 0.0
            generations_attempted = 1
            answer_text = normalize_answer(llm_response.text)
        except (OllamaConnectionError, OllamaModelNotFoundError, OllamaTimeoutError, LocalLLMError) as exc:
            return self._error_result(
                cleaned,
                f"Local LLM failed: {friendly_error(exc)}",
                start_total,
                retrieval,
                context_items,
                llm_called=True,
            )
        except Exception as exc:
            return self._error_result(
                cleaned,
                f"Unexpected local LLM failure: {friendly_error(exc)}",
                start_total,
                retrieval,
                context_items,
                llm_called=True,
            )

        if not answer_text:
            return self._error_result(cleaned, "Local LLM returned an empty response.", start_total, retrieval, context_items)
        if invalid_model_answer(answer_text):
            return self._error_result(
                cleaned,
                "Local LLM returned a placeholder-style response instead of a grounded answer.",
                start_total,
                retrieval,
                context_items,
                llm_called=True,
            )

        citation_validation = validate_citations(answer_text, context_items)
        retry_attempted = False
        retry_successful = False
        retry_error = None
        retry_failure_reason = None

        if not citation_validation.valid and self.config.max_citation_retries > 0:
            retry_attempted = True
            try:
                retry_prompt = build_citation_retry_prompt(cleaned, context_text, answer_text, citation_validation.reason)
                retry_start = time.perf_counter()
                retry_response = self.llm_service.generate(retry_prompt, num_predict=RAG_NUM_PREDICT)
                retry_llm_latency = elapsed(retry_start)
                llm_latency += retry_llm_latency
                generations_attempted += 1
                retry_answer = normalize_answer(retry_response.text)
                if retry_answer and not invalid_model_answer(retry_answer):
                    retry_validation = validate_citations(retry_answer, context_items)
                    if retry_validation.valid:
                        answer_text = retry_validation.answer
                        citation_validation = retry_validation
                        retry_successful = True
                    else:
                        retry_failure_reason = retry_validation.reason
                else:
                    retry_failure_reason = "retry returned an empty or placeholder-style answer"
            except (OllamaConnectionError, OllamaModelNotFoundError, OllamaTimeoutError, LocalLLMError) as exc:
                retry_error = f"Local LLM citation retry failed: {friendly_error(exc)}"
            except Exception as exc:
                retry_error = f"Unexpected citation retry failure: {friendly_error(exc)}"

        if not citation_validation.valid:
            error_message = citation_validation.reason or "Local LLM response did not include valid evidence labels."
            if retry_error:
                error_message = f"{error_message} {retry_error}"
            return self._error_result(
                cleaned,
                error_message,
                start_total,
                retrieval,
                context_items,
                llm_called=True,
                citation_metadata=citation_metadata(
                    citation_validation,
                    retry_attempted,
                    retry_successful,
                    generations_attempted,
                    retry_failure_reason=retry_failure_reason,
                ),
            )

        answer_text = citation_validation.answer

        answer_is_insufficient = is_insufficient_answer(answer_text)

        return {
            "question": cleaned,
            "status": INSUFFICIENT_INFORMATION if answer_is_insufficient else ANSWERED,
            "answer": INSUFFICIENT_MESSAGE if answer_is_insufficient else answer_text,
            "llm_called": True,
            "sources": [] if answer_is_insufficient else deduplicate_sources(context_items),
            "retrieved_context": context_items,
            "retrieval_metadata": retrieval_metadata(retrieval),
            "timing": {
                "retrieval_seconds": retrieval_latency,
                "context_construction_seconds": context_latency,
                "llm_generation_seconds": llm_latency,
                "initial_llm_generation_seconds": initial_llm_latency,
                "retry_llm_generation_seconds": retry_llm_latency,
                "llm_reported_total_duration_seconds": llm_response.total_duration_seconds,
                "total_seconds": elapsed(start_total),
            },
            "error": None,
            "model": llm_response.model,
            "answer_warnings": [],
            "citation_metadata": citation_metadata(
                citation_validation,
                retry_attempted,
                retry_successful,
                generations_attempted,
                retry_failure_reason=retry_failure_reason,
            ),
        }

    def _error_result(
        self,
        question: str,
        message: str,
        start_total: float,
        retrieval: dict[str, Any] | None = None,
        context_items: list[dict[str, Any]] | None = None,
        llm_called: bool = False,
        citation_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "question": question,
            "status": ERROR,
            "answer": "The local RAG pipeline could not complete the request safely.",
            "llm_called": llm_called,
            "sources": [],
            "retrieved_context": context_items or [],
            "retrieval_metadata": retrieval_metadata(retrieval or {}),
            "timing": {
                "retrieval_seconds": None,
                "context_construction_seconds": None,
                "llm_generation_seconds": None,
                "total_seconds": elapsed(start_total),
            },
            "error": message,
            "citation_metadata": citation_metadata or {},
        }


def build_context(
    results: list[dict[str, Any]],
    *,
    max_context_characters: int = MAX_CONTEXT_CHARACTERS,
    max_passage_characters: int = MAX_PASSAGE_CHARACTERS,
) -> tuple[list[dict[str, Any]], str]:
    context_items: list[dict[str, Any]] = []
    rendered_blocks: list[str] = []
    used_characters = 0

    for index, result in enumerate(results, start=1):
        label = f"S{index}"
        passage = truncate_passage(result.get("text", ""), max_passage_characters)
        block = render_context_block(label, result, passage)
        projected = used_characters + len(block) + (2 if rendered_blocks else 0)
        if rendered_blocks and projected > max_context_characters:
            break
        if not rendered_blocks and len(block) > max_context_characters:
            passage = truncate_passage(passage, max_context_characters // 2)
            block = render_context_block(label, result, passage)

        rendered_blocks.append(block)
        used_characters += len(block) + (2 if rendered_blocks else 0)
        context_items.append(
            {
                "label": label,
                "chunk_id": result.get("chunk_id"),
                "source_id": result.get("source_id"),
                "title": result.get("title"),
                "source_name": result.get("source_name"),
                "source_type": result.get("metadata", {}).get("source_type", ""),
                "url": result.get("url"),
                "category": result.get("category"),
                "section_heading": result.get("section_heading"),
                "similarity_score": result.get("similarity_score"),
                "distance": result.get("distance"),
                "passage": passage,
            }
        )

    return context_items, "\n\n".join(rendered_blocks)


def render_context_block(label: str, result: dict[str, Any], passage: str) -> str:
    section = result.get("section_heading") or "Not specified"
    source_name = result.get("source_name") or "Not specified"
    return (
        f"[{label}]\n"
        f"Title: {result.get('title') or 'Not specified'}\n"
        f"Source: {source_name}\n"
        f"Section: {section}\n"
        f"Content:\n{passage}"
    )


def normalize_conversation_context(context: str | None) -> str:
    return " ".join((context or "").split())[:600]


def build_contextual_retrieval_query(question: str, conversation_context: str | None) -> str:
    if not conversation_context:
        return question
    return f"{conversation_context} Current follow-up question: {question}"


def build_grounded_prompt(question: str, context: str, conversation_context: str | None = None) -> str:
    conversation_block = ""
    if conversation_context:
        conversation_block = f"""
CONVERSATION CONTEXT FOR REFERENCE RESOLUTION ONLY:
{conversation_context}

Important: Conversation context is not factual evidence. Use it only to interpret pronouns or short follow-up questions. Cite and rely only on CONTEXT passages below.
"""
    return f"""You are an AI-Powered Computer Engineering Student Advisor.

Rules:
- Use only the supplied context.
- Conversation context, when supplied, is not evidence and must not be cited.
- Do not use outside knowledge.
- Do not invent facts, statistics, salaries, university policies, course names, career claims, source IDs, or URLs.
- Every factual statement must be directly stated by the cited context.
- Do not infer extra facts because they sound reasonable.
- If evidence supports only part of the question, answer only that supported part and mention that the remaining evidence is insufficient.
- Prefer a short supported answer over a longer speculative answer.
- If the context does not directly support an answer, write exactly: INSUFFICIENT_INFORMATION
- Cite only supplied labels such as [S1] or [S2].
- Cite the exact label whose passage directly states the fact.
- Every bullet must include at least one valid [S#] citation.
- Keep the answer to 1-3 short bullets.

Return two sections: ANSWER and USED_SOURCES.
In ANSWER, write 1-3 bullets and end every bullet with a valid citation.
In USED_SOURCES, list only the source labels used in ANSWER.
{conversation_block}
CONTEXT:
{context}

QUESTION:
{question}

ANSWER:"""


def build_citation_retry_prompt(question: str, context: str, previous_answer: str, reason: str | None) -> str:
    return f"""Rewrite the answer using only the supplied context.

Fix the citation problem: {reason or 'invalid or missing source labels'}.
Rewrite the answer; do not merely list sources.
Every factual bullet or claim in ANSWER must contain an appropriate inline [S#] citation.
USED_SOURCES alone is not sufficient; citations must appear inside the answer bullets.
Use only source labels supplied in the retrieved context, such as [S1] or [S2].
Do not invent citations, source labels, facts, statistics, course names, or career claims.
Keep the answer concise: 1-3 short bullets.
If the answer cannot be supported, write exactly: INSUFFICIENT_INFORMATION

Return two sections: ANSWER and USED_SOURCES.
In ANSWER, write 1-3 bullets and end every bullet with a valid citation.
In USED_SOURCES, list only the source labels used in ANSWER.

CONTEXT:
{context}

QUESTION:
{question}

PREVIOUS ANSWER:
{previous_answer}

ANSWER:"""


def truncate_passage(text: str, max_characters: int) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= max_characters:
        return cleaned
    cutoff = cleaned[:max_characters]
    sentence_end = max(cutoff.rfind("."), cutoff.rfind("?"), cutoff.rfind("!"))
    if sentence_end >= max_characters * 0.6:
        return cutoff[: sentence_end + 1]
    space = cutoff.rfind(" ")
    if space > 0:
        return cutoff[:space].rstrip() + "..."
    return cutoff.rstrip() + "..."


def select_context_results(question: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prefer more directly authoritative context without changing retrieval."""
    q = question.lower()
    if any(phrase in q for phrase in ["what is computer engineering", "define computer engineering"]):
        preferred = [
            result
            for result in results
            if (result.get("category") or "").lower() == "department_information"
            or "about" in (result.get("title") or "").lower()
        ]
        if preferred:
            return preferred[:2]

    if not any(term in q for term in ["course", "courses", "curriculum", "semester", "classes"]):
        unique_by_source: list[dict[str, Any]] = []
        duplicate_by_source: list[dict[str, Any]] = []
        seen_sources: set[str] = set()
        for result in results:
            source_id = str(result.get("source_id") or result.get("chunk_id") or "")
            if source_id in seen_sources:
                duplicate_by_source.append(result)
                continue
            seen_sources.add(source_id)
            unique_by_source.append(result)

        if len(unique_by_source) >= 3:
            return unique_by_source
        return results

    preferred_source_types = {"course_descriptions", "curriculum_document"}
    preferred = [
        result
        for result in results
        if result.get("category") == "curriculum"
        and str(result.get("metadata", {}).get("source_type") or "").lower() in preferred_source_types
    ]
    if len(preferred) >= 2:
        return preferred + [result for result in results if result not in preferred]
    return results


def deduplicate_sources(context_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: dict[tuple[str, str], dict[str, Any]] = {}
    for item in context_items:
        key = (item.get("source_id") or "", item.get("url") or "")
        if key not in sources:
            sources[key] = {
                "source_id": item.get("source_id"),
                "title": item.get("title"),
                "source_name": item.get("source_name"),
                "source_type": item.get("source_type"),
                "url": item.get("url"),
                "category": item.get("category"),
                "supporting_chunk_ids": [],
                "evidence_labels": [],
                "best_similarity_score": item.get("similarity_score"),
            }
        sources[key]["supporting_chunk_ids"].append(item.get("chunk_id"))
        sources[key]["evidence_labels"].append(item.get("label"))
        current = sources[key].get("best_similarity_score")
        score = item.get("similarity_score")
        if score is not None and (current is None or score > current):
            sources[key]["best_similarity_score"] = score
    return list(sources.values())


def retrieval_metadata(retrieval: dict[str, Any]) -> dict[str, Any]:
    return {
        "top_k": retrieval.get("top_k"),
        "candidate_top_k": retrieval.get("candidate_top_k"),
        "similarity_threshold": retrieval.get("similarity_threshold"),
        "results_above_threshold": retrieval.get("results_above_threshold"),
        "top_similarity_score": retrieval.get("top_similarity_score"),
        "evidence_sufficient": retrieval.get("evidence_sufficient"),
        "out_of_scope": retrieval.get("out_of_scope"),
    }


def normalize_answer(text: str) -> str:
    return (text or "").strip()


def is_insufficient_answer(answer: str) -> bool:
    normalized = normalize_answer(answer).lower()
    return (
        "insufficient_information" in normalized
        or "don't have enough reliable information" in normalized
        or "do not have enough reliable information" in normalized
        or "not have enough reliable information" in normalized
        or "do not have enough information" in normalized
        or "not enough reliable information" in normalized
        or "cannot answer" in normalized and "context" in normalized
    )


def validate_citations(answer: str, context_items: list[dict[str, Any]]) -> CitationValidation:
    if is_insufficient_answer(answer):
        return CitationValidation(True, INSUFFICIENT_MESSAGE, (), (), available_labels(context_items))

    answer_section, used_sources = split_structured_answer(answer)
    normalized_answer, normalized = normalize_citation_format(answer_section)
    labels = extract_citation_labels(normalized_answer)
    available = available_labels(context_items)
    invalid = tuple(label for label in labels if label not in available)
    uncited_bullets = tuple(line for line in answer_bullets(normalized_answer) if not extract_citation_labels(line))
    incomplete_bullets = tuple(line for line in answer_bullets(normalized_answer) if not bullet_ends_cleanly(line))

    if not labels:
        return CitationValidation(False, normalized_answer, (), invalid, available, normalized, "missing inline [S#] citation")
    if uncited_bullets:
        return CitationValidation(
            False,
            normalized_answer,
            tuple(labels),
            invalid,
            available,
            normalized,
            "missing inline [S#] citation on one or more answer bullets",
        )
    if incomplete_bullets:
        return CitationValidation(
            False,
            normalized_answer,
            tuple(labels),
            invalid,
            available,
            normalized,
            "answer appears incomplete or truncated",
        )
    if invalid:
        return CitationValidation(
            False,
            normalized_answer,
            tuple(labels),
            invalid,
            available,
            normalized,
            f"citation labels are not in retrieved context: {list(invalid)}",
        )
    invalid_used = tuple(label for label in used_sources if label not in available)
    if invalid_used:
        return CitationValidation(
            False,
            normalized_answer,
            tuple(labels),
            invalid_used,
            available,
            normalized,
            f"USED_SOURCES contains labels not in retrieved context: {list(invalid_used)}",
        )
    return CitationValidation(True, normalized_answer, tuple(labels), (), available, normalized)


def split_structured_answer(answer: str) -> tuple[str, tuple[str, ...]]:
    text = normalize_answer(answer)
    used_sources: tuple[str, ...] = ()
    answer_match = re.search(r"ANSWER:\s*(.*?)(?:\n\s*USED_SOURCES:|$)", text, flags=re.IGNORECASE | re.DOTALL)
    if answer_match:
        answer_text = answer_match.group(1).strip()
    else:
        answer_text = re.split(r"\n\s*USED_SOURCES:", text, flags=re.IGNORECASE)[0].strip()

    used_match = re.search(r"USED_SOURCES:\s*(.*)$", text, flags=re.IGNORECASE | re.DOTALL)
    if used_match:
        normalized_sources, _ = normalize_citation_format(used_match.group(1))
        used_sources = tuple(dict.fromkeys(extract_source_list_labels(normalized_sources)))
    answer_text = re.sub(r"(?im)^\s*-?\s*USED_SOURCES\s*:.*$", "", answer_text).strip()
    return answer_text, used_sources


def normalize_citation_format(answer: str) -> tuple[str, bool]:
    normalized = re.sub(r"\[S\s*(\d+)\s*\.?\]", r"[S\1]", answer)
    return normalized, normalized != answer


def extract_citation_labels(answer: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(f"S{match}" for match in re.findall(r"\[S(\d+)\]", answer)))


def answer_bullets(answer: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in answer.splitlines() if line.strip().startswith(("-", "*")))


def bullet_ends_cleanly(bullet: str) -> bool:
    return bullet.rstrip().endswith((".", "?", "!", "]"))


def extract_source_list_labels(source_text: str) -> tuple[str, ...]:
    bracket_labels = list(extract_citation_labels(source_text))
    bare_labels = [f"S{match}" for match in re.findall(r"\bS(\d+)\b", source_text, flags=re.IGNORECASE)]
    return tuple(dict.fromkeys(bracket_labels + bare_labels))


def available_labels(context_items: list[dict[str, Any]]) -> tuple[str, ...]:
    return tuple(item["label"] for item in context_items if item.get("label") and item.get("chunk_id") and item.get("source_id"))


def citation_metadata(
    validation: CitationValidation,
    retry_attempted: bool,
    retry_successful: bool,
    generations_attempted: int,
    *,
    retry_failure_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "valid": validation.valid,
        "cited_labels": list(validation.cited_labels),
        "invalid_labels": list(validation.invalid_labels),
        "available_labels": list(validation.available_labels),
        "normalized": validation.normalized,
        "reason": validation.reason,
        "retry_attempted": retry_attempted,
        "retry_successful": retry_successful,
        "generations_attempted": generations_attempted,
        "retry_failure_reason": retry_failure_reason,
    }


def unsupported_specific_fact_reason(question: str, results: list[dict[str, Any]]) -> str | None:
    q = question.lower()
    checks = [
        (("tuition", "fee", "fees", "cost"), ("tuition", "fee", "fees", "cost", "payment")),
        (("deadline", "application date", "registration date"), ("deadline", "date", "registration", "application")),
        (("quota", "capacity"), ("quota", "capacity")),
        (("scholarship",), ("scholarship",)),
        (("salary", "salaries", "pay", "wage"), ("salary", "salaries", "pay", "wage", "earnings")),
        (("cybersecurity",), ("cybersecurity",)),
        (("gpa", "grade point"), ("gpa", "grade point", "grade")),
        (("project", "projects", "portfolio"), ("project", "projects", "portfolio")),
    ]
    missing_groups: list[list[str]] = []
    evidence_text = " ".join((result.get("text") or "").lower() for result in results)
    for triggers, evidence_terms in checks:
        if any(term in q for term in triggers):
            required_terms = list(evidence_terms)
            if not contains_any_term(evidence_text, required_terms):
                missing_groups.append(required_terms)
    if missing_groups:
        return f"retrieved evidence does not contain requested specific fact terms: {missing_groups}"
    return None


def unsupported_category_reason(question: str, results: list[dict[str, Any]]) -> str | None:
    q = question.lower()
    if "cybersecurity" not in q:
        return None
    categories = {(result.get("category") or "").lower() for result in results}
    if "cybersecurity" not in categories:
        return "retrieved evidence did not include a cybersecurity-category source"
    return None


def unsupported_claim_reason(question: str, results: list[dict[str, Any]]) -> str | None:
    q = question.lower()
    asks_gpa_project_internship_comparison = (
        "gpa" in q
        and any(term in q for term in ["project", "projects", "portfolio"])
        and any(term in q for term in ["internship", "internships"])
    )
    if asks_gpa_project_internship_comparison:
        return "retrieved evidence does not directly compare GPA, projects, and internships for software career preparation"

    asks_ai_replacement = (
        "replace" in q
        and any(term in q for term in ["ai", "artificial intelligence", "automation", "generative ai"])
    )
    if not asks_ai_replacement:
        return None

    evidence_text = " ".join((result.get("text") or "").lower() for result in results)
    replacement_terms = [
        "replace",
        "replacing",
        "replacement",
        "displace",
        "displacement",
        "substitute",
    ]
    if not contains_any_term(evidence_text, replacement_terms):
        return "retrieved evidence does not directly address whether AI replaces computer engineers"
    return None


def contains_any_term(text: str, terms: list[str] | tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) for term in terms)


def invalid_model_answer(answer: str) -> bool:
    lowered = answer.lower()
    copied_prompt_phrases = [
        "answer text",
        "directly supported fact",
        "<1-4 bullets",
        "comma-separated source labels",
        "ceng 213 is listed as discrete computing structures",
    ]
    return any(phrase in lowered for phrase in copied_prompt_phrases)


def elapsed(start: float) -> float:
    return round(time.perf_counter() - start, 3)


def friendly_error(exc: Exception) -> str:
    return str(exc) or exc.__class__.__name__
