from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import require_roles
from app.modules.auth.store import user_store
from app.modules.evaluation.schemas import (
    RetrievalEvaluationRequest,
    RetrievalEvaluationResponse,
)
from app.modules.evaluation.service import retrieval_evaluation_service
from app.modules.memory.store import conversation_memory_store
from app.services.knowledge_graph_service import knowledge_graph_service
from app.services.metrics_service import usage_metrics_store
from app.services.semantic_cache_service import semantic_cache_service
from app.services.vector_store_service import vector_store_service


router = APIRouter(prefix="/api/v1/admin", tags=["Administration"])


@router.get("/metrics")
def metrics(
    _admin: dict = Depends(require_roles("admin")),
) -> dict:
    return {
        "usage": usage_metrics_store.summary(),
        "users": user_store.stats(),
        "memory": conversation_memory_store.stats(),
        "cache": semantic_cache_service.stats(),
        "documents": vector_store_service.stats(),
        "knowledge_graph": knowledge_graph_service.stats(),
    }


@router.post(
    "/evaluations/retrieval",
    response_model=RetrievalEvaluationResponse,
)
def evaluate_retrieval(
    request: RetrievalEvaluationRequest,
    admin: dict = Depends(require_roles("admin")),
) -> RetrievalEvaluationResponse:
    return retrieval_evaluation_service.evaluate(
        request=request,
        owner_id=admin["id"],
    )
