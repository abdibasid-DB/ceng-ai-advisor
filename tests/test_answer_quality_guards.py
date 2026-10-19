"""Regression tests for answer-quality guards found during live Ollama checks."""

import sys
import unittest
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.query_understanding import resolve_query, understand_query
from backend.app.rag.rag_pipeline import (
    clean_answer_artifacts,
    cited_claim_supported,
    remove_repeated_sentences,
    strip_citation_text,
    validate_citations,
)


@dataclass(frozen=True)
class PreviousTurn:
    question: str
    answer: str = ""


PHYSICS_ITEM = {
    "label": "S3",
    "chunk_id": "src_020_chunk_001",
    "source_id": "src_020",
    "passage": "PHYSICS 5A or 7A are required for all engineering majors and must be preceded by Calculus.",
}


class AnswerQualityGuardTests(unittest.TestCase):
    def test_negated_paraphrase_of_cited_passage_is_rejected(self):
        self.assertFalse(
            cited_claim_supported("Physics is not required for all engineering majors [S3].", PHYSICS_ITEM)
        )
        self.assertTrue(
            cited_claim_supported("PHYSICS 5A or 7A are required for all engineering majors [S3].", PHYSICS_ITEM)
        )

    def test_statement_about_missing_evidence_is_not_a_polarity_conflict(self):
        self.assertTrue(
            cited_claim_supported(
                "The source does not state how much physics every engineering major requires [S3].", PHYSICS_ITEM
            )
        )

    def test_answer_wrapped_in_brackets_is_still_checked(self):
        self.assertIn("work abroad", strip_citation_text("[Graduates can work abroad [S2].]"))
        self.assertEqual(
            clean_answer_artifacts("[Graduates can work abroad, as evidenced by the [S2] source.]"),
            "Graduates can work abroad, as evidenced by the source [S2].",
        )

    def test_unsupported_wrapped_answer_fails_validation(self):
        validation = validate_citations("[Physics is not required for all engineering majors [S3].]", [PHYSICS_ITEM])
        self.assertFalse(validation.valid)

    def test_grouped_citation_labels_are_recognised(self):
        from backend.app.rag.rag_pipeline import extract_citation_labels, normalize_citation_format

        normalized, changed = normalize_citation_format("AI skills are growing (S1, S4). Also [S2 and S3].")
        self.assertTrue(changed)
        self.assertEqual(extract_citation_labels(normalized), ("S1", "S4", "S2", "S3"))

    def test_mostly_unverified_answer_keeps_verified_claim_and_says_it_is_partial(self):
        answer = (
            "Computer engineering does not require much physics. "
            "PHYSICS 5A or 7A are required for all engineering majors [S3]. "
            "You will probably find physics easy. "
            "Most students skip physics entirely."
        )
        validation = validate_citations(answer, [PHYSICS_ITEM])
        self.assertTrue(validation.valid)
        self.assertNotIn("does not require much physics", validation.answer)
        self.assertIn("required for all engineering majors [S3]", validation.answer)
        self.assertIn("partial_answer", validation.repair_actions)
        self.assertNotIn("do not cover", validation.answer)

    def test_taxonomy_claim_needs_passage_support(self):
        item = {"label": "S3", "passage": "Software engineering focuses on the development and maintenance of software systems."}
        self.assertFalse(
            cited_claim_supported("Software engineering is a subset of computer engineering focused on software systems [S3].", item)
        )
        self.assertTrue(cited_claim_supported("Software engineering focuses on the development of software systems [S3].", item))

    def test_sentence_continuing_earlier_text_cannot_open_answer(self):
        from backend.app.rag.rag_pipeline import starts_with_dangling_reference

        self.assertTrue(starts_with_dangling_reference("While the report also indicates AI skills grow [S1]."))
        self.assertFalse(starts_with_dangling_reference("AI and big data skills are growing in importance [S1]."))

    def test_label_as_subject_is_rewritten_into_cited_claim(self):
        from backend.app.rag.rag_pipeline import rewrite_label_subject_sentences

        self.assertEqual(
            rewrite_label_subject_sentences("The [S1] source indicates that physics concepts form the basis of EE content."),
            "Physics concepts form the basis of EE content [S1].",
        )
        self.assertEqual(
            rewrite_label_subject_sentences("[S3] suggests that the physics series is heavily calculus-based."),
            "The physics series is heavily calculus-based [S3].",
        )
        unchanged = "[S2] highlights the versatility of programming skills."
        self.assertEqual(rewrite_label_subject_sentences(unchanged), unchanged)

    def test_bracketed_section_headers_are_parsed(self):
        cleaned = clean_answer_artifacts("[ANSWER]\nPhysics concepts form the basis of EE content [S3].\n\n[USED_SOURCES]\n[S3]")
        self.assertTrue(cleaned.startswith("ANSWER:"))
        validation = validate_citations(cleaned, [PHYSICS_ITEM])
        self.assertNotIn("ANSWER]", validation.answer)

    def test_label_starting_sentence_is_pruned_separately(self):
        from backend.app.rag.rag_pipeline import prune_unverified_sentences

        answer = "You will find physics easy. [S3] PHYSICS 5A or 7A are required for all engineering majors."
        pruned = prune_unverified_sentences(answer, [PHYSICS_ITEM])
        self.assertIsNone(pruned)  # the label-led fragment ends without its own citation pattern
        answer = "You will find physics easy. PHYSICS 5A or 7A are required for all engineering majors [S3]."
        self.assertEqual(
            prune_unverified_sentences(answer, [PHYSICS_ITEM]),
            "PHYSICS 5A or 7A are required for all engineering majors [S3].",
        )

    def test_inference_glue_between_cited_facts_is_removed(self):
        self.assertEqual(
            clean_answer_artifacts("Physics underpins EE content [S1]. This means that MATH 51 comes before physics [S3]."),
            "Physics underpins EE content [S1]. MATH 51 comes before physics [S3].",
        )

    def test_coding_and_theory_answers_count_as_on_topic(self):
        from backend.app.rag.rag_pipeline import unsupported_generated_answer_reason

        reason = unsupported_generated_answer_reason(
            "Does computer engineering have lots of coding or is it mostly theory?",
            "Computer engineering programs include hands-on programming and design laboratories alongside mathematics foundations [S1].",
            [{"label": "S1", "passage": "Programs include programming, design laboratories and mathematics foundations."}],
        )
        self.assertNotEqual(reason, "generated answer did not address the question's distinctive topic terms")

    def test_topic_coverage_accepts_word_forms(self):
        from backend.app.rag.rag_pipeline import unsupported_generated_answer_reason

        reason = unsupported_generated_answer_reason(
            "What electives can help me specialize?",
            "Technical elective courses let students shape their specialization [S1].",
            [{"label": "S1", "passage": "Technical elective courses allow students to shape their specialization."}],
        )
        self.assertNotEqual(reason, "generated answer did not address the question's distinctive topic terms")

    def test_repeated_sentence_is_removed(self):
        answer = (
            "You need skills in debugging embedded programs [S1]. "
            "You should know serial communication protocols and signaling levels [S1]. "
            "Additionally, you should know the serial communication protocols and signaling levels [S1]."
        )
        cleaned = remove_repeated_sentences(answer)
        self.assertEqual(cleaned.count("signaling levels"), 1)

    def test_homework_requests_are_out_of_scope(self):
        for question in (
            "Can you write my Python homework for me?",
            "solve my data structures assignment",
            "do my lab report please",
        ):
            with self.subTest(question=question):
                self.assertEqual(understand_query(question).kind, "out_of_scope_persona_meta")
        self.assertEqual(understand_query("How should I study for my data structures exam?").kind, "standalone_domain_question")

    def test_ok_is_not_dropped_as_filler(self):
        resolution = resolve_query("is it ok if im bad at physics, does ceng need alot of it?", None)
        self.assertIn("is it ok", resolution.resolved_question.lower())

    def test_ordinal_follow_up_uses_first_sentence_list_not_later_detail(self):
        previous = PreviousTurn(
            "What skills do I need for a career in embedded systems?",
            "You need skills in using an IDE to debug embedded programs [S1]. "
            "You should also know standards such as signaling levels, serial protocols, and bus timing [S1].",
        )
        resolution = resolve_query("can you explain the first one in more detail?", previous)
        self.assertIn("ide", resolution.resolved_question.lower())


if __name__ == "__main__":
    unittest.main()
