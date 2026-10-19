"""Reusable retrieval layer for local ChromaDB evidence search.

Stage 13 only: this module retrieves source chunks. It does not generate final
answers, construct RAG prompts, call Ollama, or implement chatbot behavior.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import chromadb

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

from ..core.retrieval_config import (
    CANDIDATE_TOP_K,
    CATEGORY_BOOST,
    CATEGORY_CANDIDATES_PER_CATEGORY,
    CHROMA_PATH,
    COLLECTION_NAME,
    DEFAULT_TOP_K,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL_NAME,
    MAX_RESULTS_PER_SOURCE,
    MIN_RESULTS_ABOVE_THRESHOLD,
    MIN_SIMILARITY_THRESHOLD,
    OFFICIAL_SOURCE_BOOST,
    TITLE_KEYWORD_BOOST,
    VECTOR_STORE_MANIFEST_PATH,
)


EXCLUDED_SOURCE_IDS = {"src_019", "src_021", "src_022", "src_023", "src_024", "src_027", "src_046"}

QUERY_EXPANSION_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("ceng",),
        "Computer Engineering discipline career skills",
    ),
    (
        ("high-school", "high school", "simple terms"),
        "Computer Engineering definition department hardware software systems",
    ),
    (
        ("hardware or software", "hardware/software", "electronics", "mixture of both", "mostly coding"),
        "Computer Engineering hardware software systems components curriculum department",
    ),
    (
        ("no coding", "never coded", "no programming", "already behind", "prior programming"),
        "beginner programming no prior programming experience introductory course",
    ),
    (
        ("skills should i develop", "successful computer engineer", "before graduation", "technologies should i learn"),
        "skills technologies programming career readiness professional skills",
    ),
    (
        ("algorithm", "algorithms", "data structures"),
        "algorithms data structures programming curriculum problem solving software engineering",
    ),
    (
        ("testing", "debugging", "debug", "command line", "cli"),
        "software development testing debugging command line developer tools programming skills",
    ),
    (
        ("frontend", "backend", "react", "sql", "database", "databases"),
        "software development web backend frontend databases programming developer skills",
    ),
    (
        ("teamwork", "team work", "collaboration", "work in teams"),
        "teamwork collaboration communication professional skills employer career readiness",
    ),
    (
        ("future-proof", "future proof"),
        "future skills technology demand career adaptability reskilling",
    ),
    (
        ("low gpa", "gpa", "grade point"),
        "GPA candidate screening skills-based hiring major internship experience resume portfolio projects employer hiring career readiness",
    ),
    (
        ("personal projects", "portfolio", "impressive portfolio"),
        "portfolio projects resume GitHub skills career readiness",
    ),
    (
        ("cv", "resume", "curriculum vitae"),
        "resume CV portfolio projects skills experience career readiness job application",
    ),
    (
        ("hackathon", "hackathons", "coding competition", "coding competitions"),
        "hackathons coding competitions projects skills portfolio career readiness",
    ),
    (
        ("web development", "mobile development"),
        "software development programming mobile web applications career skills specialization",
    ),
    (
        ("computer architecture", "arduino", "fpga", "microcontroller", "microcontrollers", "iot"),
        "computer architecture embedded systems hardware microcontrollers FPGA IoT computer engineering curriculum projects",
    ),
    (
        ("industries hire", "what industries", "hiring industries"),
        "Turkey information communication technology ICT employment market industry organizations",
    ),
    (
        ("starting salary", "average salary", "salary", "salaries", "wage", "pay"),
        "salary wage pay Turkey ICT labor market employment information communication technology sector",
    ),
    (
        ("work abroad", "internationally", "international work", "working internationally"),
        "work abroad international qualifications remote work graduate employment",
    ),
    (
        ("digital nomad",),
        "remote work hybrid work professional developers survey work from home",
    ),
    (
        ("remote", "remotely", "work from home"),
        "remote work hybrid work professional developers survey work from home",
    ),
    (
        ("right major", "choose computer engineering", "instead of another engineering", "right field", "which field"),
        "computer engineering subdisciplines specializations hardware software systems career sectors professional practice",
    ),
    (
        ("startup", "software company", "own company", "entrepreneur"),
        "entrepreneurship business startup company software career",
    ),
    (
        ("without a master's", "without a masters", "master's degree", "masters degree"),
        "graduate studies artificial intelligence career research applied roles",
    ),
    (
        ("academia", "academic career", "professor", "research career"),
        "graduate studies research academia computer science computer engineering career",
    ),
    (
        ("stressful", "stress", "work-life", "work life"),
        "work life balance stress wellbeing burnout workload common misconceptions workplace",
    ),
    (
        ("all day writing code", "all day coding", "only coding"),
        "computer engineering misconceptions hardware software systems tasks careers",
    ),
    (
        ("women", "welcoming for women"),
        "women in computing diversity participation technical careers misconceptions employment",
    ),
    (
        ("ethical hacking", "hacking", "cybersec", "certs", "certification", "certifications"),
        "cybersecurity workforce framework security skills knowledge certifications ethical practice",
    ),
    (
        ("student clubs", "student communities", "social clubs", "competitions", "study abroad", "erasmus"),
        "OSTIM Technical University student life social clubs communities Erasmus competitions student affairs",
    ),
    (
        ("first internship", "get my first internship", "find internships", "apply to jobs"),
        "internship career center job application resume skills workplace experience",
    ),
)


@dataclass(frozen=True)
class QueryProfile:
    preferred_categories: tuple[str, ...] = ()
    official_source_preferred: bool = False
    title_keywords: tuple[str, ...] = ()
    focused_non_curriculum: bool = False


class Retriever:
    """Local embedding + ChromaDB retrieval helper."""

    def __init__(
        self,
        *,
        chroma_path: Path = CHROMA_PATH,
        collection_name: str = COLLECTION_NAME,
        model_name: str = EMBEDDING_MODEL_NAME,
    ) -> None:
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self.model_name = model_name
        self._model: SentenceTransformer | None = None
        self._client = chromadb.PersistentClient(path=str(self.chroma_path))
        self._collection = self._client.get_collection(self.collection_name)

    @property
    def collection_count(self) -> int:
        return self._collection.count()

    def load_manifest(self) -> dict[str, Any]:
        with VECTOR_STORE_MANIFEST_PATH.open("r", encoding="utf-8") as file:
            return json.load(file)

    def get_model(self) -> SentenceTransformer:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode_query(self, query: str) -> list[float]:
        cleaned = self._clean_query(query)
        embedding = self.get_model().encode(
            [cleaned],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0]
        if embedding.shape[0] != EMBEDDING_DIMENSION:
            raise ValueError(f"Expected query embedding dimension {EMBEDDING_DIMENSION}, got {embedding.shape[0]}.")
        return embedding.astype(float).tolist()

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        candidate_top_k: int = CANDIDATE_TOP_K,
    ) -> dict[str, Any]:
        cleaned = self._clean_query(query)
        if top_k <= 0:
            raise ValueError("top_k must be positive.")
        if candidate_top_k < top_k:
            candidate_top_k = top_k

        expanded_query = expand_query_for_retrieval(cleaned)
        query_embedding = self.encode_query(expanded_query)
        profile = infer_query_profile(expanded_query)
        raw = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=candidate_top_k,
            include=["documents", "metadatas", "distances"],
        )
        candidates = self._format_candidates(raw)
        candidates.extend(self._category_supplemental_candidates(query_embedding, profile))
        candidates = deduplicate_candidates(candidates)
        reranked = rerank_candidates(candidates, profile)
        selected = diversify_results(reranked, top_k=top_k)
        selected = [dict(result, rank=index) for index, result in enumerate(selected, start=1)]

        top_similarity = selected[0]["similarity_score"] if selected else 0.0
        above_threshold = sum(1 for result in selected if result["similarity_score"] >= MIN_SIMILARITY_THRESHOLD)
        evidence_sufficient = top_similarity >= MIN_SIMILARITY_THRESHOLD and above_threshold >= MIN_RESULTS_ABOVE_THRESHOLD

        return {
            "query": cleaned,
            "retrieval_query": expanded_query,
            "top_k": top_k,
            "candidate_top_k": candidate_top_k,
            "similarity_threshold": MIN_SIMILARITY_THRESHOLD,
            "results_above_threshold": above_threshold,
            "top_similarity_score": top_similarity,
            "evidence_sufficient": evidence_sufficient,
            "out_of_scope": not evidence_sufficient,
            "results": selected,
        }

    def _format_candidates(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        ids = raw.get("ids", [[]])[0]
        documents = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]
        candidates: list[dict[str, Any]] = []

        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
            source_id = metadata.get("source_id")
            if source_id in EXCLUDED_SOURCE_IDS:
                continue
            similarity = 1.0 - float(distance)
            candidates.append(
                {
                    "rank": 0,
                    "chunk_id": chunk_id,
                    "source_id": source_id,
                    "text": text,
                    "title": metadata.get("title") or "",
                    "source_name": metadata.get("source_name") or "",
                    "url": metadata.get("url") or "",
                    "category": metadata.get("category") or "",
                    "section_heading": metadata.get("section_heading") or "",
                    "similarity_score": similarity,
                    "distance": float(distance),
                    "rerank_score": similarity,
                    "metadata": metadata,
                }
            )

        return candidates

    def _category_supplemental_candidates(
        self, query_embedding: list[float], profile: QueryProfile
    ) -> list[dict[str, Any]]:
        supplemental: list[dict[str, Any]] = []
        for category in profile.preferred_categories:
            try:
                raw = self._collection.query(
                    query_embeddings=[query_embedding],
                    n_results=CATEGORY_CANDIDATES_PER_CATEGORY,
                    where={"category": category},
                    include=["documents", "metadatas", "distances"],
                )
            except Exception:
                continue
            supplemental.extend(self._format_candidates(raw))
        return supplemental

    @staticmethod
    def _clean_query(query: str) -> str:
        cleaned = " ".join((query or "").split())
        if not cleaned:
            raise ValueError("Query must not be empty.")
        return cleaned


def expand_query_for_retrieval(query: str) -> str:
    """Append generic semantic hints while preserving the user's original wording."""
    cleaned = " ".join((query or "").split())
    if not cleaned:
        return cleaned
    lowered = cleaned.lower()
    additions: list[str] = []
    for triggers, expansion in QUERY_EXPANSION_RULES:
        if any(trigger in lowered for trigger in triggers):
            additions.append(expansion)
    if not additions:
        return cleaned
    return f"{cleaned} {' '.join(dict.fromkeys(additions))}"


