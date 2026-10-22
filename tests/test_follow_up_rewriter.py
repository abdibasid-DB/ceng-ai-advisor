import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.api.chat import ConversationTurn, apply_follow_up_rewrite, attach_resolution_metadata
from backend.app.query_understanding import resolve_query
from backend.app.services.follow_up_rewriter import build_rewrite_prompt, clean_rewrite, needs_rewrite
from tests.test_rag_pipeline import FakeLLM


PREVIOUS = ConversationTurn(
    question="I prefer hardware.",
    status="answered",
    answer="Hardware work includes embedded systems and FPGA design [S1].",
)


class FollowUpRewriterTests(unittest.TestCase):
    def test_follow_up_and_reference_questions_need_rewrite_only_with_history(self):
        self.assertTrue(needs_rewrite("What projects should I build?", "contextual_follow_up", True))
        self.assertTrue(needs_rewrite("Is that hard to learn?", "standalone_domain_question", True))
        self.assertTrue(needs_rewrite("What about the first one?", "standalone_domain_question", True))
        self.assertFalse(needs_rewrite("Is that hard to learn?", "standalone_domain_question", False))
        self.assertFalse(needs_rewrite("What is Computer Engineering?", "standalone_domain_question", True))
        self.assertFalse(needs_rewrite("Is it raining?", "out_of_scope_persona_meta", True))

    def test_prompt_has_last_two_turns_and_forbids_answering(self):
        turns = [ConversationTurn(question=f"Question {n}?", status="answered", answer=f"Answer {n} [S1].") for n in range(3)]
        prompt = build_rewrite_prompt(turns, "What about that?")
        self.assertNotIn("Question 0?", prompt)
        self.assertIn("Student: Question 1?", prompt)
        self.assertIn("Advisor: Answer 2 .", prompt.replace("  ", " "))
        self.assertNotIn("[S1]", prompt)
        self.assertIn("Do not answer the question", prompt)

    def test_clean_rewrite_keeps_one_question(self):
        self.assertEqual(clean_rewrite('Standalone question: "What hardware projects should I build?"\n'), "What hardware projects should I build?")
        self.assertIsNone(clean_rewrite(""))
        self.assertIsNone(clean_rewrite("INSUFFICIENT_INFORMATION"))
        self.assertIsNone(clean_rewrite("Build an FPGA project [S1]."))
        self.assertIsNone(clean_rewrite("You should build robots. They teach embedded systems. Start small."))

    def test_rewrite_replaces_rule_based_resolution_and_logs_both(self):
        resolution = resolve_query("What projects should I build?", PREVIOUS)
        llm = FakeLLM(text="What hardware projects should a Computer Engineering student build?")
        rewritten = apply_follow_up_rewrite(resolution, [PREVIOUS], llm, enabled=True)
        self.assertEqual(rewritten.resolved_question, "What hardware projects should a Computer Engineering student build?")
        self.assertEqual(llm.kwargs[0]["temperature"], 0.0)
        self.assertEqual(llm.kwargs[0]["num_predict"], 60)
        metadata = attach_resolution_metadata({"retrieval_metadata": {}}, rewritten)["retrieval_metadata"]["follow_up_rewrite"]
        self.assertEqual(metadata["used"], "llm")
        self.assertEqual(metadata["rule_based"], resolution.resolved_question)
        self.assertEqual(metadata["llm_rewrite"], rewritten.resolved_question)

    def test_failed_or_empty_rewrite_keeps_rule_based_resolution(self):
        resolution = resolve_query("What projects should I build?", PREVIOUS)
        for llm in (FakeLLM(text=""), FakeLLM(error=RuntimeError("Ollama down"))):
            kept = apply_follow_up_rewrite(resolution, [PREVIOUS], llm, enabled=True)
            self.assertEqual(kept.resolved_question, resolution.resolved_question)
            self.assertEqual(kept.rewrite_metadata["used"], "rule_based")

    def test_rewrite_that_repeats_previous_question_is_rejected(self):
        previous = ConversationTurn(question="What is CENG 303?", status="answered", answer="CENG 303 covers operating systems [S1].")
        resolution = resolve_query("Is it hard?", previous)
        kept = apply_follow_up_rewrite(resolution, [previous], FakeLLM(text="What is CENG 303?"), enabled=True)
        self.assertEqual(kept.resolved_question, resolution.resolved_question)
        self.assertEqual(kept.rewrite_metadata["used"], "rule_based")

    def test_disabled_flag_skips_llm(self):
        resolution = resolve_query("What projects should I build?", PREVIOUS)
        llm = FakeLLM(text="unused")
        self.assertIs(apply_follow_up_rewrite(resolution, [PREVIOUS], llm, enabled=False), resolution)
        self.assertEqual(llm.calls, 0)


if __name__ == "__main__":
    unittest.main()
