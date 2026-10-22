"""Core RAG pipeline for Stage 15.

This module connects the existing retriever to the existing local Ollama
service. It does not expose API endpoints, implement chat history, or build a
frontend chatbot.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
import re
from typing import Any

from ..core.retrieval_config import (
    CANDIDATE_TOP_K,
    DEFAULT_TOP_K,
    QUESTION_ANSWER_SIMILARITY_THRESHOLD,
    SENTENCE_PASSAGE_SIMILARITY_THRESHOLD,
)
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

INSUFFICIENT_MESSAGE = (
    "I understand your question, but I don't currently have enough reliable information in my knowledge base to answer it."
)

MAX_CONTEXT_CHARACTERS = 3000
MAX_PASSAGE_CHARACTERS = 700
RAG_NUM_PREDICT = 220
PROJECT_ROOT = Path(__file__).resolve().parents[3]


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
    repair_actions: tuple[str, ...] = ()


@dataclass
class GenerationLog:
    """Raw model output for one answer, and whether a fallback replaced it."""

    raw: list[str] = field(default_factory=list)
    replaced: bool = False


@dataclass(frozen=True)
class PreparedAnswer:
    cleaned: str
    gate_question: str
    retrieval: dict[str, Any]
    retrieval_latency: float
    context_items: list[dict[str, Any]]
    context_text: str
    context_latency: float
    prompt: str
    start_total: float


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
        # Semantic grounding checks reuse the retriever's embedding model.
        # Retrievers without one (test fakes) leave only the lexical checks.
        configure_semantic_encoder(getattr(self.retriever, "encode_texts", None))

    def answer(
        self,
        question: str,
        conversation_context: str | None = None,
        resolved_question: str | None = None,
    ) -> dict[str, Any]:
        early_result, prepared = self._prepare_answer(question, conversation_context, resolved_question)
        if early_result is not None:
            return early_result
        return with_partial_answer_warning(self._generate_validated_answer(prepared))

    def answer_stream(
        self,
        question: str,
        conversation_context: str | None = None,
        resolved_question: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Stream progress events using exactly the same validation as answer().

        Raw model tokens are never forwarded: the only token event carries the
        final answer after citation and grounding validation succeeded.
        """
        early_result, prepared = self._prepare_answer(question, conversation_context, resolved_question)
        if early_result is not None:
            yield {"event": "final", "result": early_result}
            return
        yield {
            "event": "metadata",
            "retrieval_metadata": retrieval_metadata(prepared.retrieval),
            "retrieved_context": prepared.context_items,
            "llm_called": True,
        }
        result = with_partial_answer_warning(self._generate_validated_answer(prepared))
        if result.get("status") == ANSWERED and result.get("answer"):
            yield {"event": "token", "text": result["answer"]}
        yield {"event": "final", "result": result}

    def _prepare_answer(
        self,
        question: str,
        conversation_context: str | None,
        resolved_question: str | None,
    ) -> tuple[dict[str, Any] | None, "PreparedAnswer | None"]:
        """Retrieve, apply answerability gates and build the grounded prompt."""
        start_total = time.perf_counter()
        cleaned = " ".join((question or "").split())
        if not cleaned:
            return self._error_result(question or "", "Question must not be empty.", start_total), None
        context_hint = normalize_conversation_context(conversation_context)
        retrieval_query = normalize_resolved_question(resolved_question) or cleaned

        try:
            retrieval_start = time.perf_counter()
            retrieval = self.retriever.retrieve(
                retrieval_query,
                top_k=self.config.top_k,
                candidate_top_k=self.config.candidate_top_k,
            )
            retrieval_latency = elapsed(retrieval_start)
        except Exception as exc:
            return self._error_result(cleaned, f"Retrieval failed: {friendly_error(exc)}", start_total), None

        evidence_results = retrieval.get("results", [])

        if not retrieval.get("evidence_sufficient"):
            status = OUT_OF_SCOPE if retrieval.get("out_of_scope") else INSUFFICIENT_INFORMATION
            return ({
                "question": cleaned,
                "status": status,
                "answer": INSUFFICIENT_MESSAGE,
                "llm_called": False,
                "sources": [],
                "retrieved_context": evidence_results,
                "retrieval_metadata": retrieval_metadata(retrieval),
                "timing": {
                    "retrieval_seconds": retrieval_latency,
                    "context_construction_seconds": 0.0,
                    "llm_generation_seconds": 0.0,
                    "total_seconds": elapsed(start_total),
                },
                "error": None,
            }, None)

        # Lexical gates judge the student's question, not the retrieval hints
        # ("(Computer Engineering; topics: ai, career)") appended for search.
        gate_question = strip_retrieval_annotations(retrieval_query)
        answerability_reason = unsupported_answerability_reason(gate_question, evidence_results)
        if answerability_reason:
            return ({
                "question": cleaned,
                "status": INSUFFICIENT_INFORMATION,
                "answer": INSUFFICIENT_MESSAGE,
                "llm_called": False,
                "sources": [],
                "retrieved_context": evidence_results,
                "retrieval_metadata": {**retrieval_metadata(retrieval), "unsupported_reason": answerability_reason},
                "timing": {
                    "retrieval_seconds": retrieval_latency,
                    "context_construction_seconds": 0.0,
                    "llm_generation_seconds": 0.0,
                    "total_seconds": elapsed(start_total),
                },
                "error": None,
            }, None)

        unsupported_reason = unsupported_specific_fact_reason(gate_question, evidence_results)
        if unsupported_reason:
            return ({
                "question": cleaned,
                "status": INSUFFICIENT_INFORMATION,
                "answer": INSUFFICIENT_MESSAGE,
                "llm_called": False,
                "sources": [],
                "retrieved_context": evidence_results,
                "retrieval_metadata": {**retrieval_metadata(retrieval), "unsupported_reason": unsupported_reason},
                "timing": {
                    "retrieval_seconds": retrieval_latency,
                    "context_construction_seconds": 0.0,
                    "llm_generation_seconds": 0.0,
                    "total_seconds": elapsed(start_total),
                },
                "error": None,
            }, None)

        category_reason = unsupported_category_reason(gate_question, evidence_results)
        if category_reason:
            return ({
                "question": cleaned,
                "status": INSUFFICIENT_INFORMATION,
                "answer": INSUFFICIENT_MESSAGE,
                "llm_called": False,
                "sources": [],
                "retrieved_context": evidence_results,
                "retrieval_metadata": {**retrieval_metadata(retrieval), "unsupported_reason": category_reason},
                "timing": {
                    "retrieval_seconds": retrieval_latency,
                    "context_construction_seconds": 0.0,
                    "llm_generation_seconds": 0.0,
                    "total_seconds": elapsed(start_total),
                },
                "error": None,
            }, None)

        claim_reason = unsupported_claim_reason(gate_question, evidence_results)
        if claim_reason:
            return ({
                "question": cleaned,
                "status": INSUFFICIENT_INFORMATION,
                "answer": INSUFFICIENT_MESSAGE,
                "llm_called": False,
                "sources": [],
                "retrieved_context": evidence_results,
                "retrieval_metadata": {**retrieval_metadata(retrieval), "unsupported_reason": claim_reason},
                "timing": {
                    "retrieval_seconds": retrieval_latency,
                    "context_construction_seconds": 0.0,
                    "llm_generation_seconds": 0.0,
                    "total_seconds": elapsed(start_total),
                },
                "error": None,
            }, None)

        try:
            context_start = time.perf_counter()
            context_results = select_context_results(retrieval_query, evidence_results)
            context_items, context_text = build_context(
                context_results,
                question=retrieval_query,
                max_context_characters=self.config.max_context_characters,
                max_passage_characters=self.config.max_passage_characters,
            )
            prompt_question = prompt_question_for_generation(cleaned, retrieval_query)
            prompt = build_grounded_prompt(prompt_question, context_text)
            if context_hint:
                prompt = build_grounded_prompt(prompt_question, context_text, conversation_context=context_hint)
            context_latency = elapsed(context_start)
        except Exception as exc:
            return self._error_result(cleaned, f"Context construction failed: {friendly_error(exc)}", start_total, retrieval), None
        return None, PreparedAnswer(
            cleaned=cleaned,
            gate_question=gate_question,
            retrieval=retrieval,
            retrieval_latency=retrieval_latency,
            context_items=context_items,
            context_text=context_text,
            context_latency=context_latency,
            prompt=prompt,
            start_total=start_total,
        )

    def _generate_validated_answer(self, prepared: "PreparedAnswer") -> dict[str, Any]:
        """Generate with the local LLM and keep only citation-validated, grounded output.

        When the model's text is not what the student receives, the raw
        generation is kept in retrieval_metadata so evaluations can be replayed
        offline without calling the model again.
        """
        log = GenerationLog()
        result = self._generate_and_validate(prepared, log)
        if log.raw and (result.get("status") != ANSWERED or log.replaced):
            metadata = dict(result.get("retrieval_metadata") or {})
            metadata["discarded_generation"] = log.raw[0]
            if len(log.raw) > 1:
                metadata["discarded_retry_generation"] = log.raw[1]
            result = {**result, "retrieval_metadata": metadata}
        return result

    def _generate_and_validate(self, prepared: "PreparedAnswer", log: "GenerationLog") -> dict[str, Any]:
        cleaned = prepared.cleaned
        gate_question = prepared.gate_question
        retrieval = prepared.retrieval
        retrieval_latency = prepared.retrieval_latency
        context_items = prepared.context_items
        context_text = prepared.context_text
        context_latency = prepared.context_latency
        prompt = prepared.prompt
        start_total = prepared.start_total

        try:
            llm_start = time.perf_counter()
            llm_response = self.llm_service.generate(prompt, num_predict=RAG_NUM_PREDICT)
            log.raw.append(llm_response.text or "")
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
        early_fallback_validation = None
        if not citation_validation.valid:
            early_fallback = extractive_partial_answer(gate_question, context_items)
            if early_fallback:
                candidate = validate_citations(early_fallback, context_items)
                if candidate.valid and not unsupported_generated_answer_reason(gate_question, candidate.answer, context_items):
                    early_fallback_validation = candidate
        retry_attempted = False
        retry_successful = False
        retry_error = None
        retry_failure_reason = None

        if not citation_validation.valid and early_fallback_validation is None and self.config.max_citation_retries > 0:
            retry_attempted = True
            try:
                retry_prompt = build_citation_retry_prompt(cleaned, context_text, answer_text, citation_validation.reason)
                retry_start = time.perf_counter()
                retry_response = self.llm_service.generate(retry_prompt, num_predict=RAG_NUM_PREDICT)
                log.raw.append(retry_response.text or "")
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
            fallback_answer = None if early_fallback_validation else extractive_partial_answer(gate_question, context_items)
            if early_fallback_validation or fallback_answer:
                fallback_validation = early_fallback_validation or validate_citations(fallback_answer, context_items)
                if fallback_validation.valid and not unsupported_generated_answer_reason(gate_question, fallback_validation.answer, context_items):
                    answer_text = fallback_validation.answer
                    answer_is_insufficient = is_insufficient_answer(answer_text)
                    log.replaced = True
                    return {
                        "question": cleaned,
                        "status": INSUFFICIENT_INFORMATION if answer_is_insufficient else ANSWERED,
                        "answer": INSUFFICIENT_MESSAGE if answer_is_insufficient else answer_text,
                        "llm_called": True,
                        "sources": [] if answer_is_insufficient else cited_sources(context_items, fallback_validation),
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
                        "answer_warnings": ["local_llm_answer_replaced_with_extractive_fallback"],
                        "citation_metadata": citation_metadata(
                            fallback_validation,
                            retry_attempted,
                            retry_successful,
                            generations_attempted,
                            retry_failure_reason=retry_failure_reason,
                        ),
                    }
            safe_citation_metadata = citation_metadata(
                citation_validation,
                retry_attempted,
                retry_successful,
                generations_attempted,
                retry_failure_reason=retry_failure_reason,
            )
            safe_citation_metadata.update(
                {
                    "valid": True,
                    "cited_labels": [],
                    "invalid_labels": [],
                    "discarded_invalid_generation": True,
                    "discarded_generation_reason": citation_validation.reason,
                }
            )
            return {
                "question": cleaned,
                "status": INSUFFICIENT_INFORMATION,
                "answer": INSUFFICIENT_MESSAGE,
                "llm_called": True,
                "sources": [],
                "retrieved_context": context_items,
                "retrieval_metadata": {**retrieval_metadata(retrieval), "unsupported_reason": error_message},
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
                "answer_warnings": ["local_llm_answer_failed_citation_validation"],
                "citation_metadata": safe_citation_metadata,
            }

        answer_text = citation_validation.answer

        generated_answer_reason = unsupported_generated_answer_reason(gate_question, answer_text, context_items)
        if generated_answer_reason:
            fallback_answer = extractive_partial_answer(gate_question, context_items)
            if fallback_answer:
                fallback_validation = validate_citations(fallback_answer, context_items)
                if fallback_validation.valid and not unsupported_generated_answer_reason(gate_question, fallback_validation.answer, context_items):
                    citation_validation = fallback_validation
                    answer_text = citation_validation.answer
                    generated_answer_reason = None
                    log.replaced = True
            if not generated_answer_reason:
                pass
            else:
                return {
                    "question": cleaned,
                    "status": INSUFFICIENT_INFORMATION,
                    "answer": INSUFFICIENT_MESSAGE,
                    "llm_called": True,
                    "sources": [],
                    "retrieved_context": context_items,
                    "retrieval_metadata": {**retrieval_metadata(retrieval), "unsupported_reason": generated_answer_reason},
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

        answer_is_insufficient = is_insufficient_answer(answer_text)
        if answer_is_insufficient:
            fallback_answer = extractive_partial_answer(gate_question, context_items)
            if fallback_answer:
                fallback_validation = validate_citations(fallback_answer, context_items)
                if fallback_validation.valid and not unsupported_generated_answer_reason(gate_question, fallback_validation.answer, context_items):
                    citation_validation = fallback_validation
                    answer_text = citation_validation.answer
                    answer_is_insufficient = False
                    log.replaced = True

        return {
            "question": cleaned,
            "status": INSUFFICIENT_INFORMATION if answer_is_insufficient else ANSWERED,
            "answer": INSUFFICIENT_MESSAGE if answer_is_insufficient else answer_text,
            "llm_called": True,
            "sources": [] if answer_is_insufficient else cited_sources(context_items, citation_validation),
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
    question: str = "",
    max_context_characters: int = MAX_CONTEXT_CHARACTERS,
    max_passage_characters: int = MAX_PASSAGE_CHARACTERS,
) -> tuple[list[dict[str, Any]], str]:
    context_items: list[dict[str, Any]] = []
    rendered_blocks: list[str] = []
    used_characters = 0

    for index, result in enumerate(results, start=1):
        result = annotate_context_source(result)
        label = f"S{index}"
        passage = focus_passage(result.get("text", ""), question, max_passage_characters)
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


@lru_cache(maxsize=128)
def is_curated_source(source_id: str) -> bool:
    if not re.fullmatch(r"src_\d+", source_id or ""):
        return False
    path = PROJECT_ROOT / "knowledge_base" / "processed" / "documents" / f"{source_id}.txt"
    try:
        with path.open("r", encoding="utf-8") as source:
            return "Curated source note" in source.read(500)
    except OSError:
        return False


def annotate_context_source(result: dict[str, Any]) -> dict[str, Any]:
    if not is_curated_source(str(result.get("source_id") or "")):
        return result
    source = result.get("source_name") or "the linked source"
    metadata = {**(result.get("metadata") or {}), "source_type": "curated_source_note"}
    return {
        **result,
        "title": f"Curated note: {result.get('title') or 'Untitled'}",
        "source_name": f"CENG AI Advisor summary based on {source}",
        "metadata": metadata,
    }


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
    return " ".join((context or "").split())[:900]


def normalize_resolved_question(question: str | None) -> str:
    return " ".join((question or "").split())[:500]


def prompt_question_for_generation(cleaned_question: str, retrieval_query: str) -> str:
    """Keep user wording when the resolver only changed case or punctuation-sensitive terms."""
    if retrieval_query != cleaned_question and retrieval_query.lower() != cleaned_question.lower():
        return retrieval_query
    return cleaned_question


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
    answerability_block = answerability_prompt_guidance(question)
    return f"""You are an AI-Powered Computer Engineering Student Advisor.

Rules:
- Use only the supplied context.
- Conversation context, when supplied, is not evidence and must not be cited.
- Do not use outside knowledge.
- Do not invent facts, statistics, salaries, university policies, course names, career claims, source IDs, or URLs.
- Every factual statement must be directly stated by the cited context.
- Do not infer extra facts because they sound reasonable.
- Answer the exact question in the first sentence. Do not replace it with a related topic.
- Make one checkable factual claim per sentence and put its supporting [S#] label in that same sentence.
- Do not collect citations at the end of a paragraph or after a separate sentence.
- Do not recommend a degree, learning order, or career outcome unless the context supports that recommendation.
- A sample course's hours, a list of topics, or an occupation description is not proof of a program-wide total, a prerequisite, or an entry-level job title.
- If evidence supports only part of the question, answer only that supported part and mention that the remaining evidence is insufficient.
- For comparison questions, compare the exact items named in the question; do not substitute a different field or topic.
- Prefer a short supported answer over a longer speculative answer.
- If the context does not directly support an answer, write exactly: INSUFFICIENT_INFORMATION
- Cite only supplied labels such as [S1] or [S2].
- Cite the exact label whose passage directly states the fact.
- Write in normal, student-friendly English.
- Start with one or two short explanatory paragraphs before the source cards shown by the app.
- Do not use bullets unless the question asks for a list.
- Every paragraph or bullet must include at least one valid [S#] citation.
- Keep the answer concise, usually 2-5 sentences total.
{answerability_block}

Return two sections: ANSWER and USED_SOURCES.
In ANSWER, write one or two clear paragraphs. Include valid citations inside the paragraphs.
In USED_SOURCES, list only the source labels used in ANSWER.
{conversation_block}
CONTEXT:
{context}

QUESTION:
{question}

ANSWER:"""


def build_citation_retry_prompt(question: str, context: str, previous_answer: str, reason: str | None) -> str:
    answerability_block = answerability_prompt_guidance(question)
    return f"""Rewrite the answer using only the supplied context.

Fix the citation problem: {reason or 'invalid or missing source labels'}.
Rewrite the answer; do not merely list sources.
Answer the exact question first, using one directly supported claim per sentence.
Every factual sentence in ANSWER must contain its own appropriate inline [S#] citation.
Remove claims that the cited passage does not directly support; do not attach a citation just because the topic is similar.
USED_SOURCES alone is not sufficient; citations must appear inside the answer text.
Use only source labels supplied in the retrieved context, such as [S1] or [S2].
Do not invent citations, source labels, facts, statistics, course names, or career claims.
Write in normal, student-friendly English.
Start with one or two short explanatory paragraphs before the source cards shown by the app.
Do not use bullets unless the question asks for a list.
Keep the answer concise, usually 2-5 sentences total.
If the answer cannot be supported, write exactly: INSUFFICIENT_INFORMATION
{answerability_block}

Return two sections: ANSWER and USED_SOURCES.
In ANSWER, write one or two clear paragraphs. Include valid citations inside the paragraphs.
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


def focus_passage(text: str, question: str, max_characters: int) -> str:
    """Keep a complete question-relevant sentence when the retrieved chunk is long."""
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= max_characters or not question:
        return truncate_passage(cleaned, max_characters)
    terms = significant_terms(question) - {"computer", "engineering", "student", "students", "ceng"}
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    scored = [
        (len(terms.intersection(significant_terms(sentence))), index)
        for index, sentence in enumerate(sentences)
        if len(sentence) <= max_characters and sentence.rstrip().endswith((".", "!", "?"))
    ]
    if not scored or max(score for score, _ in scored) == 0:
        return truncate_passage(cleaned, max_characters)
    _, best_index = max(scored, key=lambda pair: (pair[0], -pair[1]))
    selected = [sentences[best_index]]
    for neighbor in (best_index - 1, best_index + 1):
        if 0 <= neighbor < len(sentences) and len(" ".join(selected + [sentences[neighbor]])) <= max_characters:
            if neighbor < best_index:
                selected.insert(0, sentences[neighbor])
            else:
                selected.append(sentences[neighbor])
    return " ".join(selected)


def select_context_results(question: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prefer more directly authoritative context without changing retrieval."""
    q = question.lower()
    if is_linux_operating_system_question(q):
        preferred = [
            result
            for result in results
            if linux_operating_system_evidence_text(result.get("text") or "")
            or linux_operating_system_evidence_text(result.get("title") or "")
        ]
        if preferred:
            return preferred

    if is_specialization_question(q):
        preferred = [
            result
            for result in results
            if (result.get("category") or "").lower() == "specializations"
            or (result.get("source_id") or "") in {"src_043", "src_131"}
            or "subdiscipline" in (result.get("title") or "").lower()
        ]
        if preferred:
            return preferred + [result for result in results if result not in preferred]

    if is_computer_engineering_it_comparison_question(q):
        preferred = [
            result
            for result in results
            if (result.get("source_id") or "") in {"src_042", "src_128"}
        ]
        if preferred:
            return preferred + [result for result in results if result not in preferred]

    if is_future_technology_question(q):
        preferred = [
            result
            for result in results
            if (result.get("source_id") or "") in {"src_063", "src_129", "src_043", "src_131"}
            or "new trends" in (result.get("title") or "").lower()
            or "subdiscipline" in (result.get("title") or "").lower()
        ]
        if preferred:
            return preferred + [result for result in results if result not in preferred]

    definition_question = any(
        phrase in q
        for phrase in [
            "what is computer engineering",
            "define computer engineering",
            "definition of computer engineering",
            "meaning of computer engineering",
        ]
    )
    if definition_question:
        broad_definition = [
            result
            for result in results
            if (result.get("source_id") or "") in {"src_042", "src_128"}
            or "curricular guidance" in (result.get("title") or "").lower()
            or (result.get("category") or "").lower() == "common_misconceptions"
        ]
        preferred = [
            result
            for result in results
            if (result.get("category") or "").lower() == "department_information"
            or "about" in (result.get("title") or "").lower()
        ]
        if broad_definition or preferred:
            return (broad_definition + [result for result in preferred if result not in broad_definition])[:3]

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
            return unique_by_source + duplicate_by_source
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


def is_specialization_question(question: str) -> bool:
    q = (question or "").lower()
    return any(
        term in q
        for term in [
            "field",
            "fields",
            "area",
            "areas",
            "branch",
            "branches",
            "track",
            "tracks",
            "specialization",
            "specializations",
            "subdiscipline",
            "subdisciplines",
            "sub-discipline",
            "sub-disciplines",
        ]
    )


def is_computer_engineering_it_comparison_question(question: str) -> bool:
    q = (question or "").lower()
    asks_it = bool(re.search(r"\bit\b", q)) or "information technology" in q
    asks_ce = "computer engineering" in q or "ceng" in q
    asks_comparison = any(
        phrase in q
        for phrase in (
            "difference between",
            "different from",
            "compare",
            "versus",
            " vs ",
            "choosing between",
        )
    )
    return asks_it and asks_ce and asks_comparison


def is_future_technology_question(question: str) -> bool:
    q = (question or "").lower()
    asks_future = contains_any_term(
        q,
        (
            "future",
            "emerging",
            "new trend",
            "new trends",
            "latest trend",
            "latest trends",
            "modern",
            "new",
        ),
    )
    asks_technology = contains_any_term(q, ("technology", "technologies", "tech", "field", "fields", "topic", "topics", "follow", "covered"))
    asks_ceng = contains_any_term(q, ("ceng", "computer engineering", "computer engineer", "student"))
    return asks_future and asks_technology and asks_ceng


def is_programming_language_question(question: str) -> bool:
    q = (question or "").lower()
    asks_language = contains_any_term(
        q,
        (
            "programming language",
            "programming languages",
            "language taught",
            "languages taught",
            "which languages",
            "python",
            "c++",
            "java",
        ),
    )
    asks_program = contains_any_term(q, ("ceng", "computer engineering", "programming", "coding", "course", "courses"))
    return asks_language and asks_program


def is_linux_operating_system_question(question: str) -> bool:
    q = (question or "").lower()
    return contains_any_term(q, ("linux", "unix", "operating system", "operating systems"))


def linux_operating_system_evidence_text(text: str) -> bool:
    lowered = (text or "").lower()
    return contains_any_term(
        lowered,
        (
            "linux or windows",
            "linux command",
            "linux-based",
            "unix",
            "operating system",
            "operating systems",
        ),
    )


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


def cited_sources(context_items: list[dict[str, Any]], validation: CitationValidation) -> list[dict[str, Any]]:
    cited = set(validation.cited_labels)
    return deduplicate_sources([item for item in context_items if item.get("label") in cited])


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
        or "don't currently have enough reliable information" in normalized
        or "do not have enough reliable information" in normalized
        or "do not currently have enough reliable information" in normalized
        or "not have enough reliable information" in normalized
        or "do not have enough information" in normalized
        or "not enough reliable information" in normalized
        or "cannot answer" in normalized and "context" in normalized
    )