def infer_query_profile(query: str) -> QueryProfile:
    q = query.lower()
    preferred_categories: list[str] = []
    official_source_preferred = False
    title_keywords: list[str] = []
    focused_non_curriculum = False

    if any(term in q for term in ["course", "courses", "curriculum", "semester", "class", "classes"]):
        preferred_categories.extend(["curriculum", "programming", "mathematics"])
        official_source_preferred = True
        title_keywords.extend(["course", "curriculum"])

    if any(term in q for term in ["department", "university", "ostim", "technical university", "program in english", "english program"]):
        preferred_categories.extend(["department_information", "curriculum", "student_life"])
        official_source_preferred = True

    if any(term in q for term in ["programming", "coding", "language", "python", "java", "software", "algorithm", "algorithms", "data structures"]):
        preferred_categories.extend(["programming", "skills_and_technologies", "curriculum"])
        title_keywords.extend(["programming", "developer"])

    if any(term in q for term in ["frontend", "backend", "react", "sql", "database", "databases", "testing", "debugging", "command line", "cli"]):
        preferred_categories.extend(["skills_and_technologies", "programming", "employment"])
        title_keywords.extend(["developer", "skills", "software"])
        focused_non_curriculum = True

    if any(term in q for term in ["cv", "resume", "curriculum vitae"]):
        preferred_categories.extend(["employment", "skills_and_technologies"])
        title_keywords.extend(["resume", "cv", "career"])
        focused_non_curriculum = True

    if any(term in q for term in ["career", "job", "employment", "graduate", "work abroad", "salary", "senior engineer", "freelance", "freelancing"]):
        preferred_categories.extend(["career_opportunities", "employment", "skills_and_technologies", "future_technologies"])
        focused_non_curriculum = True

    if any(term in q for term in ["teamwork", "team work", "collaboration", "communication"]):
        preferred_categories.extend(["skills_and_technologies", "employment", "student_life"])

    if any(term in q for term in ["future-proof", "future proof", "future", "next 10 years"]):
        preferred_categories.extend(["future_technologies", "employment", "skills_and_technologies"])
        title_keywords.extend(["future", "jobs"])
        focused_non_curriculum = True

    if any(term in q for term in ["gpa", "grade point", "grade", "portfolio", "personal project", "projects", "github", "open source"]):
        preferred_categories.extend(["employment", "skills_and_technologies", "student_life"])
        title_keywords.extend(["resume", "portfolio", "skills"])
        focused_non_curriculum = True

    if any(term in q for term in ["hackathon", "hackathons", "coding competition", "coding competitions"]):
        preferred_categories.extend(["skills_and_technologies", "student_life", "employment"])
        focused_non_curriculum = True

    if any(
        term in q
        for term in [
            "specialization",
            "specializations",
            "field",
            "fields",
            "subdiscipline",
            "subdisciplines",
            "discipline",
            "disciplines",
            "web development",
            "mobile development",
            "computer architecture",
            "embedded",
            "arduino",
            "fpga",
            "microcontroller",
            "iot",
        ]
    ):
        preferred_categories.extend(["specializations", "skills_and_technologies", "career_opportunities", "curriculum"])
        title_keywords.extend(["subdiscipline", "specialization"])

    if any(term in q for term in ["right major", "choose", "instead of another engineering"]):
        preferred_categories.extend(
            [
                "department_information",
                "common_misconceptions",
                "specializations",
                "career_opportunities",
                "employment",
                "future_technologies",
                "curriculum",
            ]
        )
        official_source_preferred = True
        title_keywords.extend(["curriculum", "career", "jobs", "subdiscipline"])

    if any(term in q for term in ["artificial intelligence", " ai ", " gen ai", "automation", "replace"]):
        preferred_categories.extend(["artificial_intelligence", "future_technologies", "skills_and_technologies"])
        title_keywords.extend(["ai", "future", "jobs"])

    if any(term in q for term in ["cybersecurity", "cyber security", "cybersec", "security", "ethical hacking", "hacking", "certification", "certifications"]):
        preferred_categories.extend(["cybersecurity", "specializations", "skills_and_technologies", "future_technologies"])
        title_keywords.extend(["security", "cyber"])

    if any(term in q for term in ["internship", "internships", "co-op", "workplace"]):
        preferred_categories.extend(["internships", "employment", "curriculum"])
        official_source_preferred = "ostim" in q or "university" in q

    if any(term in q for term in ["master", "graduate school", "phd", "postgraduate"]):
        preferred_categories.extend(["graduate_studies", "career_opportunities"])

    if any(term in q for term in ["academia", "academic career", "research career"]):
        preferred_categories.extend(["graduate_studies", "career_opportunities", "skills_and_technologies"])

    if any(term in q for term in ["club", "clubs", "community", "communities", "competition", "competitions", "erasmus", "study abroad"]):
        preferred_categories.extend(["student_life", "internships", "department_information"])
        official_source_preferred = True
        focused_non_curriculum = True

    if any(term in q for term in ["academic staff", "faculty", "professor", "professors"]):
        preferred_categories.extend(["department_information"])
        official_source_preferred = True
        title_keywords.extend(["academic staff"])

    if any(term in q for term in ["remote", "remotely", "hybrid", "digital nomad", "work from home", "international work", "working internationally"]):
        preferred_categories.extend(["remote_work", "employment"])

    if any(term in q for term in ["startup", "entrepreneur", "business", "start a", "start my", "company"]):
        preferred_categories.extend(["entrepreneurship", "career_opportunities"])

    if any(term in q for term in ["work-life", "work life", "balance", "stress"]):
        preferred_categories.extend(["work_life_balance", "employment"])

    if any(term in q for term in ["woman", "women", "diversity", "welcoming"]):
        preferred_categories.extend(["common_misconceptions", "employment"])

    if any(term in q for term in ["misconception", "only coding", "all day coding", "all day writing code"]):
        preferred_categories.extend(["common_misconceptions", "department_information", "career_opportunities"])

    return QueryProfile(
        preferred_categories=tuple(dict.fromkeys(preferred_categories)),
        official_source_preferred=official_source_preferred,
        title_keywords=tuple(dict.fromkeys(title_keywords)),
        focused_non_curriculum=focused_non_curriculum,
    )


