import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.api.chat import clear_all_sessions_for_tests, get_rag_pipeline
from backend.app.api import sources as sources_api
from backend.app.main import app


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

    def answer(self, question, conversation_context=None):
        self.calls.append({"question": question, "conversation_context": conversation_context})
        if self.error:
            raise self.error
        return self.result


class EchoPipeline:
    def __init__(self):
        self.calls = []

    def answer(self, question, conversation_context=None):
        self.calls.append({"question": question, "conversation_context": conversation_context})
        return {**rag_result("answered"), "question": question}


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

    def test_follow_up_question_receives_recent_session_context(self):
        pipeline = self.override_pipeline(EchoPipeline())
        self.client.post("/api/v1/chat", json={"question": "What programming languages are taught?", "session_id": "session-a"})
        response = self.client.post("/api/v1/chat", json={"question": "What about internships?", "session_id": "session-a"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(pipeline.calls[1]["question"], "What about internships?")
        self.assertIn("What programming languages are taught?", pipeline.calls[1]["conversation_context"])
        self.assertNotIn("Computer Engineering combines software and hardware", pipeline.calls[1]["conversation_context"])

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
        self.assertEqual(data["count"], 56)
        self.assertEqual(len(data["sources"]), 56)
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

    def test_sources_endpoint_missing_registry_is_controlled(self):
        original_path = sources_api.SOURCES_REGISTRY_PATH
        try:
            sources_api.SOURCES_REGISTRY_PATH = original_path.with_name("missing-sources.json")
            response = self.client.get("/api/v1/sources")
        finally:
            sources_api.SOURCES_REGISTRY_PATH = original_path
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "The source registry is currently unavailable.")


if __name__ == "__main__":
    unittest.main()
