import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.rag_pipeline import (
    ANSWERED,
    ERROR,
    INSUFFICIENT_INFORMATION,
    OUT_OF_SCOPE,
    RAG_NUM_PREDICT,
    RAGPipeline,
    select_context_results,
    validate_citations,
)
from backend.app.services.llm_service import LLMResponse, OllamaTimeoutError


def retrieval_result(*, sufficient=True, out_of_scope=False):
    return {
        "query": "What is Computer Engineering?",
        "top_k": 2,
        "candidate_top_k": 4,
        "similarity_threshold": 0.3,
        "results_above_threshold": 2 if sufficient else 0,
        "top_similarity_score": 0.7 if sufficient else 0.1,
        "evidence_sufficient": sufficient,
        "out_of_scope": out_of_scope,
        "results": [
            {
                "rank": 1,
                "chunk_id": "src_001_chunk_001",
                "source_id": "src_001",
                "text": "Computer Engineering combines software, hardware, and systems topics.",
                "title": "About the Department",
                "source_name": "OSTIM Technical University",
                "url": "https://example.edu/about",
                "category": "department_information",
                "section_heading": "About",
                "similarity_score": 0.7,
                "distance": 0.3,
                "metadata": {"source_type": "official_department_page"},
            },
            {
                "rank": 2,
                "chunk_id": "src_001_chunk_002",
                "source_id": "src_001",
                "text": "Students learn engineering, computer engineering, and professional skills.",
                "title": "About the Department",
                "source_name": "OSTIM Technical University",
                "url": "https://example.edu/about",
                "category": "department_information",
                "section_heading": "About",
                "similarity_score": 0.65,
                "distance": 0.35,
                "metadata": {"source_type": "official_department_page"},
            },
        ],
    }


class FakeRetriever:
    def __init__(self, result):
        self.result = result
        self.calls = 0
        self.queries = []

    def retrieve(self, *args, **kwargs):
        self.calls += 1
        self.queries.append(args[0] if args else kwargs.get("query"))
        return self.result


class FakeLLM:
    def __init__(self, text="Computer Engineering combines software and hardware [S1].", error=None, responses=None):
        self.text = text
        self.error = error
        self.responses = list(responses or [])
        self.calls = 0
        self.prompts = []
        self.kwargs = []

    def generate(self, prompt, **kwargs):
        self.calls += 1
        self.prompts.append(prompt)
        self.kwargs.append(kwargs)
        if self.error:
            raise self.error
        if self.responses:
            text = self.responses.pop(0)
        else:
            text = self.text
        return LLMResponse(
            text=text,
            model="qwen2.5:3b",
            total_duration_seconds=1.0,
            load_duration_seconds=0.0,
            prompt_eval_count=10,
            eval_count=10,
            eval_duration_seconds=0.5,
            wall_time_seconds=1.0,
            raw={},
        )


