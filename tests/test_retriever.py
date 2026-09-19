import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.retrieval_config import EMBEDDING_DIMENSION
from backend.app.rag.retriever import EXCLUDED_SOURCE_IDS, Retriever, expand_query_for_retrieval, infer_query_profile


class RetrieverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = Retriever()

    def test_retriever_initializes_and_collection_loads(self):
        self.assertEqual(self.retriever.collection_count, 803)

    def test_query_embedding_dimension_is_correct(self):
        embedding = self.retriever.encode_query("What programming languages should I learn?")
        self.assertEqual(len(embedding), EMBEDDING_DIMENSION)

    def test_top_k_returns_requested_count_when_possible(self):
        result = self.retriever.retrieve("What programming languages should a Computer Engineering student learn?", top_k=5)
        self.assertEqual(len(result["results"]), 5)

    def test_metadata_survives_retrieval(self):
        result = self.retriever.retrieve("How important are internships for students?", top_k=3)
        first = result["results"][0]
        for field in ["chunk_id", "source_id", "title", "source_name", "url", "category", "text"]:
            self.assertTrue(first[field])

    def test_results_are_sorted_by_rerank_score(self):
        result = self.retriever.retrieve("What courses are taught in Computer Engineering?", top_k=5)
        scores = [item["rerank_score"] for item in result["results"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_empty_query_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.retriever.retrieve("   ")

    def test_out_of_scope_behavior(self):
        result = self.retriever.retrieve("What is the best recipe for chocolate cake?", top_k=5)
        self.assertTrue(result["out_of_scope"])
        self.assertFalse(result["evidence_sufficient"])

    def test_excluded_source_ids_never_appear(self):
        result = self.retriever.retrieve("What technology jobs are in demand?", top_k=8)
        source_ids = {item["source_id"] for item in result["results"]}
        self.assertFalse(source_ids & EXCLUDED_SOURCE_IDS)

    def test_source_traceability_fields_exist(self):
        result = self.retriever.retrieve("Will artificial intelligence replace Computer Engineers?", top_k=5)
        for item in result["results"]:
            self.assertTrue(item["chunk_id"])
            self.assertTrue(item["source_id"])
            self.assertTrue(item["url"])

    def test_query_expansion_preserves_original_question_in_retrieval_result(self):
        question = "Can I study CENG if I have no coding experience?"
        result = self.retriever.retrieve(question, top_k=3)
        self.assertEqual(result["query"], question)
        self.assertIn(question, result["retrieval_query"])
        self.assertIn("Computer Engineering", result["retrieval_query"])
        self.assertIn("beginner programming", result["retrieval_query"])

    def test_query_expansion_leaves_unmatched_questions_unchanged(self):
        question = "What mathematics courses are in the curriculum?"
        self.assertEqual(expand_query_for_retrieval(question), question)

    def test_query_expansion_adds_ceng_and_beginner_programming_terms(self):
        expanded = expand_query_for_retrieval("I want CENG but I have no coding experience.")
        self.assertIn("Computer Engineering department", expanded)
        self.assertIn("beginner programming", expanded)

    def test_query_expansion_adds_high_school_explanation_terms(self):
        expanded = expand_query_for_retrieval("Explain Computer Engineering in simple terms for high school students.")
        self.assertIn("definition department hardware software systems", expanded)

    def test_query_expansion_adds_hardware_software_terms(self):
        expanded = expand_query_for_retrieval("Is Computer Engineering hardware or software?")
        self.assertIn("hardware software systems components", expanded)

    def test_query_expansion_adds_skills_terms(self):
        expanded = expand_query_for_retrieval("What skills should I develop before graduation?")
        self.assertIn("skills technologies programming career readiness", expanded)

    def test_query_expansion_adds_employment_industry_terms(self):
        expanded = expand_query_for_retrieval("What industries hire Computer Engineering graduates?")
        self.assertIn("information communication technology ICT employment", expanded)

    def test_query_expansion_adds_salary_market_terms(self):
        expanded = expand_query_for_retrieval("What is the average salary for Computer Engineering graduates?")
        self.assertIn("salary wage pay Turkey ICT labor market", expanded)

    def test_query_expansion_adds_international_remote_terms(self):
        expanded = expand_query_for_retrieval("Can Computer Engineers work abroad or internationally?")
        self.assertIn("international qualifications remote work", expanded)

    def test_query_expansion_adds_digital_nomad_terms(self):
        expanded = expand_query_for_retrieval("Can a Computer Engineer become a digital nomad?")
        self.assertIn("remote work hybrid work professional developers", expanded)

    def test_query_expansion_adds_startup_terms(self):
        expanded = expand_query_for_retrieval("Can I start my own software company after CENG?")
        self.assertIn("entrepreneurship business startup", expanded)

    def test_query_expansion_adds_graduate_ai_terms(self):
        expanded = expand_query_for_retrieval("Can I work in AI without a master's degree?")
        self.assertIn("graduate studies artificial intelligence", expanded)

    def test_query_expansion_adds_work_life_balance_terms(self):
        expanded = expand_query_for_retrieval("Is this career stressful for work-life balance?")
        self.assertIn("work life balance stress wellbeing burnout workload", expanded)

    def test_query_expansion_adds_misconception_terms(self):
        expanded = expand_query_for_retrieval("Do Computer Engineers spend all day writing code?")
        self.assertIn("computer engineering misconceptions", expanded)

    def test_query_expansion_adds_women_diversity_terms(self):
        expanded = expand_query_for_retrieval("Is Computer Engineering welcoming for women?")
        self.assertIn("women in computing diversity", expanded)

    def test_expanded_queries_drive_relevant_query_profiles(self):
        profile = infer_query_profile(expand_query_for_retrieval("Can a CENG graduate work internationally?"))
        self.assertIn("department_information", profile.preferred_categories)
        self.assertIn("remote_work", profile.preferred_categories)
        self.assertIn("employment", profile.preferred_categories)


if __name__ == "__main__":
    unittest.main()
