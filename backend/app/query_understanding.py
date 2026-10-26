"""Pre-retrieval query understanding for the Computer Engineering advisor.

This module converts raw student wording into a structured interpretation used
for classification, follow-up handling, and retrieval. It never creates factual
evidence; RAG evidence is still retrieved and validated downstream.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Literal


QueryKind = Literal[
    "standalone_domain_question",
    "contextual_follow_up",
    "source_follow_up",
    "vague_no_referent",
    "assistant_help",
    "out_of_scope_persona_meta",
    "conversational_feedback",
]


@dataclass(frozen=True)
class QueryTopic:
    name: str
    matched_terms: tuple[str, ...] = ()
    confidence: float = 1.0


@dataclass(frozen=True)
class QueryUnderstanding:
    original_question: str
    normalized_question: str
    retrieval_question: str | None
    kind: QueryKind
    topics: tuple[QueryTopic, ...] = ()
    task: str | None = None
    constraints: tuple[str, ...] = ()
    entities: tuple[str, ...] = ()
    referents: tuple[str, ...] = ()
    requires_context: bool = False
    requires_clarification: bool = False
    is_source_follow_up: bool = False
    is_persona_meta: bool = False
    is_out_of_domain: bool = False
    confidence: float = 1.0
    debug: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "original_question": self.original_question,
            "normalized_question": self.normalized_question,
            "retrieval_question": self.retrieval_question,
            "kind": self.kind,
            "topics": [
                {"name": topic.name, "matched_terms": list(topic.matched_terms), "confidence": topic.confidence}
                for topic in self.topics
            ],
            "task": self.task,
            "constraints": list(self.constraints),
            "entities": list(self.entities),
            "referents": list(self.referents),
            "requires_context": self.requires_context,
            "requires_clarification": self.requires_clarification,
            "is_source_follow_up": self.is_source_follow_up,
            "is_persona_meta": self.is_persona_meta,
            "is_out_of_domain": self.is_out_of_domain,
            "confidence": self.confidence,
            "debug": self.debug,
            "changed": self.normalized_question.lower().rstrip("?.!") != self.original_question.lower().rstrip("?.!"),
        }


@dataclass(frozen=True)
class QueryResolution:
    kind: QueryKind
    question: str
    resolved_question: str | None = None
    previous_turn: Any | None = None
    understanding: QueryUnderstanding | None = None
    normalization_metadata: dict[str, Any] | None = None
    rewrite_metadata: dict[str, Any] | None = None


TOKEN_REPLACEMENTS = {
    "u": "you",
    "ur": "your",
    "dont": "do not",
    "eng": "engineering",
    "engneering": "engineering",
    "engeneering": "engineering",
    "enginnering": "engineering",
    "enginering": "engineering",
    "enginer": "engineer",
    "enginers": "engineers",
    "engeneer": "engineer",
    "engeneers": "engineers",
    "programing": "programming",
    "programmin": "programming",
    "langauge": "language",
    "lang": "language",
    "lern": "learn",
    "lerning": "learning",
    "necessery": "necessary",
    "neccessary": "necessary",
    "algoritm": "algorithm",
    "alogrithm": "algorithm",
    "cybersec": "cybersecurity",
    "cert": "certificate",
    "certs": "certifications",
    "sofware": "software",
    "hardwere": "hardware",
    "maths": "math",
    "staj": "internship",
    # Informal / SMS-style student spelling.
    "wat": "what",
    "wats": "what is",
    "whats": "what is",
    "wht": "what",
    "hw": "how",
    "shud": "should",
    "shld": "should",
    "shoud": "should",
    "cud": "could",
    "wud": "would",
    "r": "are",
    "rly": "really",
    "pls": "please",
    "plz": "please",
    "b4": "before",
    "bc": "because",
    "cuz": "because",
    "coz": "because",
    "becuz": "because",
    "gonna": "going to",
    "wanna": "want to",
    "gotta": "have to",
    "im": "i am",
    "ive": "i have",
    "isnt": "is not",
    "doesnt": "does not",
    "cant": "cannot",
    "wont": "will not",
    "yr": "year",
    "yrs": "years",
    "uni": "university",
    "diff": "difference",
    "comp": "computer",
    "sec": "security",
    "sci": "science",
}

# Conversational filler that carries no meaning for retrieval or evidence checks.
FILLER_TOKENS = {"bro", "bruh", "dude", "lol", "lmao", "nah", "tbh", "idk", "kinda", "sorta", "pls", "plz", "please", "hey", "hi", "hello", "guys", "man", "fr"}

FUZZY_DOMAIN_TERMS = {
    "computer",
    "engineering",
    "engineer",
    "engineers",
    "programming",
    "language",
    "learn",
    "software",
    "hardware",
    "technology",
    "technologies",
    "embedded",
    "systems",
    "theoretical",
    "practical",
    "robotics",
    "robotic",
    "mechanical",
    "future",
    "curriculum",
    "course",
    "courses",
    "algorithm",
    "algorithms",
    "testing",
    "debugging",
    "debug",
    "command",
    "architecture",
    "arduino",
    "fpga",
    "iot",
    "robotics",
    "robotic",
    "sql",
    "react",
    "frontend",
    "backend",
    "calculus",
    "mathematics",
    "math",
    "artificial",
    "intelligence",
    "specialization",
    "internship",
    "internships",
    "career",
    "cybersecurity",
    "cybersec",
    "hacking",
    "certificate",
    "certification",
    "certifications",
    "difficult",
    "hard",
    "elective",
    "electives",
    "erasmus",
    "laptop",
    "interview",
    "interviews",
    "cv",
    "gpa",
    "projects",
    "skills",
    "freelancing",
    "freelance",
    "senior",
    "open",
    "source",
    "linux",
    "unix",
    "regulation",
    "regulations",
    "exams",
    "grading",
    "clubs",
    "communities",
    "difference",
    "different",
    "between",
    "important",
    "importance",
    "structures",
    "structure",
    "electronics",
    "digital",
    "logic",
    "learning",
    "machine",
    "security",
    "network",
    "networks",
    "database",
    "databases",
    "operating",
    "development",
    "university",
    "graduate",
    "graduates",
    "experience",
    "portfolio",
    "semester",
    "project",
    "physics",
    "probability",
    "statistics",
    "calculus",
    "electrical",
    "science",
    "student",
    "students",
}

DOMAIN_TERMS = (
    "computer engineering",
    "computer engineer",
    "computer engineers",
    "ceng",
    "ce",
    "programming",
    "programmer",
    "programmers",
    "python",
    "java",
    "javascript",
    "c++",
    "coding",
    "algorithm",
    "algorithms",
    "data structures",
    "software",
    "frontend",
    "backend",
    "web development",
    "mobile development",
    "database",
    "databases",
    "sql",
    "react",
    "testing",
    "debugging",
    "debug",
    "hardware",
    "computer architecture",
    "architecture",
    "arduino",
    "fpga",
    "microcontroller",
    "microcontrollers",
    "iot",
    "technology",
    "technologies",
    "embedded",
    "systems",
    "curriculum",
    "course",
    "courses",
    "class",
    "classes",
    "elective",
    "electives",
    "lab",
    "labs",
    "calculus",
    "mathematics",
    "math",
    "ai",
    "artificial intelligence",
    "data science",
    "future technologies",
    "future technology",
    "robotics",
    "linux",
    "unix",
    "operating system",
    "operating systems",
    "specialization",
    "internship",
    "internships",
    "career",
    "academic staff",
    "faculty",
    "tuition",
    "fee",
    "fees",
    "scholarship",
    "regulation",
    "regulations",
    "exam",
    "exams",
    "grading",
    "deadline",
    "quota",
    "job",
    "jobs",
    "salary",
    "gpa",
    "project",
    "projects",
    "portfolio",
    "skill",
    "skills",
    "cv",
    "interview",
    "interviews",
    "cybersecurity",
    "cybersec",
    "ethical hacking",
    "hacking",
    "certificate",
    "certification",
    "certifications",
    "work abroad",
    "remote work",
    "startup",
    "freelancing",
    "freelance",
    "open source",
    "senior engineer",
    "club",
    "clubs",
    "student club",
    "student clubs",
    "student community",
    "student communities",
    "social club",
    "social clubs",
    "community",
    "communities",
    "stress",
    "master",
    "graduate",
    "masters",
    "academia",
    "english",
    "program in english",
    "english program",
    "academic",
    "staff",
    "professor",
    "professors",
    "erasmus",
    "study abroad",
    "laptop",
    "ostim",
)

TOPIC_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("computer_engineering", ("computer engineering", "computer engineer", "computer engineers", "ceng")),
    ("definition", ("definition", "meaning", "what is", "explain")),
    ("curriculum", ("curriculum", "course", "courses", "class", "classes", "semester", "theoretical", "practical")),
    ("electives", ("elective", "electives", "choose")),
    ("programming", ("programming", "language", "python", "java", "c++", "coding", "algorithm", "algorithms", "data structures")),
    ("operating_systems", ("linux", "unix", "operating system", "operating systems")),
    ("mathematics", ("math", "mathematics", "calculus")),
    ("hardware", ("hardware", "embedded", "systems", "electronics", "computer architecture", "architecture", "arduino", "fpga", "microcontroller", "microcontrollers", "iot", "robotics")),
    ("software", ("software", "web", "mobile", "frontend", "backend", "web development", "mobile development", "database", "databases", "sql", "react", "testing", "debugging", "debug", "command line", "cli")),
    ("ai", ("ai", "artificial intelligence", "machine learning")),
    ("future_technologies", ("future technology", "future technologies", "future", "robotics")),
    ("cybersecurity", ("cybersecurity", "cyber security", "cybersec", "security", "ethical hacking", "hacking", "certificate", "certification", "certifications")),
    ("internships", ("internship", "internships")),
    ("gpa", ("gpa", "grade", "grades")),
    ("projects", ("project", "projects", "portfolio", "github", "open source", "hackathon", "hackathons", "coding competition", "coding competitions")),
    ("skills", ("skill", "skills", "technical skills", "professional skills")),
    ("cv", ("cv", "resume")),
    ("interviews", ("interview", "interviews")),
    ("erasmus", ("erasmus", "exchange", "study abroad")),
    ("laptop", ("laptop", "computer to buy")),
    ("career", ("career", "job", "jobs", "employment", "work", "senior engineer", "freelancing", "freelance")),
    ("remote_work", ("remote", "hybrid", "digital nomad")),
    ("work_life_balance", ("work-life", "work life", "balance", "stress")),
    ("entrepreneurship", ("startup", "company", "entrepreneur")),
    ("academic_regulations", ("regulation", "regulations", "exam", "exams", "grading", "attendance", "attendance rule")),
    ("academic_staff", ("academic staff", "faculty", "professor", "professors")),
    ("graduate_studies", ("master", "master's", "masters", "graduate school", "phd", "academia")),
    ("salary", ("salary", "salaries", "pay", "wage")),
    ("scholarship", ("scholarship", "scholarships")),
    ("department_information", ("program in english", "english program", "language of instruction")),
    ("student_life", ("club", "clubs", "student club", "student clubs", "student community", "student communities", "social club", "social clubs", "community", "communities", "hackathon", "hackathons", "competition", "competitions")),
)

CONSTRAINT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("low_gpa", ("low gpa", "bad gpa", "weak gpa")),
    ("no_internship", ("no internship", "do not have internship", "dont have internship", "without internship")),
    ("first_year", ("first year", "freshman", "beginner")),
    ("before_starting", ("before starting", "before university")),
    ("turkey", ("turkey", "turkiye", "turkish")),
    ("ostim", ("ostim",)),
)

SOURCE_TERMS = {"source", "sources", "citation", "citations", "cite", "cited", "reference", "references", "evidence", "proof"}
REFERENTIAL_TERMS = {"information", "answer", "that", "this", "claim", "it", "those", "these"}
ASSISTANT_REFERENCES = {"you", "your", "yourself", "advisor", "chatbot", "bot", "assistant", "name"}
ORIGIN_ACTIONS = {"made", "make", "created", "create", "built", "build", "developed", "develop", "designed", "design"}


def resolve_query(question: str, previous_turn: Any | None) -> QueryResolution:
    cleaned = " ".join((question or "").split())
    understanding = understand_query(cleaned, previous_turn=previous_turn)
    if understanding.kind == "contextual_follow_up" and previous_turn and understanding.retrieval_question is None:
        resolved = resolve_follow_up_question(understanding.normalized_question, previous_turn)
    else:
        resolved = understanding.retrieval_question
    return QueryResolution(
        understanding.kind,
        cleaned,
        resolved_question=resolved,
        previous_turn=previous_turn if understanding.kind == "contextual_follow_up" else None,
        understanding=understanding,
        normalization_metadata=understanding.to_metadata(),
    )


def understand_query(question: str, previous_turn: Any | None = None) -> QueryUnderstanding:
    cleaned = " ".join((question or "").split())
    normalized, debug = normalize_question_text(cleaned)
    tokens = tokenize_for_resolution(normalized)
    text = normalized_question(normalized)
    topics = extract_topics(text)
    constraints = extract_constraints(text)
    entities = extract_entities(text, topics)
    referents = extract_referents(tokens)
    task = infer_task(text, tokens)
    correction = extract_correction_request(cleaned)

    feedback = conversational_feedback_type(cleaned)
    if feedback:
        return QueryUnderstanding(
            original_question=cleaned,
            normalized_question=normalized,
            retrieval_question=None,
            kind="conversational_feedback",
            task=feedback,
            confidence=0.97,
            debug=debug,
        )

    if correction:
        normalized_correction, correction_debug = normalize_question_text(correction)
        correction_topics = extract_topics(normalized_question(normalized_correction))
        return QueryUnderstanding(
            original_question=cleaned,
            normalized_question=normalized_correction,
            retrieval_question=build_retrieval_question(normalized_correction, correction_topics, constraints),
            kind="contextual_follow_up" if previous_turn else "standalone_domain_question",
            topics=correction_topics,
            task=task,
            constraints=constraints,
            entities=extract_entities(normalized_question(normalized_correction), correction_topics),
            confidence=0.9,
            debug={**debug, "correction": correction_debug},
        )

    source_follow_up = is_source_follow_up_text(text, tokens)
    if source_follow_up:
        return QueryUnderstanding(
            original_question=cleaned,
            normalized_question=normalized,
            retrieval_question=None,
            kind="source_follow_up" if previous_turn else "vague_no_referent",
            topics=topics,
            task="source_request",
            constraints=constraints,
            entities=entities,
            referents=referents,
            requires_context=not bool(previous_turn),
            requires_clarification=not bool(previous_turn),
            is_source_follow_up=True,
            confidence=0.98,
            debug=debug,
        )

    if is_assistant_help_text(tokens):
        return QueryUnderstanding(
            original_question=cleaned,
            normalized_question=normalized,
            retrieval_question=None,
            kind="assistant_help",
            task="assistant_help",
            is_persona_meta=True,
            confidence=0.98,
            debug=debug,
        )

    persona_meta = is_persona_or_meta_text(text, tokens)
    if persona_meta:
        return QueryUnderstanding(
            original_question=cleaned,
            normalized_question=normalized,
            retrieval_question=None,
            kind="out_of_scope_persona_meta",
            topics=topics,
            task="persona_meta",
            constraints=constraints,
            entities=entities,
            is_persona_meta=True,
            is_out_of_domain=True,
            confidence=0.95,
            debug=debug,
        )

    external_task = is_external_or_unsupported_task_text(text, tokens)
    if external_task:
        return QueryUnderstanding(
            original_question=cleaned,
            normalized_question=normalized,
            retrieval_question=None,
            kind="out_of_scope_persona_meta",
            topics=topics,
            task="external_or_unsupported_task",
            constraints=constraints,
            entities=entities,
            is_out_of_domain=True,
            confidence=0.94,
            debug={**debug, "external_task": True},
        )

    context_dependent = is_context_dependent_follow_up_text(text, tokens)
    contextual_skill_follow_up = is_contextual_skill_follow_up_text(text, tokens)
    contextual_advice_follow_up = is_contextual_advice_follow_up_text(text, tokens)
    contextual_project_follow_up = is_contextual_project_follow_up_text(text, tokens)
    domain_topics = tuple(topic for topic in topics if topic.name != "definition")
    domain = has_domain_anchor(text) or bool(domain_topics)
    if contextual_skill_follow_up and previous_turn and previous_turn_has_domain_context(previous_turn):
        return QueryUnderstanding(
            original_question=cleaned,
            normalized_question=normalized,
            retrieval_question=None,
            kind="contextual_follow_up",
            topics=topics,
            task=task,
            constraints=constraints,
            entities=entities,
            referents=referents,
            requires_context=True,
            confidence=0.84,
            debug={**debug, "contextual_skill_follow_up": True},
        )
    if contextual_advice_follow_up and previous_turn and previous_turn_has_domain_context(previous_turn):
        return QueryUnderstanding(
            original_question=cleaned,
            normalized_question=normalized,
            retrieval_question=None,
            kind="contextual_follow_up",
            topics=topics,
            task=task,
            constraints=constraints,
            entities=entities,
            referents=referents,
            requires_context=True,
            confidence=0.83,
            debug={**debug, "contextual_advice_follow_up": True},
        )
    if contextual_project_follow_up and previous_turn and previous_turn_has_domain_context(previous_turn):
        return QueryUnderstanding(
            original_question=cleaned,
            normalized_question=normalized,
            retrieval_question=None,
            kind="contextual_follow_up",
            topics=topics,
            task=task,
            constraints=constraints,
            entities=entities,
            referents=referents,
            requires_context=True,
            confidence=0.83,
            debug={**debug, "contextual_project_follow_up": True},
        )
    if (
        not context_dependent
        and previous_turn
        and previous_turn_has_domain_context(previous_turn)
        and (
            is_additive_follow_up_text(text, tokens)
            or is_pronoun_follow_up_with_generic_anchor(text, tokens, topics)
            or referenced_answer_item(normalized, getattr(previous_turn, "answer", "") or "")
            or (asks_for_elaboration(normalized) and not domain_topics)
        )
    ):
        context_dependent = True
    if context_dependent and previous_turn:
        return QueryUnderstanding(
            original_question=cleaned,
            normalized_question=normalized,
            retrieval_question=None,
            kind="contextual_follow_up",
            topics=topics,
            task=task,
            constraints=constraints,
            entities=entities,
            referents=referents,
            requires_context=True,
            confidence=0.85,
            debug=debug,
        )
    if context_dependent and not domain:
        return QueryUnderstanding(
            original_question=cleaned,
            normalized_question=normalized,
            retrieval_question=None,
            kind="vague_no_referent",
            topics=topics,
            task=task,
            constraints=constraints,
            entities=entities,
            referents=referents,
            requires_context=True,
            requires_clarification=True,
            confidence=0.8,
            debug=debug,
        )
    if domain:
        retrieval_question = build_retrieval_question(normalized, topics, constraints)
        return QueryUnderstanding(
            original_question=cleaned,
            normalized_question=normalized,
            retrieval_question=retrieval_question,
            kind="standalone_domain_question",
            topics=topics,
            task=task,
            constraints=constraints,
            entities=entities,
            referents=referents,
            confidence=0.86 if not topics else 0.92,
            debug=debug,
        )
    return QueryUnderstanding(
        original_question=cleaned,
        normalized_question=normalized,
        retrieval_question=None,
        kind="out_of_scope_persona_meta",
        topics=topics,
        task=task,
        constraints=constraints,
        entities=entities,
        is_out_of_domain=True,
        confidence=0.9,
        debug=debug,
    )


def normalize_question_text(question: str) -> tuple[str, dict[str, Any]]:
    cleaned = " ".join((question or "").split())
    lowered = normalized_question(cleaned)
    phrase_normalized = lowered
    phrase_replacements = {
        r"\bcomp\s+eng\b": "computer engineering",
        r"\bcomputer\s+eng\b": "computer engineering",
        r"\bcomputer\s+engg\b": "computer engineering",
        r"\bgit\s+hub\b": "github",
        r"\bopen\s+source\b": "open source",
        r"\bcommand\s+line\b": "command line",
        r"\bcomputer\s+engeneering\b": "computer engineering",
        r"\bcomputer\s+engneering\b": "computer engineering",
        r"\bcomputer\s+enginnering\b": "computer engineering",
        r"\bcyber\s+sec\b": "cybersecurity",
        r"\bcyber\s+security\b": "cybersecurity",
        r"\bostimtech\b": "ostim technical university",
        r"\bceng\b": "computer engineering",
    }
    replacements: list[dict[str, str]] = []
    for pattern, replacement in phrase_replacements.items():
        updated = re.sub(pattern, replacement, phrase_normalized)
        if updated != phrase_normalized:
            replacements.append({"from": pattern, "to": replacement})
            phrase_normalized = updated

    tokens = tokenize_for_resolution(phrase_normalized)
    normalized_tokens = normalize_domain_tokens(tokens)
    normalized_text = readable_question(" ".join(normalized_tokens))
    return normalized_text, {
        "token_count": len(tokens),
        "replacements": replacements,
        "normalized_tokens": normalized_tokens,
        "changed": normalized_text.lower().rstrip("?.!") != cleaned.lower().rstrip("?.!"),
    }


def tokenize_for_resolution(text: str) -> list[str]:
    return re.findall(r"[a-z0-9+#]+", text.lower())


def normalize_domain_tokens(tokens: list[str]) -> list[str]:
    normalized: list[str] = []
    for index, token in enumerate(tokens):
        if token == "eng" and index > 0 and tokens[index - 1] in {"computer", "comp"}:
            normalized.append("engineering")
            continue
        if token in FILLER_TOKENS and len(tokens) > 2:
            continue
        replacement = TOKEN_REPLACEMENTS.get(token)
        if replacement:
            normalized.extend(replacement.split())
            continue
        normalized.append(fuzzy_domain_token(token))
    return normalized


def fuzzy_domain_token(token: str) -> str:
    if len(token) < 6 or token in FUZZY_DOMAIN_TERMS:
        return token
    # Real inflections ("developed", "graduated") are not spelling mistakes.
    stems = FUZZY_DOMAIN_TERMS | {term[:-1] for term in FUZZY_DOMAIN_TERMS if term.endswith("e")}
    if any(token.endswith(suffix) and token[: -len(suffix)] in stems for suffix in ("ed", "d", "ing", "s", "es")):
        return token
    best_term = token
    best_score = 0.0
    for term in FUZZY_DOMAIN_TERMS:
        if abs(len(term) - len(token)) > 3:
            continue
        score = SequenceMatcher(None, token, term).ratio()
        if score > best_score:
            best_score = score
            best_term = term
    # Longer words tolerate one more dropped letter ("languges" -> "language").
    if best_score >= (0.85 if len(token) >= 8 else 0.88):
        return best_term
    return token


def readable_question(text: str) -> str:
    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        return ""
    replacements = {
        " i ": " I ",
        " ai ": " AI ",
        " gpa ": " GPA ",
        " cv ": " CV ",
        " ce ": " CE ",
        " cs ": " CS ",
    }
    rendered = f" {cleaned} "
    for needle, replacement in replacements.items():
        rendered = rendered.replace(needle, replacement)
    rendered = rendered.strip()
    # Drop a dangling "or" left after conversational filler such as "or nah".
    rendered = re.sub(r"\s+or[?.!]*$", "", rendered)
    if rendered.startswith(("what ", "why ", "how ", "which ", "where ", "when ", "is ", "does ", "do ", "can ", "who ")):
        rendered = rendered[0].upper() + rendered[1:]
    if not rendered.endswith("?"):
        rendered += "?"
    return rendered


def extract_topics(text: str) -> tuple[QueryTopic, ...]:
    found: list[QueryTopic] = []
    for topic_name, patterns in TOPIC_PATTERNS:
        matched = tuple(pattern for pattern in patterns if contains_phrase(text, pattern))
        if topic_name == "student_life" and matched and not is_student_life_domain_text(text):
            continue
        if matched:
            found.append(QueryTopic(topic_name, matched_terms=matched, confidence=1.0))
    return tuple(found)


def is_student_life_domain_text(text: str) -> bool:
    return any(
        contains_phrase(text, term)
        for term in (
            "ostim",
            "university",
            "student",
            "students",
            "student club",
            "student clubs",
            "student community",
            "student communities",
        )
    )


def extract_constraints(text: str) -> tuple[str, ...]:
    constraints = []
    for name, patterns in CONSTRAINT_PATTERNS:
        if any(contains_phrase(text, pattern) for pattern in patterns):
            constraints.append(name)
    tokens = set(tokenize_for_resolution(text))
    if {"gpa", "low"}.issubset(tokens):
        constraints.append("low_gpa")
    return tuple(dict.fromkeys(constraints))


def extract_entities(text: str, topics: tuple[QueryTopic, ...]) -> tuple[str, ...]:
    entities = [topic.name for topic in topics if topic.name not in {"definition"}]
    if contains_phrase(text, "ostim"):
        entities.append("OSTIM Technical University")
    if contains_phrase(text, "turkey") or contains_phrase(text, "turkiye"):
        entities.append("Turkey")
    return tuple(dict.fromkeys(entities))


def extract_referents(tokens: list[str]) -> tuple[str, ...]:
    return tuple(token for token in tokens if token in {"it", "this", "that", "those", "these", "they", "them", "one", "ones"})


def infer_task(text: str, tokens: list[str]) -> str | None:
    if any(token in tokens for token in {"what", "explain", "definition", "meaning"}):
        return "explain"
    if any(token in tokens for token in {"which", "choose", "start"}):
        return "recommend"
    if any(token in tokens for token in {"can", "could", "is", "do", "does", "should"}):
        return "assess"
    if contains_phrase(text, "source") or contains_phrase(text, "citation"):
        return "source_request"
    return None


def build_retrieval_question(
    normalized_question_text: str,
    topics: tuple[QueryTopic, ...],
    constraints: tuple[str, ...],
) -> str:
    topic_names = [topic.name for topic in topics if topic.name not in {"computer_engineering", "definition"}]
    # "Do I need discrete math for software and algorithms?" names more than
    # the amount of mathematics; the generic canonical question would drop it.
    specific = bool(set(topic_names) - {"mathematics"})
    base = normalize_special_case_question(normalized_question_text, specific_math_question=specific)
    if is_compatibility_canonical_question(normalized_question_text, specific_math_question=specific):
        return base
    extras: list[str] = []
    if "computer_engineering" not in {topic.name for topic in topics} and topic_names:
        extras.append("Computer Engineering")
    if len(topic_names) >= 2:
        extras.append("topics: " + ", ".join(topic_names))
    if constraints:
        extras.append("constraints: " + ", ".join(constraints))
    if extras:
        return f"{base} ({'; '.join(extras)})"
    return base


def normalize_special_case_question(question: str, specific_math_question: bool = False) -> str:
    text = normalized_question(question).rstrip("?.!")
    tokens = tokenize_for_resolution(text)
    has_ce = "computer" in tokens and "engineering" in tokens
    has_engineer = "computer" in tokens and "engineer" in tokens
    asks_comparison = contains_phrase(text, "difference between") or contains_phrase(text, "different from")
    comparison_targets = {
        "it",
        "information",
        "technology",
        "science",
        "software",
        "engineering",
        "cs",
        "se",
    }
    if has_ce and asks_comparison and comparison_targets & set(tokens):
        return readable_question(text)
    if has_ce and "definition" in tokens:
        return "What is the definition of Computer Engineering?"
    if has_ce and "definition" not in tokens and (
        asks_what_computer_engineering_is(text) or "what computer engineering mean" in text or "explain computer engineering" in text
    ):
        return "What is Computer Engineering?"
    if has_engineer and "do" in tokens:
        return "What does a Computer Engineer do?"
    if has_ce and any(term in tokens for term in ("hard", "difficult")):
        return "Is Computer Engineering difficult?"
    if "programming" in tokens and ("language" in tokens or "languages" in tokens) and any(term in tokens for term in ("start", "first")):
        return "Which programming language should I learn first?"
    if "programming" in tokens and ("language" in tokens or "languages" in tokens) and "learn" in tokens:
        return "What programming languages should I learn?"
    if "ai" in tokens and "work" in tokens and has_ce:
        return "Can I work in AI after studying Computer Engineering?"
    if "linux" in tokens or "unix" in tokens or ("operating" in tokens and ("system" in tokens or "systems" in tokens)):
        return readable_question(text)
    if any(term in tokens for term in ("regulation", "regulations", "exam", "exams", "grading")):
        return readable_question(text)
    if any(term in tokens for term in ("club", "clubs", "community", "communities")):
        return readable_question(text)
    if (
        not specific_math_question
        and any(term in tokens for term in ("math", "mathematics", "calculus"))
        and any(term in tokens for term in ("need", "required", "much"))
    ):
        return "How much mathematics is required in Computer Engineering?"
    if "work" in tokens and "life" in tokens and "balance" in tokens and (has_ce or "engineers" in tokens):
        return "Do Computer Engineers have a good work-life balance?"
    return readable_question(text)


def asks_what_computer_engineering_is(text: str) -> bool:
    """Only "what is (a/the) computer engineering ..." is a definition request.

    "What is the exact placement rate of computer engineering graduates?" must
    not be rewritten into the definition question.
    """
    return re.match(r"what(?: is|'s| exactly is)\s+(?:a\s+|the\s+)?computer engineering\b", text) is not None


def is_compatibility_canonical_question(question: str, specific_math_question: bool = False) -> bool:
    text = normalized_question(question).rstrip("?.!")
    tokens = tokenize_for_resolution(text)
    has_ce = "computer" in tokens and "engineering" in tokens
    has_engineer = "computer" in tokens and "engineer" in tokens
    return (
        (has_ce and "definition" in tokens)
        or
        (has_ce and "definition" not in tokens and (asks_what_computer_engineering_is(text) or "what computer engineering mean" in text))
        or (has_engineer and "do" in tokens)
        or (has_ce and any(term in tokens for term in ("hard", "difficult")))
        or ("programming" in tokens and ("language" in tokens or "languages" in tokens) and any(term in tokens for term in ("learn", "start", "first")))
        or ("ai" in tokens and "work" in tokens and has_ce)
        or (
            not specific_math_question
            and any(term in tokens for term in ("math", "mathematics", "calculus"))
            and any(term in tokens for term in ("need", "required", "much"))
        )
        or ("work" in tokens and "life" in tokens and "balance" in tokens and (has_ce or "engineers" in tokens))
    )


def is_source_follow_up_text(text: str, tokens: list[str]) -> bool:
    asks_origin = any(
        phrase in text
        for phrase in (
            "where did",
            "where do",
            "where is",
            "where are",
            "where was",
            "what did you base",
            "what is this based",
            "what are you basing",
            "how do you know",
        )
    )
    refers_to_previous = any(term in tokens for term in REFERENTIAL_TERMS) or any(
        phrase in text for phrase in ("your answer", "previous answer", "that information", "this information", "used for")
    )
    asks_for_sources = any(term in tokens for term in SOURCE_TERMS)
    return (asks_origin and refers_to_previous) or (asks_for_sources and refers_to_previous) or (
        asks_for_sources and len(tokens) <= 5 and not has_domain_anchor(text)
    )


FEEDBACK_LEADING_WORDS = {"no", "nope", "nah", "but", "and", "so", "well", "oh", "um", "uh", "hmm", "hey", "sorry", "actually", "bro", "dude", "man", "lol", "ok", "okay"}
FEEDBACK_TRAILING_WORDS = {"bro", "dude", "man", "lol", "though", "tho", "sorry", "again", "here"}
ACKNOWLEDGEMENT_WORDS = {
    "ok", "okay", "k", "kk", "alright", "fine", "sure", "cool", "great", "nice", "good", "perfect", "awesome", "wow",
    "yes", "yeah", "yep", "thanks", "thank", "thx", "ty", "cheers", "got", "it", "understood", "you", "a", "lot", "so",
    "much", "very", "bye", "goodbye",
}
ACKNOWLEDGEMENT_FILLER_WORDS = {"it", "you", "a", "lot", "so", "much", "very"}


def conversational_feedback_type(question: str) -> str | None:
    """"complaint" or "acknowledgement" for messages that are not questions, else None.

    Only whole messages match, so "that's wrong, what about salaries?" and
    "no, I meant internships" still go through the normal resolution.
    """
    text = re.sub(r"['’`]", "", (question or "").lower())
    tokens = [TOKEN_REPLACEMENTS.get(token, token) for token in re.findall(r"[a-z0-9]+", text)]
    tokens = " ".join(tokens).split()
    while tokens and tokens[0] in FEEDBACK_LEADING_WORDS and len(tokens) > 1:
        tokens = tokens[1:]
    while tokens and tokens[-1] in FEEDBACK_TRAILING_WORDS and len(tokens) > 1:
        tokens = tokens[:-1]
    if not tokens:
        return None
    text = " ".join(tokens)

    asked = r"(?:asked|meant|wanted|was asking|was asking about|asked for|asked about|wanted to know)"
    subject = r"(?:that|this|it|thats|its|your answer|the answer|that answer|this answer)(?: is| was| s)?"
    complaints = (
        r"no|nope|nah|wrong|incorrect|not (?:right|correct|true|helpful)",
        r"(?:i )?(?:did not|didnt|never|do not|dont) (?:ask|asked|mean|meant|want|wanted)"
        r"(?: (?:you )?(?:that|this|for that|for this|about that|about this|that one|this one))?(?: question)?",
        rf"{subject} (?:not )?(?:wrong|incorrect|right|correct|true|helpful|relevant|irrelevant|off topic)(?: answer)?",
        rf"{subject} not (?:what i {asked}|my question|the question i asked|an answer to my question|what i was looking for)",
        rf"not (?:what i {asked}|my question|the question i asked|what i was looking for)",
        r"wrong (?:answer|question|topic)",
        r"(?:you are|youre) wrong|you misunderstood(?: me| my question| the question)?|you got (?:it|that) wrong",
        r"(?:you|that|this|it) (?:did not|didnt|does not|doesnt) answer (?:my|the) question",
        r"you answered (?:the |a )?(?:wrong|different) question|i asked (?:something else|a different question)",
    )
    if any(re.fullmatch(pattern, text) for pattern in complaints):
        return "complaint"
    if set(tokens) <= ACKNOWLEDGEMENT_WORDS and not set(tokens) <= ACKNOWLEDGEMENT_FILLER_WORDS:
        return "acknowledgement"
    return None


def is_assistant_help_text(tokens: list[str]) -> bool:
    """Recognize requests for orientation, without matching unrelated tasks.

    Full matches keep "can you help me with pizza" and domain questions such
    as "what can you tell me about internships" out of this shortcut.
    """
    text = " ".join(tokens)
    assistant = r"(?:you|this (?:advisor|assistant|chatbot)|the (?:advisor|assistant|chatbot))"
    patterns = (
        rf"(?:who|what) (?:are|is) {assistant}",
        r"what (?:is|s) your (?:name|role|purpose)",
        r"what (?:can|could|do) you (?:do|help(?: me| us| students)? with|answer)",
        r"what (?:questions |topics )?(?:can|could|should|do) (?:i|we|students|prospective students) ask you(?: about)?",
        r"what (?:questions|topics) (?:can|do) you (?:answer|cover|help with)",
        rf"how (?:do|does) {assistant} work",
        r"tell me about yourself",
        r"can you help(?: me| us)?",
        r"help(?: me)?",
    )
    return any(re.fullmatch(pattern, text) for pattern in patterns)


def is_persona_or_meta_text(text: str, tokens: list[str]) -> bool:
    if not tokens:
        return False
    asks_origin = any(token in ORIGIN_ACTIONS for token in tokens) or any(
        phrase in text
        for phrase in (
            "who made",
            "who created",
            "who built",
            "who developed",
            "what is your name",
            "who are you",
            "what can you do",
            "what do you do",
        )
    )
    refers_to_assistant = any(token in ASSISTANT_REFERENCES for token in tokens)
    return refers_to_assistant and asks_origin


def is_external_or_unsupported_task_text(text: str, tokens: list[str]) -> bool:
    if not tokens:
        return False
    if contains_phrase(text, "write my") and contains_phrase(text, "report"):
        return True
    # Doing graded work for the student is outside an advisor's role,
    # whatever the subject ("write my Python homework", "solve my assignment").
    if re.search(
        r"\b(?:write|do|solve|complete|finish|make)\s+(?:my|our|this|the)\s+(?:\w+\s+){0,2}"
        r"(?:homework|assignment|assignments|essay|exam|quiz|lab report|thesis)\b",
        text,
    ):
        return True
    if contains_phrase(text, "exchange rate") or contains_phrase(text, "current exchange"):
        return True
    if contains_phrase(text, "best laptop deal") or (contains_phrase(text, "deal today") and "laptop" in tokens):
        return True
    if "translate" in tokens and ("contract" in tokens or "legal" in tokens):
        return True
    return False


def is_context_dependent_follow_up_text(text: str, tokens: list[str]) -> bool:
    if not tokens:
        return False
    if extract_correction_request(text):
        return True
    if text.startswith(("what about ", "how about ", "and ", "or ", "but ", "which one", "what courses does ")):
        return True
    if has_domain_anchor(text):
        return False
    if len(tokens) <= 3 and tokens[0] in {"why", "how", "which", "what"}:
        return True
    if any(token in {"it", "this", "that", "those", "these", "they", "them", "one", "ones"} for token in tokens):
        return True
    return False


def is_contextual_advice_follow_up_text(text: str, tokens: list[str]) -> bool:
    if has_non_skill_domain_anchor(text):
        return False
    if any(phrase in text for phrase in ("before first year", "before university", "prepare before")):
        return True
    if len(tokens) <= 7 and any(token in tokens for token in {"prepare", "start", "learn", "improve", "prioritize"}):
        return True
    return False


def is_contextual_skill_follow_up_text(text: str, tokens: list[str]) -> bool:
    if not tokens:
        return False
    if not contains_phrase(text, "skill") and not contains_phrase(text, "skills"):
        return False
    if has_non_skill_domain_anchor(text):
        return False
    return any(token in tokens for token in {"what", "which", "build", "develop", "learn", "improve", "need", "should"})


def is_contextual_project_follow_up_text(text: str, tokens: list[str]) -> bool:
    if len(tokens) > 9 or not any(token in tokens for token in {"project", "projects"}):
        return False
    if any(contains_phrase(text, term) for term in ("hardware", "software", "embedded", "robotics", "cybersecurity", "ai", "portfolio")):
        return False
    return any(token in tokens for token in {"what", "which", "should", "they", "them", "those"})


def normalized_question(question: str) -> str:
    return " ".join((question or "").lower().split())


def extract_correction_request(question: str) -> str | None:
    text = " ".join((question or "").split()).strip()
    lowered = text.lower()
    markers = (
        "i asked you ",
        "i asked ",
        "i am asking ",
        "i'm asking ",
        "i meant ",
        "what i mean is ",
    )
    for marker in markers:
        index = lowered.rfind(marker)
        if index >= 0:
            requested = text[index + len(marker) :].strip(" .?!")
            return normalize_requested_question(requested)
    return None


def normalize_requested_question(requested: str) -> str | None:
    cleaned = " ".join((requested or "").split()).strip(" .?!")
    if not cleaned:
        return None
    lowered = cleaned.lower()
    if lowered.startswith("the "):
        cleaned = cleaned[4:]
        lowered = cleaned.lower()
    if "definition of computer engineering" in lowered:
        return "What is the definition of Computer Engineering?"
    if lowered.startswith(("definition of ", "meaning of ")):
        return f"What is the {cleaned}?"
    if lowered.startswith(("what ", "why ", "how ", "which ", "where ", "when ", "is ", "does ", "do ", "can ")):
        return cleaned[0].upper() + cleaned[1:] + "?"
    return cleaned[0].upper() + cleaned[1:] + "?"


def has_domain_anchor(text: str) -> bool:
    student_life_terms = {
        "club",
        "clubs",
        "student club",
        "student clubs",
        "student community",
        "student communities",
        "social club",
        "social clubs",
        "community",
        "communities",
    }
    for term in DOMAIN_TERMS:
        if term in student_life_terms and not is_student_life_domain_text(text):
            continue
        if contains_phrase(text, term):
            return True
    return False


def has_non_skill_domain_anchor(text: str) -> bool:
    return any(contains_phrase(text, term) for term in DOMAIN_TERMS if term not in {"skill", "skills"})


def previous_turn_has_domain_context(previous_turn: Any) -> bool:
    previous_question = normalized_question(getattr(previous_turn, "question", ""))
    if has_domain_anchor(previous_question):
        return True
    return any(topic.name != "definition" for topic in extract_topics(previous_question))


ORDINAL_POSITIONS = {
    "first": 0,
    "1st": 0,
    "second": 1,
    "2nd": 1,
    "third": 2,
    "3rd": 2,
    "fourth": 3,
    "4th": 3,
    "fifth": 4,
    "5th": 4,
    "last": -1,
    "final": -1,
}
ANSWER_ITEM_NOUNS = (
    "one", "point", "item", "thing", "skill", "option", "step", "reason", "part",
    "example", "suggestion", "tip", "area", "language", "course", "project", "path", "job", "role",
)
ELABORATION_PHRASES = (
    "explain more",
    "explain that",
    "explain this",
    "explain it",
    "more detail",
    "more details",
    "in detail",
    "elaborate",
    "tell me more",
    "expand on",
    "go deeper",
    "say more",
)
# Topics that describe what is being asked about rather than naming the subject,
# so "what jobs use it?" still needs the previous turn to know what "it" is.
GENERIC_FOLLOW_UP_TOPICS = {
    "career", "skills", "curriculum", "projects", "internships", "salary", "cv", "interviews",
    "remote_work", "work_life_balance", "definition", "electives", "gpa",
}
PRONOUN_REFERENTS = {"it", "this", "that", "those", "these", "they", "them"}


def answer_items(answer: str) -> list[str]:
    """Split a previous validated answer into the items a student may point at."""
    text = re.sub(r"\[S\d+\]", "", answer or "")
    text = re.split(r"\n\s*USED_SOURCES\b", text, maxsplit=1)[0]
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    bullets = [re.sub(r"^(?:[-*•]|\d+[.)])\s*", "", line) for line in lines if re.match(r"^(?:[-*•]|\d+[.)])\s+", line)]
    if len(bullets) >= 2:
        return [clean_answer_item(item) for item in bullets if clean_answer_item(item)]
    flat = " ".join(text.split())
    sentences = re.split(r"(?<=[.!?])\s+", flat)
    # Only an enumeration in the opening sentence is "the list" a student points
    # at; a list buried in a later sentence is detail, not the answer's items.
    enumeration = re.search(
        r"(?:such as|including|include|includes|like|are|:)\s+([^.;:]+?,[^.;:]+?(?:,?\s+(?:and|or)\s+[^.;:]+))[.;]",
        sentences[0] if sentences else "",
        flags=re.IGNORECASE,
    )
    if enumeration:
        parts = re.split(r",\s*(?:and\s+|or\s+)?|\s+(?:and|or)\s+", enumeration.group(1))
        items = [clean_answer_item(part) for part in parts if clean_answer_item(part)]
        if len(items) >= 2:
            return items
    return [clean_answer_item(sentence) for sentence in sentences if clean_answer_item(sentence)]


ITEM_LEAD_IN = re.compile(
    r"^(?:for [^,]{3,80},\s*)?(?:you|students|computer engineers)\s+(?:will\s+)?(?:also\s+)?"
    r"(?:need|should|must|can)\s+(?:also\s+)?(?:to\s+)?(?:be able to\s+)?(?:have\s+)?(?:skills? in\s+)?",
    re.IGNORECASE,
)


def clean_answer_item(item: str) -> str:
    cleaned = " ".join((item or "").split()).strip(" .,:;-")
    cleaned = re.sub(r"^\*\*(.+?)\*\*", r"\1", cleaned)
    # A whole answer sentence is not a usable item: keep the thing it names
    # ("For a career in X, you need skills in using an IDE ..." -> "using an IDE ...").
    cleaned = ITEM_LEAD_IN.sub("", cleaned).strip(" .,:;-")
    words = cleaned.split()
    if len(words) > 14:
        clipped = " ".join(words[:14])
        # Cut at a clause boundary rather than mid-phrase.
        boundary = max(clipped.rfind(","), clipped.rfind(" and "), clipped.rfind(" to "))
        cleaned = clipped[:boundary] if boundary > 20 else clipped
    return cleaned.strip(" .,:;-")


def referenced_answer_item(question: str, previous_answer: str) -> str | None:
    """Return the item of the previous answer that an ordinal follow-up points to."""
    text = normalized_question(question)
    noun_pattern = "|".join(ANSWER_ITEM_NOUNS)
    for ordinal, position in ORDINAL_POSITIONS.items():
        if re.search(rf"\b(?:the\s+)?{ordinal}\s+(?:{noun_pattern})s?\b", text) or re.search(rf"\bthe\s+{ordinal}\b", text):
            items = answer_items(previous_answer)
            if not items:
                return None
            if position >= len(items):
                return None
            return items[position]
    return None


def asks_for_elaboration(question: str) -> bool:
    text = normalized_question(question)
    return any(contains_phrase(text, phrase) for phrase in ELABORATION_PHRASES)


PREVIOUS_ANSWER_PHRASES = (
    "you said",
    "you mentioned",
    "you listed",
    "you suggested",
    "your answer",
    "your last answer",
    "previous answer",
    "last answer",
)


def refers_to_previous_answer(question: str, previous_turn: Any) -> bool:
    """True when the student points at the content of the previous answer itself."""
    text = normalized_question(question)
    if any(phrase in text for phrase in PREVIOUS_ANSWER_PHRASES) or asks_for_elaboration(text):
        return True
    return referenced_answer_item(text, getattr(previous_turn, "answer", "") or "") is not None


def is_additive_follow_up_text(text: str, tokens: list[str]) -> bool:
    """Short questions ending in "too"/"also"/"as well" build on the previous topic."""
    if not tokens or len(tokens) > 8:
        return False
    if any(contains_phrase(text, phrase) for phrase in ("computer engineering", "computer engineer")):
        return False
    stripped = text.rstrip(" ?.!")
    return stripped.endswith((" too", " also", " as well")) or tokens[0] in {"also", "plus"}


def is_pronoun_follow_up_with_generic_anchor(text: str, tokens: list[str], topics: tuple[QueryTopic, ...]) -> bool:
    """Detect follow-ups like "what jobs use it?" whose only domain words are generic."""
    if not any(token in PRONOUN_REFERENTS for token in tokens) or len(tokens) > 10:
        return False
    if any(contains_phrase(text, phrase) for phrase in ("computer engineering", "computer engineer", "ceng")):
        return False
    return all(topic.name in GENERIC_FOLLOW_UP_TOPICS for topic in topics)


def resolve_follow_up_question(question: str, previous_turn: Any) -> str:
    topic = previous_topic(getattr(previous_turn, "question", ""))
    cleaned = " ".join((question or "").split()).rstrip()
    if not topic:
        return cleaned
    previous_question = " ".join((getattr(previous_turn, "question", "") or "").split()).rstrip(" ?.!")
    item = referenced_answer_item(cleaned, getattr(previous_turn, "answer", "") or "")
    if item:
        return f"Explain {item} in more detail (follow-up to: {previous_question}) in Computer Engineering?"
    if asks_for_elaboration(cleaned):
        return f"Explain {topic} in more detail in Computer Engineering?"
    text = normalized_question(cleaned)
    if text.startswith("is it "):
        return f"Is {topic} {cleaned[6:].strip()} in the context of Computer Engineering?"
    if text.startswith("does it "):
        return f"Does {topic} {cleaned[8:].strip()} in the context of Computer Engineering?"
    if text.startswith("what courses does it have"):
        return f"What courses does {topic} have in Computer Engineering?"
    if "skill" in text or "skills" in text:
        return f"{cleaned} for {topic} in Computer Engineering."
    if text.startswith("which one"):
        return f"{cleaned} Regarding {topic} in Computer Engineering."
    if text in {"why", "why?", "why is that", "why is that?"}:
        return f"Why is {topic} important in Computer Engineering?"
    return f"{cleaned} Regarding {topic} in Computer Engineering."


def previous_topic(question: str) -> str:
    text = " ".join((question or "").split()).strip(" ?.!").strip()
    replacements = (
        "I prefer ",
        "i prefer ",
        "I want to build ",
        "i want to build ",
        "Tell me about ",
        "tell me about ",
        "What is ",
        "what is ",
        "What are ",
        "what are ",
        "How much ",
        "how much ",
        "How many ",
        "how many ",
    )
    for prefix in replacements:
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    return text.strip(" ?.!") or "Computer Engineering"


def contains_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None
