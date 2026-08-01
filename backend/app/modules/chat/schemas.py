from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=5000,
        examples=["Explain artificial intelligence in simple language."],
    )
    document_id: str | None = Field(
        default=None,
        examples=["0f84b868-1925-4ef7-a019-3d77346da63f"],
    )


class ChatSource(BaseModel):
    filename: str | None = None
    page: int | None = None
    chunk_index: int | None = None
    score: float


class ChatResponse(BaseModel):
    response: str
    provider: str
    model: str
    sources: list[ChatSource] = Field(default_factory=list)
