import sys
import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.api.chat import clear_all_sessions_for_tests, get_rag_pipeline
from backend.app.api import sources as sources_api
from backend.app.main import app
from tests.test_rag_pipeline import FakeLLM


def rag_result(status="answered"):
    return {
        "question": "What is Computer Engineering?",
        "status": status,
        "answer": "Computer Engineering combines software and hardware [S1]."
        if status == "answered"
        else "I don't have enough reliable information in the current knowledge base to answer that question.",
        "llm_called": status == "answered",
        "sources": [
            {
                "source_id": "src_001",
                "title": "About the Department",
                "source_name": "OSTIM Technical University",
                "source_type": "official_department_page",
                "url": "https://example.edu/about",
                "category": "department_information",
                "supporting_chunk_ids": ["src_001_chunk_001"],
                "evidence_labels": ["S1"],
                "best_similarity_score": 0.88,
            }
        ]
        if status == "answered"
        else [],
        "retrieved_context": [
            {
                "label": "S1",
                "chunk_id": "src_001_chunk_001",
                "source_id": "src_001",
                "title": "About the Department",
                "source_name": "OSTIM Technical University",
                "source_type": "official_department_page",
                "url": "https://example.edu/about",
                "category": "department_information",
                "section_heading": "About",
                "similarity_score": 0.88,
                "distance": 0.12,
                "passage": "Computer Engineering combines software, hardware, and systems topics.",
            }
        ],
        "retrieval_metadata": {"top_k": 5, "evidence_sufficient": status == "answered"},
        "timing": {"total_seconds": 0.123, "llm_generation_seconds": 0.1},
        "citation_metadata": {"valid": status == "answered", "cited_labels": ["S1"] if status == "answered" else []},
        "answer_warnings": [],
        "model": "qwen2.5:3b" if status == "answered" else None,
        "error": "controlled failure" if status == "error" else None,
    }


class FakePipeline:
    def __init__(self, result=None, error=None):
        self.result = result or rag_result()
        self.error = error
        self.calls = []

    def answer(self, question, conversation_context=None, resolved_question=None):
        self.calls.append({"question": question, "conversation_context": conversation_context, "resolved_question": resolved_question})
        if self.error:
            raise self.error
        return self.result


class EchoPipeline:
    def __init__(self):
        self.calls = []

    def answer(self, question, conversation_context=None, resolved_question=None):
        self.calls.append({"question": question, "conversation_context": conversation_context, "resolved_question": resolved_question})
        return {**rag_result("answered"), "question": question}


class FakeStreamPipeline(FakePipeline):
    def __init__(self, result=None, events=None, error=None):
        super().__init__(result=result, error=error)
        self.events = events

    def answer_stream(self, question, conversation_context=None, resolved_question=None):
        self.calls.append({"question": question, "conversation_context": conversation_context, "resolved_question": resolved_question})
        if self.error:
            raise self.error
        if self.events is not None:
            yield from self.events
            return
        yield {
            "event": "metadata",
            "retrieval_metadata": {"top_k": 5, "evidence_sufficient": True},
            "retrieved_context": rag_result("answered")["retrieved_context"],
            "llm_called": True,
        }
        yield {"event": "token", "text": "Computer Engineering "}
        yield {"event": "token", "text": "combines software and hardware [S1]."}
        yield {"event": "final", "result": {**rag_result("answered"), "question": question}}


def decode_stream_response(response):
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


