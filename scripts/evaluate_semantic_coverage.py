"""Diagnostic semantic-coverage evaluation for the Computer Engineering advisor.

This script is intentionally read-only with respect to application behavior. It
creates a reusable question set, runs query-understanding plus retrieval-only
checks, and can run a small selected subset through the real RAG/Ollama path.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
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
    RAGPipeline,
    augment_context_results,
    unsupported_answerability_reason,
    unsupported_category_reason,
    unsupported_claim_reason,
    unsupported_specific_fact_reason,
)
DEFAULT_QUESTIONS = PROJECT_ROOT / "docs" / "semantic-coverage-200-questions.json"
DEFAULT_RETRIEVAL_RESULTS = PROJECT_ROOT / "docs" / "semantic-coverage-retrieval-results.json"
DEFAULT_E2E_RESULTS = PROJECT_ROOT / "docs" / "semantic-coverage-e2e-results.json"

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


def add_case(
    cases: list[dict[str, Any]],
    case_id: str,
    question: str,
    *,
    group: str,
    topics: tuple[str, ...] = (),
    categories: tuple[str, ...] = (),
    expected: str = "answer_or_gap",
    previous: str | None = None,
) -> None:
    cases.append(
        {
            "id": case_id,
            "question": question,
            "group": group,
            "expected_topics": list(topics),
            "expected_categories": list(categories),
            "expected_behavior": expected,
            "previous_question": previous,
        }
    )


def build_question_set() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    n = 1

    def bulk(prefix: str, group: str, rows: list[tuple[Any, ...]]) -> None:
        nonlocal n
        for row in rows:
            question, topics, categories, *rest = row
            expected = rest[0] if rest else "answer_or_gap"
            add_case(
                cases,
                f"{prefix}{n:03d}",
                question,
                group=group,
                topics=tuple(topics),
                categories=tuple(categories),
                expected=expected,
            )
            n += 1

    bulk(
        "F",
        "fundamentals",
        [
            ("What is Computer Engineering?", ["computer_engineering"], ["department_information", "common_misconceptions"]),
            ("What does a computer engineer actually study?", ["computer_engineering"], ["department_information", "curriculum"]),
            ("Is CENG mostly coding or also hardware?", ["hardware", "software"], ["curriculum", "common_misconceptions"]),
            ("Explain computer engineering to a high school student.", ["computer_engineering"], ["department_information", "common_misconceptions"]),
            ("How is computer engineering different from computer science?", ["computer_engineering"], ["common_misconceptions"]),
            ("CENG vs software engineering, which one is broader?", ["computer_engineering", "software"], ["common_misconceptions", "curriculum"]),
            ("Do computer engineers build physical devices or just apps?", ["hardware", "software"], ["curriculum", "hardware"]),
            ("Is computer engineering an engineering discipline or a computing major?", ["computer_engineering"], ["department_information", "common_misconceptions"]),
            ("What kind of problems do computer engineers solve?", ["computer_engineering"], ["department_information", "career_opportunities"]),
            ("computer eng ne demek basically?", ["computer_engineering"], ["department_information"]),
            ("Is computer engineering good for someone who likes both physics and code?", ["computer_engineering", "hardware", "software"], ["department_information", "curriculum"]),
            ("What is the difference between IT and Computer Engineering?", ["computer_engineering"], ["common_misconceptions"]),
        ],
    )
    bulk(
        "C",
        "curriculum",
        [
            ("What courses are taught in Computer Engineering?", ["curriculum"], ["curriculum"]),
            ("Which classes will I take in the first year?", ["curriculum"], ["curriculum"]),
            ("Are there operating systems courses in the program?", ["operating_systems"], ["curriculum"]),
            ("Does the curriculum include databases and networks?", ["networks", "software"], ["curriculum"]),
            ("What is in CENG 303?", ["operating_systems"], ["curriculum"]),
            ("Is there a workplace training or applied education course?", ["internships"], ["curriculum", "internships"]),
            ("Do students take electronics and digital logic?", ["hardware"], ["curriculum", "hardware"]),
            ("How much lab work is there in computer engineering?", ["curriculum", "hardware"], ["curriculum"]),
            ("What electives can help me specialize?", ["specializations"], ["curriculum", "specializations"]),
            ("what lesson r in ceng? typo but mean courses", ["curriculum"], ["curriculum"]),
            ("Which subjects connect math, programming, and circuits together?", ["mathematics", "programming", "hardware"], ["curriculum"]),
            ("Can I avoid hardware courses if I only like software?", ["hardware", "software"], ["curriculum", "common_misconceptions"]),
            ("Is the curriculum closer to EE or CS?", ["curriculum"], ["curriculum", "common_misconceptions"]),
            ("Are senior design projects part of CE education?", ["projects", "curriculum"], ["curriculum", "projects"]),
        ],
    )
    bulk(
        "M",
        "mathematics",
        [
            ("How much mathematics is required in Computer Engineering?", ["mathematics"], ["curriculum", "mathematics"]),
            ("I am weak at math; can I still study computer engineering?", ["mathematics"], ["mathematics", "common_misconceptions"]),
            ("Which math topics matter most for CENG?", ["mathematics"], ["curriculum", "mathematics"]),
            ("Is calculus used in computer engineering?", ["mathematics"], ["curriculum", "mathematics"]),
            ("Do I need discrete math for software and algorithms?", ["mathematics", "programming"], ["curriculum", "mathematics"]),
            ("math scary, should i quit ceng?", ["mathematics"], ["mathematics", "common_misconceptions"]),
            ("Can good programming compensate for average mathematics?", ["mathematics", "programming"], ["mathematics", "programming"]),
            ("What should I review before starting university: algebra, calculus, or coding?", ["mathematics", "programming"], ["mathematics", "programming"]),
            ("mathematic requirment computr eng?", ["mathematics"], ["curriculum", "mathematics"]),
            ("How theoretical is the degree compared with practical engineering?", ["mathematics", "curriculum"], ["curriculum"]),
            ("Do I need statistics for AI or data science?", ["mathematics", "ai"], ["mathematics", "artificial_intelligence"]),
            ("Is linear algebra important for machine learning?", ["mathematics", "ai"], ["mathematics", "artificial_intelligence"]),
        ],
    )
    bulk(
        "P",
        "programming_software",
        [
            ("What programming languages should a Computer Engineering student learn?", ["programming"], ["programming", "skills_and_technologies"]),
            ("Should I start with Python, Java, or C++?", ["programming"], ["programming"]),
            ("Is C++ still useful for computer engineers?", ["programming"], ["programming", "skills_and_technologies"]),
            ("Do I need web development if I study CENG?", ["software"], ["software", "skills_and_technologies"]),
            ("Should every student learn Git and GitHub?", ["projects"], ["skills_and_technologies"]),
            ("linux important?", ["operating_systems"], ["curriculum", "skills_and_technologies"]),
            ("Is Linux worth learning for embedded systems?", ["operating_systems", "hardware"], ["curriculum", "skills_and_technologies"]),
            ("I can only code simple apps; what skill next?", ["skills", "programming"], ["programming", "skills_and_technologies"]),
            ("How do I become better at algorithms?", ["programming"], ["programming", "curriculum"]),
            ("Should I learn data structures before building projects?", ["programming", "projects"], ["programming", "projects"]),
            ("git hub learn necessery?", ["projects"], ["skills_and_technologies"]),
            ("What software engineering habits should I build early?", ["software", "skills"], ["software", "skills_and_technologies"]),
            ("Can I become a backend developer from computer engineering?", ["software", "career"], ["software", "career_opportunities"]),
            ("frontend vs backend for ceng student?", ["software", "career"], ["software", "career_opportunities"]),
            ("Are databases important for computer engineers?", ["software"], ["curriculum", "software"]),
            ("Which is more useful first: SQL or React?", ["software", "skills"], ["software", "skills_and_technologies"]),
            ("Should I learn testing and debugging?", ["software", "skills"], ["software", "skills_and_technologies"]),
            ("How important is command line usage?", ["operating_systems", "skills"], ["skills_and_technologies"]),
        ],
    )
    bulk(
        "H",
        "hardware_networks",
        [
            ("What hardware topics should I understand?", ["hardware"], ["hardware", "curriculum"]),
            ("Is embedded systems a good path for Computer Engineering?", ["hardware", "career"], ["hardware", "career_opportunities"]),
            ("Do computer engineers work with microcontrollers?", ["hardware"], ["hardware", "curriculum"]),
            ("How important is computer architecture?", ["hardware"], ["curriculum", "hardware"]),
            ("Are networks part of Computer Engineering?", ["networks"], ["curriculum"]),
            ("What network skills are useful for cybersecurity?", ["networks", "cybersecurity"], ["cybersecurity", "skills_and_technologies"]),
            ("hardware hard but software ok, can I survive?", ["hardware", "software"], ["curriculum", "common_misconceptions"]),
            ("Does CE include electronics labs?", ["hardware"], ["curriculum", "hardware"]),
            ("Should I learn Arduino or FPGA first?", ["hardware", "projects"], ["hardware", "projects"]),
            ("What is the connection between operating systems and hardware?", ["operating_systems", "hardware"], ["curriculum", "hardware"]),
            ("Can I work on IoT after Computer Engineering?", ["hardware", "networks", "career"], ["hardware", "career_opportunities"]),
            ("Are computer networks useful outside cybersecurity?", ["networks", "career"], ["curriculum", "career_opportunities"]),
        ],
    )
    bulk(
        "A",
        "ai_future",
        [
            ("Will artificial intelligence replace Computer Engineers?", ["ai", "career"], ["artificial_intelligence", "future_technologies"]),
            ("How should I prepare for an AI-heavy software industry?", ["ai", "skills"], ["artificial_intelligence", "skills_and_technologies"]),
            ("Can a computer engineering student become an AI engineer?", ["ai", "career"], ["artificial_intelligence", "career_opportunities"]),
            ("Do I need a master's degree for AI jobs?", ["ai", "graduate_studies"], ["artificial_intelligence", "graduate_studies"]),
            ("What AI skills are useful besides prompt engineering?", ["ai", "skills"], ["artificial_intelligence", "skills_and_technologies"]),
            ("Is machine learning part of computer engineering?", ["ai", "curriculum"], ["artificial_intelligence", "curriculum"]),
            ("AI taking jobs, should I still study CENG?", ["ai", "career"], ["artificial_intelligence", "future_technologies"]),
            ("Which future technologies should a CENG student follow?", ["future_technologies"], ["future_technologies"]),
            ("Will software jobs disappear because of coding agents?", ["ai", "software", "career"], ["artificial_intelligence", "employment"]),
            ("how ai affect engineers work?", ["ai", "career"], ["artificial_intelligence", "skills_and_technologies"]),
            ("Can I specialize in data science after computer engineering?", ["ai", "career"], ["artificial_intelligence", "career_opportunities"]),
            ("Is robotics closer to computer engineering or mechanical engineering?", ["hardware", "ai"], ["specializations", "hardware"]),
            ("Should I learn ML math before using AI tools?", ["ai", "mathematics"], ["artificial_intelligence", "mathematics"]),
            ("What parts of engineering work are changed by generative AI?", ["ai", "career"], ["artificial_intelligence", "skills_and_technologies"]),
        ],
    )
    bulk(
        "Y",
        "cybersecurity",
        [
            ("Can Computer Engineers work in cybersecurity?", ["cybersecurity", "career"], ["cybersecurity", "career_opportunities"]),
            ("What skills should I build for cybersecurity?", ["cybersecurity", "skills"], ["cybersecurity", "skills_and_technologies"]),
            ("Do I need networking before security?", ["cybersecurity", "networks"], ["cybersecurity", "skills_and_technologies"]),
            ("Is cybersecurity more software or hardware?", ["cybersecurity", "software", "hardware"], ["cybersecurity", "curriculum"]),
            ("How can I start ethical hacking safely as a student?", ["cybersecurity"], ["cybersecurity", "skills_and_technologies"]),
            ("security career path from ceng?", ["cybersecurity", "career"], ["cybersecurity", "career_opportunities"]),
            ("Should I learn Linux for cyber security?", ["cybersecurity", "operating_systems"], ["cybersecurity", "skills_and_technologies"]),
            ("Can I work in cloud security after CENG?", ["cybersecurity", "career"], ["cybersecurity", "career_opportunities"]),
            ("cybersec certs or degree which matters?", ["cybersecurity", "career"], ["cybersecurity", "employment"]),
            ("Is cryptography too math-heavy for me?", ["cybersecurity", "mathematics"], ["cybersecurity", "mathematics"]),
            ("What is the difference between cybersecurity and software engineering?", ["cybersecurity", "software"], ["cybersecurity", "software"]),
            ("Can I learn security without doing illegal hacking?", ["cybersecurity"], ["cybersecurity", "skills_and_technologies"]),
        ],
    )
    bulk(
        "R",
        "career_employment",
        [
            ("What jobs can I do after graduating from Computer Engineering?", ["career"], ["career_opportunities", "employment"]),
            ("Is it easy to find a job after CENG?", ["employment"], ["employment"]),
            ("What should I include in my CV as a CENG student?", ["cv", "career"], ["employment"]),
            ("How do I build a portfolio before graduation?", ["portfolio", "projects"], ["projects", "employment"]),
            ("Should I focus more on GPA, projects, or internships?", ["gpa", "projects", "internships"], ["employment", "internships", "projects"]),
            ("Does low GPA ruin my software career?", ["gpa", "career"], ["employment"]),
            ("How important are internships?", ["internships"], ["internships", "employment"]),
            ("What if I graduate without internship experience?", ["internships", "employment"], ["internships", "employment"]),
            ("Can personal projects replace internship experience?", ["projects", "internships"], ["projects", "internships", "employment"]),
            ("Are hackathons useful for computer engineering students?", ["projects", "student_life"], ["student_life", "projects"]),
            ("How can I get my first internship?", ["internships"], ["internships", "employment"]),
            ("Where can Turkish students find internships?", ["internships"], ["internships", "employment"]),
            ("Erasmus useful for computer engineering?", ["erasmus"], ["internships", "student_life"]),
            ("Can CENG graduates work abroad?", ["career", "remote_work"], ["career_opportunities", "remote_work"]),
            ("Can I work remotely as a new graduate?", ["remote_work", "employment"], ["remote_work", "employment"]),
            ("Which specialization pays the most in Turkey?", ["salary", "specializations"], ["salaries", "employment"], "insufficient"),
            ("What is starting salary for OSTIM CENG graduates?", ["salary"], ["salaries"], "insufficient"),
            ("How long until I become senior engineer?", ["career"], ["employment"]),
            ("Will employers care about university name or skills?", ["employment", "skills"], ["employment", "skills_and_technologies"]),
            ("What kind of projects impress recruiters?", ["projects", "employment"], ["projects", "employment"]),
            ("Do open source contributions help?", ["projects", "skills"], ["projects", "skills_and_technologies"]),
            ("Can I start freelancing while studying?", ["entrepreneurship", "career"], ["entrepreneurship", "employment"]),
            ("Should I build mobile apps, web apps, or embedded projects?", ["projects", "software", "hardware"], ["projects", "software", "hardware"]),
            ("GPA project staj hangisi daha onemli?", ["gpa", "projects", "internships"], ["employment", "internships"]),
            ("No experience, no internship, low GPA - what can I do?", ["gpa", "internships", "career"], ["employment", "internships"]),
            ("What are entry-level computer engineering job titles?", ["career", "employment"], ["employment", "career_opportunities"]),
            ("Is LinkedIn useful for finding internships?", ["internships", "employment"], ["internships", "employment"]),
            ("Should I apply to jobs before graduating?", ["employment"], ["employment", "internships"]),
        ],
    )
    bulk(
        "S",
        "student_local",
        [
            ("Should I do a master's after Computer Engineering?", ["graduate_studies"], ["graduate_studies", "career_opportunities"]),
            ("Is a master's necessary for industry jobs?", ["graduate_studies", "career"], ["graduate_studies", "employment"]),
            ("Can I go into academia after CENG?", ["graduate_studies", "career"], ["graduate_studies"]),
            ("What is student life like at OSTIM Technical University?", ["student_life"], ["student_life", "department_information"]),
            ("OSTIMTECH social clubs/student communities?", ["student_life"], ["student_life"]),
            ("Does OSTIM have student clubs for engineering students?", ["student_life"], ["student_life"]),
            ("Which official regulation explains exams and grading?", ["academic_regulations"], ["academic_regulations"]),
            ("What is the attendance rule for CENG courses?", ["academic_regulations"], ["academic_regulations"], "insufficient"),
            ("What is the exact 2026 tuition fee?", ["tuition"], ["department_information"], "insufficient"),
            ("Can I transfer from another university to CENG?", ["academic_regulations"], ["academic_regulations"]),
            ("Is the program in English?", ["department_information"], ["department_information"]),
            ("Who are the academic staff in the department?", ["academic_staff"], ["department_information"]),
            ("Is OSTIM connected with industry?", ["department_information", "internships"], ["department_information", "internships"]),
            ("What makes OSTIM CENG different?", ["department_information"], ["department_information"]),
            ("Are there competitions or student projects?", ["student_life", "projects"], ["student_life", "projects"]),
            ("Can I ask about scholarship opportunities?", ["scholarship"], ["department_information"], "insufficient"),
            ("Does the department have Erasmus agreements?", ["erasmus"], ["student_life", "internships"]),
            ("Can I study abroad for one semester as a CENG student?", ["erasmus"], ["student_life", "internships"]),
        ],
    )
    bulk(
        "X",
        "complex",
        [
            ("I like AI and cybersecurity but hate electronics; is CENG still a good choice and what should I learn first?", ["ai", "cybersecurity", "hardware"], ["artificial_intelligence", "cybersecurity", "curriculum"]),
            ("Compare focusing on GPA, internships, GitHub projects, and networking for getting a first software job.", ["gpa", "internships", "projects", "employment"], ["employment", "internships", "projects"]),
            ("If I want remote work abroad, should I prioritize English, portfolio, cloud, or algorithms?", ["remote_work", "skills", "projects"], ["remote_work", "employment", "skills_and_technologies"]),
            ("What should a first-year student do each semester to become employable by graduation?", ["career", "skills"], ["employment", "skills_and_technologies", "curriculum"]),
            ("I am choosing between data science, embedded systems, and cybersecurity; how do I explore them safely?", ["ai", "hardware", "cybersecurity"], ["specializations", "projects"]),
            ("What are realistic expectations about salary, work-life balance, and job security?", ["salary", "work_life_balance", "employment"], ["salaries", "work_life_balance", "employment"]),
            ("Can you rank AI, cloud, cybersecurity, and embedded by future demand?", ["ai", "cybersecurity", "hardware", "future_technologies"], ["future_technologies", "employment"]),
            ("What should I learn before internship interviews: data structures, Git, Linux, or databases?", ["internships", "programming", "projects", "operating_systems"], ["internships", "programming", "skills_and_technologies"]),
            ("I failed a course and my GPA is low; can projects and internships still help me?", ["gpa", "projects", "internships"], ["employment", "internships", "projects"]),
            ("How do curriculum courses connect to actual industry roles?", ["curriculum", "career"], ["curriculum", "career_opportunities"]),
            ("I want to work in AI but also need a job quickly; should I start backend or ML first?", ["ai", "software", "employment"], ["artificial_intelligence", "software", "employment"]),
            ("If I dislike pure theory but enjoy building things, how should I approach CENG?", ["projects", "curriculum"], ["curriculum", "projects"]),
        ],
    )
    bulk(
        "U",
        "unsupported",
        [
            ("What is the exact job placement rate of OSTIM CENG graduates in 2026?", ["employment"], ["employment"], "insufficient"),
            ("Which professor is the easiest grader?", ["academic_staff"], ["department_information"], "insufficient"),
            ("Give me the private phone number of the department chair.", [], [], "out_of_scope"),
            ("What is the guaranteed salary if I graduate first in class?", ["salary"], ["salaries"], "insufficient"),
            ("Which company will hire me after graduation?", ["employment"], ["employment"], "insufficient"),
            ("Predict whether I personally will succeed in CENG.", ["career"], ["career_opportunities"], "insufficient"),
            ("What exact questions will be on CENG 303 final exam?", ["academic_regulations"], ["curriculum"], "insufficient"),
            ("Can you write my internship report for me?", [], [], "out_of_scope"),
            ("Tell me the current exchange rate for tuition payment.", [], [], "out_of_scope"),
            ("What is the best laptop deal today?", [], [], "out_of_scope"),
            ("Give me a list of all 2027 CENG exam dates.", ["academic_regulations"], ["academic_regulations"], "insufficient"),
            ("What GPA do I need to guarantee a Google internship?", ["gpa", "internships"], ["employment", "internships"], "insufficient"),
            ("Can you promise I will get a remote job after this degree?", ["remote_work", "employment"], ["remote_work", "employment"], "insufficient"),
        ],
    )
    bulk(
        "O",
        "out_of_scope",
        [
            ("How do I bake sourdough bread?", [], [], "out_of_scope"),
            ("Who won the football match yesterday?", [], [], "out_of_scope"),
            ("Write a love poem in Spanish.", [], [], "out_of_scope"),
            ("What is the capital of Australia?", [], [], "out_of_scope"),
            ("Can you diagnose my chest pain?", [], [], "out_of_scope"),
            ("What stocks should I buy today?", [], [], "out_of_scope"),
            ("Plan a seven-day beach vacation.", [], [], "out_of_scope"),
            ("Translate this legal contract.", [], [], "out_of_scope"),
            ("Make a workout plan for bodybuilding.", [], [], "out_of_scope"),
            ("What is the weather tomorrow?", [], [], "out_of_scope"),
            ("Summarize the latest NBA game.", [], [], "out_of_scope"),
            ("Find me cheap flights to Berlin.", [], [], "out_of_scope"),
            ("Give me a recipe for Turkish coffee.", [], [], "out_of_scope"),
        ],
    )

    followups = [
        ("Can Computer Engineers work in cybersecurity?", "What skills should I build?", ["cybersecurity", "skills"], ["cybersecurity", "skills_and_technologies"], "answer_or_gap"),
        ("I want to become an AI engineer.", "Do I need a master's?", ["ai", "graduate_studies"], ["artificial_intelligence", "graduate_studies"], "answer_or_gap"),
        ("Should I learn Git and GitHub?", "What sources did you use?", [], [], "source_follow_up"),
        ("I am weak at math.", "How can I prepare before first year?", ["mathematics"], ["mathematics", "curriculum"], "answer_or_gap"),
        ("I care about internships.", "Where can I find one in Turkey?", ["internships"], ["internships", "employment"], "answer_or_gap"),
        ("I prefer hardware.", "What projects should I build?", ["hardware", "projects"], ["hardware", "projects"], "answer_or_gap"),
        ("I asked about software jobs.", "What about remote work?", ["remote_work", "employment"], ["remote_work", "employment"], "answer_or_gap"),
        ("Tell me about the curriculum.", "Does it include Linux?", ["operating_systems", "curriculum"], ["curriculum"], "answer_or_gap"),
        ("I want cybersecurity.", "Is Linux important too?", ["cybersecurity", "operating_systems"], ["cybersecurity", "skills_and_technologies"], "answer_or_gap"),
        ("Computer Engineering vs Computer Science?", "Which one has more hardware?", ["hardware", "computer_engineering"], ["curriculum", "common_misconceptions"], "answer_or_gap"),
        ("I want to build portfolio projects.", "Should they be team projects or solo?", ["projects"], ["projects", "employment"], "answer_or_gap"),
        ("I have low GPA.", "Can internships compensate?", ["gpa", "internships"], ["employment", "internships"], "answer_or_gap"),
        ("Tell me about OSTIM CENG.", "What makes it different?", ["department_information"], ["department_information"], "answer_or_gap"),
        ("Can CENG students do Erasmus?", "Will it help my career?", ["erasmus", "career"], ["internships", "career_opportunities"], "answer_or_gap"),
        ("What jobs can graduates do?", "And salaries?", ["salary", "career"], ["salaries", "employment"], "insufficient"),
        ("Is AI changing engineering work?", "So will it replace us?", ["ai", "career"], ["artificial_intelligence", "future_technologies"], "answer_or_gap"),
        ("What is CENG 303?", "Is it hard?", ["operating_systems", "curriculum"], ["curriculum"], "answer_or_gap"),
        ("How important are networks?", "For cloud security?", ["networks", "cybersecurity"], ["cybersecurity", "skills_and_technologies"], "answer_or_gap"),
        ("Should I learn Python first?", "or C++?", ["programming"], ["programming"], "answer_or_gap"),
        ("Can I work abroad?", "What skills matter most?", ["remote_work", "skills"], ["remote_work", "skills_and_technologies"], "answer_or_gap"),
        ("I asked about GPA and projects.", "Which one should I prioritize this semester?", ["gpa", "projects"], ["employment", "projects"], "answer_or_gap"),
        ("I asked about student clubs.", "Where do I find them?", ["student_life"], ["student_life"], "answer_or_gap"),
    ]
    for previous, question, topics, categories, expected in followups:
        add_case(
            cases,
            f"T{n:03d}",
            question,
            group="multi_turn",
            topics=tuple(topics),
            categories=tuple(categories),
            expected=expected,
            previous=previous,
        )
        n += 1

    if len(cases) != 200:
        raise AssertionError(f"expected 200 cases, built {len(cases)}")
    return cases


def save_questions(path: Path) -> list[dict[str, Any]]:
    cases = build_question_set()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"case_count": len(cases), "cases": cases}, ensure_ascii=False, indent=2), encoding="utf-8")
    return cases


def load_or_create_questions(path: Path) -> list[dict[str, Any]]:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data["cases"])
    return save_questions(path)


def previous_turn(case: dict[str, Any]) -> ConversationTurn | None:
    previous = case.get("previous_question")
    if not previous:
        return None
    return ConversationTurn(
        question=previous,
        status=ANSWERED,
        answer="Previous diagnostic turn.",
        sources=({"source_id": "diagnostic_previous_source", "evidence_labels": ["S1"]},),
        retrieved_context=({"source_id": "diagnostic_previous_source", "label": "S1", "title": "Diagnostic previous context"},),
        citation_metadata={"valid": True},
    )


def understanding_ok(case: dict[str, Any], resolution: Any) -> bool:
    expected = case["expected_behavior"]
    kind = resolution.kind
    if expected == "out_of_scope":
        return kind == "out_of_scope_persona_meta"
    if expected == "source_follow_up":
        return kind == "source_follow_up"
    if case.get("previous_question"):
        return kind not in {"out_of_scope_persona_meta", "vague_no_referent"}
    return kind != "out_of_scope_persona_meta"


def retrieval_relevant(case: dict[str, Any], retrieval: dict[str, Any], context: list[dict[str, Any]]) -> bool:
    expected = case["expected_behavior"]
    if expected == "out_of_scope":
        return bool(retrieval.get("out_of_scope")) or retrieval.get("evidence_sufficient") is False
    if expected == "insufficient":
        return True

    text = " ".join(
        " ".join(
            str(part or "")
            for part in (
                item.get("category"),
                item.get("title"),
                item.get("source_id"),
                (item.get("text") or item.get("passage") or "")[:350],
            )
        )
        for item in context[:5]
    ).lower()
    retrieved_categories = {item.get("category") for item in context[:5]}
    expected_categories = set(case.get("expected_categories") or ())
    category_match = bool(expected_categories & retrieved_categories) if expected_categories else True
    topic_match = any(
        any(term in text for term in TOPIC_SYNONYMS.get(topic, (topic,)))
        for topic in case.get("expected_topics") or ()
    )
    return bool(retrieval.get("evidence_sufficient")) and (category_match or topic_match)


def failure_cause(
    case: dict[str, Any],
    resolution: Any,
    retrieval: dict[str, Any] | None,
    relevant: bool,
    gate_reason: str | None,
) -> str:
    expected = case["expected_behavior"]
    kind = resolution.kind
    if expected == "out_of_scope":
        return "ok" if kind == "out_of_scope_persona_meta" else "query_misunderstanding"
    if expected == "source_follow_up":
        return "ok" if kind == "source_follow_up" else "conversation_context_failure"
    if kind == "out_of_scope_persona_meta":
        return "query_misunderstanding"
    if kind == "vague_no_referent":
        return "conversation_context_failure" if case.get("previous_question") else "query_misunderstanding"
    if retrieval is None:
        return "ok"
    if retrieval.get("out_of_scope"):
        return "incorrect_semantic_retrieval"
    if not relevant:
        return "incorrect_semantic_retrieval"
    if expected == "insufficient":
        return "ok" if gate_reason or not retrieval.get("evidence_sufficient") else "answerability_gap_unsupported_may_pass"
    if gate_reason:
        return "answerability_gate_possible_false_reject"
    return "ok"


def run_retrieval_only(cases: list[dict[str, Any]], output_path: Path) -> dict[str, Any]:
    pipeline = RAGPipeline()
    results: list[dict[str, Any]] = []
    cause_counts: Counter[str] = Counter()
    group_stats: dict[str, Counter[str]] = defaultdict(Counter)

    for index, case in enumerate(cases, start=1):
        print(f"retrieval {index:03d}/{len(cases)} {case['id']}", flush=True)
        resolution = resolve_query(case["question"], previous_turn(case))
        qmeta = resolution.understanding.to_metadata() if resolution.understanding else {}
        retrieval = None
        context: list[dict[str, Any]] = []
        gate_reason = None
        relevant = understanding_ok(case, resolution)

        if resolution.kind not in {"out_of_scope_persona_meta", "source_follow_up", "vague_no_referent"}:
            retrieval_query = resolution.resolved_question or case["question"]
            retrieval = pipeline.retriever.retrieve(retrieval_query, top_k=3, candidate_top_k=8)
            context = augment_context_results(retrieval_query, retrieval.get("results", []))
            gate_reason = (
                unsupported_answerability_reason(retrieval_query, context)
                or unsupported_specific_fact_reason(case["question"], context)
                or unsupported_category_reason(case["question"], context)
                or unsupported_claim_reason(case["question"], context)
            )
            relevant = retrieval_relevant(case, retrieval, context)

        cause = failure_cause(case, resolution, retrieval, relevant, gate_reason)
        cause_counts[cause] += 1
        group_stats[case["group"]][cause] += 1
        results.append(
            {
                **case,
                "query_kind": resolution.kind,
                "resolved_question": resolution.resolved_question,
                "understanding_ok": understanding_ok(case, resolution),
                "query_topics": [topic["name"] for topic in qmeta.get("topics", [])],
                "retrieval_relevant": relevant,
                "evidence_sufficient": None if retrieval is None else retrieval.get("evidence_sufficient"),
                "retrieval_out_of_scope": None if retrieval is None else retrieval.get("out_of_scope"),
                "top_similarity_score": None if retrieval is None else retrieval.get("top_similarity_score"),
                "answerability_gate_reason": gate_reason,
                "failure_cause": cause,
                "top_context": [
                    {
                        "source_id": item.get("source_id"),
                        "title": item.get("title"),
                        "category": item.get("category"),
                        "similarity_score": item.get("similarity_score"),
                        "preview": (item.get("text") or item.get("passage") or item.get("passage_preview") or "")[:240],
                    }
                    for item in context[:3]
                ],
            }
        )

    summary = {
        "case_count": len(results),
        "understood_correctly": sum(1 for row in results if row["understanding_ok"]),
        "retrieved_relevant_evidence": sum(1 for row in results if row["retrieval_relevant"]),
        "cause_counts": dict(cause_counts),
        "group_stats": {group: dict(counter) for group, counter in group_stats.items()},
        "failures": [row for row in results if row["failure_cause"] != "ok"],
    }
    output = {"summary": summary, "results": results}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def select_e2e_cases(retrieval_output: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    results = retrieval_output["results"]
    selected: list[dict[str, Any]] = []

    def add_matching(predicate: Any) -> None:
        for row in results:
            if len(selected) >= limit:
                return
            if row["id"] not in {item["id"] for item in selected} and predicate(row):
                selected.append(row)

    add_matching(lambda row: row["failure_cause"] != "ok")
    for group in (
        "fundamentals",
        "curriculum",
        "mathematics",
        "programming_software",
        "hardware_networks",
        "ai_future",
        "cybersecurity",
        "career_employment",
        "student_local",
        "complex",
        "multi_turn",
        "unsupported",
        "out_of_scope",
    ):
        add_matching(lambda row, group=group: row["group"] == group)

    challenging_questions = {
        "linux important?",
        "Will artificial intelligence replace Computer Engineers?",
        "Should I focus more on GPA, projects, or internships?",
        "GPA project staj hangisi daha onemli?",
        "Which official regulation explains exams and grading?",
        "OSTIMTECH social clubs/student communities?",
        "What sources did you use?",
        "Can you rank AI, cloud, cybersecurity, and embedded by future demand?",
    }
    add_matching(lambda row: row["question"] in challenging_questions)
    add_matching(lambda row: True)
    return selected[:limit]


def run_e2e(cases: list[dict[str, Any]], output_path: Path) -> dict[str, Any]:
    pipeline = RAGPipeline()
    existing: dict[str, Any] = {"results": []}
    if output_path.exists():
        existing = json.loads(output_path.read_text(encoding="utf-8"))
    done = {row["id"] for row in existing.get("results", [])}
    results = list(existing.get("results", []))

    for index, case in enumerate(cases, start=1):
        if case["id"] in done:
            continue
        print(f"ollama {index:03d}/{len(cases)} {case['id']}", flush=True)
        start = time.perf_counter()
        resolution = resolve_query(case["question"], previous_turn(case))
        try:
            if resolution.kind == "source_follow_up":
                result = previous_source_response(case["question"], previous_turn(case) or previous_turn({"previous_question": "diagnostic"}))
            elif resolution.kind == "vague_no_referent":
                result = unresolved_follow_up_response(
                    case["question"],
                    "I am not sure which previous topic or information you are referring to. Please ask a complete question about Computer Engineering.",
                )
            elif resolution.kind == "out_of_scope_persona_meta":
                result = out_of_scope_response(case["question"])
            else:
                result = pipeline.answer(
                    case["question"],
                    conversation_context=build_resolution_context(resolution),
                    resolved_question=resolution.resolved_question,
                )
            result = attach_resolution_metadata(result, resolution)
            citation = result.get("citation_metadata") or {}
            row = {
                **case,
                "query_kind": resolution.kind,
                "resolved_question": resolution.resolved_question,
                "status": result.get("status"),
                "llm_called": result.get("llm_called"),
                "answerability_decision": (result.get("retrieval_metadata") or {}).get("unsupported_reason") or "allowed_or_bypassed",
                "citation_valid": bool(citation.get("valid", True)) and not citation.get("invalid_labels"),
                "sources": [source.get("source_id") for source in result.get("sources") or []],
                "top_context": [
                    {
                        "source_id": item.get("source_id"),
                        "title": item.get("title"),
                        "category": item.get("category"),
                        "similarity_score": item.get("similarity_score"),
                    }
                    for item in (result.get("retrieved_context") or [])[:3]
                ],
                "answer_preview": (result.get("answer") or "")[:700],
                "error": result.get("error"),
                "elapsed_seconds": round(time.perf_counter() - start, 2),
            }
        except Exception as exc:
            row = {**case, "status": "harness_error", "error": repr(exc), "elapsed_seconds": round(time.perf_counter() - start, 2)}
        results.append(row)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps({"case_count": len(cases), "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "case_count": len(results),
        "status_counts": dict(Counter(row.get("status") for row in results)),
        "error_cases": [row for row in results if row.get("status") in {ERROR, "harness_error"}],
    }
    output = {"summary": summary, "results": results}
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["questions", "retrieval", "e2e", "all"], default="all")
    parser.add_argument("--questions", default=str(DEFAULT_QUESTIONS))
    parser.add_argument("--retrieval-output", default=str(DEFAULT_RETRIEVAL_RESULTS))
    parser.add_argument("--e2e-output", default=str(DEFAULT_E2E_RESULTS))
    parser.add_argument("--e2e-limit", type=int, default=25)
    args = parser.parse_args()

    questions_path = Path(args.questions)
    retrieval_path = Path(args.retrieval_output)
    e2e_path = Path(args.e2e_output)

    cases = load_or_create_questions(questions_path)
    print(f"questions_file={questions_path}")
    print(f"case_count={len(cases)}")
    if args.mode == "questions":
        return

    retrieval_output = None
    if args.mode in {"retrieval", "all"} or not retrieval_path.exists():
        retrieval_output = run_retrieval_only(cases, retrieval_path)
    else:
        retrieval_output = json.loads(retrieval_path.read_text(encoding="utf-8"))
    print(f"retrieval_results={retrieval_path}")
    print(json.dumps(retrieval_output["summary"], ensure_ascii=False, indent=2)[:4000])

    if args.mode in {"e2e", "all"}:
        selected = select_e2e_cases(retrieval_output, args.e2e_limit)
        e2e_output = run_e2e(selected, e2e_path)
        print(f"e2e_results={e2e_path}")
        print(json.dumps(e2e_output["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
