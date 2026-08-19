from pydantic import BaseModel, Field


class RetrievalEvaluationCase(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    expected_terms: list[str] = Field(min_length=1, max_length=20)
    document_id: str | None = None
    limit: int = Field(default=4, ge=1, le=10)


class RetrievalEvaluationRequest(BaseModel):
    cases: list[RetrievalEvaluationCase] = Field(
        min_length=1,
        max_length=50,
    )


class RetrievalCaseResult(BaseModel):
    query: str
    retrieved_chunks: int
    matched_terms: list[str]
    missing_terms: list[str]
    recall: float
    reciprocal_rank: float
    passed: bool
    latency_ms: float


class RetrievalEvaluationResponse(BaseModel):
    case_count: int
    pass_rate: float
    average_recall: float
    mean_reciprocal_rank: float
    average_latency_ms: float
    results: list[RetrievalCaseResult]
