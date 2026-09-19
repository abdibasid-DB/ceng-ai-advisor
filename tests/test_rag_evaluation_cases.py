import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = PROJECT_ROOT / "tests" / "rag_comprehensive_evaluation_cases.json"

import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_rag_quality import (
    CATEGORY_COMPATIBILITY,
    category_matches,
    classify_retrieval,
    count_matching_categories,
)


class RagEvaluationCaseSetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with CASES_PATH.open("r", encoding="utf-8") as file:
            cls.data = json.load(file)
        cls.cases = cls.data["cases"]

    def test_case_set_has_all_representative_questions(self):
        originals = [case for case in self.cases if case["case_kind"] == "original"]
        question_numbers = sorted(case["question_number"] for case in originals)

        self.assertEqual(60, len(originals))
        self.assertEqual(list(range(1, 61)), question_numbers)

    def test_case_set_has_unseen_paraphrase_coverage(self):
        paraphrased = [case for case in self.cases if case["case_kind"] == "paraphrased_unseen"]

        self.assertGreaterEqual(len(paraphrased), 15)
        self.assertEqual(20, len(paraphrased))

    def test_every_case_contains_required_evaluation_metadata(self):
        required_fields = {
            "id",
            "question",
            "case_kind",
            "expected_topic",
            "expected_categories",
            "expected_behavior",
        }
        allowed_kinds = {"original", "paraphrased_unseen"}
        allowed_behaviors = {
            "answer",
            "answer_or_refuse_if_evidence_insufficient",
            "insufficient_ok",
            "out_of_scope",
        }
        seen_ids = set()

        for case in self.cases:
            self.assertTrue(required_fields.issubset(case.keys()), case)
            self.assertNotIn(case["id"], seen_ids)
            seen_ids.add(case["id"])
            self.assertIn(case["case_kind"], allowed_kinds)
            self.assertIn(case["expected_behavior"], allowed_behaviors)
            self.assertIsInstance(case["expected_categories"], list)
            self.assertGreater(len(case["expected_categories"]), 0)
            self.assertTrue(case["question"].strip())

    def test_declared_case_count_matches_cases(self):
        self.assertEqual(self.data["case_count"], len(self.cases))


class RagEvaluationCategoryCompatibilityTest(unittest.TestCase):
    def test_declared_aliases_are_narrow_and_explicit(self):
        self.assertEqual(("artificial_intelligence",), CATEGORY_COMPATIBILITY["AI"])
        self.assertEqual(("skills_and_technologies",), CATEGORY_COMPATIBILITY["skills"])
        self.assertEqual(("curriculum",), CATEGORY_COMPATIBILITY["mathematics"])
        self.assertEqual(("work_life_balance",), CATEGORY_COMPATIBILITY["remote_work"])

    def test_exact_category_match_still_works(self):
        self.assertTrue(category_matches("employment", ["employment"]))
        self.assertTrue(category_matches("curriculum", ["curriculum"]))

    def test_category_aliases_match_only_documented_compatible_categories(self):
        self.assertTrue(category_matches("artificial_intelligence", ["AI"]))
        self.assertTrue(category_matches("skills_and_technologies", ["skills"]))
        self.assertTrue(category_matches("curriculum", ["mathematics"]))
        self.assertTrue(category_matches("career_opportunities", ["employment"]))
        self.assertTrue(category_matches("work_life_balance", ["remote_work"]))

        self.assertFalse(category_matches("future_technologies", ["AI"]))
        self.assertFalse(category_matches("employment", ["remote_work"]))
        self.assertFalse(category_matches("student_life", ["skills"]))

    def test_matching_count_uses_compatibility_without_collapsing_all_related_categories(self):
        categories = ["artificial_intelligence", "skills_and_technologies", "student_life"]

        self.assertEqual(2, count_matching_categories(categories, ["AI", "skills"]))
        self.assertEqual(0, count_matching_categories(categories, ["remote_work", "employment"]))

    def test_classify_retrieval_uses_category_compatibility(self):
        retrieved_context = [
            {"category": "artificial_intelligence"},
            {"category": "skills_and_technologies"},
        ]
        retrieval_metadata = {
            "evidence_sufficient": True,
            "out_of_scope": False,
            "top_similarity_score": 0.5,
        }

        self.assertEqual(
            "Highly relevant",
            classify_retrieval(retrieved_context, retrieval_metadata, ["AI", "skills"], "answer"),
        )


if __name__ == "__main__":
    unittest.main()