PRUNABLE_CITATION_FAILURES = (
    "missing inline [S#] citation on one or more answer paragraphs or bullets",
    "answer appears incomplete or truncated",
    "unsupported claim could not be matched to retrieved evidence",
    "cited passage does not support one or more answer claims",
    "citation labels are not in retrieved context",
)


def validate_citations(answer: str, context_items: list[dict[str, Any]]) -> CitationValidation:
    """Validate citations, keeping the verified part of a partly unsupported answer.

    A single uncited, unsupported, or token-limit-truncated sentence used to
    discard an otherwise grounded answer. Such sentences are removed instead,
    and the remaining answer must pass the full strict validation again.
    """
    validation = validate_citations_strict(clean_answer_artifacts(answer), context_items)
    if validation.valid and not starts_with_dangling_reference(validation.answer):
        deduplicated = remove_repeated_sentences(validation.answer)
        if deduplicated != validation.answer and deduplicated.strip():
            return CitationValidation(
                True, deduplicated, extract_citation_labels(deduplicated), (), validation.available_labels,
                True, None, tuple(dict.fromkeys(validation.repair_actions + ("removed_repeated_sentence",))),
            )
        return validation
    if not validation.valid and not (validation.reason or "").startswith(PRUNABLE_CITATION_FAILURES):
        return validation
    pruned = prune_unverified_sentences(validation.answer, context_items)
    if not pruned:
        return validation
    pruned_validation = validate_citations_strict(pruned, context_items)
    if not pruned_validation.valid:
        if validation.valid:
            # Only the opening was dangling and nothing better remains.
            return CitationValidation(
                False, validation.answer, validation.cited_labels, (), validation.available_labels,
                validation.normalized, "answer opens with a reference to missing earlier text", validation.repair_actions,
            )
        return validation
    actions = validation.repair_actions + pruned_validation.repair_actions + ("pruned_unverified_sentences",)
    if len(answer_claim_sentences(pruned_validation.answer)) * 2 <= len(answer_claim_sentences(validation.answer)):
        # Most of the generation was unverifiable. The answer text keeps only
        # cited claims; the partial-coverage notice travels as a warning that
        # the app shows beside the answer (see PARTIAL_ANSWER_WARNING).
        actions += (PARTIAL_ANSWER_WARNING,)
    return CitationValidation(
        True,
        pruned_validation.answer,
        pruned_validation.cited_labels,
        (),
        pruned_validation.available_labels,
        True,
        None,
        tuple(dict.fromkeys(actions)),
    )


