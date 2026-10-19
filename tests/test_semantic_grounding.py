import sys
import unittest
import zlib
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.rag.rag_pipeline import (
    ANSWERED,
    INSUFFICIENT_INFORMATION,
    RAGPipeline,
    cited_claim_supported,
    configure_semantic_encoder,
    semantic_similarity,
    unsupported_generated_answer_reason,
    validate_citations,
)
from tests.test_rag_pipeline import FakeLLM, FakeRetriever, retrieval_result


# Texts that mention words from the same concept embed identically; any other
# text gets its own direction, so unrelated texts are dissimilar.
CONCEPTS = (
    ("hands-on", "laboratory", "lab", "practical"),
    ("employ", "career", "hire"),
)


def fake_encoder(texts):
    vectors = []
    for text in texts:
        lowered = text.lower()
        vector = np.zeros(64)
        hits = [index for index, words in enumerate(CONCEPTS) if any(word in lowered for word in words)]
        if hits:
            vector[hits] = 1.0
        else:
            vector[8 + zlib.crc32(lowered.encode()) % 56] = 1.0
        vectors.append(vector / np.linalg.norm(vector))
    return np.stack(vectors)


LAB_CONTEXT = [
    {
        "label": "S1",
        "chunk_id": "src_067_chunk_001",
        "source_id": "src_067",
        "passage": "The program emphasizes laboratory experiences for students.",
        "title": "Curriculum guidance",
        "source_name": "ACM",
        "section_heading": "",
        "category": "curriculum",
    }
]


class SemanticGroundingTests(unittest.TestCase):
    def setUp(self):
        configure_semantic_encoder(fake_encoder)

    def tearDown(self):
        configure_semantic_encoder(None)

    def test_without_encoder_paraphrase_fails_lexical_check(self):
        configure_semantic_encoder(None)
        self.assertIsNone(semantic_similarity("a", "b"))
        self.assertFalse(cited_claim_supported("Students get hands-on practice in labs [S1].", LAB_CONTEXT[0]))

    def test_cited_paraphrase_is_supported_semantically(self):
        self.assertTrue(cited_claim_supported("Students get hands-on practice in labs [S1].", LAB_CONTEXT[0]))

    def test_guards_still_reject_semantically_similar_claims(self):
        for claim in (
            "Students get 40 hands-on lab sessions [S1].",
            "Students must get hands-on lab practice [S1].",
            "Students likely get hands-on lab practice [S1].",
        ):
            with self.subTest(claim=claim):
                self.assertFalse(cited_claim_supported(claim, LAB_CONTEXT[0]))

    def test_unrelated_cited_claim_is_not_supported(self):
        self.assertFalse(cited_claim_supported("Employers hire graduates quickly [S1].", LAB_CONTEXT[0]))

    def test_uncited_paraphrase_gets_semantic_label(self):
        validation = validate_citations("Students get hands-on practice in labs.", LAB_CONTEXT)
        self.assertTrue(validation.valid)
        self.assertIn("[S1]", validation.answer)

    def test_uncited_paraphrase_needs_encoder(self):
        configure_semantic_encoder(None)
        self.assertFalse(validate_citations("Students get hands-on practice in labs.", LAB_CONTEXT).valid)

    def test_uncited_sentence_failing_guard_is_not_labeled(self):
        validation = validate_citations("Students get 40 hands-on lab sessions.", LAB_CONTEXT)
        self.assertFalse(validation.valid)

    def test_on_topic_paraphrased_answer_passes_topic_check(self):
        question = "What practical training will I receive?"
        answer = "Students get hands-on practice in labs [S1]."
        configure_semantic_encoder(None)
        self.assertIsNotNone(unsupported_generated_answer_reason(question, answer, LAB_CONTEXT))
        configure_semantic_encoder(fake_encoder)
        self.assertIsNone(unsupported_generated_answer_reason(question, answer, LAB_CONTEXT))

    def test_off_topic_answer_still_fails_topic_check(self):
        reason = unsupported_generated_answer_reason(
            "Which employers hire graduates?", "Students get hands-on practice in labs [S1].", LAB_CONTEXT
        )
        self.assertEqual(reason, "generated answer did not address the question's distinctive topic terms")

    def test_pipeline_uses_retriever_encoder(self):
        retriever = FakeRetriever(retrieval_result())
        retriever.encode_texts = fake_encoder
        configure_semantic_encoder(None)
        RAGPipeline(retriever=retriever, llm_service=FakeLLM())
        self.assertAlmostEqual(semantic_similarity("lab work", "hands-on practice"), 1.0)

    def test_fake_retriever_disables_semantic_checks(self):
        RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=FakeLLM())
        self.assertIsNone(semantic_similarity("lab work", "hands-on practice"))


class DiscardedGenerationTests(unittest.TestCase):
    def tearDown(self):
        configure_semantic_encoder(None)

    def test_refused_answer_keeps_raw_generations(self):
        first = "Bananas are yellow fruit grown in tropical climates."
        retry = "Mangoes ripen quickly in warm weather."
        llm = FakeLLM(responses=[first, retry])
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer(
            "Does the department teach hardware and software?"
        )
        self.assertEqual(result["status"], INSUFFICIENT_INFORMATION)
        self.assertEqual(result["retrieval_metadata"]["discarded_generation"], first)
        self.assertEqual(result["retrieval_metadata"]["discarded_retry_generation"], retry)

    def test_answer_replaced_by_fallback_keeps_raw_generation(self):
        first = "Bananas are yellow fruit grown in tropical climates."
        llm = FakeLLM(responses=[first, first])
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=llm).answer("What is Computer Engineering?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertIn("local_llm_answer_replaced_with_bounded_fallback", result["answer_warnings"])
        self.assertEqual(result["retrieval_metadata"]["discarded_generation"], first)

    def test_accepted_answer_has_no_discarded_generation(self):
        result = RAGPipeline(retriever=FakeRetriever(retrieval_result()), llm_service=FakeLLM()).answer("What is Computer Engineering?")
        self.assertEqual(result["status"], ANSWERED)
        self.assertNotIn("discarded_generation", result["retrieval_metadata"])


if __name__ == "__main__":
    unittest.main()