def rerank_candidates(candidates: list[dict[str, Any]], profile: QueryProfile) -> list[dict[str, Any]]:
    reranked = []
    for candidate in candidates:
        score = candidate["similarity_score"]
        category = candidate.get("category", "")
        title = (candidate.get("title") or "").lower()
        source_name = (candidate.get("source_name") or "").lower()
        source_type = str(candidate.get("metadata", {}).get("source_type") or "").lower()

        if category in profile.preferred_categories:
            score += CATEGORY_BOOST
        elif profile.focused_non_curriculum and category == "curriculum":
            score -= CATEGORY_BOOST
        if profile.official_source_preferred and (
            "ostim" in source_name
            or source_type in {"official_department_page", "curriculum_document", "course_descriptions"}
        ):
            score += OFFICIAL_SOURCE_BOOST
        if any(keyword in title for keyword in profile.title_keywords):
            score += TITLE_KEYWORD_BOOST

        reranked.append(dict(candidate, rerank_score=score))

    return sorted(reranked, key=lambda item: (item["rerank_score"], item["similarity_score"]), reverse=True)


def deduplicate_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        chunk_id = candidate["chunk_id"]
        previous = by_id.get(chunk_id)
        if previous is None or candidate["similarity_score"] > previous["similarity_score"]:
            by_id[chunk_id] = candidate
    return list(by_id.values())


def diversify_results(candidates: list[dict[str, Any]], *, top_k: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}
    skipped: list[dict[str, Any]] = []

    for candidate in candidates:
        source_id = candidate["source_id"]
        if source_counts.get(source_id, 0) >= MAX_RESULTS_PER_SOURCE:
            skipped.append(candidate)
            continue
        selected.append(candidate)
        source_counts[source_id] = source_counts.get(source_id, 0) + 1
        if len(selected) == top_k:
            return selected

    for candidate in skipped:
        selected.append(candidate)
        if len(selected) == top_k:
            break

    return selected