# A sentence opening like this depends on an earlier sentence. If it ends up
# first (because the model began mid-thought or its predecessor was pruned)
# the student sees "They are critical in ..." with no subject.
DANGLING_OPENER = re.compile(
    r"^\s*(?:[-*•]\s*)?(?:they|it|this|these|those|that|additionally|furthermore|moreover|also|however|"
    r"therefore|thus|hence|consequently|for instance|for example|in addition|as a result|similarly)\b",
    re.IGNORECASE,
)
META_OPENER = re.compile(
    r"(^|(?<=[.!?]\s))(?:given|based on|according to) (?:the )?(?:provided |supplied |retrieved )?context(?: provided)?,\s*(\w)",
    re.IGNORECASE,
)
SPECULATIVE_CLAIM = re.compile(
    r"\b(?:likely|probably|presumably|inferred|infer|assume|assumed|given that|it is reasonable to)\b",
    re.IGNORECASE,
)


NEGATION = re.compile(r"\b(?:not|no|never|none|neither|nor|cannot|without)\b|n't\b", re.IGNORECASE)
ABSENCE_CLAIM = re.compile(
    r"\b(?:source|sources|excerpt|evidence|passage|context|syllabus|it|this)\s+(?:does|do|did)\s+not\s+"
    r"(?:say|state|establish|mention|specify|quantify|rank|name|prove|justify|give|list|provide)",
    re.IGNORECASE,
)


def polarity_conflicts_with_passage(claim: str, passage: str) -> bool:
    """Catch a cited claim that flips the meaning of the sentence it paraphrases.

    "Physics is not required for all engineering majors" cited to "Physics is
    required for all engineering majors" overlaps lexically but is false.
    """
    if ABSENCE_CLAIM.search(claim):
        return False
    claim_terms = significant_terms(claim)
    if len(claim_terms) < 3:
        return False
    best_sentence, best_overlap = "", 0.0
    for sentence in re.split(r"(?<=[.!?])\s+", passage):
        overlap = len(claim_terms & significant_terms(sentence)) / len(claim_terms)
        if overlap > best_overlap:
            best_sentence, best_overlap = sentence, overlap
    if best_overlap < 0.6:
        return False
    return bool(NEGATION.search(claim)) != bool(NEGATION.search(best_sentence))


def remove_repeated_sentences(answer: str) -> str:
    """Drop a sentence that restates an earlier sentence of the same answer."""
    seen: list[set[str]] = []
    lines: list[str] = []
    for line in answer.splitlines():
        kept: list[str] = []
        for sentence in re.split(r"(?<=[.!?\]])\s+(?=[A-Z\-*•\d(]|\[(?!S\d+\]))", line.strip()):
            terms = significant_terms(strip_citation_text(sentence))
            if terms and any(len(terms & earlier) / len(terms | earlier) >= 0.7 for earlier in seen):
                continue
            seen.append(terms)
            kept.append(sentence)
        if kept:
            lines.append(" ".join(kept))
    return "\n".join(lines)


INFERENCE_GLUE = re.compile(
    r"((?:^|(?<=[.!?]\s))(?:[-*•]\s*)?)(?:this|which|that)\s+(?:means|implies|indicates|suggests|shows)\s+that\s+(\w)",
    re.IGNORECASE | re.MULTILINE,
)


def closing_bracket_index(text: str) -> int:
    """Index of the bracket that closes text[0], or -1."""
    depth = 0
    for index, character in enumerate(text):
        if character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
            if depth == 0:
                return index
    return -1


LABEL_SUBJECT = re.compile(
    r"^(?P<lead>(?:[-*•]\s*)?)(?:\[[^\]]{3,80}\]\s*)?(?:the\s+)?(?P<labels>(?:\[S\d+\]\s*)+)"
    r"(?:source|context|passage|document|report|note)?\s*"
    r"(?:also\s+)?(?:indicates|states|suggests|mentions|highlights|notes|shows|explains|emphasizes|says|"
    r"describes|recommends|explains)\s+that\s+(?P<claim>.+?)(?P<end>[.!?])?$",
    re.IGNORECASE,
)


def rewrite_label_subject_sentences(line: str) -> str:
    """Turn "[S3] suggests that X." into "X [S3]." so the claim carries its citation.

    Small models often use the label as the grammatical subject. The claim is
    unchanged; only the citation moves to where the validators expect it.
    """
    sentences = re.split(r"(?<=[.!?])\s+", line.strip())
    rewritten = []
    for sentence in sentences:
        match = LABEL_SUBJECT.match(sentence)
        if match and len(match.group("claim").split()) >= 4:
            claim = match.group("claim").strip()
            labels = " ".join(re.findall(r"\[S\d+\]", match.group("labels")))
            rewritten.append(f"{match.group('lead')}{claim[0].upper()}{claim[1:]} {labels}{match.group('end') or '.'}")
        else:
            rewritten.append(sentence)
    return " ".join(rewritten)


def clean_answer_artifacts(answer: str) -> str:
    """Remove model boilerplate that is not part of the advice itself."""
    text = (answer or "").strip()
    # Section headers written as "[ANSWER]" or "**USED_SOURCES**" -> "ANSWER:".
    text = re.sub(
        r"(?im)^\s*(?:\[|\*\*)?\s*(ANSWER|USED_SOURCES)\s*(?:\]|\*\*)?\s*:?\s*$",
        lambda match: f"{match.group(1).upper()}:",
        text,
    )
    # An answer wrapped in one pair of square brackets: "[Computer engineers ... [S2] ...]".
    if text.startswith("[") and closing_bracket_index(text) == len(text) - 1 and not re.match(r"\[S\d+\]", text):
        text = text[1:-1].strip()
    # "as evidenced by the [S2] source" -> "as evidenced by the source [S2]"
    text = re.sub(r"\bthe (\[S\d+\]) (source|passage|document)\b", r"the \2 \1", text)
    text = META_OPENER.sub(lambda match: match.group(1) + match.group(2).upper(), text)
    # "This means that X [S3]." asserts a logical link the sources never make
    # between X and the previous sentence; keep only the cited claim X.
    text = INFERENCE_GLUE.sub(lambda match: match.group(1) + match.group(2).upper(), text)
    text = "\n".join(rewrite_label_subject_sentences(line) for line in text.splitlines())
    # "components.] [S1]" -> "components [S1]."
    text = re.sub(r"([.!?])\]\s*((?:\[S\d+\]\s*)+)", lambda match: f" {match.group(2).strip()}{match.group(1)}", text)
    return text


RELATION_CLAIM = (
    r"\b(?:subsets?|supersets?|sub-?fields?|sub-?disciplines?|branch(?:es)? of|types? of|kinds? of|forms? of|"
    r"part of|belongs? to)\b"
)
# "While the report also indicates ..." continues an earlier sentence.
EARLY_ALSO = re.compile(r"^\W*(?:\w+\W+){0,5}also\b", re.IGNORECASE)


def is_dangling_opening(sentence: str) -> bool:
    return bool(DANGLING_OPENER.match(sentence) or EARLY_ALSO.match(sentence))


def starts_with_dangling_reference(answer: str) -> bool:
    first = next((line for line in (answer or "").splitlines() if line.strip()), "")
    return is_dangling_opening(first)


PARTIAL_ANSWER_WARNING = "partial_answer"


def with_partial_answer_warning(result: dict[str, Any]) -> dict[str, Any]:
    """Expose the pruning step's partial-coverage flag as an answer warning."""
    actions = (result.get("citation_metadata") or {}).get("repair_actions") or []
    if result.get("status") != ANSWERED or PARTIAL_ANSWER_WARNING not in actions:
        return result
    warnings = list(dict.fromkeys([*(result.get("answer_warnings") or []), PARTIAL_ANSWER_WARNING]))
    return {**result, "answer_warnings": warnings}


def prune_unverified_sentences(answer: str, context_items: list[dict[str, Any]]) -> str | None:
    """Drop sentences whose citations cannot be verified; None if too little remains."""
    context_by_label = {item.get("label"): item for item in context_items if item.get("label")}
    available = set(available_labels(context_items))
    kept_lines: list[str] = []
    total = kept = 0
    first_kept = False
    for line in answer.splitlines():
        if not line.strip():
            continue
        kept_sentences: list[str] = []
        for sentence in re.split(r"(?<=[.!?\]])\s+(?=[A-Z\-*•\d(]|\[(?!S\d+\]))", line.strip()):
            if not sentence.strip():
                continue
            total += 1
            labels = extract_citation_labels(sentence)
            verified = (
                answer_line_ends_cleanly(sentence)
                and bool(labels)
                and all(label in available for label in labels)
                and any(cited_claim_supported(sentence, context_by_label[label]) for label in labels)
            )
            if verified and kept == 0 and is_dangling_opening(sentence):
                verified = False
            if verified:
                kept += 1
                first_kept = first_kept or total == 1
                kept_sentences.append(sentence.strip())
        if kept_sentences:
            kept_lines.append(" ".join(kept_sentences))
    if kept == 0 or kept == total:
        return None
    # Relevance of what remains is checked afterwards by
    # unsupported_generated_answer_reason, so one verified, on-topic claim is a
    # better reply than a refusal.
    return "\n".join(kept_lines)


