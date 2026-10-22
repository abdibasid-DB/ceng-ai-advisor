import sys
import unittest
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.query_understanding import resolve_query, understand_query


@dataclass(frozen=True)
class PreviousTurn:
    question: str
    answer: str = ""


def topic_names(understanding):
    return {topic.name for topic in understanding.topics}


class QueryUnderstandingTests(unittest.TestCase):
    def test_multi_topic_electives_preserves_cybersecurity_and_ai(self):
        understanding = understand_query("what electives should I choose if I like cybersecurity and AI?")
        self.assertEqual(understanding.kind, "standalone_domain_question")
        self.assertTrue({"electives", "cybersecurity", "ai"}.issubset(topic_names(understanding)))
        self.assertIn("cybersecurity", understanding.retrieval_question.lower())
        self.assertIn("ai", understanding.retrieval_question.lower())
        self.assertIn("electives", understanding.retrieval_question.lower())

    def test_multi_topic_low_gpa_projects_internship_preserved(self):
        understanding = understand_query("my GPA is low but I have projects, can I still get an internship?")
        self.assertEqual(understanding.kind, "standalone_domain_question")
        self.assertTrue({"gpa", "projects", "internships"}.issubset(topic_names(understanding)))
        self.assertIn("low_gpa", understanding.constraints)
        self.assertIn("GPA", understanding.retrieval_question)
        self.assertIn("projects", understanding.retrieval_question)
        self.assertIn("internship", understanding.retrieval_question)

    def test_unseen_student_questions_without_explicit_computer_engineering_are_domain(self):
        examples = {
            "what should I put on my CV as a first year student": {"cv"},
            "should i buy a laptop before starting computer engineering": {"laptop", "computer_engineering"},
            "can computer engineering students do erasmus": {"computer_engineering", "erasmus"},
            "how can I prepare for interviews as a computer engineering student": {"interviews", "computer_engineering"},
        }
        for question, expected_topics in examples.items():
            with self.subTest(question=question):
                understanding = understand_query(question)
                self.assertEqual(understanding.kind, "standalone_domain_question")
                self.assertTrue(expected_topics.issubset(topic_names(understanding)))
                self.assertIsNotNone(understanding.retrieval_question)

    def test_typos_bad_grammar_and_abbreviations_keep_domain_intent(self):
        examples = {
            "what is computer engneering": {"computer_engineering", "definition"},
            "which programing language good for ai": {"programming", "ai"},
            "i dont have internship what should i do": {"internships"},
        }
        for question, expected_topics in examples.items():
            with self.subTest(question=question):
                understanding = understand_query(question)
                self.assertEqual(understanding.kind, "standalone_domain_question")
                self.assertTrue(expected_topics.issubset(topic_names(understanding)))

    def test_academic_regulations_are_domain_questions(self):
        examples = {
            "Which official regulation explains exams and grading?": {"academic_regulations"},
            "where can I find exam grading rules": {"academic_regulations"},
            "what regulation covers course exams?": {"academic_regulations", "curriculum"},
        }
        for question, expected_topics in examples.items():
            with self.subTest(question=question):
                understanding = understand_query(question)
                self.assertEqual(understanding.kind, "standalone_domain_question")
                self.assertTrue(expected_topics.issubset(topic_names(understanding)))
                self.assertIsNotNone(understanding.retrieval_question)

    def test_linux_and_operating_system_questions_are_domain_questions(self):
        examples = {
            "linux important?": {"operating_systems"},
            "is Unix useful for computer engineering students": {"operating_systems", "computer_engineering"},
            "should I learn operating systems?": {"operating_systems"},
        }
        for question, expected_topics in examples.items():
            with self.subTest(question=question):
                understanding = understand_query(question)
                self.assertEqual(understanding.kind, "standalone_domain_question")
                self.assertTrue(expected_topics.issubset(topic_names(understanding)))

    def test_practical_skill_questions_are_domain_questions(self):
        examples = {
            "How do I become better at algorithms?": {"programming"},
            "Should I learn testing and debugging?": {"software"},
            "How important is command line usage?": {"software"},
            "How important is computer architecture?": {"hardware"},
            "Should I learn Arduino or FPGA first?": {"hardware"},
            "How can I start ethical hacking safely as a student?": {"cybersecurity"},
            "cybersec certs or degree which matters?": {"cybersecurity"},
            "Are hackathons useful for computer engineering students?": {"projects", "student_life"},
        }
        for question, expected_topics in examples.items():
            with self.subTest(question=question):
                understanding = understand_query(question)
                self.assertEqual(understanding.kind, "standalone_domain_question")
                self.assertTrue(expected_topics.issubset(topic_names(understanding)))

    def test_it_comparison_is_not_collapsed_to_definition(self):
        understanding = understand_query("What is the difference between IT and Computer Engineering?")
        self.assertEqual(understanding.kind, "standalone_domain_question")
        self.assertIn("difference between it and computer engineering", understanding.retrieval_question.lower())
        self.assertNotEqual(understanding.retrieval_question, "What is Computer Engineering?")

    def test_informal_typos_preserve_tooling_intent(self):
        understanding = understand_query("git hub learn necessery?")
        self.assertEqual(understanding.kind, "standalone_domain_question")
        self.assertIn("projects", topic_names(understanding))
        self.assertIn("github", understanding.normalized_question.lower())

    def test_university_clubs_and_student_communities_are_domain_questions(self):
        examples = {
            "OSTIMTECH Social clubs/student communities": {"student_life"},
            "does OSTIM Technical University have student clubs?": {"student_life"},
            "social communities for students at ostim": {"student_life"},
        }
        for question, expected_topics in examples.items():
            with self.subTest(question=question):
                understanding = understand_query(question)
                self.assertEqual(understanding.kind, "standalone_domain_question")
                self.assertTrue(expected_topics.issubset(topic_names(understanding)))
                self.assertIn("OSTIM Technical University", understanding.entities)

    def test_contextual_short_questions_use_previous_referent(self):
        previous = PreviousTurn("Tell me about AI in Computer Engineering.")
        why = resolve_query("why?", previous)
        which_one = resolve_query("which one?", previous)
        self.assertEqual(why.kind, "contextual_follow_up")
        self.assertIn("AI in Computer Engineering", why.resolved_question)
        self.assertEqual(which_one.kind, "contextual_follow_up")
        self.assertIn("AI in Computer Engineering", which_one.resolved_question)

    def test_contextual_skills_follow_up_uses_domain_previous_turn(self):
        previous = PreviousTurn("Can Computer Engineers work in cybersecurity?")
        result = resolve_query("What skills should I build?", previous)
        self.assertEqual(result.kind, "contextual_follow_up")
        self.assertIn("cybersecurity", result.resolved_question.lower())
        self.assertIn("skills", result.resolved_question.lower())

    def test_contextual_short_advice_and_choice_follow_ups_use_previous_turn(self):
        math_previous = PreviousTurn("I am weak at math.")
        prepare = resolve_query("How can I prepare before first year?", math_previous)
        self.assertEqual(prepare.kind, "contextual_follow_up")
        self.assertIn("math", prepare.resolved_question.lower())

        programming_previous = PreviousTurn("Should I learn Python first?")
        cpp = resolve_query("or C++?", programming_previous)
        self.assertEqual(cpp.kind, "contextual_follow_up")
        self.assertIn("python", cpp.resolved_question.lower())

    def test_explicit_skills_question_stays_standalone_despite_history(self):
        previous = PreviousTurn("Can Computer Engineers work in cybersecurity?")
        result = resolve_query("What skills should Computer Engineering students build?", previous)
        self.assertEqual(result.kind, "standalone_domain_question")
        self.assertIn("computer engineering", result.resolved_question.lower())

    def test_unrelated_history_does_not_contaminate_generic_skills_question(self):
        previous = PreviousTurn("What is the weather today?")
        result = resolve_query("What skills should I build?", previous)
        self.assertEqual(result.kind, "standalone_domain_question")
        self.assertNotIn("weather", result.resolved_question.lower())

    def test_vague_follow_up_without_referent_requires_clarification(self):
        understanding = understand_query("what about that?")
        self.assertEqual(understanding.kind, "vague_no_referent")
        self.assertTrue(understanding.requires_clarification)
        self.assertTrue(understanding.requires_context)

    def test_source_follow_up_without_referent_requires_clarification(self):
        understanding = understand_query("what is your source?")
        self.assertEqual(understanding.kind, "vague_no_referent")
        self.assertTrue(understanding.is_source_follow_up)
        self.assertTrue(understanding.requires_clarification)

    def test_out_of_domain_negatives_do_not_become_domain_questions(self):
        for question in ("football transfer news", "make me a cake", "what is the weather today", "which social clubs are best in London", "Can you help me with pizza?"):
            with self.subTest(question=question):
                understanding = understand_query(question)
                self.assertEqual(understanding.kind, "out_of_scope_persona_meta")
                self.assertTrue(understanding.is_out_of_domain)

    def test_assistant_orientation_is_help_with_or_without_domain_history(self):
        questions = (
            "what can I ask you?",
            "what should students ask you?",
            "who are you?",
            "what are you?",
            "what can you help with?",
            "what can you help me with?",
            "how do you work?",
            "what can you do?",
            "what topics do you cover?",
            "how does this chatbot work?",
            "hey what can i ask u about?",
            "help",
            "Help me!",
        )
        for previous in (None, PreviousTurn("Who are the academic staff at OSTIM?")):
            for question in questions:
                with self.subTest(question=question, previous=previous):
                    result = resolve_query(question, previous)
                    self.assertEqual(result.kind, "assistant_help")
                    self.assertIsNone(result.resolved_question)
                    self.assertFalse(result.understanding.is_out_of_domain)
                    self.assertFalse(result.understanding.requires_clarification)

    def test_help_wording_does_not_capture_domain_questions(self):
        for question in (
            "What can you tell me about internships?",
            "How do computer networks work?",
            "What should students ask you about programming?",
        ):
            with self.subTest(question=question):
                self.assertEqual(understand_query(question).kind, "standalone_domain_question")

    def test_external_tasks_with_domain_words_stay_out_of_scope(self):
        for question in (
            "Can you write my internship report for me?",
            "Tell me the current exchange rate for tuition payment.",
            "What is the best laptop deal today?",
            "Translate this legal contract.",
        ):
            with self.subTest(question=question):
                understanding = understand_query(question)
                self.assertEqual(understanding.kind, "out_of_scope_persona_meta")
                self.assertTrue(understanding.is_out_of_domain)

    def test_informal_and_misspelled_questions_are_normalized(self):
        cases = {
            "wats the diffrence between computer enginering and software enginering?": "difference between computer engineering and software engineering",
            "hw do i get an internshp as a 2nd year ceng student": "how do i get an internship",
            "bro is data structures rly that important or nah": "is data structures really that important",
            "which programing languges shud i learn first for ceng": "which programming language should i learn first",
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                resolution = resolve_query(question, None)
                self.assertEqual(resolution.kind, "standalone_domain_question")
                self.assertIn(expected, resolution.resolved_question.lower())
                self.assertNotIn("bro", resolution.resolved_question.lower().split())

    def test_real_inflections_are_not_spell_corrected(self):
        understanding = understand_query("who developed this advisor")
        self.assertEqual(understanding.kind, "out_of_scope_persona_meta")
        self.assertIn("graduated", understand_query("I graduated in computer engineering").normalized_question)

    def test_ordinal_follow_up_resolves_item_from_previous_answer(self):
        previous = PreviousTurn(
            "What skills do I need for embedded systems?",
            "Embedded systems work needs skills such as C programming, microcontroller interfacing, and digital logic design [S1].",
        )
        for question, expected in (
            ("can you explain the first one in more detail?", "c programming"),
            ("what about the second one?", "microcontroller interfacing"),
            ("tell me more about the last point", "digital logic design"),
        ):
            with self.subTest(question=question):
                resolution = resolve_query(question, previous)
                self.assertEqual(resolution.kind, "contextual_follow_up")
                self.assertIn(expected, resolution.resolved_question.lower())
                self.assertNotIn("[s1]", resolution.resolved_question.lower())

    def test_ordinal_follow_up_uses_bulleted_previous_answer(self):
        previous = PreviousTurn(
            "What projects should I build for hardware?",
            "- Build an Arduino sensor project [S1].\n- Design a simple FPGA counter [S2].",
        )
        resolution = resolve_query("explain the second one", previous)
        self.assertIn("fpga counter", resolution.resolved_question.lower())

    def test_pronoun_follow_up_with_generic_anchor_uses_previous_topic(self):
        previous = PreviousTurn("Tell me about machine learning in computer engineering.")
        resolution = resolve_query("what jobs use it?", previous)
        self.assertEqual(resolution.kind, "contextual_follow_up")
        self.assertIn("machine learning", resolution.resolved_question.lower())

    def test_specific_what_is_question_is_not_rewritten_to_definition(self):
        resolution = resolve_query("What is the exact job placement rate of OSTIM CENG graduates in 2026?", None)
        self.assertIn("placement rate", resolution.resolved_question.lower())
        self.assertEqual(resolve_query("what is ceng", None).resolved_question, "What is Computer Engineering?")
        self.assertEqual(resolve_query("What is computer engineering about?", None).resolved_question, "What is Computer Engineering?")

    def test_additive_follow_up_keeps_previous_topic(self):
        resolution = resolve_query("Is Linux important too?", PreviousTurn("I want cybersecurity."))
        self.assertEqual(resolution.kind, "contextual_follow_up")
        self.assertIn("cybersecurity", resolution.resolved_question.lower())
        self.assertIn("linux", resolution.resolved_question.lower())
        self.assertEqual(resolve_query("Is Linux important too?", None).kind, "standalone_domain_question")

    def test_pronoun_question_with_specific_subject_stays_standalone(self):
        previous = PreviousTurn("Tell me about machine learning in computer engineering.")
        resolution = resolve_query("Is it hard to get a job as a computer engineer?", previous)
        self.assertEqual(resolution.kind, "standalone_domain_question")


if __name__ == "__main__":
    unittest.main()
