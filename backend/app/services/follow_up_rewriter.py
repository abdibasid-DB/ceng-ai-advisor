"""Rewrite a follow-up question into one standalone question with the local LLM.

The rewrite is used only for retrieval and as the question the answer prompt
answers; the LLM is told not to answer. When the rewrite is empty, invalid or
the LLM fails, the caller keeps the rule-based resolution from
query_understanding.
"""

from __future__ import annotations

import re
import time
from typing import Any, Protocol

from ..core.llm_config import FOLLOW_UP_REWRITE_NUM_CTX, FOLLOW_UP_REWRITE_NUM_PREDICT, LLM_SEED

REFERENCE_RE = re.compile(r"\b(?:it|that|those|what about|the first one)\b", re.IGNORECASE)
PREVIOUS_ANSWER_CHARACTERS = 400
MAX_REWRITE_WORDS = 40
PREFIX_RE = re.compile(r"^\s*(?:standalone question|rewritten question|question)\s*:\s*", re.IGNORECASE)


class Turn(Protocol):
    question: str
    answer: str


def needs_rewrite(question: str, kind: str, has_previous_turn: bool) -> bool:
    """Follow-ups, or domain questions that point back with "it", "that", "those", "what about" or "the first one"."""
    if not has_previous_turn:
        return False
    if kind == "contextual_follow_up":
        return True
    return kind == "standalone_domain_question" and bool(REFERENCE_RE.search(question or ""))


def build_rewrite_prompt(turns: list[Turn], question: str) -> str:
    lines = []
    for turn in turns[-2:]:
        lines.append(f"Student: {turn.question}")
        answer = " ".join(re.sub(r"\[S\d+\]", "", turn.answer or "").split())
        if answer:
            if len(answer) > PREVIOUS_ANSWER_CHARACTERS:
                answer = answer[: PREVIOUS_ANSWER_CHARACTERS - 3].rsplit(" ", 1)[0] + "..."
            lines.append(f"Advisor: {answer}")
    conversation = "\n".join(lines)
    return (
        "Rewrite the student's latest question as one standalone question that can be understood without the conversation. "
        'Replace words such as "it", "that", "those", "what about" or "the first one" with what they refer to. '
        "Do not answer the question. Output only the rewritten question on one line.\n\n"
        f"Conversation:\n{conversation}\n\n"
        f"Latest question: {question}\n"
        "Standalone question:"
    )


def clean_rewrite(text: str) -> str | None:
    """First line of the output, without labels or quotes; None if it does not look like one question."""
    line = next((line.strip() for line in (text or "").splitlines() if line.strip()), "")
    line = PREFIX_RE.sub("", line).strip().strip('"').strip("'").strip()
    if not line or "INSUFFICIENT" in line.upper() or re.search(r"\[S\d+\]", line):
        return None
    if len(line.split()) > MAX_REWRITE_WORDS or len(re.findall(r"[.!?](?:\s|$)", line)) > 1:
        return None
    return line


def normalize(text: str) -> str:
    return " ".join(re.findall(r"\w+", (text or "").casefold()))


# Words a rewrite may drop: references it resolves and fillers ("Is Linux important too?").
REWRITE_FILLER_WORDS = {
    "a", "an", "the", "is", "are", "am", "was", "be", "do", "does", "did", "can", "could", "should", "would", "will",
    "i", "me", "my", "you", "your", "we", "us", "our", "it", "its", "that", "this", "those", "these", "them", "they",
    "their", "what", "which",
    "how", "why", "when", "where", "who", "about", "first", "one", "too", "also", "then", "so", "and", "or", "but",
    "of", "to", "in", "on", "for", "with", "at", "by", "from", "as", "if", "any", "there", "really", "ok", "okay",
    # Generic verbs a correct paraphrase may replace ("Does it include Linux?" -> "... Linux covered ...").
    "include", "includes", "have", "has", "get", "make", "use", "go", "take", "give", "cover", "covers",
}


def content_words(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9+#]+", (text or "").casefold()) if word not in REWRITE_FILLER_WORDS}


def word_kept(word: str, rewrite_words: set[str]) -> bool:
    """"prepare" is kept by "preparing", "years" by "year"."""
    stem = word[:5] if len(word) > 5 else word.rstrip("s")
    return any(candidate.startswith(stem) for candidate in rewrite_words)


def rewrite_problem(rewrite: str, question: str, turns: list[Turn]) -> str | None:
    """Why a fluent rewrite still changes the question, or None.

    "Is Linux important too?" -> "What role does Linux play in cybersecurity?"
    drops "important"; "How can I prepare before first year?" -> "... considering
    MATH 101 and MATH 202?" imports course codes from the advisor's answer.
    """
    if normalize(rewrite) == normalize(question):
        return "rewrite left the question unchanged"
    rewrite_words = content_words(rewrite)
    dropped = sorted(word for word in content_words(question) if not word_kept(word, rewrite_words))
    if dropped:
        return f"rewrite dropped words of the question: {dropped}"
    student_text = " ".join([question, *(turn.question for turn in turns)])
    added_numbers = set(re.findall(r"\d+", rewrite)) - set(re.findall(r"\d+", student_text))
    if added_numbers:
        return f"rewrite added numbers not asked by the student: {sorted(added_numbers)}"
    return None


def rewrite_follow_up(llm_service: Any, turns: list[Turn], question: str) -> tuple[str | None, dict[str, Any]]:
    """(standalone question or None, metadata for retrieval_metadata)."""
    start = time.perf_counter()
    metadata: dict[str, Any] = {"llm_rewrite": None, "raw_output": None, "error": None}
    try:
        response = llm_service.generate(
            build_rewrite_prompt(turns, question),
            temperature=0.0,
            seed=LLM_SEED,
            num_ctx=FOLLOW_UP_REWRITE_NUM_CTX,
            num_predict=FOLLOW_UP_REWRITE_NUM_PREDICT,
        )
        metadata["raw_output"] = response.text
        rewrite = clean_rewrite(response.text)
        # A rewrite that only repeats an earlier question has dropped the new one ("Is it hard?" -> "What is CENG 303?").
        if rewrite and any(normalize(rewrite) == normalize(turn.question) for turn in turns):
            rewrite = None
            metadata["error"] = "rewrite repeated a previous question"
        problem = rewrite_problem(rewrite, question, turns) if rewrite else None
        if problem:
            rewrite = None
            metadata["error"] = problem
        metadata["llm_rewrite"] = rewrite
    except Exception as exc:
        metadata["error"] = str(exc) or exc.__class__.__name__
    metadata["seconds"] = round(time.perf_counter() - start, 3)
    return metadata["llm_rewrite"], metadata
