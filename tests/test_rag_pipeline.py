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
    build_context,
    select_context_results,
    unsupported_answerability_reason,
    unsupported_category_reason,
    unsupported_generated_answer_reason,
    unsupported_claim_reason,
    unsupported_specific_fact_reason,
    validate_citations,
)
from backend.app.services.llm_service import LLMResponse, LLMStreamChunk, OllamaTimeoutError


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


class FakeStreamingLLM(FakeLLM):
    def generate_stream(self, prompt, **kwargs):
        self.prompts.append(prompt)
        yield LLMStreamChunk(text=self.text, done=True, model="qwen2.5:3b")


class RAGPipelineTests(unittest.TestCase):

    def assert_overreach_withheld(self, result, phrase):
        """An overreaching generation is replaced by a verbatim source excerpt or refused, never shown."""
        self.assertNotIn(phrase.lower(), (result["answer"] or "").lower())
        if result["status"] == ANSWERED:
            self.assertTrue(result["answer"].startswith("The retrieved source states:"), result["answer"])
        else:
            self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
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

    def test_missing_inline_citation_produces_safe_insufficient_answer(self):
        llm = FakeLLM(text="Computer Engineering guarantees a high-paying job after graduation.")
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=llm,
        ).answer("What is CE?")
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertTrue(result["llm_called"])
        self.assertEqual(llm.calls, 2)
        self.assertIsNone(result["error"])
        self.assertFalse(result["sources"])
        self.assertIn("unsupported claim", result["retrieval_metadata"]["unsupported_reason"])
        self.assertTrue(result["citation_metadata"]["valid"])
        self.assertEqual(result["citation_metadata"]["cited_labels"], [])
        self.assertTrue(result["citation_metadata"]["discarded_invalid_generation"])
        self.assertEqual(result["citation_metadata"]["retry_failure_reason"], "unsupported claim could not be matched to retrieved evidence")
        self.assertIn("Every factual sentence in ANSWER", llm.prompts[1])
        self.assertIn("USED_SOURCES alone is not sufficient", llm.prompts[1])
        self.assertIn("Do not invent citations", llm.prompts[1])

    def test_grounded_uncited_answer_is_repaired_without_retry(self):
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=FakeLLM(text="Computer Engineering combines software, hardware, and systems topics."),
        ).answer("What is CE?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertEqual(result["answer"], "Computer Engineering combines software, hardware, and systems topics [S1].")
        self.assertEqual(result["citation_metadata"]["cited_labels"], ["S1"])
        self.assertEqual(result["citation_metadata"]["generations_attempted"], 1)
        self.assertIn("added_supported_inline_label", result["citation_metadata"]["repair_actions"])

    def test_end_only_citation_is_moved_inline_when_supported(self):
        answer = "Computer Engineering combines software, hardware, and systems topics.\nSources: [S1]"
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=FakeLLM(text=answer),
        ).answer("What is CE?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertEqual(result["answer"], "Computer Engineering combines software, hardware, and systems topics [S1].")
        self.assertEqual(result["citation_metadata"]["generations_attempted"], 1)
        self.assertIn("removed_trailing_source_labels", result["citation_metadata"]["repair_actions"])

    def test_citation_only_tail_is_removed_after_cited_answer(self):
        answer = "Computer Engineering combines software and hardware [S1]. [S1] and [S2]"
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()), llm_service=FakeLLM(text=answer)
        ).answer("What is CE?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertEqual(result["answer"], "Computer Engineering combines software and hardware [S1].")

    def test_source_name_citation_is_repaired_to_retrieved_label(self):
        answer = "Computer Engineering combines software, hardware, and systems topics (About the Department)."
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=FakeLLM(text=answer),
        ).answer("What is CE?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertEqual(result["answer"], "Computer Engineering combines software, hardware, and systems topics (About the Department) [S1].")
        self.assertIn("source_name_to_inline_label", result["citation_metadata"]["repair_actions"])

    def test_source_name_citation_is_not_enough_for_unsupported_claim(self):
        answer = "Computer Engineering guarantees a high-paying job after graduation (About the Department)."
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=FakeLLM(text=answer),
        ).answer("What is CE?")
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertIn("unsupported claim", result["retrieval_metadata"]["unsupported_reason"])

    def test_citations_do_not_validate_unrelated_paragraph_claims(self):
        answer = (
            "Computer Engineering is a computing field that sits alongside computer science, software engineering, "
            "information systems, and information technology [S1]. It focuses on preparing engineers to solve "
            "technical problems using analysis, synthesis, modeling, research, and technology transfer skills [S2]."
        )
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=FakeLLM(text=answer),
        ).answer("What is Computer Engineering?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertNotEqual(result["answer"], answer)
        self.assertNotIn("technical problems using analysis", result["answer"])

    def test_cited_number_must_appear_in_cited_passage(self):
        context = [{"label": "S1", "source_id": "src_test", "chunk_id": "src_test_1", "passage": "The course has laboratory work and weekly exercises."}]
        validation = validate_citations("The course has 28 laboratory hours [S1].", context)
        self.assertFalse(validation.valid)
        self.assertIn("does not support", validation.reason)

    def test_unrelated_cited_claim_is_not_accepted(self):
        context = [{"label": "S1", "source_id": "src_test", "chunk_id": "src_test_1", "passage": "The course covers digital logic and circuits."}]
        validation = validate_citations("Graduates are guaranteed remote jobs abroad [S1].", context)
        self.assertFalse(validation.valid)

    def test_personal_math_degree_choice_is_not_decided_by_excerpt(self):
        from backend.app.rag.rag_pipeline import extractive_partial_answer

        context = [{"label": "S1", "source_id": "src_test", "chunk_id": "src_test_1", "passage": "It is up to each program to decide the quantity and level of mathematics for its graduates."}]
        answer = extractive_partial_answer("Math is scary; should I quit CENG?", context)
        self.assertIsNone(answer)

    def test_lab_and_laboratory_are_matched_for_partial_answer(self):
        from backend.app.rag.rag_pipeline import extractive_partial_answer

        context = [{
            "label": "S1", "source_id": "src_test", "chunk_id": "src_test_1",
            "passage": "Good laboratory experiences expose students to tools and prepare them for real engineering work after graduation.",
        }]
        answer = extractive_partial_answer("How much lab work is there in Computer Engineering?", context)
        self.assertIn("laboratory experiences", answer)
        self.assertTrue(validate_citations(answer, context).valid)

    def test_cloud_security_question_rejects_generic_career_sectors(self):
        from backend.app.rag.rag_pipeline import is_career_jobs_question

        question = "Can I work in cloud security after CENG?"
        answer = "Computer Engineers work across business, industry, and government [S1]."
        self.assertFalse(is_career_jobs_question(question))
        self.assertIn("distinctive topic terms", unsupported_generated_answer_reason(
            question, answer, [{"label": "S1", "passage": answer}]
        ))

    def test_team_vs_solo_requires_evidence_about_both_options(self):
        from backend.app.rag.rag_pipeline import extractive_partial_answer

        answer = extractive_partial_answer(
            "Should they be team projects or solo? Regarding portfolio projects in Computer Engineering.",
            [{"label": "S1", "passage": "Projects and internships show practical skills for employers."}],
        )
        self.assertIsNone(answer)

    def test_paragraph_end_citation_does_not_cover_unsupported_first_sentence(self):
        llm = FakeLLM(text=(
            "Computer Engineering guarantees a high-paying job after graduation. "
            "Computer Engineering combines software and hardware [S1]."
        ))
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer("What is CE?")
        # The uncited, unsupported claim is removed; only the verified sentence remains.
        self.assertNotIn("guarantees", result["answer"])
        self.assertEqual(result["status"], ANSWERED)
        self.assertIn("combines software and hardware [S1]", result["answer"])
        self.assertIn("pruned_unverified_sentences", result["citation_metadata"]["repair_actions"])

    def test_supported_first_sentence_receives_its_own_citation(self):
        answer = (
            "Computer Engineering combines software and hardware. "
            "Students learn professional skills [S2]."
        )
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()), llm_service=FakeLLM(text=answer)
        ).answer("What is CE?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertIn("hardware [S1]. Students", result["answer"])

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
        self.assertEqual(llm.calls, 1)
        self.assertFalse(result["citation_metadata"]["retry_attempted"])
        self.assertIn("Students learn professional skills [S2].", result["answer"])

    def test_uncited_answer_paragraph_is_rejected(self):
        llm = FakeLLM(
            responses=[
                "Computer Engineering combines software and hardware [S1].\nStudents learn professional skills.",
                "Computer Engineering combines software and hardware [S1].\nStudents learn professional skills [S2].",
            ]
        )
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=llm,
        ).answer("What is CE?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertEqual(llm.calls, 1)
        self.assertFalse(result["citation_metadata"]["retry_attempted"])
        self.assertIn("Students learn professional skills [S2].", result["answer"])

    def test_truncated_cited_answer_bullet_is_dropped_not_shown(self):
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
        self.assertEqual(llm.calls, 1)
        self.assertNotIn("Students learn professional", result["answer"])
        self.assertIn("pruned_unverified_sentences", result["citation_metadata"]["repair_actions"])

    def test_pruning_keeps_verified_sentences_and_drops_unsupported_ones(self):
        llm = FakeLLM(
            text=(
                "Computer Engineering combines software and hardware [S1]. "
                "Graduates are guaranteed a job at a top company within one month [S1]."
            )
        )
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer("What is CE?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertIn("combines software and hardware", result["answer"])
        self.assertNotIn("guaranteed", result["answer"])

    def test_pruning_refuses_when_no_sentence_is_verified(self):
        llm = FakeLLM(text="Graduates are guaranteed a job at a top company within one month [S1].")
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer("What is CE?")
        self.assertNotIn("guaranteed", result["answer"])

    def test_nonexistent_citation_is_rejected_after_one_failed_retry(self):
        llm = FakeLLM(text="- Computer Engineering combines software and hardware [S8].")
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=llm,
        ).answer("What is CE?")
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertEqual(llm.calls, 2)
        self.assertIn("S8", result["retrieval_metadata"]["unsupported_reason"])
        self.assertIn("citation labels are not in retrieved context", result["citation_metadata"]["retry_failure_reason"])

    def test_malformed_s_spacing_citation_is_normalized(self):
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=FakeLLM(text="- Computer Engineering combines software and hardware [S 1]."),
        ).answer("What is CE?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertIn("[S1]", result["answer"])
        self.assertTrue(result["citation_metadata"]["normalized"])

    def test_malformed_source_word_citation_is_normalized(self):
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=FakeLLM(text="- Computer Engineering combines software and hardware [Source 1]."),
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
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertEqual(llm.calls, 2)

    def test_controlled_retry_can_repair_missing_citation(self):
        llm = FakeLLM(
            responses=[
                "- Computer Engineering guarantees a high-paying job after graduation.",
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
                "- Computer Engineering guarantees a high-paying job after graduation.",
                "- Computer Engineering guarantees a high-paying job after graduation.",
            ]
        )
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval_result()),
            llm_service=llm,
        ).answer("What is CE?")
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertEqual(llm.calls, 2)
        self.assertFalse(result["citation_metadata"]["retry_successful"])
        self.assertEqual(result["answer"], "I understand your question, but I don't currently have enough reliable information in my knowledge base to answer it.")
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

    def test_graduate_salaries_without_graduate_salary_evidence_are_not_generated(self):
        llm = FakeLLM(text="- Graduates earn strong salaries [S1].")
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer(
            "And salaries? Regarding What jobs can graduates do in Computer Engineering."
        )
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertFalse(result["llm_called"])
        self.assertEqual(llm.calls, 0)
        self.assertIn("unsupported_reason", result["retrieval_metadata"])

    def test_resolved_salary_follow_up_uses_resolved_question_for_claim_gate(self):
        llm = FakeLLM(text="- ICT wages grew, so graduates can expect competitive salaries [S1].")
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer(
            "And salaries?",
            resolved_question="and salaries? Regarding What jobs can graduates do in Computer Engineering.",
        )
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertFalse(result["llm_called"])
        self.assertEqual(llm.calls, 0)
        self.assertIn("unsupported_reason", result["retrieval_metadata"])

    def test_generic_wage_evidence_is_not_enough_for_graduate_salary_follow_up(self):
        results = [
            {
                "text": "Wages in ICT services have grown more than in the total business sector.",
                "category": "skills_and_technologies",
            },
            {
                "text": "Computer hardware engineers design and test computer-related equipment.",
                "category": "skills_and_technologies",
            },
        ]
        reason = unsupported_claim_reason("And salaries? Regarding What jobs can graduates do in Computer Engineering.", results)
        self.assertIn("salary evidence", reason)

    def test_salary_terms_and_graduate_terms_must_be_in_same_evidence_item(self):
        results = [
            {
                "text": "Starting salary data is summarized for broad ICT services.",
                "category": "skills_and_technologies",
            },
            {
                "text": "Computer Engineering graduates can work in hardware and software roles.",
                "category": "career_opportunities",
            },
        ]
        reason = unsupported_claim_reason("What salaries can Computer Engineering graduates expect?", results)
        self.assertIn("salary evidence", reason)

    def test_attendance_rule_requires_policy_level_evidence(self):
        results = [
            {
                "text": "CENG 303 includes quizzes, assignments, and an attendance item in the syllabus table.",
                "category": "curriculum",
            }
        ]
        reason = unsupported_claim_reason("What is the attendance rule for CENG courses?", results)
        self.assertIn("attendance-rule", reason)

    def test_attendance_policy_requires_policy_level_evidence(self):
        results = [
            {
                "text": "CENG 303 includes an attendance item in the syllabus table.",
                "category": "curriculum",
            }
        ]
        reason = unsupported_claim_reason("Is there a reliable attendance policy for Computer Engineering classes?", results)
        self.assertIn("attendance-rule", reason)

    def test_scholarship_question_requires_opportunity_evidence(self):
        results = [
            {
                "text": "The curriculum introduces Computer Engineering and student advising topics.",
                "category": "department_information",
            }
        ]
        reason = unsupported_claim_reason("Can I ask about scholarship opportunities?", results)
        self.assertIn("scholarship-opportunity", reason)

    def test_general_fellowship_guidance_is_not_program_scholarship_evidence(self):
        results = [
            {
                "text": "Review national fellowship programs and ask an advisor to review your statement of purpose for graduate school.",
                "category": "graduate_studies",
            }
        ]
        reason = unsupported_claim_reason("Where can I find scholarship options for the Computer Engineering program?", results)
        self.assertIn("scholarship-opportunity", reason)

    def test_scholarship_terms_and_program_anchor_must_be_in_same_evidence_item(self):
        results = [
            {
                "text": "Scholarship opportunities and financial aid may exist at some universities.",
                "category": "graduate_studies",
            },
            {
                "text": "The Computer Engineering curriculum includes hardware, software, and systems topics.",
                "category": "curriculum",
            },
        ]
        reason = unsupported_claim_reason("Can I ask about scholarship opportunities?", results)
        self.assertIn("scholarship-opportunity", reason)

    def test_hackathon_question_requires_hackathon_or_competition_evidence(self):
        results = [
            {
                "text": "Project portfolios can show programming skills and experience.",
                "category": "projects",
            }
        ]
        reason = unsupported_claim_reason("Are hackathons useful for computer engineering students?", results)
        self.assertIn("hackathons", reason)

    def test_ordered_choice_requires_evidence_about_alternatives_and_sequence(self):
        results = [
            {
                "text": "Introductory programming courses help students choose a first computing course.",
                "category": "programming",
            },
            {
                "text": "Computer Engineering includes hardware, embedded systems, and digital design.",
                "category": "curriculum",
            },
        ]
        reason = unsupported_claim_reason("Should I learn Arduino or FPGA first?", results)
        self.assertIn("learning alternatives", reason)

    def test_ordered_choice_requires_sequence_evidence_even_when_terms_exist(self):
        results = [
            {
                "text": "Laboratories can use Arduino, microcontroller, and FPGA development boards for embedded systems.",
                "category": "curriculum",
            }
        ]
        reason = unsupported_claim_reason("Should I learn Arduino or FPGA first?", results)
        self.assertIn("learning order", reason)

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
            {"chunk_id": "src_042_chunk_001", "source_id": "src_042", "category": "common_misconceptions", "title": "Curricular Guidance"},
            {
                "chunk_id": "src_001_chunk_001",
                "source_id": "src_001",
                "category": "department_information",
                "title": "About the Department",
            },
            {"chunk_id": "src_003_chunk_001", "source_id": "src_003", "category": "curriculum", "title": "Curriculum"},
        ]
        selected = select_context_results("What is Computer Engineering?", results)
        self.assertEqual([item["source_id"] for item in selected], ["src_042", "src_001"])

    def test_fields_question_prefers_specialization_context(self):
        results = [
            {"chunk_id": "src_042_chunk_001", "source_id": "src_042", "category": "common_misconceptions", "title": "Curricular Guidance"},
            {"chunk_id": "src_014_chunk_001", "source_id": "src_014", "category": "skills_and_technologies", "title": "Computer Hardware Engineers"},
            {"chunk_id": "src_043_chunk_002", "source_id": "src_043", "category": "specializations", "title": "Subdisciplines"},
        ]
        selected = select_context_results("What fields are available in Computer Engineering?", results)
        self.assertEqual(selected[0]["source_id"], "src_043")

    def test_programming_language_question_uses_official_context_in_answer(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "chunk_id": "src_126_chunk_001",
                "source_id": "src_126",
                "text": (
                    "CENG109 Programming and Computation I. CENG110 Programming and Computation II. "
                    "SENG116 Object Oriented Programming: through hands-on projects and coding exercises, students gain "
                    "practical experience in building robust software systems using object-oriented languages such as Python or C++."
                ),
                "title": "Course Contents: programming courses (CENG109, CENG110, SENG116)",
                "category": "programming",
            }
        ]
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval),
            llm_service=FakeLLM(
                text=(
                    "The OSTIM course contents include Programming and Computation I and II, and the "
                    "Object-Oriented Programming course says students use object-oriented languages such as Python or C++ [S1]."
                )
            ),
        ).answer("Which programming languages are taught in CENG?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertEqual(result["citation_metadata"]["cited_labels"], ["S1"])

    def test_programming_language_overinference_is_withheld(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "chunk_id": "src_067_chunk_130",
                "source_id": "src_067",
                "text": "Computer engineering curricula mention programming languages generally.",
                "title": "Computer Engineering Curricula 2016",
                "category": "curriculum",
            }
        ]
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval),
            llm_service=FakeLLM(
                text=(
                    "Therefore, it can be inferred that students in CENG109 and CENG110 might be introduced to "
                    "object-oriented programming languages like Python or C++ [S1]."
                )
            ),
        ).answer("Which programming languages are taught in CENG?")
        self.assert_overreach_withheld(result, "might be introduced")

    def test_programming_language_could_be_bridge_is_withheld(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "chunk_id": "src_067_chunk_130",
                "source_id": "src_067",
                "text": "Computer engineering curricula mention programming languages generally.",
                "title": "Computer Engineering Curricula 2016",
                "category": "curriculum",
            }
        ]
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval),
            llm_service=FakeLLM(
                text=(
                    "CENG109 and CENG110 do not explicitly mention languages, therefore the languages "
                    "could be either Python or C++ depending on the specific implementation [S1]."
                )
            ),
        ).answer("Which programming languages are taught in CENG?")
        self.assert_overreach_withheld(result, "could be either")

    def test_prior_programming_requirement_overreach_is_withheld(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "text": (
                    "Computer Science 61A is a rigorous introduction designed for students with some prior programming experience. "
                    "Students who haven't programmed before often get more out of CS 61A if they take another course first."
                ),
                "title": "Choosing your first computer science course",
                "category": "programming",
            }
        ]
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval),
            llm_service=FakeLLM(text="Prior programming experience is not strictly required but is beneficial for starting the computer engineering program [S1]."),
        ).answer("Do I need prior programming experience before starting Computer Engineering?")
        self.assert_overreach_withheld(result, "beneficial for starting the computer engineering program")

    def test_git_github_invalid_generation_is_withheld(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "text": (
                    "Using the command line or other interfaces, a Git repository allows interaction with history, "
                    "branches, commits, merges, and comparisons. GitHub provides project transparency and collaboration."
                ),
                "title": "About Git",
                "category": "skills_and_technologies",
            }
        ]
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval),
            llm_service=FakeLLM(responses=["Every student must learn GitHub.", "Every student must learn GitHub."]),
        ).answer("Should every student learn Git and GitHub?")
        self.assert_overreach_withheld(result, "every student must learn github")

    def test_command_line_importance_claim_requires_direct_importance_evidence(self):
        context_items = [
            {
                "label": "S1",
                "passage": "Using the command line, a Git repository allows interaction with history, branches, commits, and merges.",
            }
        ]
        reason = unsupported_generated_answer_reason(
            "How important is command line usage?",
            "Command line usage is considered a fundamental part of Computer Engineering [S1].",
            context_items,
        )
        self.assertIn("command-line importance", reason)

    def test_terminal_skill_importance_question_requires_direct_evidence_before_generation(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "text": "Computer Engineering programs include software, hardware, systems, and professional practice.",
                "title": "Computer Engineering Curricula 2016",
                "category": "curriculum",
            }
        ]
        llm = FakeLLM(text="Terminal skills are essential for Computer Engineering students [S1].")
        result = RAGPipeline(retriever=FakeRetriever(retrieval), llm_service=llm).answer(
            "Are terminal skills considered essential in Computer Engineering?"
        )
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertFalse(result["llm_called"])
        self.assertEqual(llm.calls, 0)
        self.assertIn("unsupported_reason", result["retrieval_metadata"])

    def test_command_line_importance_can_answer_bounded_supported_mention(self):
        context_items = [
            {
                "label": "S1",
                "passage": "Using the command line, a Git repository allows interaction with history, branches, commits, and merges.",
            }
        ]
        reason = unsupported_generated_answer_reason(
            "How important is command line usage?",
            "The KB does not directly rate command-line importance, but it says Git repositories can be used from the command line for history, branches, commits, and merges [S1].",
            context_items,
        )
        self.assertIsNone(reason)

    def test_future_technology_importance_claim_requires_direct_importance_evidence(self):
        context_items = [
            {
                "label": "S1",
                "passage": (
                    "CENG 316 New Trends in Computer Engineering covers advancements in Artificial Intelligence "
                    "and Machine Learning, Cloud Computing, IoT, Quantum Computing, DevOps, and Blockchain."
                ),
            }
        ]
        reason = unsupported_generated_answer_reason(
            "Which future technologies should a CENG student follow?",
            "Artificial Intelligence and Machine Learning are important future technologies for CENG students [S1].",
            context_items,
        )
        self.assertIn("rated future technologies", reason)

    def test_future_technology_overreach_is_withheld(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "chunk_id": "src_063_chunk_001",
                "source_id": "src_063",
                "text": "CENG 316 New Trends in Computer Engineering covers emerging technologies.",
                "title": "CENG 316 New Trends in Computer Engineering Course Syllabus",
                "category": "curriculum",
            }
        ]
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval),
            llm_service=FakeLLM(text="AI and machine learning will have significant growth in the future [S1]."),
        ).answer("Which future technologies should a CENG student follow?")
        self.assert_overreach_withheld(result, "significant growth in the future")

    def test_non_curriculum_context_prefers_unique_sources(self):
        results = [
            {"chunk_id": "src_017_chunk_001", "source_id": "src_017"},
            {"chunk_id": "src_017_chunk_002", "source_id": "src_017"},
            {"chunk_id": "src_014_chunk_001", "source_id": "src_014"},
            {"chunk_id": "src_016_chunk_001", "source_id": "src_016"},
        ]
        selected = select_context_results("What jobs can I do after graduating?", results)
        self.assertEqual([item["source_id"] for item in selected[:3]], ["src_017", "src_014", "src_016"])
        self.assertEqual(selected[3]["chunk_id"], "src_017_chunk_002")

    def test_long_chunk_keeps_relevant_later_sentence(self):
        from backend.app.rag.rag_pipeline import focus_passage

        text = "General curriculum introduction. " * 20 + "Digital logic teaches Boolean circuits and gates."
        focused = focus_passage(text, "What does digital logic teach?", 180)
        self.assertIn("Boolean circuits and gates", focused)

    def test_curated_note_is_not_presented_as_verbatim_publisher_text(self):
        result = {
            "source_id": "src_084", "chunk_id": "src_084_chunk_001",
            "title": "What Is an FPGA?", "source_name": "Altera",
            "text": "An FPGA is a reconfigurable integrated circuit.",
            "url": "https://www.altera.com/what-is-an-fpga",
        }
        context, prompt = build_context([result])
        self.assertTrue(context[0]["title"].startswith("Curated note:"))
        self.assertEqual(context[0]["source_type"], "curated_source_note")
        self.assertIn("summary based on Altera", prompt)

    def test_failed_generation_uses_relevant_digital_logic_excerpt(self):
        retrieval = retrieval_result()
        retrieval["results"] = [{
            **retrieval["results"][0],
            "text": "Electrical engineering related coursework typically comes from circuits, digital logic, microelectronics, signal processing, electromagnetics, control systems, and integrated circuit design.",
        }]
        llm = FakeLLM(text="Every student must complete electronics and digital logic [S1].")
        result = RAGPipeline(retriever=FakeRetriever(retrieval), llm_service=llm).answer("Do students take electronics and digital logic?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertIn("digital logic", result["answer"])
        self.assertIn("does not establish the rest", result["answer"])
        self.assertEqual(llm.calls, 1)

    def test_retrieved_context_is_passed_into_prompt(self):
        llm = FakeLLM()
        RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer("What is Computer Engineering?")
        self.assertIn("[S1]", llm.prompts[0])
        self.assertIn("Computer Engineering combines software", llm.prompts[0])

    def test_conversation_context_does_not_augment_retrieval_query(self):
        retriever = FakeRetriever(retrieval_result())
        RAGPipeline(retriever=retriever, llm_service=FakeLLM()).answer(
            "What about internships?",
            conversation_context="Previous user question 1: What programming languages are taught?",
        )
        self.assertEqual(retriever.queries[0], "What about internships?")

    def test_resolved_question_is_used_for_retrieval(self):
        retriever = FakeRetriever(retrieval_result())
        RAGPipeline(retriever=retriever, llm_service=FakeLLM()).answer(
            "Is it difficult?",
            conversation_context="Previous user question: Tell me about AI in Computer Engineering.",
            resolved_question="Is AI in Computer Engineering difficult?",
        )
        self.assertEqual(retriever.queries[0], "Is AI in Computer Engineering difficult?")

    def test_conversation_context_is_marked_as_non_evidence_in_prompt(self):
        llm = FakeLLM()
        RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer(
            "What is Computer Engineering?",
            conversation_context="Previous user question 1: What programming languages are taught?",
        )
        self.assertIn("CONVERSATION CONTEXT FOR REFERENCE RESOLUTION ONLY", llm.prompts[0])
        self.assertIn("Conversation context is not factual evidence", llm.prompts[0])
        self.assertIn("Cite and rely only on CONTEXT passages", llm.prompts[0])

    def test_answerability_gate_rejects_unrelated_high_scoring_retrieval(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "text": "About the authors. Adrienn Lawson is a data analyst and supports survey development.",
                "title": "2024 State of Tech Talent Report",
                "category": "skills_and_technologies",
                "similarity_score": 0.37,
            },
            {
                **retrieval["results"][1],
                "text": "Portfolio tools and advising resources are available to students.",
                "title": "Portfolios",
                "category": "employment",
                "similarity_score": 0.36,
            },
        ]
        llm = FakeLLM()
        result = RAGPipeline(retriever=FakeRetriever(retrieval), llm_service=llm).answer("who developed this advisor")
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertFalse(result["llm_called"])
        self.assertEqual(llm.calls, 0)
        self.assertIn("unsupported_reason", result["retrieval_metadata"])

    def test_answerability_does_not_treat_hardware_as_hard(self):
        results = [
            {
                "text": "Computer Engineering combines hardware, software, and systems topics.",
                "category": "department_information",
            }
        ]
        reason = unsupported_answerability_reason("Is Computer Engineering more focused on hardware or software?", results)
        self.assertIsNone(reason)

    def test_answerability_accepts_teamwork_collaboration_evidence(self):
        results = [
            {
                "text": "Employers value collaboration, communication, and working effectively in teams for technical careers.",
                "category": "skills_and_technologies",
            }
        ]
        reason = unsupported_answerability_reason("Is teamwork important in Computer Engineering?", results)
        self.assertIsNone(reason)

    def test_answerability_accepts_future_proof_adaptability_evidence(self):
        results = [
            {
                "text": "Future jobs reports emphasize future skills, adaptability, reskilling, and lifelong learning in technology careers.",
                "category": "future_technologies",
            }
        ]
        reason = unsupported_answerability_reason("Is Computer Engineering a future-proof career?", results)
        self.assertIsNone(reason)

    def test_answerability_accepts_portfolio_project_evidence(self):
        results = [
            {
                "text": "A portfolio can show projects, skills, GitHub examples, and experience for a resume.",
                "category": "employment",
            }
        ]
        reason = unsupported_answerability_reason("How can I build an impressive portfolio before graduation?", results)
        self.assertIsNone(reason)

    def test_answerability_accepts_linux_operating_system_evidence(self):
        results = [
            {
                "text": "Operating systems coursework covers Linux and Unix concepts, process management, and system calls.",
                "category": "curriculum",
            }
        ]
        reason = unsupported_answerability_reason("Should Computer Engineering students learn Linux?", results)
        self.assertIsNone(reason)

    def test_answerability_accepts_git_github_version_control_evidence(self):
        results = [
            {
                "text": "Students can use Git and GitHub repositories to show projects, source control habits, and portfolio evidence.",
                "category": "employment",
            }
        ]
        reason = unsupported_answerability_reason("Should I learn Git and GitHub for Computer Engineering projects?", results)
        self.assertIsNone(reason)

    def test_answerability_allows_partial_multi_topic_when_some_topics_are_supported(self):
        results = [
            {
                "text": "Computer engineering evidence covers artificial intelligence, embedded systems, hardware systems, and student projects.",
                "category": "specializations",
            }
        ]
        reason = unsupported_answerability_reason(
            "How should I think about AI, cybersecurity, embedded systems, and projects?",
            results,
        )
        self.assertIsNone(reason)

    def test_answerability_still_rejects_single_unsupported_topic(self):
        results = [
            {
                "text": "Computer engineering evidence covers artificial intelligence, embedded systems, and student projects.",
                "category": "specializations",
            }
        ]
        reason = unsupported_answerability_reason("Should I focus on cybersecurity?", results)
        self.assertIsNotNone(reason)

    def test_category_gate_allows_partial_multi_topic_when_some_topics_are_supported(self):
        results = [
            {
                "text": "Computer engineering evidence covers artificial intelligence, embedded systems, hardware systems, and student projects.",
                "category": "specializations",
            }
        ]
        reason = unsupported_category_reason(
            "How should I think about AI, cybersecurity, embedded systems, and projects?",
            results,
        )
        self.assertIsNone(reason)

    def test_answerability_keeps_hardest_major_comparison_insufficient_without_difficulty_evidence(self):
        results = [
            {
                "text": "Computer Engineering includes hardware, software, systems, curriculum, and specialization areas.",
                "category": "curriculum",
            }
        ]
        reason = unsupported_answerability_reason("Is Computer Engineering one of the hardest engineering majors?", results)
        self.assertIn("required question terms", reason)

    def test_specific_fact_rejects_weekly_study_hours_without_time_evidence(self):
        results = [
            {
                "text": "Computer Engineering students study courses in programming, mathematics, hardware, and systems.",
                "category": "curriculum",
            }
        ]
        reason = unsupported_specific_fact_reason("How many hours do Computer Engineering students typically study each week?", results)
        self.assertIn("weekly study-hour", reason)

    def test_claim_gate_rejects_highest_salary_specialization_without_comparison(self):
        results = [
            {
                "text": "The ICT sector includes employment, salaries, skills, and many technology fields in Turkey.",
                "category": "employment",
            }
        ]
        reason = unsupported_claim_reason("Which Computer Engineering specialization offers the highest salaries in Turkey?", results)
        self.assertIn("compare salaries", reason)

    def test_ai_replacement_allows_bounded_impact_advice_when_supported(self):
        results = [
            {
                "text": (
                    "AI and big data skills are expected to grow in importance. "
                    "Employers expect workers to need reskilling and upskilling to work alongside AI."
                ),
                "category": "future_technologies",
            }
        ]
        reason = unsupported_claim_reason("Will artificial intelligence replace Computer Engineers?", results)
        self.assertIsNone(reason)

    def test_ai_replacement_still_rejects_when_no_ai_impact_evidence(self):
        results = [
            {
                "text": "Computer Engineering combines software, hardware, and systems topics.",
                "category": "department_information",
            }
        ]
        reason = unsupported_claim_reason("Will artificial intelligence replace Computer Engineers?", results)
        self.assertIn("does not directly address", reason)

    def test_ai_replacement_prompt_requires_uncertainty_when_replacement_not_established(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "text": "AI and big data skills are growing, and workers need reskilling and upskilling to work alongside AI.",
                "category": "future_technologies",
                "title": "Future of Jobs",
            }
        ]
        llm = FakeLLM(
            text=(
                "The KB cannot establish whether AI will replace computer engineers, but it does show "
                "that AI and big data skills are growing and workers need upskilling [S1]."
            )
        )
        result = RAGPipeline(retriever=FakeRetriever(retrieval), llm_service=llm).answer(
            "Will artificial intelligence replace Computer Engineers?"
        )
        self.assertEqual(result["status"], ANSWERED)
        self.assertIn("cannot establish whether replacement will happen", llm.prompts[0])
        self.assertNotIn("unsupported_reason", result["retrieval_metadata"])

    def test_gpa_projects_internships_allows_supported_bounded_advice(self):
        results = [
            {
                "text": (
                    "The use of GPA as a candidate screening tool has fallen into disfavor. "
                    "Projects and portfolios show technical skills. Internship experience is important to employers."
                ),
                "category": "employment",
            }
        ]
        reason = unsupported_claim_reason(
            "Should I focus more on GPA, projects, or internships when preparing for a software career?",
            results,
        )
        self.assertIsNone(reason)

    def test_low_gpa_failed_course_projects_internships_does_not_require_curriculum_evidence(self):
        results = [
            {
                "text": (
                    "The use of GPA as a candidate screening tool has fallen into disfavor. "
                    "Projects and portfolios show technical skills. Internship experience is important to employers."
                ),
                "category": "employment",
            }
        ]
        reason = unsupported_answerability_reason(
            "I failed a course and my GPA is low; can projects and internships still help me?",
            results,
        )
        self.assertIsNone(reason)

    def test_gpa_projects_internships_still_rejects_when_component_evidence_missing(self):
        results = [
            {
                "text": "The use of GPA as a candidate screening tool has fallen into disfavor.",
                "category": "employment",
            }
        ]
        reason = unsupported_claim_reason(
            "Should I focus more on GPA, projects, or internships when preparing for a software career?",
            results,
        )
        self.assertIn("GPA, projects, and internships advice", reason)

    def test_gpa_projects_internships_prompt_disallows_universal_ranking(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "text": (
                    "GPA is one screening signal. Projects and portfolios show technical skills. "
                    "Internship experience is important to employers."
                ),
                "category": "employment",
                "title": "Career preparation",
            }
        ]
        llm = FakeLLM(
            text=(
                "The KB cannot rank GPA, projects, and internships universally [S1]. GPA can be a screening signal, "
                "projects can show technical skills, and internship experience matters to employers [S1]."
            )
        )
        result = RAGPipeline(retriever=FakeRetriever(retrieval), llm_service=llm).answer(
            "Should I focus more on GPA, projects, or internships when preparing for a software career?"
        )
        self.assertEqual(result["status"], ANSWERED)
        self.assertIn("do not invent a universal ranking", llm.prompts[0])
        self.assertNotIn("unsupported_reason", result["retrieval_metadata"])

    def test_gpa_projects_internships_generated_ranking_is_withheld(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "text": (
                    "GPA is one screening signal. Projects and portfolios show technical skills. "
                    "Internship experience is important to employers."
                ),
                "category": "employment",
                "title": "Career preparation",
            }
        ]
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval),
            llm_service=FakeLLM(
                text=(
                    "It is more advisable to focus on projects and internships over GPA because they show practical skills [S1]."
                )
            ),
        ).answer("Should I focus more on GPA, projects, or internships when preparing for a software career?")
        self.assert_overreach_withheld(result, "focus on projects and internships over GPA")

    def test_ai_replacement_generated_definite_claim_is_withheld(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "text": "AI and big data skills are growing, and workers need upskilling to work alongside AI.",
                "category": "future_technologies",
                "title": "Future of Jobs",
            }
        ]
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval),
            llm_service=FakeLLM(text="AI will not replace computer engineers because they can learn new skills [S1]."),
        ).answer("Will artificial intelligence replace Computer Engineers?")
        self.assert_overreach_withheld(result, "will not replace computer engineers")

    def test_ai_replacement_invalid_generation_is_withheld(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "text": "AI and big data skills are expected to grow in importance for workers.",
                "category": "future_technologies",
                "title": "Future of Jobs",
            },
            {
                **retrieval["results"][1],
                "text": "Rapid technological development calls for closely monitoring how AI systems evolve and anticipating shifts in skill demand.",
                "category": "skills_and_technologies",
                "title": "Skills for the digital age",
            },
        ]
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval),
            llm_service=FakeLLM(
                responses=[
                    "AI will not replace computer engineers because they can work with AI.",
                    "AI will not replace computer engineers because they can work with AI.",
                ]
            ),
        ).answer("Will artificial intelligence replace Computer Engineers?")
        self.assert_overreach_withheld(result, "will not replace computer engineers")

    def test_ai_replacement_model_insufficient_gives_no_template_answer(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "text": "AI and big data skills are expected to grow in importance for workers.",
                "category": "future_technologies",
                "title": "Future of Jobs",
            }
        ]
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval),
            llm_service=FakeLLM(text="INSUFFICIENT_INFORMATION"),
        ).answer("Will artificial intelligence replace Computer Engineers?")
        self.assert_overreach_withheld(result, "will not replace")

    def test_cybersecurity_pathway_question_accepts_cybersecurity_framework_evidence(self):
        results = [
            {
                "text": "The NICE Framework describes cybersecurity workforce roles, tasks, knowledge, and skills.",
                "title": "Workforce Framework for Cybersecurity (NICE Framework)",
                "category": "cybersecurity",
            }
        ]
        reason = unsupported_answerability_reason("How can I become a cybersecurity specialist?", results)
        self.assertIsNone(reason)

    def test_cybersecurity_certification_overreach_is_withheld(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "text": "The NICE Framework describes cybersecurity workforce roles, tasks, knowledge, and skills.",
                "title": "Workforce Framework for Cybersecurity (NICE Framework)",
                "category": "cybersecurity",
            }
        ]
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval),
            llm_service=FakeLLM(text="You should take cybersecurity courses and certifications to become a specialist [S1]."),
        ).answer("How can I become a cybersecurity specialist?")
        self.assert_overreach_withheld(result, "you should take cybersecurity courses and certifications")

    def test_cybersecurity_generic_pathway_advice_is_withheld(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "text": "The NICE Framework describes cybersecurity workforce roles, tasks, knowledge, and skills.",
                "title": "Workforce Framework for Cybersecurity (NICE Framework)",
                "category": "cybersecurity",
            }
        ]
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval),
            llm_service=FakeLLM(
                text=(
                    "You can focus on programming and data structures, develop skills in machine learning, "
                    "and continuing professional development will be beneficial [S1]."
                )
            ),
        ).answer("How can I become a cybersecurity specialist?")
        self.assert_overreach_withheld(result, "continuing professional development will be beneficial")

    def test_career_question_invalid_generation_is_withheld(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "text": (
                    "CE professionals apply their skills in a broad range of diverse career sectors that include "
                    "business, industry, government, services, organizations, and other structured entities."
                ),
                "title": "Computer Engineering Curricula 2016",
                "category": "career_opportunities",
            },
            {
                **retrieval["results"][1],
                "text": "Computer Hardware Engineers research, design, develop, or test computer or computer-related equipment.",
                "title": "Computer Hardware Engineers",
                "category": "employment",
            },
        ]
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval),
            llm_service=FakeLLM(responses=["Computer engineering graduates can work in many jobs.", "They can work in hardware."]),
        ).answer("What jobs can Computer Engineering graduates do?")
        self.assert_overreach_withheld(result, "can work in many jobs")

    def test_career_question_broad_role_overreach_is_withheld(self):
        retrieval = retrieval_result()
        retrieval["results"] = [
            {
                **retrieval["results"][0],
                "text": (
                    "CE professionals apply their skills in a broad range of diverse career sectors that include "
                    "business, industry, government, services, organizations, and other structured entities."
                ),
                "title": "Computer Engineering Curricula 2016",
                "category": "career_opportunities",
            },
            {
                **retrieval["results"][1],
                "text": "Computer Hardware Engineers research, design, develop, or test computer or computer-related equipment.",
                "title": "Computer Hardware Engineers",
                "category": "employment",
            },
        ]
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval),
            llm_service=FakeLLM(
                text=(
                    "Computer Engineering graduates can become computer programmers and mobile application developers, "
                    "and those roles require a degree [S1]."
                )
            ),
        ).answer("What jobs can Computer Engineering graduates do?")
        self.assert_overreach_withheld(result, "mobile application developers")

    def test_work_abroad_is_not_answered_with_generic_career_sectors(self):
        retrieval = retrieval_result()
        retrieval["results"] = [{
            **retrieval["results"][0],
            "text": "CE professionals work across business, industry, government, and services.",
            "category": "career_opportunities",
        }]
        result = RAGPipeline(
            retriever=FakeRetriever(retrieval),
            llm_service=FakeLLM(text="CE professionals work across business and industry [S1]."),
        ).answer("Can CENG graduates work abroad?")
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertFalse(result["llm_called"])
        self.assertIn("unsupported_reason", result["retrieval_metadata"])

    def test_personal_degree_recommendation_requires_direct_evidence(self):
        reason = unsupported_generated_answer_reason(
            "I like AI and cybersecurity but hate electronics; is CENG still a good choice and what should I learn first?",
            "CENG is still a good choice, and you should start with cybersecurity [S1].",
            [{"label": "S1", "passage": "Cybersecurity includes software and system security."}],
        )
        self.assertTrue("personal degree recommendation" in reason or "distinctive topic terms" in reason)

    def test_sample_lab_hours_cannot_become_program_total(self):
        reason = unsupported_generated_answer_reason(
            "How much lab work is there in computer engineering?",
            "Computer Engineering has 28 lab hours [S1].",
            [{"label": "S1", "passage": "One sample course has Lecture Hours: 28; Lab Hours: 28."}],
        )
        self.assertIn("sample course hours", reason)

    def test_math_foundation_is_not_a_degree_requirement(self):
        reason = unsupported_generated_answer_reason(
            "Does studying AI in CENG require linear algebra and probability?",
            "Studying AI in CENG likely requires linear algebra and probability [S1].",
            [{"label": "S1", "passage": "Linear algebra and probability are foundations for machine learning."}],
        )
        self.assertIn("unverified CENG requirement", reason)

    def test_hardware_comparison_needs_both_sides_of_comparison(self):
        passage = "Computer Engineering involves processor-based systems comprised of hardware, software, and communications components."
        reason = unsupported_generated_answer_reason(
            "Which one has more hardware? Regarding Computer Engineering vs Computer Science.",
            "Computer Engineering has more hardware than Computer Science [S1].",
            [{"label": "S1", "passage": passage}],
        )
        self.assertIn("unsupported CENG/CS hardware ranking", reason)

    def test_definition_cannot_invent_disciplinary_position(self):
        reason = unsupported_generated_answer_reason(
            "What is Computer Engineering?",
            "ACM places Computer Engineering between Computer Science and Software Engineering [S1].",
            [{"label": "S1", "passage": "Computer Engineering involves processor-based systems."}],
        )
        self.assertIn("invented a position", reason)

    def test_streaming_invalid_generation_ends_in_safe_insufficiency(self):
        llm = FakeStreamingLLM(text="Computer Engineering guarantees a high-paying job after graduation.")
        events = list(RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer_stream("What is CE?"))
        self.assertEqual(events[-1]["result"]["status"], INSUFFICIENT_INFORMATION)
        self.assertEqual(events[-1]["result"]["sources"], [])
        self.assertFalse(any(event["event"] == "token" for event in events))

    def test_streaming_and_non_streaming_share_validation(self):
        for text in (
            "Computer Engineering combines software and hardware [S1].",
            "Computer Engineering guarantees a high-paying job after graduation.",
            "Computer Engineering combines software and hardware [S9].",
        ):
            with self.subTest(text=text):
                blocking = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=FakeLLM(text=text)).answer("What is CE?")
                events = list(
                    RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=FakeStreamingLLM(text=text)).answer_stream("What is CE?")
                )
                streamed = events[-1]["result"]
                self.assertEqual(events[-1]["event"], "final")
                for key in ("status", "answer", "sources", "citation_metadata", "answer_warnings"):
                    self.assertEqual(streamed[key], blocking[key], key)
                tokens = [event["text"] for event in events if event["event"] == "token"]
                self.assertEqual(tokens, [streamed["answer"]] if streamed["status"] == ANSWERED else [])

    def test_answer_never_opens_with_dangling_reference(self):
        llm = FakeLLM(
            text=(
                "They are combined in many products [S1]. "
                "Computer Engineering combines software and hardware [S1]. "
                "Students learn professional skills [S2]."
            )
        )
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer("What is CE?")
        if result["status"] == ANSWERED:
            self.assertFalse(result["answer"].startswith("They"))

    def test_speculative_inference_is_not_accepted_as_cited_fact(self):
        from backend.app.rag.rag_pipeline import cited_claim_supported

        item = {"label": "S1", "passage": "Core units represent the minimal knowledge a computer engineering program should cover."}
        self.assertFalse(cited_claim_supported("Data structures are likely a core unit of computer engineering programs [S1].", item))
        self.assertTrue(cited_claim_supported("Core units represent the minimal knowledge a computer engineering program should cover [S1].", item))

    def test_meta_openers_and_bracket_artifacts_are_cleaned(self):
        from backend.app.rag.rag_pipeline import clean_answer_artifacts

        self.assertEqual(
            clean_answer_artifacts("Given the context provided, the language is Python [S3]."),
            "The language is Python [S3].",
        )
        self.assertEqual(clean_answer_artifacts("It has hardware components.] [S1]"), "It has hardware components [S1].")

    def test_extractive_fallback_never_quotes_navigation_text(self):
        from backend.app.rag.rag_pipeline import extractive_partial_answer

        answer = extractive_partial_answer(
            "Computer Engineering vs Computer Science?",
            [{"label": "S1", "passage": "Curricular Guidance Computer Engineering Computer Science Cybersecurity Data Science - Coming soon!"}],
        )
        self.assertIsNone(answer)

    def test_source_traceability_survives(self):
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=FakeLLM()).answer("What is CE?")
        self.assertEqual(result["retrieved_context"][0]["source_id"], "src_001")
        self.assertEqual(result["retrieved_context"][0]["chunk_id"], "src_001_chunk_001")
        self.assertEqual(result["retrieved_context"][0]["url"], "https://example.edu/about")

    def test_source_deduplication(self):
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=FakeLLM()).answer("What is CE?")
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(result["sources"][0]["supporting_chunk_ids"], ["src_001_chunk_001"])

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
