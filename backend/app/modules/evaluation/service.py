from time import perf_counter

from app.modules.evaluation.schemas import (
    RetrievalCaseResult,
    RetrievalEvaluationRequest,
    RetrievalEvaluationResponse,
)
from app.services.vector_store_service import vector_store_service


class RetrievalEvaluationService:
    def evaluate(
        self,
        request: RetrievalEvaluationRequest,
        owner_id: str,
    ) -> RetrievalEvaluationResponse:
        results = [
            self._evaluate_case(case, owner_id)
            for case in request.cases
        ]
        case_count = len(results)

        return RetrievalEvaluationResponse(
            case_count=case_count,
            pass_rate=round(
                sum(result.passed for result in results) / case_count * 100,
                2,
            ),
            average_recall=round(
                sum(result.recall for result in results) / case_count,
                4,
            ),
            mean_reciprocal_rank=round(
                sum(result.reciprocal_rank for result in results)
                / case_count,
                4,
            ),
            average_latency_ms=round(
                sum(result.latency_ms for result in results) / case_count,
                2,
            ),
            results=results,
        )

    def _evaluate_case(self, case, owner_id: str) -> RetrievalCaseResult:
        started_at = perf_counter()
        chunks = vector_store_service.search(
            query=case.query,
            limit=case.limit,
            document_id=case.document_id,
            owner_id=owner_id,
        )
        latency_ms = (perf_counter() - started_at) * 1000
        expected = {
            term.strip().lower()
            for term in case.expected_terms
            if term.strip()
        }
        matched: set[str] = set()
        first_relevant_rank = 0

        for rank, chunk in enumerate(chunks, start=1):
            content = chunk["content"].lower()
            chunk_matches = {
                term for term in expected if term in content
            }
            if chunk_matches and not first_relevant_rank:
                first_relevant_rank = rank
            matched.update(chunk_matches)

        missing = expected - matched
        recall = len(matched) / len(expected) if expected else 0.0

        return RetrievalCaseResult(
            query=case.query,
            retrieved_chunks=len(chunks),
            matched_terms=sorted(matched),
            missing_terms=sorted(missing),
            recall=round(recall, 4),
            reciprocal_rank=(
                round(1 / first_relevant_rank, 4)
                if first_relevant_rank
                else 0.0
            ),
            passed=not missing,
            latency_ms=round(latency_ms, 2),
        )


retrieval_evaluation_service = RetrievalEvaluationService()