def validate_citations_strict(answer: str, context_items: list[dict[str, Any]]) -> CitationValidation:
    if is_insufficient_answer(answer):
        return CitationValidation(True, INSUFFICIENT_MESSAGE, (), (), available_labels(context_items))

    answer_section, used_sources = split_structured_answer(answer)
    normalized_answer, normalized = normalize_citation_format(answer_section)
    repaired_answer, repair_actions, unsupported_lines = repair_missing_inline_citations(
        normalized_answer,
        context_items,
        used_sources,
    )
    normalized_answer = repaired_answer
    normalized = normalized or bool(repair_actions)
    labels = extract_citation_labels(normalized_answer)
    available = available_labels(context_items)
    invalid = tuple(label for label in labels if label not in available)
    claim_lines = answer_claim_sentences(normalized_answer)
    uncited_claim_lines = tuple(line for line in claim_lines if not extract_citation_labels(line))
    incomplete_claim_lines = tuple(line for line in claim_lines if not answer_line_ends_cleanly(line))

    if not labels:
        reason = "missing inline [S#] citation"
        if unsupported_lines:
            reason = "unsupported claim could not be matched to retrieved evidence"
        return CitationValidation(False, normalized_answer, (), invalid, available, normalized, reason, repair_actions)
    if uncited_claim_lines:
        reason = "missing inline [S#] citation on one or more answer paragraphs or bullets"
        if unsupported_lines:
            reason = "unsupported claim could not be matched to retrieved evidence"
        return CitationValidation(
            False,
            normalized_answer,
            tuple(labels),
            invalid,
            available,
            normalized,
            reason,
            repair_actions,
        )
    if incomplete_claim_lines:
        return CitationValidation(
            False,
            normalized_answer,
            tuple(labels),
            invalid,
            available,
            normalized,
            "answer appears incomplete or truncated",
            repair_actions,
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
            repair_actions,
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
            repair_actions,
        )
    if unsupported_lines:
        return CitationValidation(
            False,
            normalized_answer,
            tuple(labels),
            (),
            available,
            normalized,
            "unsupported claim could not be matched to retrieved evidence",
            repair_actions,
        )
    context_by_label = {item.get("label"): item for item in context_items}
    unsupported_citations = tuple(
        sentence for sentence in claim_lines
        if not any(
            cited_claim_supported(sentence, context_by_label[label])
            for label in extract_citation_labels(sentence)
        )
    )
    if unsupported_citations:
        return CitationValidation(
            False, normalized_answer, tuple(labels), (), available, normalized,
            "cited passage does not support one or more answer claims", repair_actions,
        )
    return CitationValidation(True, normalized_answer, tuple(labels), (), available, normalized, None, repair_actions)


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
    normalized = answer
    normalized = re.sub(r"\[\s*S\s*(\d+)\s*\.?\]", r"[S\1]", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\[\s*(?:source|src)\s*(\d+)\s*\.?\]", r"[S\1]", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\(\s*S\s*(\d+)\s*\.?\)", r"[S\1]", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\(\s*(?:source|src)\s*(\d+)\s*\.?\)", r"[S\1]", normalized, flags=re.IGNORECASE)
    # Grouped labels such as "(S1, S4)" or "[S2 and S3]" -> "[S1] [S4]".
    normalized = re.sub(
        r"[\(\[]\s*S\s*\d+(?:\s*(?:,|;|and|&)\s*S?\s*\d+)+\s*[\)\]]",
        lambda match: " ".join(f"[S{number}]" for number in re.findall(r"\d+", match.group(0))),
        normalized,
        flags=re.IGNORECASE,
    )
    return normalized, normalized != answer


def extract_citation_labels(answer: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(f"S{match}" for match in re.findall(r"\[S(\d+)\]", answer)))


def answer_bullets(answer: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in answer.splitlines() if line.strip().startswith(("-", "*")))


def answer_claim_lines(answer: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in answer.splitlines() if line.strip())


def answer_claim_sentences(answer: str) -> tuple[str, ...]:
    return tuple(
        sentence.strip()
        for line in answer_claim_lines(answer)
        for sentence in re.split(r"(?<=[.!?])\s+", line)
        if sentence.strip()
    )


def answer_line_ends_cleanly(line: str) -> bool:
    return line.rstrip().endswith((".", "?", "!", "]"))


def extract_source_list_labels(source_text: str) -> tuple[str, ...]:
    bracket_labels = list(extract_citation_labels(source_text))
    bare_labels = [f"S{match}" for match in re.findall(r"\bS(\d+)\b", source_text, flags=re.IGNORECASE)]
    return tuple(dict.fromkeys(bracket_labels + bare_labels))


def repair_missing_inline_citations(
    answer: str,
    context_items: list[dict[str, Any]],
    used_sources: tuple[str, ...],
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """Repair citation formatting only when retrieved evidence supports the line."""
    if not answer.strip():
        return answer, (), ()

    actions: list[str] = []
    unsupported: list[str] = []
    answer, extracted_end_labels = strip_trailing_source_labels(answer)
    standalone_match = re.search(r"(?<=[.!?])\s+((?:\[S\d+\]\s*(?:,|and)?\s*)+)$", answer)
    if standalone_match:
        extracted_end_labels += extract_citation_labels(standalone_match.group(1))
        answer = answer[: standalone_match.start()].rstrip()
    if extracted_end_labels:
        actions.append("removed_trailing_source_labels")

    lines = answer.splitlines()
    repaired_lines: list[str] = []
    changed = False
    context_by_label = {item.get("label"): item for item in context_items if item.get("label")}
    fallback_labels = tuple(label for label in dict.fromkeys(used_sources + extracted_end_labels) if label in context_by_label)

    for line in lines:
        if not line.strip():
            repaired_lines.append(line)
            continue
        sentences = re.split(r"(?<=[.!?])\s+", line.strip())
        repaired_sentences: list[str] = []
        for sentence in sentences:
            if not answer_line_ends_cleanly(sentence):
                repaired_sentences.append(sentence)
                continue

            labels = tuple(label for label in extract_citation_labels(sentence) if label in context_by_label)
            if labels:
                repaired_sentences.append(sentence)
                continue
            if re.search(r"\[[^\]]+\]", sentence):
                repaired_sentences.append(sentence)
                continue

            source_name_labels = labels_from_source_names(sentence, context_items)
            if source_name_labels:
                matching_labels = tuple(
                    label for label in source_name_labels
                    if claim_supported_by_context(sentence, context_by_label[label])
                )
                if matching_labels:
                    repaired_sentences.append(append_citation_labels(sentence, matching_labels))
                    actions.append("source_name_to_inline_label")
                    changed = True
                    continue

            supported_labels = tuple(
                label for label in fallback_labels
                if claim_supported_by_context(sentence, context_by_label[label])
            )
            if not supported_labels:
                supported_labels = best_supported_labels(sentence, context_items)
            if not supported_labels:
                supported_labels = semantic_supported_labels(sentence, context_items)

            if supported_labels:
                repaired_sentences.append(append_citation_labels(sentence, supported_labels))
                actions.append("added_supported_inline_label")
                changed = True
            else:
                repaired_sentences.append(sentence)
                unsupported.append(sentence)
        repaired_lines.append(" ".join(repaired_sentences))

    if not changed and not extracted_end_labels:
        return answer, (), tuple(unsupported)
    return "\n".join(repaired_lines), tuple(dict.fromkeys(actions)), tuple(unsupported)


def strip_trailing_source_labels(answer: str) -> tuple[str, tuple[str, ...]]:
    lines = answer.rstrip().splitlines()
    if not lines:
        return answer, ()

    last = lines[-1].strip()
    if not re.match(r"(?i)^(?:sources?|references?|citations?|used_sources)\s*:", last):
        return answer, ()

    labels = extract_source_list_labels(last)
    if not labels:
        return answer, ()
    return "\n".join(lines[:-1]).rstrip(), labels


def labels_from_source_names(line: str, context_items: list[dict[str, Any]]) -> tuple[str, ...]:
    normalized_line = normalize_match_text(line)
    labels: list[str] = []
    for item in context_items:
        label = item.get("label")
        if not label:
            continue
        names = [
            item.get("source_id"),
            item.get("title"),
            item.get("source_name"),
            item.get("section_heading"),
        ]
        for name in names:
            normalized_name = normalize_match_text(str(name or ""))
            if len(normalized_name) >= 4 and normalized_name in normalized_line:
                labels.append(label)
                break
    return tuple(dict.fromkeys(labels))


def best_supported_labels(line: str, context_items: list[dict[str, Any]]) -> tuple[str, ...]:
    scored: list[tuple[float, str]] = []
    for item in context_items:
        label = item.get("label")
        if not label:
            continue
        score = claim_support_score(line, item)
        if score >= 0.62:
            scored.append((score, label))
    scored.sort(reverse=True)
    return tuple(label for _, label in scored[:2])


def semantic_supported_labels(line: str, context_items: list[dict[str, Any]]) -> tuple[str, ...]:
    """Label of the passage an uncited sentence paraphrases closely.

    The labeled sentence must still pass cited_claim_supported, so the
    number, negation, speculation and must/required guards apply.
    """
    scored: list[tuple[float, str]] = []
    for item in context_items:
        label = item.get("label")
        if not label:
            continue
        score = semantic_sentence_support(line, item)
        if score is not None and score >= SENTENCE_PASSAGE_SIMILARITY_THRESHOLD:
            scored.append((score, label))
    for _, label in sorted(scored, reverse=True):
        item = next(item for item in context_items if item.get("label") == label)
        if cited_claim_supported(append_citation_labels(line, (label,)), item):
            return (label,)
    return ()


def claim_supported_by_context(line: str, context_item: dict[str, Any]) -> bool:
    return claim_support_score(line, context_item) >= 0.5


def cited_claim_supported(line: str, context_item: dict[str, Any]) -> bool:
    """Reject clearly unrelated or numerically inconsistent citations.

    Lexical agreement is only a screening check, not proof of entailment.
    """
    passage = str(context_item.get("passage") or "")
    claim = strip_citation_text(line)
    if re.match(r"\s*(?:the )?(?:retrieved evidence|source|excerpt|syllabus) does not (?:establish|justify|prove|state|rank|quantify)", claim, re.I):
        return True
    if not ABSENCE_CLAIM.search(line) and polarity_conflicts_with_passage(claim, passage):
        return False
    if SPECULATIVE_CLAIM.search(claim) and not SPECULATIVE_CLAIM.search(passage):
        # "X is likely a core unit, so it is important" is the model's guess,
        # not something the cited passage states.
        return False
    claim_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", claim))
    if claim_numbers - set(re.findall(r"\b\d+(?:\.\d+)?\b", passage)):
        return False
    if not re.search(r"\b(?:does not|do not|not stated|no evidence|cannot establish)\b", claim, re.I):
        strong_claims = r"\b(?:guarantee\w*|mandatory|prerequisite|requir\w*|must|always|never|every|all)\b"
        lowered_claim = claim.lower()
        lowered_passage = passage.lower()
        if re.search(strong_claims, lowered_claim) and not re.search(strong_claims, lowered_passage):
            return False
        # Taxonomy claims ("software engineering is a subset of computer
        # engineering") must come from the passage, not from word overlap.
        relation = re.search(RELATION_CLAIM, lowered_claim)
        if relation and not re.search(RELATION_CLAIM, lowered_passage):
            return False
    # Paraphrases share few words with the passage; a close sentence-level
    # embedding match counts as support once the guards above have passed.
    return claim_support_score(claim, context_item) >= 0.25 or semantically_supported(claim, context_item)


def claim_support_score(line: str, context_item: dict[str, Any]) -> float:
    claim_terms = significant_terms(strip_citation_text(line))
    if len(claim_terms) < 2:
        return 0.0
    evidence = " ".join(
        str(context_item.get(key) or "")
        for key in ("passage", "title", "source_name", "section_heading", "category")
    )
    evidence_terms = significant_terms(evidence)
    if not evidence_terms:
        return 0.0
    matched = sum(1 for term in claim_terms if term in evidence_terms)
    coverage = matched / len(claim_terms)
    if matched < 2:
        return 0.0
    if len(claim_terms) <= 4 and matched < len(claim_terms):
        coverage *= 0.75
    return coverage


_semantic_encoder: Callable[[list[str]], Any] | None = None


def configure_semantic_encoder(encoder: Callable[[list[str]], Any] | None) -> None:
    """Set the function returning normalized embeddings for a list of texts (None disables)."""
    global _semantic_encoder
    _semantic_encoder = encoder
    _embed_text.cache_clear()


@lru_cache(maxsize=4096)
def _embed_text(text: str) -> Any:
    return _semantic_encoder([text])[0]


def semantic_similarity(first: str, second: str) -> float | None:
    """Cosine similarity of two texts, or None when no encoder is configured."""
    if _semantic_encoder is None or not first.strip() or not second.strip():
        return None
    try:
        return float(_embed_text(first) @ _embed_text(second))
    except Exception:
        return None


def passage_sentences(passage: str) -> list[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", passage or "") if len(part.split()) >= 4]
    return sentences or ([passage.strip()] if (passage or "").strip() else [])


def semantic_sentence_support(claim: str, context_item: dict[str, Any]) -> float | None:
    """Best similarity between a claim and any sentence of the cited passage."""
    text = " ".join(strip_citation_text(claim).split())
    scores = [semantic_similarity(text, sentence) for sentence in passage_sentences(str(context_item.get("passage") or ""))]
    scores = [score for score in scores if score is not None]
    return max(scores) if scores else None


def semantically_supported(claim: str, context_item: dict[str, Any]) -> bool:
    score = semantic_sentence_support(claim, context_item)
    return score is not None and score >= SENTENCE_PASSAGE_SIMILARITY_THRESHOLD


def answer_addresses_question(question: str, answer: str) -> bool:
    score = semantic_similarity(strip_retrieval_annotations(question), " ".join(strip_citation_text(answer).split()))
    return score is not None and score >= QUESTION_ANSWER_SIMILARITY_THRESHOLD


def significant_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for match in re.findall(r"[a-zA-Z0-9+]{3,}", text.lower()):
        if match in STOPWORDS:
            continue
        terms.add(match.rstrip("s"))
    return terms


def strip_citation_text(text: str) -> str:
    # Remove only citation labels. Removing any bracketed text let an answer
    # wrapped entirely in "[ ... ]" skip claim checking.
    without_labels = re.sub(r"\[\s*S\d+(?:\s*[,;]\s*S?\d+)*\s*\]", " ", text)
    return re.sub(r"(?i)\b(?:according to|source|sources|reference|references|citation|citations)\b", " ", without_labels)


def normalize_match_text(text: str) -> str:
    return " ".join(re.findall(r"[a-zA-Z0-9+]+", text.lower()))


def append_citation_labels(line: str, labels: tuple[str, ...]) -> str:
    citation = " ".join(f"[{label}]" for label in labels)
    if not citation:
        return line
    trailing = ""
    body = line.rstrip()
    while body and body[-1] in ".!?":
        trailing = body[-1] + trailing
        body = body[:-1].rstrip()
    return f"{body} {citation}{trailing}"


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
        "repair_actions": list(validation.repair_actions),
        "reason": validation.reason,
        "retry_attempted": retry_attempted,
        "retry_successful": retry_successful,
        "generations_attempted": generations_attempted,
        "retry_failure_reason": retry_failure_reason,
    }


RETRIEVAL_ANNOTATION = re.compile(r"\s*\((?:Computer Engineering|topics:|constraints:)[^()]*\)\s*$", re.IGNORECASE)


def strip_retrieval_annotations(question: str) -> str:
    """Remove the "(Computer Engineering; topics: ...)" suffix added for retrieval."""
    return RETRIEVAL_ANNOTATION.sub("", question or "").strip() or (question or "")


STOPWORDS = {
    "am",
    "if",
    "ok",
    "okay",
    "need",
    "needs",
    "topics",
    "constraints",
    "a",
    "about",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "can",
    "could",
    "build",
    "building",
    "did",
    "do",
    "does",
    "for",
    "from",
    "before",
    "graduation",
    "graduating",
    "have",
    "how",
    "i",
    "in",
    "important",
    "impressive",
    "is",
    "it",
    "learn",
    "me",
    "much",
    "of",
    "on",
    "or",
    "participate",
    "personal",
    "proof",
    "should",
    "student",
    "students",
    "tell",
    "that",
    "the",
    "there",
    "this",
    "to",
    "u",
    "available",
    "asked",
    "basically",
    "become",
    "closer",
    "demek",
    "doing",
    "engineer",
    "engineers",
    "find",
    "impress",
    "kind",
    "name",
    "ne",
    "outside",
    "recruiter",
    "recruiters",
    "regarding",
    "them",
    "useful",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "you",
    "your",
}

EMOTIONAL_TERMS = {
    "scary", "scared", "afraid", "fear", "worried", "worry", "nervous", "anxious", "stressed",
    "quit", "quitting", "survive", "struggle", "struggling", "hate", "love", "bad", "terrible",
    "really", "rly", "lol", "bro",
    # Informal quantity and intensity words ("lots of coding", "a powerful laptop").
    "lots", "lot", "alot", "mostly", "mainly", "much", "many", "very", "normal", "typical",
    "powerful", "strong", "enough", "actually", "kind", "sort",
}

TERM_ALIASES = {
    "difference": ("difference", "differences", "differ", "differs", "different", "whereas", "unlike", "compared", "while", "distinct", "focuses"),
    "differences": ("difference", "differences", "differ", "differs", "different", "whereas", "unlike", "compared", "while", "distinct", "focuses"),
    "vs": ("difference", "differ", "differs", "different", "whereas", "unlike", "compared", "while", "both"),
    "coding": ("coding", "code", "programming", "programs", "software development", "software"),
    "code": ("coding", "code", "programming", "programs", "software development", "software"),
    "theory": ("theory", "theoretical", "mathematics", "math", "foundations", "fundamentals", "principles", "concepts"),
    "theoretical": ("theory", "theoretical", "mathematics", "math", "foundations", "fundamentals", "principles", "concepts"),
    "practical": ("practical", "hands-on", "laboratory", "laboratories", "lab", "labs", "projects", "design"),
    "physics": ("physics", "natural sciences", "electricity and magnetism"),
    "lab": ("lab", "laboratory", "laboratories"),
    "labs": ("lab", "laboratory", "laboratories"),
    "ce": ("ce", "computer engineering"),
    "ceng": ("ceng", "computer engineering"),
    "computer engineering": ("computer engineering", "computer engineer", "engineering"),
    "ai": ("ai", "artificial intelligence", "machine learning"),
    "artificial": ("ai", "artificial intelligence"),
    "intelligence": ("ai", "artificial intelligence"),
    "math": ("math", "mathematics", "calculus", "differential", "probability", "statistics", "discrete"),
    "mathematics": ("math", "mathematics", "calculus", "differential", "probability", "statistics", "discrete"),
    "courses": ("course", "courses", "curriculum", "semester", "ects"),
    "course": ("course", "courses", "curriculum", "semester", "ects"),
    "classes": ("class", "classes", "course", "courses", "curriculum"),
    "class": ("class", "classes", "course", "courses", "curriculum"),
    "programming": ("programming", "coding", "software", "python", "java", "c++"),
    "algorithm": ("algorithm", "algorithms", "data structures", "programming", "problem solving"),
    "algorithms": ("algorithm", "algorithms", "data structures", "programming", "problem solving"),
    "testing": ("testing", "debugging", "software development", "quality"),
    "debugging": ("debugging", "testing", "software development", "quality"),
    "frontend": ("frontend", "front-end", "web development", "software development", "applications"),
    "backend": ("backend", "back-end", "software development", "applications", "databases"),
    "sql": ("sql", "database", "databases", "data"),
    "react": ("react", "web development", "frontend", "software development"),
    "language": ("language", "languages", "programming", "python", "java", "c++"),
    "languages": ("language", "languages", "programming", "python", "java", "c++"),
    "linux": ("linux", "unix", "operating system", "operating systems", "systems administration"),
    "git": ("git", "github", "version control", "repository", "repositories", "source control"),
    "github": ("github", "git", "version control", "repository", "repositories", "portfolio"),
    "difficult": ("difficult", "difficulty", "challenging", "challenge", "workload", "requirements", "preparation"),
    "hard": ("hard", "difficult", "challenging", "challenge", "workload", "requirements"),
    "hardest": ("hardest", "most difficult", "most challenging", "difficulty ranking", "hardest engineering", "comparative difficulty"),
    "embedded": ("embedded", "embedded systems", "hardware", "systems", "microcontroller", "microcontrollers", "computer systems"),
    "architecture": ("architecture", "computer architecture", "hardware", "computer systems"),
    "arduino": ("arduino", "microcontroller", "embedded", "hardware"),
    "fpga": ("fpga", "programmable logic", "hardware", "digital logic"),
    "microcontroller": ("microcontroller", "microcontrollers", "embedded", "hardware"),
    "iot": ("iot", "internet of things", "embedded", "networks", "hardware"),
    "systems": ("systems", "computer systems", "hardware", "software", "embedded systems", "operating systems"),
    "teamwork": ("teamwork", "team work", "team", "teams", "collaboration", "collaborate", "communication", "cooperation"),
    "future": ("future", "future-proof", "future proof", "future skills", "future jobs", "future technologies", "adaptability", "reskilling", "lifelong learning"),
    "career": ("career", "careers", "job", "jobs", "employment", "work", "workforce", "labor market", "labour market"),
    "gpa": ("gpa", "grade point", "grade", "grades", "academic record"),
    "project": ("project", "projects", "portfolio", "portfolios", "experience", "examples"),
    "projects": ("project", "projects", "portfolio", "portfolios", "experience", "examples"),
    "portfolio": ("portfolio", "portfolios", "project", "projects", "resume", "cv", "github"),
    "hackathons": ("hackathon", "hackathons", "coding competition", "coding competitions", "competition", "competitions", "projects", "portfolio"),
    "competitions": ("competition", "competitions", "coding competition", "coding competitions", "hackathon", "hackathons", "projects", "portfolio"),
    "cybersecurity": ("cybersecurity", "cyber security", "information security", "security", "networks", "network security"),
    "hacking": ("hacking", "ethical hacking", "cybersecurity", "security"),
    "certifications": ("certifications", "certification", "certificate", "credentials", "cybersecurity"),
    "web": ("web", "web development", "software development", "applications", "programming"),
    "mobile": ("mobile", "mobile development", "applications", "software development", "programming"),
    "field": ("field", "fields", "area", "areas", "branch", "branches", "specialization", "specializations", "subdiscipline", "subdisciplines"),
    "fields": ("field", "fields", "area", "areas", "branch", "branches", "specialization", "specializations", "subdiscipline", "subdisciplines"),
    "area": ("field", "fields", "area", "areas", "branch", "branches", "specialization", "specializations", "subdiscipline", "subdisciplines"),
    "areas": ("field", "fields", "area", "areas", "branch", "branches", "specialization", "specializations", "subdiscipline", "subdisciplines"),
    "branch": ("field", "fields", "area", "areas", "branch", "branches", "specialization", "specializations", "subdiscipline", "subdisciplines"),
    "branches": ("field", "fields", "area", "areas", "branch", "branches", "specialization", "specializations", "subdiscipline", "subdisciplines"),
    "track": ("track", "tracks", "field", "fields", "area", "areas", "specialization", "specializations"),
    "tracks": ("track", "tracks", "field", "fields", "area", "areas", "specialization", "specializations"),
    "specialization": ("field", "fields", "area", "areas", "branch", "branches", "specialization", "specializations", "subdiscipline", "subdisciplines"),
    "specializations": ("field", "fields", "area", "areas", "branch", "branches", "specialization", "specializations", "subdiscipline", "subdisciplines"),
}


def unsupported_answerability_reason(question: str, results: list[dict[str, Any]]) -> str | None:
    if cybersecurity_pathway_evidence_supported(question, results):
        return None
    if career_jobs_evidence_supported(question, results):
        return None
    terms = content_terms(question)
    if not terms:
        return "question does not contain enough domain-specific terms to verify retrieved evidence"
    evidence_text = " ".join((result.get("text") or "").lower() for result in results[:5])
    matched = {term for term in terms if term_supported_by_evidence(term, evidence_text)}
    must_have = required_terms(question, terms)
    missing_required = [term for term in must_have if term not in matched]
    if missing_required:
        if partially_answerable_multi_topic_question(question, matched):
            return None
        return f"retrieved evidence does not address required question terms: {missing_required}"
    if len(terms) >= 3 and len(matched) < 2:
        return f"retrieved evidence has too little overlap with the question terms: {sorted(terms - matched)}"
    if len(terms) <= 2 and not matched:
        return f"retrieved evidence does not address the question terms: {sorted(terms)}"
    return None


def content_terms(question: str) -> set[str]:
    terms = {
        token
        for token in re.findall(r"[a-z0-9+#]+", (question or "").lower())
        if len(token) > 1 and token not in STOPWORDS
    }
    if "computer" in terms and "engineering" in terms:
        terms.discard("computer")
        terms.discard("engineering")
        terms.add("computer engineering")
    return terms


def required_terms(question: str, terms: set[str]) -> set[str]:
    q = (question or "").lower()
    required: set[str] = set()
    for term in terms:
        if term in {"advisor", "chatbot", "assistant", "name", "developed", "created", "made", "built"}:
            required.add(term)
    practical_career_mix = contains_any_term(q, ("gpa", "grade", "grades")) and contains_any_term(
        q, ("project", "projects", "portfolio", "internship", "internships")
    )
    if contains_any_term(q, ("course", "courses", "class", "classes", "curriculum")) and not contains_any_term(
        q, ("study abroad", "erasmus")
    ) and not practical_career_mix:
        required.add(next((term for term in terms if term in {"course", "courses", "class", "classes", "curriculum"}), "courses"))
    if contains_any_term(q, ("math", "mathematics", "calculus")):
        required.add(next((term for term in terms if term in {"math", "mathematics", "calculus"}), "mathematics"))
    if contains_any_term(q, ("difficult", "difficulty", "hard", "hardest", "challenging")):
        required.add(next((term for term in terms if term in {"difficult", "difficulty", "hard", "hardest", "challenging"}), "difficult"))
    if contains_any_term(q, ("hackathon", "hackathons", "coding competition", "coding competitions")):
        required.add(next((term for term in terms if term in {"hackathon", "hackathons", "competition", "competitions"}), "hackathons"))
    return required


def term_supported_by_evidence(term: str, evidence_text: str) -> bool:
    aliases = TERM_ALIASES.get(term, (term,))
    return any(contains_any_term(evidence_text, (alias,)) for alias in aliases)


def cybersecurity_pathway_evidence_supported(question: str, results: list[dict[str, Any]]) -> bool:
    if not cybersecurity_pathway_question(question):
        return False
    for result in results[:5]:
        text = result_evidence_text(result)
        category = (result.get("category") or "").lower()
        title = (result.get("title") or "").lower()
        if category == "cybersecurity" or "cybersecurity" in title or contains_any_term(text, ("nice framework", "cybersecurity workforce")):
            return True
    return False


def career_jobs_evidence_supported(question: str, results: list[dict[str, Any]]) -> bool:
    if not is_career_jobs_question(question):
        return False
    for result in results[:5]:
        text = result_evidence_text(result)
        if contains_any_term(
            text,
            (
                "ce professionals apply their skills",
                "broad range of diverse career sectors",
                "computer hardware engineers",
                "research, design, develop, or test computer",
                "career sectors",
            ),
        ):
            return True
    return False


def unsupported_specific_fact_reason(question: str, results: list[dict[str, Any]]) -> str | None:
    q = question.lower()
    checks = [
        (("tuition", "fee", "fees", "cost"), ("tuition", "fee", "fees", "cost", "payment")),
        (("deadline", "application date", "registration date"), ("deadline", "date", "registration", "application")),
        (("quota", "capacity"), ("quota", "capacity")),
        (("scholarship",), ("scholarship",)),
        (("salary", "salaries", "pay", "wage"), ("salary", "salaries", "pay", "wage", "earnings")),
        (("gpa", "grade point"), ("gpa", "grade point", "grade")),
    ]
    missing_groups: list[list[str]] = []
    evidence_text = " ".join((result.get("text") or "").lower() for result in results)
    if (
        contains_any_term(q, ("hours", "hour", "each week", "per week", "weekly"))
        and contains_any_term(q, ("study", "students"))
        and not contains_any_term(evidence_text, ("study hours", "time spent studying", "hours studying", "typical weekly study"))
    ):
        return "retrieved evidence does not contain typical weekly study-hour evidence"
    for triggers, evidence_terms in checks:
        if any(term in q for term in triggers):
            required_terms = list(evidence_terms)
            if not contains_any_term(evidence_text, required_terms):
                missing_groups.append(required_terms)
    if missing_groups:
        return f"retrieved evidence does not contain requested specific fact terms: {missing_groups}"
    return None


def unsupported_category_reason(question: str, results: list[dict[str, Any]]) -> str | None:
    if partially_answerable_multi_topic_from_results(question, results):
        return None
    q = question.lower()
    if "cybersecurity" not in q:
        return None
    categories = {(result.get("category") or "").lower() for result in results}
    if "cybersecurity" not in categories:
        evidence_text = " ".join((result.get("text") or "").lower() for result in results)
        if not term_supported_by_evidence("cybersecurity", evidence_text):
            return "retrieved evidence did not include a cybersecurity-category source or cybersecurity evidence"
    return None


def unsupported_claim_reason(question: str, results: list[dict[str, Any]]) -> str | None:
    q = question.lower()
    evidence_text = " ".join((result.get("text") or "").lower() for result in results)
    if is_command_line_importance_question(q) and not command_line_importance_evidence_supported(results):
        return "retrieved evidence does not directly rate command-line or terminal-skill importance for Computer Engineering"

    asks_hackathon_value = contains_any_term(q, ("hackathon", "hackathons", "coding competition", "coding competitions"))
    if asks_hackathon_value and not contains_any_term(
        evidence_text,
        ("hackathon", "hackathons", "coding competition", "coding competitions", "student competition", "student competitions"),
    ):
        return "retrieved evidence does not directly address hackathons or student coding competitions"

    asks_scholarship_opportunities = contains_any_term(q, ("scholarship", "scholarships")) and contains_any_term(
        q,
        ("opportunity", "opportunities", "option", "options", "available", "apply", "ask about", "can i ask"),
    )
    if asks_scholarship_opportunities and not scholarship_opportunity_evidence_supported(results):
        return "retrieved evidence does not contain scholarship-opportunity evidence"

    asks_general_salary_for_graduates = contains_any_term(q, ("salary", "salaries", "pay", "wage", "earnings")) and contains_any_term(
        q,
        ("graduate", "graduates", "job", "jobs", "career", "careers"),
    )
    if asks_general_salary_for_graduates and not salary_for_graduates_evidence_supported(results):
        return "retrieved evidence does not contain salary evidence for Computer Engineering graduates or job outcomes"

    ordering_reason = unsupported_choice_order_reason(q, results)
    if ordering_reason:
        return ordering_reason

    asks_highest_salary_specialization = (
        contains_any_term(q, ("highest", "most", "best paying", "highest paying", "highest-paid"))
        and contains_any_term(q, ("salary", "salaries", "pay", "pays", "paying"))
        and contains_any_term(q, ("specialization", "specializations", "field", "fields"))
    )
    if asks_highest_salary_specialization and not (
        contains_any_term(
            evidence_text,
            (
                "salary by specialization",
                "salaries by specialization",
                "specialization salary",
                "specialization salaries",
                "highest-paying specialization",
                "highest paying specialization",
            ),
        )
    ):
        return "retrieved evidence does not compare salaries by Computer Engineering specialization"

    asks_local_starting_salary = (
        contains_any_term(q, ("starting salary", "starting salaries", "entry salary", "entry-level salary"))
        and contains_any_term(q, ("ostim", "ceng", "computer engineering", "graduates"))
    )
    if asks_local_starting_salary and not contains_any_term(
        evidence_text,
        ("starting salary", "starting salaries", "entry salary", "graduate salary", "graduate salaries"),
    ):
        return "retrieved evidence does not contain local Computer Engineering starting-salary evidence"

    asks_exact_current_financial_fact = (
        contains_any_term(q, ("exact", "2026", "current"))
        and contains_any_term(q, ("tuition", "fee", "fees", "scholarship", "scholarships"))
    )
    if asks_exact_current_financial_fact and contains_any_term(q, ("tuition", "fee", "fees")) and not contains_any_term(
        evidence_text,
        ("2026 tuition", "tuition fee", "tuition fees"),
    ):
        return "retrieved evidence does not contain the requested exact current financial information"
    if asks_exact_current_financial_fact and contains_any_term(q, ("scholarship", "scholarships")) and not contains_any_term(
        evidence_text,
        ("scholarship", "scholarships"),
    ):
        return "retrieved evidence does not contain the requested scholarship information"

    asks_guaranteed_outcome = contains_any_term(
        q,
        (
            "guarantee",
            "guaranteed",
            "promise",
            "will hire me",
            "which company will hire",
            "personally will succeed",
            "predict whether i",
        ),
    )
    if asks_guaranteed_outcome:
        return "knowledge base cannot support guaranteed or personalized future outcomes"

    asks_exact_exam_content = contains_any_term(q, ("exact questions", "final exam questions", "what questions will be"))
    if asks_exact_exam_content:
        return "knowledge base cannot provide exact future exam questions"

    asks_exact_exam_dates = contains_any_term(q, ("exam dates", "2027 exam", "all 2027"))
    if asks_exact_exam_dates:
        return "knowledge base cannot provide exact future exam dates"

    asks_exact_job_placement = contains_any_term(q, ("exact job placement", "placement rate"))
    if asks_exact_job_placement and not contains_any_term(evidence_text, ("placement rate", "graduate employment rate")):
        return "retrieved evidence does not contain exact Computer Engineering graduate placement-rate evidence"

    asks_attendance_rule = contains_any_term(q, ("attendance rule", "attendance requirement", "attendance policy"))
    if asks_attendance_rule and not attendance_rule_evidence_supported(evidence_text):
        return "retrieved evidence does not contain attendance-rule evidence"

    asks_gpa_project_internship_comparison = (
        "gpa" in q
        and any(term in q for term in ["project", "projects", "portfolio"])
        and any(term in q for term in ["internship", "internships"])
    )
    if asks_gpa_project_internship_comparison:
        if not gpa_project_internship_evidence_supported(evidence_text):
            return "retrieved evidence does not contain enough support for GPA, projects, and internships advice"
        return None

    asks_ai_replacement = (
        "replace" in q
        and any(term in q for term in ["ai", "artificial intelligence", "automation", "generative ai"])
    )
    if not asks_ai_replacement:
        return None

    replacement_terms = [
        "replace",
        "replacing",
        "replacement",
        "displace",
        "displacement",
        "substitute",
    ]
    if not contains_any_term(evidence_text, replacement_terms):
        if ai_impact_evidence_supported(evidence_text):
            return None
        return "retrieved evidence does not directly address whether AI replaces computer engineers"
    return None


def answerability_prompt_guidance(question: str) -> str:
    q = (question or "").lower()
    guidance: list[str] = []
    if is_computer_engineering_it_comparison_question(question):
        guidance.append(
            "- For IT versus Computer Engineering questions, explicitly compare Information Technology with Computer Engineering. "
            "Do not answer by comparing Computer Engineering with Computer Science unless the question asks for Computer Science. "
            "Use only distinctions directly stated in the context. A safe structure is: Computer Engineering involves X, while Information Technology involves Y, with citations in the same paragraph."
        )
    if contains_any_term(q, ("important", "importance")):
        guidance.append(
            "- For importance questions, do not claim something is essential, fundamental, or very important unless the context directly says that. "
            "If the context only mentions where the topic appears, do not output INSUFFICIENT_INFORMATION; say the KB does not directly rate its importance and then state only the supported mention."
        )
    if is_future_technology_question(question):
        guidance.append(
            "- For future-technology questions, do not predict growth or rank fields unless the context directly does so. "
            "Do not output INSUFFICIENT_INFORMATION when the context names new trends, emerging topics, future trends, or specialization areas. "
            "Give a bounded list of those named topics and say the KB does not rank them unless the context ranks them."
        )
    if "replace" in q and contains_any_term(q, ("ai", "artificial intelligence", "automation", "generative ai")):
        guidance.append(
            "- For AI replacement questions, do not claim AI will or will not replace computer engineers unless the context directly says so. "
            "If replacement is not directly established, say the KB cannot establish whether replacement will happen, then answer only supported points about AI's impact, changing skills, and career preparation. "
            "Do not output INSUFFICIENT_INFORMATION when supported bounded impact or preparation evidence is available."
        )
    if (
        "gpa" in q
        and contains_any_term(q, ("project", "projects", "portfolio"))
        and contains_any_term(q, ("internship", "internships"))
    ):
        guidance.append(
            "- For GPA, projects, and internships questions, do not invent a universal ranking or numerical comparison. "
            "If the context does not directly compare all three, say the KB cannot rank them universally, then explain only their supported roles. "
            "Do not recommend prioritizing one over another unless the cited context directly makes that comparison."
        )
    if is_prior_programming_experience_question(question):
        guidance.append(
            "- For prior-programming questions, do not turn advice about a specific introductory CS course into a Computer Engineering admission or program requirement. "
            "If the context does not state a CENG prerequisite, say so, then summarize only the supported preparation advice."
        )
    if cybersecurity_pathway_question(question):
        guidance.append(
            "- For cybersecurity pathway questions, do not promise outcomes or recommend certifications unless the context directly supports them. "
            "Use cybersecurity framework evidence only to discuss roles, tasks, knowledge, and skills, and keep the answer cautious."
        )
    if is_git_github_learning_question(question):
        guidance.append(
            "- For Git/GitHub learning questions, do not claim every student must learn them unless the context directly says so. "
            "State the supported uses of Git/GitHub for version control, repositories, transparency, or collaboration."
        )
    if not guidance:
        return ""
    return "\n" + "\n".join(guidance)


def ai_impact_evidence_supported(evidence_text: str) -> bool:
    return contains_any_term(
        evidence_text,
        (
            "ai and big data",
            "generative artificial intelligence",
            "genai",
            "skill demand",
            "skills may lie",
            "reskilling",
            "upskilling",
            "development work",
            "work alongside ai",
            "ai systems evolve",
        ),
    )


def gpa_project_internship_evidence_supported(evidence_text: str) -> bool:
    has_gpa = contains_any_term(evidence_text, ("gpa", "grade-point-average", "grade point", "academic achievement"))
    has_projects = contains_any_term(evidence_text, ("project", "projects", "portfolio", "github"))
    has_internships = contains_any_term(evidence_text, ("internship", "internships", "work experience"))
    return has_gpa and has_projects and has_internships


def scholarship_opportunity_evidence_supported(results: list[dict[str, Any]]) -> bool:
    for result in results:
        text = result_evidence_text(result)
        has_scholarship_detail = contains_any_term(
            text,
            (
                "scholarship opportunity",
                "scholarship opportunities",
                "scholarships are available",
                "financial aid",
                "tuition scholarship",
                "scholarship application",
                "apply for scholarship",
            ),
        )
        has_program_anchor = contains_any_term(
            text,
            ("computer engineering", "ceng", "ostim", "department of computer engineering"),
        )
        if has_scholarship_detail and has_program_anchor:
            return True
    return False


def salary_for_graduates_evidence_supported(results: list[dict[str, Any]]) -> bool:
    for result in results:
        text = result_evidence_text(result)
        has_salary_detail = contains_any_term(
            text,
            (
                "graduate salary",
                "graduate salaries",
                "starting salary",
                "starting salaries",
                "entry salary",
                "entry-level salary",
                "placement salary",
            ),
        )
        has_graduate_anchor = contains_any_term(
            text,
            ("computer engineering", "ceng", "graduate", "graduates", "job placement"),
        )
        if has_salary_detail and has_graduate_anchor:
            return True
    return False


def result_evidence_text(result: dict[str, Any]) -> str:
    return " ".join(
        str(result.get(key) or "").lower()
        for key in ("text", "passage", "title", "source_name", "section_heading", "category")
    )


def is_command_line_importance_question(question: str) -> bool:
    q = (question or "").lower()
    asks_command_line = contains_any_term(q, ("command line", "command-line", "cli", "terminal", "shell"))
    asks_importance = contains_any_term(
        q,
        ("important", "importance", "essential", "fundamental", "required", "must know", "need to know", "need"),
    )
    return asks_command_line and asks_importance


def command_line_importance_evidence_supported(results: list[dict[str, Any]]) -> bool:
    for result in results:
        text = result_evidence_text(result)
        has_command_line = contains_any_term(text, ("command line", "command-line", "cli", "terminal", "shell"))
        has_importance = contains_any_term(
            text,
            ("important", "importance", "essential", "fundamental", "required", "must know", "need to know", "need"),
        )
        has_ce_anchor = contains_any_term(
            text,
            ("computer engineering", "ceng", "computer engineer", "ce curriculum", "ce2016"),
        )
        if has_command_line and has_importance and has_ce_anchor:
            return True
    return False


def unsupported_choice_order_reason(question: str, results: list[dict[str, Any]]) -> str | None:
    q = question.lower()
    has_choice_separator = any(separator in q for separator in (" or ", " vs ", " versus ", "rather than"))
    asks_ordered_choice = contains_any_term(q, ("first", "start with", "start by", "learn before")) and has_choice_separator
    if not asks_ordered_choice:
        return None

    evidence_text = " ".join(result_evidence_text(result) for result in results)
    requested_terms = tuple(term for term in ("arduino", "fpga", "microcontroller", "embedded", "hardware") if term in q)
    strict_platform_terms = {"arduino", "fpga"}
    missing_requested_terms = [
        term
        for term in requested_terms
        if (
            not contains_any_term(evidence_text, (term,))
            if term in strict_platform_terms
            else not term_supported_by_evidence(term, evidence_text)
        )
    ]
    if missing_requested_terms:
        return "retrieved evidence does not address the requested learning alternatives"

    has_ordering_evidence = contains_any_term(
        evidence_text,
        (
            "learn first",
            "start with",
            "start by",
            "before learning",
            "prerequisite",
            "recommended sequence",
            "learning path",
            "introductory",
        ),
    )
    if not has_ordering_evidence:
        return "retrieved evidence does not compare the requested learning order or prerequisites"
    return None


def attendance_rule_evidence_supported(evidence_text: str) -> bool:
    has_attendance = contains_any_term(evidence_text, ("attendance", "absence", "absences"))
    has_rule_language = contains_any_term(
        evidence_text,
        (
            "attendance requirement",
            "attendance is required",
            "must attend",
            "required to attend",
            "absence limit",
            "absences are limited",
            "attendance rule",
            "attendance policy",
        ),
    )
    return has_attendance and has_rule_language


def word_stem(word: str) -> str:
    """Crude stem so "specialize" matches "specialization" and "electives" matches "elective"."""
    word = word.lower()
    if len(word) >= 8:
        return word[:6]
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) - len(suffix) >= 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def unsupported_generated_answer_reason(question: str, answer: str, context_items: list[dict[str, Any]]) -> str | None:
    q = (question or "").lower()
    normalized_answer = normalize_answer(answer).lower()
    evidence_text = " ".join((item.get("passage") or item.get("text") or "").lower() for item in context_items)

    focus = content_terms(question) - {
        "computer engineering", "ceng", "ce", "computer", "engineering", "career", "careers",
        "job", "jobs", "work", "study", "studying", "taking", "after", "still",
        "graduate", "graduates", "future", "technologies", "technology", "follow",
        "good", "choice", "choose", "like", "hate", "first", "right", "project",
    }
    # Feelings and decision words describe the student, not the topic a
    # grounded answer must cover ("math scary, should I quit?" is about math).
    focus -= EMOTIONAL_TERMS
    answer_stems = {word_stem(word) for word in re.findall(r"[a-z0-9+#]+", normalized_answer)}
    covered = {
        term
        for term in focus
        if term_supported_by_evidence(term, normalized_answer) or (" " not in term and word_stem(term) in answer_stems)
    }
    if focus and len(covered) < (2 if len(focus) >= 3 else 1) and not answer_addresses_question(question, answer):
        # Word coverage misses paraphrased answers; the embedding check accepts
        # an answer that is clearly about the question.
        return "generated answer did not address the question's distinctive topic terms"

    if contains_any_term(q, ("what is computer engineering", "what is ceng")):
        invented_position = contains_any_term(normalized_answer, ("between computer science and software engineering", "between computer science and software"))
        if invented_position and not contains_any_term(evidence_text, ("between computer science and software engineering", "between computer science and software")):
            return "generated answer invented a position between computing disciplines"

    if "hardware" in q and "computer engineering" in q and "computer science" in q:
        asserts_comparison = contains_any_term(normalized_answer, ("more hardware than computer science", "greater emphasis on hardware", "computer science primarily focuses on software"))
        has_direct_comparison = contains_any_term(evidence_text, ("more hardware than computer science", "computer engineering has more hardware", "computer science focuses less on hardware"))
        if asserts_comparison and not has_direct_comparison:
            return "generated answer asserted an unsupported CENG/CS hardware ranking"

    if "ai" in q and "linear algebra" in q and "probability" in q:
        asserts_requirement = contains_any_term(normalized_answer, ("requires linear algebra", "require linear algebra", "must take linear algebra"))
        has_degree_requirement = contains_any_term(evidence_text, ("ostim ceng requires linear algebra", "linear algebra is required for ai in ceng", "must take linear algebra for ai"))
        if asserts_requirement and not has_degree_requirement:
            return "generated answer turned ML math foundations into an unverified CENG requirement"

    if contains_any_term(q, ("how much lab work", "how many lab hours", "laboratory hours")):
        gives_total = contains_any_term(normalized_answer, ("credit hours", "lecture hours", "lab hours"))
        has_program_total = contains_any_term(evidence_text, ("total lab hours for the program", "total laboratory hours for the program", "program-wide lab hours"))
        if gives_total and not has_program_total:
            return "generated answer treated sample course hours as a program-wide lab amount"

    if contains_any_term(q, ("entry-level", "entry level", "junior job")):
        asserts_entry_level = contains_any_term(normalized_answer, ("entry-level", "entry level", "junior"))
        has_entry_level_evidence = contains_any_term(evidence_text, ("entry-level", "entry level", "junior role", "junior position"))
        if asserts_entry_level and not has_entry_level_evidence:
            return "generated answer labeled occupations entry-level without direct evidence"

    if "fpga" in q and "digital logic" in q and contains_any_term(q, ("before", "prerequisite", "first")):
        asserts_sequence = contains_any_term(normalized_answer, ("not recommended", "must take", "need to take", "requires digital logic", "after taking digital logic"))
        has_sequence_evidence = contains_any_term(evidence_text, ("digital logic prerequisite for fpga", "take digital logic before fpga", "digital logic is required before fpga"))
        if asserts_sequence and not has_sequence_evidence:
            return "generated answer invented an FPGA/digital-logic prerequisite"

    if "linux" in q and "important" in q:
        field_wide_claim = contains_any_term(normalized_answer, ("important in the computer engineering field", "important in computer engineering", "essential for computer engineers", "required for computer engineers"))
        field_wide_evidence = contains_any_term(evidence_text, ("linux is important in computer engineering", "linux is essential for computer engineers", "linux is required for computer engineers"))
        if field_wide_claim and not field_wide_evidence:
            return "generated answer generalized a Linux course example into a field-wide requirement"

    if contains_any_term(q, ("work abroad", "working abroad", "work overseas", "working overseas")):
        has_abroad_evidence = contains_any_term(evidence_text, ("work abroad", "working abroad", "work overseas", "working overseas", "international employment"))
        acknowledges_gap = contains_any_term(normalized_answer, ("does not establish", "cannot determine", "does not say", "not enough evidence"))
        if not has_abroad_evidence and not acknowledges_gap:
            return "generated answer did not establish whether graduates can work abroad"

    if contains_any_term(q, ("hate electronics", "dislike electronics", "do not like electronics")):
        recommends_degree = contains_any_term(normalized_answer, ("still a good choice", "should choose ceng", "should study computer engineering"))
        if recommends_degree and not contains_any_term(evidence_text, ("dislike electronics", "hate electronics", "not interested in electronics")):
            return "generated answer made a personal degree recommendation without supporting evidence"

    if contains_any_term(q, ("learn first", "start with")) and contains_any_term(q, ("ai", "artificial intelligence")) and contains_any_term(q, ("cybersecurity", "cyber security")):
        recommends_order = contains_any_term(normalized_answer, ("start with cybersecurity", "cybersecurity first", "start with ai", "ai first"))
        if recommends_order and not contains_any_term(evidence_text, ("cybersecurity before ai", "ai before cybersecurity", "start with cybersecurity", "start with ai")):
            return "generated answer recommended an unsupported AI/cybersecurity learning order"

    if is_programming_language_question(question):
        answer_links_intro_courses_to_languages = contains_any_term(normalized_answer, ("ceng109", "ceng110")) and contains_any_term(
            normalized_answer,
            ("python", "c++"),
        ) and contains_any_term(
            normalized_answer,
            ("infer", "inferred", "likely", "might", "introduced to", "could be", "depending on", "therefore"),
        )
        acknowledges_intro_course_gap = contains_any_term(
            normalized_answer,
            (
                "does not name a specific language for those two course descriptions",
                "specific programming languages taught in these courses are not explicitly mentioned",
                "does not explicitly mention the languages for ceng109 and ceng110",
            ),
        )
        unsupported_bridge = contains_any_term(
            normalized_answer,
            (
                "could be either python or c++",
                "depending on the specific implementation",
                "introduced to object-oriented programming languages",
            ),
        )
        if answer_links_intro_courses_to_languages and (unsupported_bridge or not acknowledges_intro_course_gap):
            return "generated answer inferred programming languages for CENG109/CENG110 without direct course-language evidence"

    if (
        cybersecurity_pathway_question(question)
        and (
            contains_any_term(normalized_answer, ("certification", "certifications"))
            or contains_any_term(
                normalized_answer,
                (
                    "you should focus",
                    "should focus",
                    "can focus",
                    "develop skills",
                    "developing a strong foundation",
                    "crucial",
                    "essential",
                    "vital",
                    "important",
                    "beneficial",
                    "good understanding",
                    "successful career",
                ),
            )
        )
        and not contains_any_term(
            normalized_answer,
            ("does not justify", "does not support", "no direct evidence", "retrieved evidence does not"),
        )
    ):
        return "generated answer gave cybersecurity pathway advice beyond the retrieved framework evidence"

    if is_prior_programming_experience_question(question):
        overstates_requirement = contains_any_term(
            normalized_answer,
            (
                "required before starting",
                "likely required",
                "is required",
                "must have prior",
                "need prior programming",
                "need programming experience",
                "recommended before starting computer engineering",
                "recommended before starting the program",
                "beneficial for starting the program",
                "beneficial for starting the computer engineering",
            ),
        )
        acknowledges_program_gap = contains_any_term(
            normalized_answer,
            (
                "does not state",
                "does not establish",
                "does not say",
                "kb does not",
                "retrieved evidence does not",
            ),
        )
        direct_requirement_evidence = contains_any_term(
            evidence_text,
            (
                "prior programming experience is required before starting computer engineering",
                "computer engineering admission requires prior programming",
                "ceng requires prior programming",
            ),
        )
        if overstates_requirement and not direct_requirement_evidence and not acknowledges_program_gap:
            return "generated answer turned intro-course advice into an unsupported Computer Engineering prerequisite"

    if is_git_github_learning_question(question):
        overstates_git_value = contains_any_term(
            normalized_answer,
            ("significant benefits", "valuable skills", "highlight their importance", "importance in facilitating", "any field of study"),
        )
        acknowledges_git_limit = contains_any_term(
            normalized_answer,
            ("does not prove", "not explicitly stated", "does not specify", "retrieved evidence does not"),
        )
        if overstates_git_value and not acknowledges_git_limit:
            return "generated answer overstated Git/GitHub value beyond retrieved evidence"

    if is_career_jobs_question(question):
        broad_role_overreach = contains_any_term(
            normalized_answer,
            (
                "mobile application developer",
                "mobile application developers",
                "computer programmer",
                "computer programmers",
                "future of jobs report",
                "significant growth in the future",
            ),
        )
        if broad_role_overreach:
            return "generated answer attributed broad technology roles to Computer Engineering graduates without direct role evidence"

    asks_command_line_importance = is_command_line_importance_question(q)
    if asks_command_line_importance:
        unsupported_importance_claim = contains_any_term(
            normalized_answer,
            (
                "is important",
                "considered important",
                "very important",
                "essential",
                "fundamental",
                "core skill",
                "required",
            ),
        )
        evidence_rates_importance = contains_any_term(
            evidence_text,
            (
                "command line is important",
                "command-line is important",
                "important command line",
                "essential command line",
                "required command line",
                "must use the command line",
            ),
        )
        answer_acknowledges_gap = contains_any_term(
            normalized_answer,
            (
                "does not directly rate",
                "not directly addressed",
                "does not state how important",
                "cannot determine how important",
            ),
        )
        if unsupported_importance_claim and not evidence_rates_importance and not answer_acknowledges_gap:
            return "generated answer rated command-line importance without direct importance evidence"

    if is_future_technology_question(question):
        if contains_any_term(normalized_answer, ("important", "importance", "most important")) and not contains_any_term(
            evidence_text,
            ("important", "importance", "very significant", "significant contribution"),
        ):
            return "generated answer rated future technologies as important without direct evidence"
        future_growth_claim = contains_any_term(
            normalized_answer,
            (
                "expected to grow",
                "significant growth",
                "significant impact in the future",
                "should focus on",
                "best fields",
                "most important future",
            ),
        )
        if future_growth_claim and not contains_any_term(
            evidence_text,
            (
                "expected to grow",
                "significant growth",
                "students will learn",
                "course content spans",
                "emerging trends",
                "future trends",
            ),
        ):
            return "generated answer predicted or ranked future technologies without direct evidence"

    asks_gpa_project_internship = (
        "gpa" in q
        and contains_any_term(q, ("project", "projects", "portfolio"))
        and contains_any_term(q, ("internship", "internships"))
    )
    if asks_gpa_project_internship and contains_any_term(
        normalized_answer,
        (
            "prioritize",
            "prioritizing",
            "focus more on",
            "more advisable",
            "more beneficial",
            "over gpa",
            "rather than gpa",
        ),
    ):
        if not contains_any_term(
            evidence_text,
            ("more important than", "more beneficial than", "prioritize", "ranking", "ranked"),
        ):
            return "generated answer ranked GPA, projects, or internships without direct comparison evidence"

    asks_ai_replacement = (
        "replace" in q
        and contains_any_term(q, ("ai", "artificial intelligence", "automation", "generative ai"))
    )
    if asks_ai_replacement:
        uncertainty_phrases = (
            "cannot establish",
            "cannot determine",
            "does not establish",
            "no direct evidence",
            "does not support a definitive claim",
            "cannot definitively",
            "insufficient evidence to determine",
        )
        definite_replacement_claim = contains_any_term(
            normalized_answer,
            ("will replace", "will not replace", "won't replace", "going to replace", "not going to replace"),
        )
        if definite_replacement_claim and not contains_any_term(normalized_answer, uncertainty_phrases):
            return "generated answer made a definite AI replacement claim without direct replacement evidence"

    return None


def extractive_partial_answer(question: str, context_items: list[dict[str, Any]]) -> str | None:
    """Offer a short source excerpt only when it directly shares the requested topic."""
    lowered = question.lower()
    if re.search(r"\b(?:should i|can i|will i|am i)\b", lowered) and contains_any_term(
        lowered, ("quit", "survive", "choose", "right for me", "replace", "guarantee")
    ):
        return None
    def canonical(term: str) -> str:
        if term.startswith("mathematic"):
            return "math"
        if term.startswith(("laborator", "lab")):
            return "lab"
        return term

    topic_terms = {canonical(term) for term in significant_terms(question)} - {
        "computer", "engineering", "student", "students", "should", "could", "would",
        "what", "which", "about", "want", "need", "know", "tell", "please", "ceng",
        "scary", "afraid", "worried", "bad", "quit",
    }
    if not topic_terms:
        return None
    candidates: list[tuple[float, str, str]] = []
    for item in context_items:
        label = item.get("label")
        passage = item.get("passage") or ""
        if not label:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", passage):
            words = sentence.split()
            if not (6 <= len(words) <= 25) or sentence.endswith("..."):
                continue
            if sentence.lstrip().startswith(("", "●", "•")):
                continue
            if not is_prose_sentence(sentence):
                continue
            sentence_terms = {canonical(term) for term in significant_terms(sentence)}
            matched = topic_terms.intersection(sentence_terms)
            minimum = 1 if len(topic_terms) == 1 else 2
            if len(matched) < minimum:
                continue
            if " or " in lowered:
                left, right = lowered.split(" or ", 1)
                left_terms = {canonical(term) for term in significant_terms(left)} - {"computer", "engineering", "project", "portfolio"}
                right_terms = {canonical(term) for term in significant_terms(right)} - {"computer", "engineering", "project", "portfolio"}
                if left_terms and right_terms and not (left_terms & sentence_terms and right_terms & sentence_terms):
                    continue
            candidates.append((len(matched) / len(topic_terms), sentence.strip(), label))
    if not candidates:
        return None
    _, sentence, label = max(candidates, key=lambda candidate: candidate[0])
    return f'The retrieved source states: "{sentence}" [{label}]. The retrieved evidence does not establish the rest [{label}].'


PROSE_FUNCTION_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "can", "may", "will", "should", "to", "of",
    "in", "for", "with", "and", "or", "that", "this", "it", "they", "their", "students", "helps",
    "include", "includes", "provides", "requires", "on", "by", "as", "from",
}


