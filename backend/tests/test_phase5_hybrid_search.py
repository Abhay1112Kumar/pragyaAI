import unittest

from app.services.vector_store_service import VectorStoreService


class Phase5HybridSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = VectorStoreService.__new__(VectorStoreService)

    def test_bm25_prioritizes_exact_keyword_match(self) -> None:
        results = self.service._bm25_search(
            query="invoice ZX-491",
            ids=["a", "b"],
            documents=[
                "The invoice identifier is ZX-491 and payment is pending.",
                "This passage describes general billing and payments.",
            ],
            metadatas=[{"chunk_id": "a"}, {"chunk_id": "b"}],
            limit=2,
        )

        self.assertEqual(results[0]["metadata"]["chunk_id"], "a")
        self.assertGreater(results[0]["bm25_score"], 0)

    def test_rrf_rewards_chunks_found_by_both_retrievers(self) -> None:
        semantic = [
            {"content": "shared", "metadata": {"chunk_id": "shared"}},
            {"content": "semantic", "metadata": {"chunk_id": "semantic"}},
        ]
        lexical = [
            {"content": "lexical", "metadata": {"chunk_id": "lexical"}},
            {"content": "shared", "metadata": {"chunk_id": "shared"}},
        ]

        results = self.service._reciprocal_rank_fusion(
            semantic_chunks=semantic,
            lexical_chunks=lexical,
            limit=3,
        )

        self.assertEqual(results[0]["metadata"]["chunk_id"], "shared")
        self.assertEqual(results[0]["retrieval_methods"], ["semantic", "bm25"])

    def test_tokenizer_is_case_insensitive_and_keeps_numbers(self) -> None:
        self.assertEqual(
            self.service._tokenize("Invoice ZX-491"),
            ["invoice", "zx", "491"],
        )


if __name__ == "__main__":
    unittest.main()
