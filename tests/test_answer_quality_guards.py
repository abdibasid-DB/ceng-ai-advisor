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

    def test_topic_coverage_matches_short_term_as_word_prefix(self):
        from backend.app.rag.rag_pipeline import unsupported_generated_answer_reason

        reason = unsupported_generated_answer_reason(
            "Should I start with Python, Java, or C++?",
            "Starting with Python as a first programming course is common [S2].",
            [{"label": "S2", "passage": "Python is used in the first programming course."}],
        )
        self.assertIsNone(reason)

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

    def test_year_or_course_code_in_source_title_is_not_a_numeric_claim(self):
        item = {
            "label": "S3",
            "title": "The Future of Jobs Report 2025",
            "passage": "Technology should focus on enhancing rather than substituting for human capabilities.",
        }
        self.assertTrue(cited_claim_supported(
            "The Future of Jobs Report 2025 says technology should focus on enhancing rather than substituting human capabilities [S3].", item
        ))
        self.assertFalse(cited_claim_supported(
            "By 2030 technology should focus on enhancing rather than substituting human capabilities [S3].", item
        ))

    def test_number_must_describe_the_same_thing_as_in_the_passage(self):
        from backend.app.rag.rag_pipeline import number_used_as_in_passage

        item = {
            "label": "S1",
            "passage": "The general education component of this curriculum consists of 21 credits of mathematics, "
            "16 credits of natural science, and 18 credits of humanities and social science courses.",
        }
        self.assertFalse(cited_claim_supported("The curriculum requires 18 credits of mathematics in general education [S1].", item))
        self.assertTrue(cited_claim_supported("The general education component consists of 21 credits of mathematics [S1].", item))
        # A decimal comma in a Turkish passage is the same number.
        self.assertTrue(number_used_as_in_passage("11.4", "ICT graduates found a first job in 11.4 months", "bilişim ve iletişim teknolojileri (11,4 ay)"))

    def test_comparison_needs_a_comparison_in_the_passage(self):
        item = {"label": "S3", "passage": "The most crucial aspect employers seek is relevant hands-on experience from previous employment."}
        self.assertFalse(cited_claim_supported("Hands-on experience is more important than mathematics for employers [S3].", item))
        self.assertTrue(cited_claim_supported("Employers seek relevant hands-on experience from previous employment [S3].", item))

    def test_required_as_a_noun_modifier_is_not_a_requirement_claim(self):
        item = {"label": "S4", "passage": "It is up to each program to decide the quantity and level of mathematics for its graduates."}
        self.assertTrue(cited_claim_supported(
            "The quantity and level of mathematics required for graduates is up to each program to decide [S4].", item
        ))
        self.assertFalse(cited_claim_supported("Advanced mathematics is required for each program's graduates [S4].", item))

    def test_requirement_claim_needs_the_strong_word_about_the_same_subject(self):
        item = {"label": "S1", "passage": (
            "The degree credential is likely to be necessary, but it is not sufficient for a position. A successful "
            "professional must be a good communicator, a strong team player, and a person with passion to succeed."
        )}
        self.assertFalse(cited_claim_supported(
            "A strong foundation in mathematics is a fundamental requirement for many aspects of the field [S1].", item
        ))
        self.assertTrue(cited_claim_supported("A successful professional must be a good communicator and team player [S1].", item))
        internship = {"label": "S2", "passage": "Students must complete a 20 working day internship in order to graduate."}
        self.assertTrue(cited_claim_supported("Students must complete an internship to graduate [S2].", internship))

    def test_conclusion_drawn_from_a_cited_reason_needs_support_itself(self):
        item = {"label": "S4", "passage": "It is up to each program to decide the quantity and level of mathematics for its graduates."}
        self.assertFalse(cited_claim_supported(
            "You can still succeed despite weak mathematics, as each program decides the quantity and level of mathematics [S4].", item
        ))
        self.assertTrue(cited_claim_supported(
            "Each program decides the quantity and level of mathematics, as it is up to the program [S4].", item
        ))
        self.assertTrue(cited_claim_supported(
            "For graduates, as per [S4], each program decides the quantity and level of mathematics [S4].", item
        ))

    def test_modal_words_are_not_topic_terms(self):
        from backend.app.rag.rag_pipeline import unsupported_generated_answer_reason

        reason = unsupported_generated_answer_reason(
            "Will AI replace computer engineers?",
            "Workers may need re-skilling as technologies replace workers for several tasks [S1].",
            [{"label": "S1", "passage": "Workers may need up-skilling and re-skilling as technologies replace workers for several tasks."}],
        )
        self.assertIsNone(reason)

    def test_connective_is_dropped_when_the_sentence_before_was_pruned(self):
        item = {"label": "S1", "chunk_id": "src_088_chunk_001", "source_id": "src_088",
                "passage": "A master's degree can support deeper specialization, research preparation and academic careers."}
        validation = validate_citations(
            "A bachelor's degree is always enough for industry. "
            "However, a master's degree can support deeper specialization and research preparation [S1].",
            [item],
        )
        self.assertTrue(validation.valid)
        self.assertTrue(validation.answer.startswith("A master's degree can support"))

    def test_back_reference_to_a_pruned_sentence_is_dropped(self):
        from backend.app.rag.rag_pipeline import prune_unverified_sentences

        answer = (
            "PHYSICS 5A or 7A are required for all engineering majors [S3]. "
            "Most students find physics easy. "
            "It must be preceded by Calculus [S3]."
        )
        self.assertEqual(
            prune_unverified_sentences(answer, [PHYSICS_ITEM]),
            "PHYSICS 5A or 7A are required for all engineering majors [S3].",
        )

    def test_claim_cited_to_the_wrong_retrieved_passage_is_relabelled(self):
        ethics = {"label": "S4", "chunk_id": "src_067_chunk_251", "source_id": "src_067",
                  "passage": "Contrast ethical and legal issues as related to computer engineering."}
        validation = validate_citations(
            "PHYSICS 5A or 7A are required for all engineering majors [S3]. "
            "Computer engineering study contrasts ethical and legal issues [S3].",
            [PHYSICS_ITEM, ethics],
        )
        self.assertTrue(validation.valid)
        self.assertIn("ethical and legal issues [S4]", validation.answer)

    def test_unsupported_trailing_conclusion_clause_is_cut(self):
        item = {"label": "S2", "chunk_id": "src_045_chunk_370", "source_id": "src_045",
                "passage": "Emphasising real-life applications increased female participation and confidence."}
        validation = validate_citations(
            "Emphasising real-life applications increased female participation and confidence, "
            "making students more attractive to recruiters [S2].",
            [item],
        )
        self.assertTrue(validation.valid)
        self.assertNotIn("recruiters", validation.answer)
        self.assertIn("trimmed_unsupported_inference_clause", validation.repair_actions)

    def test_insufficient_marker_before_a_cited_partial_answer(self):
        item = {"label": "S1", "chunk_id": "src_127_chunk_001", "source_id": "src_127",
                "passage": "GPA screening is falling out of favor as employers adopt skills-based hiring."}
        partial = validate_citations(
            "[INSUFFICIENT_INFORMATION] The sources say GPA screening is falling out of favor as employers adopt skills-based hiring [S1].",
            [item],
        )
        self.assertTrue(partial.valid)
        self.assertNotIn("INSUFFICIENT", partial.answer)
        refusal = validate_citations("[INSUFFICIENT_INFORMATION] The context does not cover this.", [item])
        self.assertEqual(refusal.cited_labels, ())

    def test_bracket_noise_is_removed_but_citations_and_links_stay(self):
        self.assertEqual(
            clean_answer_artifacts("[Hackathons help students build projects [S2].]\n\nUSED_SOURCES: [S2]"),
            "Hackathons help students build projects [S2].\nUSED_SOURCES: [S2]",
        )
        self.assertEqual(
            clean_answer_artifacts("[OSTIM Technical University] was founded in an industrial basin [S1]."),
            "OSTIM Technical University was founded in an industrial basin [S1].",
        )
        self.assertEqual(
            clean_answer_artifacts("AI will enhance work (World Economic Forum, Not specified [S3])."),
            "AI will enhance work [S3].",
        )
        self.assertEqual(clean_answer_artifacts("See [the guide](https://x.org) [S1, S2]."), "See [the guide](https://x.org) [S1] [S2].")
        self.assertEqual(clean_answer_artifacts("Hardware matters [1]."), "Hardware matters [1].")

    def test_model_conclusion_gets_no_automatic_citation(self):
        from backend.app.rag.rag_pipeline import repair_missing_inline_citations

        conclusion = "Therefore, PHYSICS 5A or 7A are required for all engineering majors."
        _, _, unsupported = repair_missing_inline_citations(conclusion, [PHYSICS_ITEM], ())
        self.assertEqual(unsupported, (conclusion,))
        _, actions, unsupported = repair_missing_inline_citations("PHYSICS 5A or 7A are required for all engineering majors.", [PHYSICS_ITEM], ())
        self.assertIn("added_supported_inline_label", actions)
        self.assertEqual(unsupported, ())

    def test_specific_math_question_keeps_its_subject(self):
        self.assertIn("discrete math", understand_query("Do I need discrete math for software and algorithms?").retrieval_question)
        self.assertEqual(understand_query("how much math i need").retrieval_question, "How much mathematics is required in Computer Engineering?")

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