def is_prose_sentence(sentence: str) -> bool:
    """Reject navigation menus, title lists, and page boilerplate scraped with a page.

    Such strings ("Home Courses Computer Science Data Science - Coming soon!")
    share topic words with a question but state nothing a student can rely on.
    """
    lowered = sentence.lower()
    if contains_any_term(lowered, ("coming soon", "skip to", "main menu", "click here", "read more", "all rights reserved")):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", sentence)
    if len(words) < 6:
        return False
    capitalized = sum(1 for word in words if word[0].isupper())
    if capitalized / len(words) > 0.5:
        return False
    return sum(1 for word in words if word.lower() in PROSE_FUNCTION_WORDS) >= 2


def is_prior_programming_experience_question(question: str) -> bool:
    q = (question or "").lower()
    asks_prior_experience = contains_any_term(
        q,
        (
            "prior programming",
            "programming experience",
            "before starting",
            "before university",
            "before i start",
            "no programming",
            "haven't programmed",
            "never programmed",
        ),
    )
    asks_ceng_or_programming = contains_any_term(q, ("computer engineering", "ceng", "programming", "coding"))
    return asks_prior_experience and asks_ceng_or_programming


def is_git_github_learning_question(question: str) -> bool:
    q = (question or "").lower()
    return contains_any_term(q, ("git", "github", "version control")) and contains_any_term(
        q,
        ("learn", "should", "need", "important", "student", "students", "use"),
    )