class RAGPipelineTests(unittest.TestCase):
    def test_valid_question_invokes_llm(self):
        llm = FakeLLM()
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer("What is Computer Engineering?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertEqual(llm.calls, 1)

    def test_rag_generation_budget_has_room_for_concise_complete_answers(self):
        llm = FakeLLM()
        RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer("What is Computer Engineering?")
        self.assertEqual(RAG_NUM_PREDICT, 220)
        self.assertEqual(llm.calls, 1)
        self.assertEqual(llm.kwargs[0]["num_predict"], 220)

    def test_empty_question_error(self):
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=FakeLLM()).answer("")
        self.assertEqual(result["status"], ERROR)

    def test_whitespace_question_error(self):
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=FakeLLM()).answer("   ")
        self.assertEqual(result["status"], ERROR)

    def test_insufficient_retrieval_does_not_invoke_llm(self):
        llm = FakeLLM()
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result(sufficient=False, out_of_scope=False)),
            llm_service=llm,
        ).answer("Unsupported question")
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertFalse(result["llm_called"])
        self.assertEqual(llm.calls, 0)

    def test_out_of_scope_does_not_invoke_llm(self):
        llm = FakeLLM()
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result(sufficient=False, out_of_scope=True)),
            llm_service=llm,
        ).answer("Cake recipe?")
        self.assertEqual(result["status"], OUT_OF_SCOPE)
        self.assertFalse(result["llm_called"])
        self.assertEqual(llm.calls, 0)

    def test_specific_fact_without_matching_evidence_does_not_invoke_llm(self):
        llm = FakeLLM()
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=llm,
        ).answer("What is the exact 2026 tuition fee?")
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertFalse(result["llm_called"])
        self.assertEqual(llm.calls, 0)
        self.assertIn("unsupported_reason", result["retrieval_metadata"])

    def test_cybersecurity_without_cybersecurity_category_does_not_invoke_llm(self):
        llm = FakeLLM()
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=llm,
        ).answer("Can Computer Engineers work in cybersecurity?")
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertFalse(result["llm_called"])
        self.assertEqual(llm.calls, 0)
        self.assertIn("unsupported_reason", result["retrieval_metadata"])

    def test_placeholder_model_answer_produces_error(self):
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=FakeLLM(text="- answer text [S1]."),
        ).answer("What is CE?")
        self.assertEqual(result["status"], ERROR)
        self.assertTrue(result["llm_called"])

    def test_copied_prompt_example_produces_error(self):
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=FakeLLM(text="- CENG 213 is listed as Discrete Computing Structures [S1]."),
        ).answer("What is CE?")
        self.assertEqual(result["status"], ERROR)
        self.assertTrue(result["llm_called"])

    def test_missing_inline_citation_produces_error(self):
        llm = FakeLLM(text="Computer Engineering combines software and hardware.")
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=llm,
        ).answer("What is CE?")
        self.assertEqual(result["status"], ERROR)
        self.assertTrue(result["llm_called"])
        self.assertEqual(llm.calls, 2)
        self.assertIn("citation", result["error"])
        self.assertEqual(result["citation_metadata"]["retry_failure_reason"], "missing inline [S#] citation")
        self.assertIn("Every factual bullet or claim", llm.prompts[1])
        self.assertIn("USED_SOURCES alone is not sufficient", llm.prompts[1])
        self.assertIn("Do not invent citations", llm.prompts[1])

    def test_multiple_valid_citations_are_accepted(self):
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=FakeLLM(text="- Computer Engineering combines software and hardware [S1].\n- Students learn professional skills [S2]."),
        ).answer("What is CE?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertEqual(result["citation_metadata"]["cited_labels"], ["S1", "S2"])

    def test_uncited_answer_bullet_is_rejected(self):
        llm = FakeLLM(
            responses=[
                "- Computer Engineering combines software and hardware [S1].\n- Students learn professional skills.",
                "- Computer Engineering combines software and hardware [S1].\n- Students learn professional skills [S2].",
            ]
        )
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=llm,
        ).answer("What is CE?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertEqual(llm.calls, 2)
        self.assertTrue(result["citation_metadata"]["retry_attempted"])
        self.assertTrue(result["citation_metadata"]["retry_successful"])

    def test_truncated_cited_answer_bullet_is_rejected(self):
        llm = FakeLLM(
            responses=[
                "- Computer Engineering combines software and hardware [S1].\n- Students learn professional",
                "- Computer Engineering combines software and hardware [S1].\n- Students learn professional skills [S2].",
            ]
        )
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=llm,
        ).answer("What is CE?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertEqual(llm.calls, 2)
        self.assertTrue(result["citation_metadata"]["retry_attempted"])
        self.assertTrue(result["citation_metadata"]["retry_successful"])

    def test_nonexistent_citation_is_rejected_after_one_failed_retry(self):
        llm = FakeLLM(text="- Computer Engineering combines software and hardware [S8].")
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=llm,
        ).answer("What is CE?")
        self.assertEqual(result["status"], ERROR)
        self.assertEqual(llm.calls, 2)
        self.assertIn("S8", result["error"])
        self.assertIn("citation labels are not in retrieved context", result["citation_metadata"]["retry_failure_reason"])

    def test_malformed_s_spacing_citation_is_normalized(self):
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=FakeLLM(text="- Computer Engineering combines software and hardware [S 1]."),
        ).answer("What is CE?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertIn("[S1]", result["answer"])
        self.assertTrue(result["citation_metadata"]["normalized"])

    def test_numeric_citation_is_not_converted(self):
        llm = FakeLLM(text="- Computer Engineering combines software and hardware [1].")
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=llm,
        ).answer("What is CE?")
        self.assertEqual(result["status"], ERROR)
        self.assertEqual(llm.calls, 2)

    def test_controlled_retry_can_repair_missing_citation(self):
        llm = FakeLLM(
            responses=[
                "- Computer Engineering combines software and hardware.",
                "- Computer Engineering combines software and hardware [S1].",
            ]
        )
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=llm,
        ).answer("What is CE?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertEqual(llm.calls, 2)
        self.assertTrue(result["citation_metadata"]["retry_attempted"])
        self.assertTrue(result["citation_metadata"]["retry_successful"])

    def test_failed_retry_produces_safe_error(self):
        llm = FakeLLM(
            responses=[
                "- Computer Engineering combines software and hardware.",
                "- Computer Engineering combines software and hardware.",
            ]
        )
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=llm,
        ).answer("What is CE?")
        self.assertEqual(result["status"], ERROR)
        self.assertEqual(llm.calls, 2)
        self.assertFalse(result["citation_metadata"]["retry_successful"])
        self.assertEqual(result["answer"], "The local RAG pipeline could not complete the request safely.")
        self.assertNotIn("Computer Engineering combines", result["answer"])

    def test_salary_question_without_salary_evidence_is_not_forced_to_generation(self):
        llm = FakeLLM(text="- The average salary is 100000 TRY [S1].")
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer(
            "What is the average starting salary for Computer Engineering graduates?"
        )
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertFalse(result["llm_called"])
        self.assertEqual(llm.calls, 0)
        self.assertIn("unsupported_reason", result["retrieval_metadata"])

    def test_source_mapping_uses_retrieved_context_labels(self):
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=FakeLLM()).answer("What is CE?")
        self.assertEqual(result["citation_metadata"]["available_labels"], ["S1", "S2"])
        self.assertEqual(result["citation_metadata"]["cited_labels"], ["S1"])

    def test_used_sources_line_is_not_returned_as_answer_text(self):
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=FakeLLM(text="ANSWER:\n- Computer Engineering combines software and hardware [S1].\nUSED_SOURCES:\nS1"),
        ).answer("What is CE?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertNotIn("USED_SOURCES", result["answer"])

    def test_natural_insufficient_answer_sets_insufficient_status(self):
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=FakeLLM(text="I don't have enough reliable information in the current knowledge base to answer that question."),
        ).answer("What is CE?")
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertFalse(result["sources"])

    def test_ai_replacement_question_without_direct_evidence_skips_llm(self):
        llm = FakeLLM()
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer(
            "Will AI replace Computer Engineers?"
        )
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertFalse(result["llm_called"])
        self.assertEqual(llm.calls, 0)
        self.assertIn("unsupported_reason", result["retrieval_metadata"])

    def test_gpa_project_question_without_direct_evidence_skips_llm(self):
        llm = FakeLLM()
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer(
            "Should I focus more on GPA, projects, or internships?"
        )
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertFalse(result["llm_called"])
        self.assertEqual(llm.calls, 0)
        self.assertIn("unsupported_reason", result["retrieval_metadata"])

    def test_curriculum_context_prefers_official_curriculum_sources(self):
        results = [
            {
                "chunk_id": "src_039_chunk_001",
                "source_id": "src_039",
                "category": "programming",
                "metadata": {"source_type": "university_academic_advising_resource"},
            },
            {
                "chunk_id": "src_004_chunk_001",
                "source_id": "src_004",
                "category": "curriculum",
                "metadata": {"source_type": "course_descriptions"},
            },
            {
                "chunk_id": "src_003_chunk_001",
                "source_id": "src_003",
                "category": "curriculum",
                "metadata": {"source_type": "curriculum_document"},
            },
        ]
        selected = select_context_results("What courses are taught?", results)
        self.assertEqual([item["source_id"] for item in selected[:2]], ["src_004", "src_003"])

    def test_definition_context_prefers_department_information(self):
        results = [
            {"chunk_id": "src_004_chunk_001", "source_id": "src_004", "category": "curriculum", "title": "Course Contents"},
            {
                "chunk_id": "src_001_chunk_001",
                "source_id": "src_001",
                "category": "department_information",
                "title": "About the Department",
            },
            {"chunk_id": "src_003_chunk_001", "source_id": "src_003", "category": "curriculum", "title": "Curriculum"},
        ]
        selected = select_context_results("What is Computer Engineering?", results)
        self.assertEqual([item["source_id"] for item in selected], ["src_001"])

    def test_non_curriculum_context_prefers_unique_sources(self):
        results = [
            {"chunk_id": "src_017_chunk_001", "source_id": "src_017"},
            {"chunk_id": "src_017_chunk_002", "source_id": "src_017"},
            {"chunk_id": "src_014_chunk_001", "source_id": "src_014"},
            {"chunk_id": "src_016_chunk_001", "source_id": "src_016"},
        ]
        selected = select_context_results("What jobs can I do after graduating?", results)
        self.assertEqual([item["source_id"] for item in selected[:3]], ["src_017", "src_014", "src_016"])

    def test_retrieved_context_is_passed_into_prompt(self):
        llm = FakeLLM()
        RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer("What is Computer Engineering?")
        self.assertIn("[S1]", llm.prompts[0])
        self.assertIn("Computer Engineering combines software", llm.prompts[0])

    def test_conversation_context_augments_retrieval_query(self):
        retriever = FakeRetriever(retrieval_result())
        RAGPipeline(retriever=retriever, llm_service=FakeLLM()).answer(
            "What about internships?",
            conversation_context="Previous user question 1: What programming languages are taught?",
        )
        self.assertIn("Previous user question 1", retriever.queries[0])
        self.assertIn("Current follow-up question: What about internships?", retriever.queries[0])

    def test_conversation_context_is_marked_as_non_evidence_in_prompt(self):
        llm = FakeLLM()
        RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer(
            "What about internships?",
            conversation_context="Previous user question 1: What programming languages are taught?",
        )
        self.assertIn("CONVERSATION CONTEXT FOR REFERENCE RESOLUTION ONLY", llm.prompts[0])
        self.assertIn("Conversation context is not factual evidence", llm.prompts[0])
        self.assertIn("Cite and rely only on CONTEXT passages", llm.prompts[0])

    def test_source_traceability_survives(self):
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=FakeLLM()).answer("What is CE?")
        self.assertEqual(result["retrieved_context"][0]["source_id"], "src_001")
        self.assertEqual(result["retrieved_context"][0]["chunk_id"], "src_001_chunk_001")
        self.assertEqual(result["retrieved_context"][0]["url"], "https://example.edu/about")

    def test_source_deduplication(self):
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=FakeLLM()).answer("What is CE?")
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(result["sources"][0]["supporting_chunk_ids"], ["src_001_chunk_001", "src_001_chunk_002"])

    def test_llm_failure_produces_error_status(self):
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=FakeLLM(error=RuntimeError("boom")),
        ).answer("What is CE?")
        self.assertEqual(result["status"], ERROR)

    def test_timeout_handling(self):
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=FakeLLM(error=OllamaTimeoutError("timeout")),
        ).answer("What is CE?")
        self.assertEqual(result["status"], ERROR)


if __name__ == "__main__":
    unittest.main()
