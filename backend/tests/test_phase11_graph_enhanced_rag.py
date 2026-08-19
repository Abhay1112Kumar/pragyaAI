import unittest
from unittest.mock import patch

from app.modules.graph.chat_graph import PragyaChatGraph


class Phase11GraphEnhancedRAGTests(unittest.TestCase):
    def test_document_retrieval_appends_matching_graph_relationships(self):
        graph = PragyaChatGraph.__new__(PragyaChatGraph)
        state = {
            "query": "How does PragyaAI use FastAPI?",
            "conversation_id": "phase-11",
            "document_id": "doc-1",
            "owner_id": "owner-1",
            "messages": [],
        }
        chunks = [{
            "content": "PragyaAI exposes APIs with FastAPI.",
            "metadata": {"filename": "architecture.pdf", "page": 2, "chunk_index": 0},
            "score": 0.5,
            "retrieval_methods": ["semantic", "bm25"],
        }]
        relationships = {
            "entities": [{"name": "PragyaAI"}],
            "relations": [{
                "source": "FastAPI",
                "target": "PragyaAI",
                "weight": 2,
            }],
        }

        with patch(
            "app.modules.graph.chat_graph.vector_store_service.search",
            return_value=chunks,
        ), patch(
            "app.modules.graph.chat_graph.knowledge_graph_service.query",
            return_value=relationships,
        ):
            result = graph._retrieve_document(state)

        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(len(result["retrieved_context"]), 2)
        self.assertIn("Knowledge graph relationships", result["retrieved_context"][1])
        self.assertIn("FastAPI is related to PragyaAI", result["retrieved_context"][1])


if __name__ == "__main__":
    unittest.main()