def is_career_jobs_question(question: str) -> bool:
    q = (question or "").lower()
    if re.match(r"\s*(?:can|could|will|should)\b", q):
        return False
    if re.search(r"\b(?:should i|can i|will i|am i)\b", q) and contains_any_term(q, ("study", "choose", "replace", "worth")):
        return False
    if contains_any_term(q, ("abroad", "overseas", "remote work", "work remotely", "work in another country", "entry-level", "entry level")):
        return False
    asks_jobs = contains_any_term(q, ("job", "jobs", "career", "careers", "work", "graduates", "graduate"))
    asks_ceng = contains_any_term(q, ("computer engineering", "computer engineer", "ceng", "ce"))
    return asks_jobs and asks_ceng


def cybersecurity_pathway_question(question: str) -> bool:
    q = (question or "").lower()
    if contains_any_term(q, ("hate electronics", "dislike electronics")) and contains_any_term(q, ("ai", "artificial intelligence")):
        return False
    return contains_any_term(q, ("cybersecurity", "cyber security", "security")) and contains_any_term(
        q,
        ("become", "specialist", "career", "path", "prepare", "learn", "skills"),
    )


def contains_any_term(text: str, terms: list[str] | tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) for term in terms)


def partially_answerable_multi_topic_question(question: str, matched_terms: set[str]) -> bool:
    """Allow broad multi-topic questions through when some retrieved topic evidence is grounded."""
    if not matched_terms:
        return False
    q = (question or "").lower()
    if "," not in q and " and " not in q and " or " not in q:
        return False
    topic_groups = [
        ("ai", "artificial intelligence", "machine learning", "gen ai"),
        ("cybersecurity", "cyber security", "security"),
        ("embedded", "embedded systems", "microcontroller", "microcontrollers"),
        ("project", "projects", "portfolio", "github"),
        ("linux", "unix", "operating system", "operating systems"),
        ("git", "github", "version control", "repository", "repositories"),
        ("hardware", "software", "systems"),
    ]
    mentioned_groups = 0
    supported_groups = 0
    for group in topic_groups:
        group_terms = set(group)
        if contains_any_term(q, group):
            mentioned_groups += 1
            if matched_terms & group_terms:
                supported_groups += 1
    return mentioned_groups >= 2 and supported_groups >= 1


def partially_answerable_multi_topic_from_results(question: str, results: list[dict[str, Any]]) -> bool:
    evidence_text = " ".join(
        str(result.get(key) or "").lower()
        for result in results[:5]
        for key in ("text", "title", "category", "section_heading")
    )
    matched_terms = {term for term in content_terms(question) if term_supported_by_evidence(term, evidence_text)}
    return partially_answerable_multi_topic_question(question, matched_terms)


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