class ApiTests(unittest.TestCase):
    def setUp(self):
        clear_all_sessions_for_tests()
        app.dependency_overrides.clear()
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        clear_all_sessions_for_tests()

    def override_pipeline(self, pipeline):
        app.dependency_overrides[get_rag_pipeline] = lambda: pipeline
        return pipeline

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

    def test_valid_chat_request_answered_response(self):
        self.override_pipeline(FakePipeline(rag_result("answered")))
        response = self.client.post("/api/v1/chat", json={"question": " What is Computer Engineering? "})
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "answered")
        self.assertEqual(data["question"], "What is Computer Engineering?")
        self.assertEqual(data["model"], "qwen2.5:3b")
        self.assertTrue(data["session_id"])

    def test_chat_accepts_client_session_id(self):
        pipeline = self.override_pipeline(EchoPipeline())
        response = self.client.post(
            "/api/v1/chat",
            json={"question": "What is Computer Engineering?", "session_id": "session-a"},
        )
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["session_id"], "session-a")
        self.assertIsNone(pipeline.calls[0]["conversation_context"])

    def test_contextual_follow_up_receives_resolved_question_not_full_history_query(self):
        pipeline = self.override_pipeline(EchoPipeline())
        self.client.post("/api/v1/chat", json={"question": "What programming languages are taught?", "session_id": "session-a"})
        response = self.client.post("/api/v1/chat", json={"question": "What about internships?", "session_id": "session-a"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(pipeline.calls[1]["question"], "What about internships?")
        self.assertIn("What programming languages are taught?", pipeline.calls[1]["conversation_context"])
        self.assertIn("Resolved current question", pipeline.calls[1]["conversation_context"])
        self.assertNotIn("Previous assistant answer", pipeline.calls[1]["conversation_context"])
        self.assertNotIn("Computer Engineering combines software and hardware", pipeline.calls[1]["conversation_context"])
        self.assertIn("internships", pipeline.calls[1]["resolved_question"].lower())

    def test_ordinal_follow_up_passes_previous_answer_without_citation_labels(self):
        pipeline = self.override_pipeline(
            FakePipeline(
                result={
                    **rag_result("answered"),
                    "answer": "Useful skills include C programming, microcontroller interfacing, and digital logic [S1].",
                }
            )
        )
        self.client.post("/api/v1/chat", json={"question": "What skills do I need for embedded systems?", "session_id": "session-a"})
        response = self.client.post(
            "/api/v1/chat", json={"question": "can you explain the first one in more detail?", "session_id": "session-a"}
        )
        self.assertEqual(response.status_code, 200)
        context = pipeline.calls[1]["conversation_context"]
        self.assertIn("Previous assistant answer (not evidence)", context)
        self.assertIn("C programming", context)
        self.assertNotIn("[S1]", context)
        self.assertIn("c programming", pipeline.calls[1]["resolved_question"].lower())

    def test_streaming_ordinal_follow_up_uses_previous_answer(self):
        pipeline = self.override_pipeline(
            FakeStreamPipeline(
                result={
                    **rag_result("answered"),
                    "answer": "Useful skills include C programming, microcontroller interfacing, and digital logic [S1].",
                },
                events=[{"event": "final", "result": {
                    **rag_result("answered"),
                    "answer": "Useful skills include C programming, microcontroller interfacing, and digital logic [S1].",
                }}],
            )
        )
        self.client.post("/api/v1/chat/stream", json={"question": "What skills do I need for embedded systems?", "session_id": "s-stream"})
        self.client.post("/api/v1/chat/stream", json={"question": "what about the second one?", "session_id": "s-stream"})
        self.assertIn("microcontroller interfacing", pipeline.calls[1]["resolved_question"].lower())

    def test_source_follow_up_after_refusal_does_not_cite_older_answer(self):
        pipeline = self.override_pipeline(FakePipeline())
        self.client.post("/api/v1/chat", json={"question": "What is Computer Engineering?", "session_id": "s-ref"})
        pipeline.result = {**rag_result("insufficient_information"), "sources": [], "retrieved_context": []}
        self.client.post("/api/v1/chat", json={"question": "What is the exact OSTIM CENG placement rate?", "session_id": "s-ref"})
        for endpoint in ("/api/v1/chat", "/api/v1/chat/stream"):
            with self.subTest(endpoint=endpoint):
                response = self.client.post(endpoint, json={"question": "what sources did you use for that?", "session_id": "s-ref"})
                data = response.json() if endpoint.endswith("/chat") else decode_stream_response(response)[-1]["data"]
                self.assertEqual(data["sources"], [])
                self.assertIn("did not use any sources", data["answer"])

    def test_source_follow_up_uses_previous_answer_sources(self):
        pipeline = self.override_pipeline(EchoPipeline())
        self.client.post(
            "/api/v1/chat",
            json={"question": "How much mathematics is required in Computer Engineering?", "session_id": "session-a"},
        )
        response = self.client.post(
            "/api/v1/chat",
            json={"question": "Where did you get this information from?", "session_id": "session-a"},
        )
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "answered")
        self.assertEqual(len(pipeline.calls), 1)
        self.assertTrue(data["retrieval_metadata"]["used_previous_answer_sources"])
        self.assertEqual(data["sources"][0]["source_id"], "src_001")
        self.assertEqual(data["sources"][0]["supporting_passages"], ["Computer Engineering combines software, hardware, and systems topics."])
        self.assertIn("About the Department", data["answer"])

    def test_project_follow_up_keeps_preference_even_after_insufficient_turn(self):
        pipeline = self.override_pipeline(EchoPipeline())
        self.client.post("/api/v1/chat", json={"question": "I prefer hardware.", "session_id": "session-a"})
        self.client.post("/api/v1/chat", json={"question": "What projects should I build?", "session_id": "session-a"})
        self.assertIn("hardware", pipeline.calls[-1]["resolved_question"].lower())

    def test_source_request_without_answer_does_not_retrieve(self):
        pipeline = self.override_pipeline(EchoPipeline())
        response = self.client.post("/api/v1/chat", json={"question": "Where did you get that information?", "session_id": "session-a"})
        self.assertEqual(response.json()["status"], "insufficient_information")
        self.assertEqual(pipeline.calls, [])
        self.assertIn("About the Department", data["answer"])

    def test_project_follow_up_keeps_preference_even_after_insufficient_turn(self):
        pipeline = self.override_pipeline(EchoPipeline())
        self.client.post("/api/v1/chat", json={"question": "I prefer hardware.", "session_id": "session-a"})
        self.client.post("/api/v1/chat", json={"question": "What projects should I build?", "session_id": "session-a"})
        self.assertIn("hardware", pipeline.calls[-1]["resolved_question"].lower())

    def test_source_request_without_answer_does_not_retrieve(self):
        pipeline = self.override_pipeline(EchoPipeline())
        response = self.client.post("/api/v1/chat", json={"question": "Where did you get that information?", "session_id": "session-a"})
        self.assertEqual(response.json()["status"], "insufficient_information")
        self.assertEqual(pipeline.calls, [])

    def test_standalone_question_uses_rag_without_previous_context(self):
        pipeline = self.override_pipeline(EchoPipeline())
        response = self.client.post(
            "/api/v1/chat",
            json={"question": "What programming languages should I learn?", "session_id": "session-a"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "answered")
        self.assertEqual(len(pipeline.calls), 1)
        self.assertIsNone(pipeline.calls[0]["conversation_context"])
        self.assertEqual(pipeline.calls[0]["resolved_question"], "What programming languages should I learn?")

    def test_typo_in_computer_engineering_resolves_before_classification(self):
        pipeline = self.override_pipeline(EchoPipeline())
        response = self.client.post(
            "/api/v1/chat",
            json={"question": "what is computer engneering?", "session_id": "session-a"},
        )
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["question"], "what is computer engneering?")
        self.assertEqual(data["status"], "answered")
        self.assertEqual(len(pipeline.calls), 1)
        self.assertEqual(pipeline.calls[0]["resolved_question"], "What is Computer Engineering?")
        self.assertEqual(data["retrieval_metadata"]["resolved_question"], "What is Computer Engineering?")
        self.assertTrue(data["retrieval_metadata"]["query_normalization"]["changed"])

    def test_informal_domain_questions_resolve_to_retrieval_queries(self):
        examples = {
            "what computer enginer do": "What does a Computer Engineer do?",
            "is computer eng hard": "Is Computer Engineering difficult?",
            "which programing language should i lern first": "Which programming language should I learn first?",
            "can i work ai after computer eng": "Can I work in AI after studying Computer Engineering?",
            "how much math i need": "How much mathematics is required in Computer Engineering?",
        }
        for question, expected in examples.items():
            with self.subTest(question=question):
                pipeline = self.override_pipeline(EchoPipeline())
                response = self.client.post(
                    "/api/v1/chat",
                    json={"question": question, "session_id": f"session-{question}"},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "answered")
                self.assertEqual(len(pipeline.calls), 1)
                self.assertEqual(pipeline.calls[0]["resolved_question"], expected)

    def test_fuzzy_normalization_does_not_turn_unrelated_words_into_domain_questions(self):
        negatives = ["football", "cooking", "weather", "who won the match", "make me a cake"]
        for question in negatives:
            with self.subTest(question=question):
                pipeline = self.override_pipeline(EchoPipeline())
                response = self.client.post(
                    "/api/v1/chat",
                    json={"question": question, "session_id": f"negative-{question}"},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "out_of_scope")
                self.assertEqual(len(pipeline.calls), 0)

    def test_persona_question_returns_helpful_advisor_scope_without_retrieval(self):
        pipeline = self.override_pipeline(EchoPipeline())
        response = self.client.post(
            "/api/v1/chat",
            json={"question": "what can you do?", "session_id": "session-a"},
        )
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "help")
        self.assertIn("prospective OSTİM Technical University Computer Engineering students", data["answer"])
        self.assertEqual(len(pipeline.calls), 0)

    def test_help_and_unrelated_questions_on_both_chat_endpoints(self):
        help_questions = (
            "what can I ask you?", "what should students ask you?", "who are you?",
            "what can you help with?", "how do you work?",
        )
        for endpoint in ("/api/v1/chat", "/api/v1/chat/stream"):
            for question in help_questions + ("pizza", "weather", "football", "Can you help me with pizza?"):
                with self.subTest(endpoint=endpoint, question=question):
                    pipeline = self.override_pipeline(FakeStreamPipeline())
                    response = self.client.post(endpoint, json={"question": question})
                    self.assertEqual(response.status_code, 200)
                    if endpoint.endswith("/stream"):
                        events = decode_stream_response(response)
                        self.assertEqual([event["event"] for event in events], ["final"])
                        data = events[0]["data"]
                    else:
                        data = response.json()
                    self.assertEqual(pipeline.calls, [])
                    self.assertFalse(data["llm_called"])
                    self.assertEqual(data["sources"], [])
                    self.assertEqual(data["retrieved_context"], [])
                    self.assertIsNone(data["model"])
                    self.assertEqual(data["answer_warnings"], [])
                    if question in help_questions:
                        self.assertEqual(data["status"], "help")
                        self.assertEqual(data["retrieval_metadata"]["query_kind"], "assistant_help")
                        self.assertNotIn("classified_out_of_scope", data["retrieval_metadata"])
                        self.assertIn("local RAG", data["answer"])
                        self.assertIn("OSTİM", data["answer"])
                        self.assertIn("supporting sources", data["answer"])
                        self.assertEqual(len(set(data["example_questions"])), 5)
                        for example in data["example_questions"]:
                            self.assertTrue(example.endswith("?"))
                    else:
                        self.assertEqual(data["status"], "out_of_scope")
                        self.assertEqual(data["example_questions"], [])

    def test_source_request_after_help_does_not_cite_an_older_answer(self):
        for endpoint in ("/api/v1/chat", "/api/v1/chat/stream"):
            with self.subTest(endpoint=endpoint):
                pipeline = self.override_pipeline(FakeStreamPipeline())
                session_id = endpoint
                self.client.post(endpoint, json={"question": "What is Computer Engineering?", "session_id": session_id})
                self.client.post(endpoint, json={"question": "how do you work?", "session_id": session_id})
                response = self.client.post(endpoint, json={"question": "what sources did you use for that?", "session_id": session_id})
                data = decode_stream_response(response)[-1]["data"] if endpoint.endswith("/stream") else response.json()
                self.assertEqual(data["sources"], [])
                self.assertIn("did not use any sources", data["answer"])
                self.assertEqual(len(pipeline.calls), 1)

    def test_help_does_not_replace_the_domain_topic_for_follow_ups(self):
        pipeline = self.override_pipeline(EchoPipeline())
        for question in ("Can Computer Engineers work in cybersecurity?", "how do you work?", "What skills should I build?"):
            self.client.post("/api/v1/chat", json={"question": question, "session_id": "help-context"})
        self.assertEqual(len(pipeline.calls), 2)
        self.assertIn("cybersecurity", pipeline.calls[-1]["resolved_question"].lower())

    def test_domain_anchored_source_question_is_not_treated_as_vague_follow_up(self):
        pipeline = self.override_pipeline(EchoPipeline())
        response = self.client.post(
            "/api/v1/chat",
            json={"question": "What sources explain programming languages?", "session_id": "session-a"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "answered")
        self.assertEqual(len(pipeline.calls), 1)

    def test_vague_follow_up_without_referent_does_not_retrieve(self):
        pipeline = self.override_pipeline(EchoPipeline())
        response = self.client.post(
            "/api/v1/chat",
            json={"question": "Where did you get this information from?", "session_id": "session-a"},
        )
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "insufficient_information")
        self.assertEqual(len(pipeline.calls), 0)
        self.assertTrue(data["retrieval_metadata"]["unresolved_follow_up"])
        self.assertIn("not sure which previous topic or information", data["answer"])

    def test_unrelated_question_preserves_out_of_scope_fallback(self):
        pipeline = self.override_pipeline(FakePipeline(rag_result("out_of_scope")))
        response = self.client.post(
            "/api/v1/chat",
            json={"question": "How do I cook spaghetti?", "session_id": "session-a"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "out_of_scope")
        self.assertEqual(len(pipeline.calls), 0)

    def test_session_contamination_does_not_turn_meta_question_into_staff_answer(self):
        pipeline = self.override_pipeline(EchoPipeline())
        self.client.post("/api/v1/chat", json={"question": "Who are the academic staff?", "session_id": "session-a"})
        response = self.client.post("/api/v1/chat", json={"question": "who made u", "session_id": "session-a"})
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "out_of_scope")
        self.assertEqual(len(pipeline.calls), 1)
        self.assertTrue(data["retrieval_metadata"]["classified_out_of_scope"])

    def test_contextual_ai_difficulty_follow_up_is_resolved(self):
        pipeline = self.override_pipeline(EchoPipeline())
        self.client.post("/api/v1/chat", json={"question": "Tell me about AI in Computer Engineering.", "session_id": "session-a"})
        response = self.client.post("/api/v1/chat", json={"question": "Is it difficult?", "session_id": "session-a"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "answered")
        self.assertEqual(len(pipeline.calls), 2)
        self.assertIn("AI in Computer Engineering", pipeline.calls[1]["resolved_question"])
        self.assertIn("difficult", pipeline.calls[1]["resolved_question"].lower())

    def test_correction_follow_up_extracts_actual_definition_request(self):
        pipeline = self.override_pipeline(EchoPipeline())
        self.client.post("/api/v1/chat", json={"question": "What is Computer Engineering?", "session_id": "session-a"})
        response = self.client.post(
            "/api/v1/chat",
            json={
                "question": "i did not ask you department i asked you the definition of computer engineering",
                "session_id": "session-a",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "answered")
        self.assertEqual(len(pipeline.calls), 2)
        self.assertEqual(pipeline.calls[1]["resolved_question"], "What is the definition of Computer Engineering?")

    def test_advisor_development_question_is_not_answered_from_kb_retrieval(self):
        pipeline = self.override_pipeline(EchoPipeline())
        response = self.client.post(
            "/api/v1/chat",
            json={"question": "who developed this advisor", "session_id": "session-a"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "out_of_scope")
        self.assertEqual(len(pipeline.calls), 0)

    def test_session_histories_are_isolated(self):
        pipeline = self.override_pipeline(EchoPipeline())
        self.client.post("/api/v1/chat", json={"question": "Tell me about AI careers.", "session_id": "session-a"})
        self.client.post("/api/v1/chat", json={"question": "Tell me about internships.", "session_id": "session-b"})
        self.client.post("/api/v1/chat", json={"question": "What about salaries?", "session_id": "session-a"})
        context = pipeline.calls[2]["conversation_context"]
        self.assertIn("Tell me about AI careers.", context)
        self.assertNotIn("Tell me about internships.", context)

    def test_reset_session_clears_previous_context(self):
        pipeline = self.override_pipeline(EchoPipeline())
        self.client.post("/api/v1/chat", json={"question": "Tell me about cybersecurity.", "session_id": "session-a"})
        response = self.client.post(
            "/api/v1/chat",
            json={"question": "Start over with curriculum.", "session_id": "session-a", "reset_session": True},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["session_id"], "session-a")
        self.assertIsNone(pipeline.calls[1]["conversation_context"])

    def test_insufficient_information_response_stays_http_200(self):
        self.override_pipeline(FakePipeline(rag_result("insufficient_information")))
        response = self.client.post("/api/v1/chat", json={"question": "What is the tuition fee?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "insufficient_information")
        self.assertTrue(response.json()["session_id"])

    def test_out_of_scope_response_stays_http_200(self):
        self.override_pipeline(FakePipeline(rag_result("out_of_scope")))
        response = self.client.post("/api/v1/chat", json={"question": "Best chocolate cake recipe?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "out_of_scope")

    def test_empty_question_validation(self):
        response = self.client.post("/api/v1/chat", json={"question": ""})
        self.assertEqual(response.status_code, 422)

    def test_whitespace_only_question_validation(self):
        response = self.client.post("/api/v1/chat", json={"question": "     "})
        self.assertEqual(response.status_code, 422)

    def test_missing_question_validation(self):
        response = self.client.post("/api/v1/chat", json={})
        self.assertEqual(response.status_code, 422)

    def test_excessive_question_length_validation(self):
        response = self.client.post("/api/v1/chat", json={"question": "x" * 501})
        self.assertEqual(response.status_code, 422)

    def test_structured_source_metadata_preserved(self):
        self.override_pipeline(FakePipeline(rag_result("answered")))
        response = self.client.post("/api/v1/chat", json={"question": "What is Computer Engineering?"})
        source = response.json()["sources"][0]
        self.assertEqual(source["source_id"], "src_001")
        self.assertEqual(source["url"], "https://example.edu/about")
        self.assertEqual(source["supporting_chunk_ids"], ["src_001_chunk_001"])
        self.assertEqual(source["evidence_labels"], ["S1"])
        self.assertEqual(source["section_headings"], ["About"])
        self.assertEqual(source["supporting_passages"], ["Computer Engineering combines software, hardware, and systems topics."])

    def test_timing_metadata_preserved(self):
        self.override_pipeline(FakePipeline(rag_result("answered")))
        response = self.client.post("/api/v1/chat", json={"question": "What is Computer Engineering?"})
        self.assertEqual(response.json()["timing"]["total_seconds"], 0.123)

    def test_rag_status_error_returns_controlled_503(self):
        self.override_pipeline(FakePipeline(rag_result("error")))
        response = self.client.post("/api/v1/chat", json={"question": "What is Computer Engineering?"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "error")
        self.assertNotIn("Traceback", response.text)

    def test_unexpected_rag_exception_returns_controlled_503(self):
        self.override_pipeline(FakePipeline(error=RuntimeError("secret traceback detail")))
        response = self.client.post("/api/v1/chat", json={"question": "What is Computer Engineering?"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "error")
        self.assertEqual(response.json()["error"], "The local RAG service could not process the request.")

    def test_cors_allows_local_vite_origin(self):
        response = self.client.options(
            "/api/v1/chat",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")

    def test_sources_endpoint_returns_public_registry_metadata(self):
        response = self.client.get("/api/v1/sources")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        registry = json.loads((PROJECT_ROOT / "knowledge_base" / "sources.json").read_text(encoding="utf-8"))["sources"]
        self.assertEqual(data["count"], len(registry))
        self.assertEqual(len(data["sources"]), data["count"])
        sources_by_id = {source["source_id"]: source for source in data["sources"]}
        expected_indexed_count = sum(1 for source in data["sources"] if source["indexed_in_rag"])
        self.assertEqual(data["indexed_count"], expected_indexed_count)
        self.assertTrue(sources_by_id["src_042"]["indexed_in_rag"])
        self.assertTrue(sources_by_id["src_043"]["indexed_in_rag"])
        source = data["sources"][0]
        expected_fields = {
            "source_id",
            "title",
            "source_name",
            "source_type",
            "url",
            "publication_date",
            "date_added",
            "category",
            "language",
            "indexed_in_rag",
        }
        self.assertEqual(set(source.keys()), expected_fields)
        self.assertEqual(source["date_added"], "2026-08-30")
        self.assertTrue(source["indexed_in_rag"])
        self.assertIn("department_information", data["categories"])
        self.assertIn("official_department_page", data["source_types"])

    def test_sources_endpoint_marks_registered_but_not_indexed_sources(self):
        response = self.client.get("/api/v1/sources")
        data = response.json()
        sources_by_id = {source["source_id"]: source for source in data["sources"]}
        self.assertFalse(sources_by_id["src_009"]["indexed_in_rag"])
        self.assertEqual(sources_by_id["src_009"]["title"], "Curricula Recommendations")
        self.assertEqual(sources_by_id["src_009"]["date_added"], "2026-08-30")
        self.assertIsNone(sources_by_id["src_009"]["publication_date"])

    def test_sources_endpoint_does_not_expose_internal_paths(self):
        response = self.client.get("/api/v1/sources")
        data = response.json()
        serialized = response.text
        self.assertNotIn("raw_file_path", serialized)
        self.assertNotIn("processed_file_path", serialized)
        self.assertNotIn("knowledge_base/raw", serialized)
        self.assertNotIn("date_accessed", data["sources"][0])
        self.assertNotIn("notes", data["sources"][0])

    def test_stream_chat_emits_incremental_tokens_before_final_metadata(self):
        pipeline = self.override_pipeline(FakeStreamPipeline())
        response = self.client.post("/api/v1/chat/stream", json={"question": "What is Computer Engineering?", "session_id": "session-a"})
        self.assertEqual(response.status_code, 200)
        events = decode_stream_response(response)
        self.assertEqual([event["event"] for event in events], ["metadata", "token", "token", "final"])
        self.assertEqual(events[1]["data"]["text"], "Computer Engineering ")
        self.assertEqual(events[2]["data"]["text"], "combines software and hardware [S1].")
        final = events[-1]["data"]
        self.assertEqual(final["status"], "answered")
        self.assertEqual(final["answer"], "Computer Engineering combines software and hardware [S1].")
        self.assertEqual(final["sources"][0]["source_id"], "src_001")
        self.assertEqual(final["citation_metadata"]["cited_labels"], ["S1"])
        self.assertEqual(len(pipeline.calls), 1)

    def test_stream_chat_stores_complete_turn_for_source_follow_up(self):
        pipeline = self.override_pipeline(FakeStreamPipeline())
        response = self.client.post("/api/v1/chat/stream", json={"question": "How much mathematics is required?", "session_id": "session-a"})
        events = decode_stream_response(response)
        self.assertEqual(events[-1]["data"]["status"], "answered")

        follow_up = self.client.post(
            "/api/v1/chat/stream",
            json={"question": "Where did you get this information from?", "session_id": "session-a"},
        )
        follow_events = decode_stream_response(follow_up)
        self.assertEqual([event["event"] for event in follow_events], ["final"])
        final = follow_events[-1]["data"]
        self.assertEqual(final["status"], "answered")
        self.assertTrue(final["retrieval_metadata"]["used_previous_answer_sources"])
        self.assertEqual(final["sources"][0]["source_id"], "src_001")

    def test_stream_chat_insufficient_information_final_without_tokens(self):
        pipeline = self.override_pipeline(
            FakeStreamPipeline(events=[{"event": "final", "result": rag_result("insufficient_information")}])
        )
        response = self.client.post("/api/v1/chat/stream", json={"question": "What is the tuition fee?", "session_id": "session-a"})
        events = decode_stream_response(response)
        self.assertEqual([event["event"] for event in events], ["final"])
        self.assertEqual(events[-1]["data"]["status"], "insufficient_information")
        self.assertFalse(events[-1]["data"]["sources"])
        self.assertEqual(len(pipeline.calls), 1)

    def test_stream_chat_out_of_scope_classification_without_pipeline_call(self):
        pipeline = self.override_pipeline(FakeStreamPipeline())
        response = self.client.post("/api/v1/chat/stream", json={"question": "who made u", "session_id": "session-a"})
        events = decode_stream_response(response)
        self.assertEqual([event["event"] for event in events], ["final"])
        self.assertEqual(events[-1]["data"]["status"], "out_of_scope")
        self.assertEqual(len(pipeline.calls), 0)

    def test_stream_chat_failure_is_not_stored_as_answered_turn(self):
        pipeline = self.override_pipeline(
            FakeStreamPipeline(
                events=[
                    {"event": "metadata", "retrieval_metadata": {}, "retrieved_context": [], "llm_called": True},
                    {"event": "token", "text": "Partial"},
                    {"event": "final", "result": rag_result("error")},
                ]
            )
        )
        response = self.client.post("/api/v1/chat/stream", json={"question": "What is Computer Engineering?", "session_id": "session-a"})
        events = decode_stream_response(response)
        self.assertEqual(events[-1]["data"]["status"], "error")

        follow_up = self.client.post(
            "/api/v1/chat/stream",
            json={"question": "Where did you get this information from?", "session_id": "session-a"},
        )
        follow_events = decode_stream_response(follow_up)
        self.assertEqual(follow_events[-1]["data"]["status"], "insufficient_information")
        self.assertEqual(len(pipeline.calls), 1)

    def test_sources_endpoint_missing_registry_is_controlled(self):
        original_path = sources_api.SOURCES_REGISTRY_PATH
        try:
            sources_api.SOURCES_REGISTRY_PATH = original_path.with_name("missing-sources.json")
            response = self.client.get("/api/v1/sources")
        finally:
            sources_api.SOURCES_REGISTRY_PATH = original_path
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "The source registry is currently unavailable.")


class ConversationalFeedbackApiTests(unittest.TestCase):
    setUp = ApiTests.setUp
    tearDown = ApiTests.tearDown
    override_pipeline = ApiTests.override_pipeline

    def test_feedback_gets_fixed_reply_without_retrieval_or_llm(self):
        llm = FakeLLM(text="What is Computer Engineering in Computer Engineering?")
        pipeline = EchoPipeline()
        pipeline.llm_service = llm
        stream_pipeline = FakeStreamPipeline()
        stream_pipeline.llm_service = llm
        for endpoint, active in (("/api/v1/chat", pipeline), ("/api/v1/chat/stream", stream_pipeline)):
            with self.subTest(endpoint=endpoint):
                self.override_pipeline(active)
                session = f"feedback-{endpoint}"
                self.client.post(endpoint, json={"question": "What is Computer Engineering?", "session_id": session})
                calls, llm_calls = len(active.calls), llm.calls
                response = self.client.post(endpoint, json={"question": "but i didnt ask that question", "session_id": session})
                data = decode_stream_response(response)[-1]["data"] if endpoint.endswith("stream") else response.json()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(data["status"], "help")
                self.assertTrue(data["answer"].startswith("Sorry about that. Could you ask your question again in a full sentence?"))
                self.assertFalse(data["llm_called"])
                self.assertEqual(data["sources"], [])
                self.assertIsNone(data["answered_as"])
                self.assertEqual(data["retrieval_metadata"]["query_kind"], "conversational_feedback")
                self.assertEqual(len(active.calls), calls)
                self.assertEqual(llm.calls, llm_calls)

    def test_thanks_gets_acknowledgement_reply(self):
        pipeline = self.override_pipeline(EchoPipeline())
        data = self.client.post("/api/v1/chat", json={"question": "thanks!"}).json()
        self.assertEqual(data["status"], "help")
        self.assertTrue(data["answer"].startswith("You're welcome."))
        self.assertEqual(pipeline.calls, [])

    def test_follow_up_after_feedback_still_uses_the_answered_topic(self):
        pipeline = self.override_pipeline(EchoPipeline())
        for question in ("Can Computer Engineers work in cybersecurity?", "that's wrong", "What skills should I build?"):
            self.client.post("/api/v1/chat", json={"question": question, "session_id": "feedback-context"})
        self.assertEqual(len(pipeline.calls), 2)
        self.assertIn("cybersecurity", pipeline.calls[-1]["resolved_question"].lower())

    def test_answered_as_shows_the_rewritten_follow_up_only(self):
        pipeline = self.override_pipeline(EchoPipeline())
        first = self.client.post("/api/v1/chat", json={"question": "What programming languages are taught?", "session_id": "answered-as"}).json()
        follow_up = self.client.post("/api/v1/chat", json={"question": "What about internships?", "session_id": "answered-as"}).json()
        self.assertIsNone(first["answered_as"])
        self.assertEqual(follow_up["answered_as"], pipeline.calls[1]["resolved_question"])
        self.assertIn("internships", follow_up["answered_as"].lower())
        self.assertNotEqual(follow_up["answered_as"], "What about internships?")

    def test_answered_as_on_stream_endpoint(self):
        pipeline = self.override_pipeline(FakeStreamPipeline())
        self.client.post("/api/v1/chat/stream", json={"question": "What programming languages are taught?", "session_id": "answered-as-stream"})
        response = self.client.post("/api/v1/chat/stream", json={"question": "What about internships?", "session_id": "answered-as-stream"})
        final = decode_stream_response(response)[-1]["data"]
        self.assertEqual(final["answered_as"], pipeline.calls[1]["resolved_question"])


if __name__ == "__main__":
    unittest.main()
