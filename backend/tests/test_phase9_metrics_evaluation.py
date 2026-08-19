import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.dependencies import get_current_user
from app.modules.evaluation.schemas import RetrievalEvaluationRequest
from app.modules.evaluation.service import RetrievalEvaluationService
from app.services.metrics_service import UsageMetricsStore


class Phase9MetricsAndEvaluationTests(unittest.TestCase):
    def test_usage_metrics_summary_tracks_routes_latency_and_success(self):
        store = UsageMetricsStore(":memory:")
        store.record_chat("user-1", "general", 100.0, True)
        store.record_chat("user-1", "document_rag", 300.0, True)
        store.record_chat("user-2", "error", 200.0, False)

        summary = store.summary()
        store.close()

        self.assertEqual(summary["total_requests"], 3)
        self.assertEqual(summary["requests_24h"], 3)
        self.assertEqual(summary["average_latency_ms"], 200.0)
        self.assertEqual(summary["success_rate"], 66.67)
        self.assertEqual(summary["route_counts"]["general"], 1)

    def test_retrieval_evaluation_calculates_recall_and_reciprocal_rank(self):
        request = RetrievalEvaluationRequest(
            cases=[
                {
                    "query": "Explain the refund timeline",
                    "expected_terms": ["refund", "timeline"],
                    "document_id": "document-1",
                }
            ]
        )
        chunks = [
            {
                "content": "Unrelated introduction.",
                "metadata": {},
                "score": 0.2,
            },
            {
                "content": "The refund timeline is seven working days.",
                "metadata": {},
                "score": 0.1,
            },
        ]

        with patch(
            "app.modules.evaluation.service.vector_store_service.search",
            return_value=chunks,
        ) as search:
            result = RetrievalEvaluationService().evaluate(
                request=request,
                owner_id="admin-1",
            )

        self.assertEqual(result.pass_rate, 100.0)
        self.assertEqual(result.average_recall, 1.0)
        self.assertEqual(result.mean_reciprocal_rank, 0.5)
        self.assertTrue(result.results[0].passed)
        self.assertEqual(search.call_args.kwargs["owner_id"], "admin-1")

    def test_retrieval_evaluation_reports_missing_terms(self):
        request = RetrievalEvaluationRequest(
            cases=[
                {
                    "query": "Find payment details",
                    "expected_terms": ["payment", "deadline"],
                }
            ]
        )

        with patch(
            "app.modules.evaluation.service.vector_store_service.search",
            return_value=[
                {
                    "content": "Payment is supported.",
                    "metadata": {},
                    "score": 0.1,
                }
            ],
        ):
            result = RetrievalEvaluationService().evaluate(
                request=request,
                owner_id="admin-1",
            )

        self.assertEqual(result.pass_rate, 0.0)
        self.assertEqual(result.average_recall, 0.5)
        self.assertEqual(result.results[0].missing_terms, ["deadline"])

    def test_normal_user_cannot_open_admin_metrics(self):
        app.dependency_overrides[get_current_user] = lambda: {
            "id": "user-1",
            "username": "regular-user",
            "role": "user",
            "is_active": True,
        }
        try:
            response = TestClient(app).get("/api/v1/admin/metrics")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
