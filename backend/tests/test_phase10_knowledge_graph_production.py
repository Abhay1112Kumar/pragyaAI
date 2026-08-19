import unittest

from fastapi.testclient import TestClient
from langchain_core.documents import Document

from app.main import app
from app.services.knowledge_graph_service import KnowledgeGraphService


class Phase10KnowledgeGraphProductionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = KnowledgeGraphService(":memory:")
        self.addCleanup(self.graph.close)

    def test_graph_extracts_entities_and_relations_with_owner_isolation(self):
        documents = [
            Document(
                page_content="PragyaAI uses FastAPI and ChromaDB. FastAPI connects PragyaAI.",
                metadata={"owner_id": "owner-1", "document_id": "doc-1"},
            )
        ]

        indexed = self.graph.index_documents(documents)
        result = self.graph.query("PragyaAI", owner_id="owner-1")
        isolated = self.graph.query("PragyaAI", owner_id="owner-2")

        self.assertGreaterEqual(indexed["entities"], 2)
        self.assertGreaterEqual(indexed["relations"], 1)
        self.assertTrue(any(item["name"] == "PragyaAI" for item in result["entities"]))
        self.assertTrue(result["relations"])
        self.assertEqual(isolated, {"entities": [], "relations": []})

    def test_reindex_replaces_document_graph_without_duplicates(self):
        document = Document(
            page_content="PragyaAI connects FastAPI.",
            metadata={"owner_id": "owner-1", "document_id": "doc-1"},
        )

        first = self.graph.index_documents([document])
        second = self.graph.index_documents([document])

        self.assertEqual(first, second)
        self.assertEqual(self.graph.stats()["entities"], first["entities"])

    def test_health_response_has_production_headers_and_readiness(self):
        client = TestClient(app)

        health = client.get("/api/v1/health", headers={"X-Request-ID": "phase-10"})
        ready = client.get("/api/v1/ready")

        self.assertEqual(health.headers["x-request-id"], "phase-10")
        self.assertEqual(health.headers["x-content-type-options"], "nosniff")
        self.assertEqual(health.headers["x-frame-options"], "DENY")
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json()["status"], "ready")
        self.assertIn("production_secrets", ready.json()["checks"])


if __name__ == "__main__":
    unittest.main()
