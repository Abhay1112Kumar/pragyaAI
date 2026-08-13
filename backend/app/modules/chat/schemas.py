from uuid import uuid4

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
    conversation_id: str = Field(
        default_factory=lambda: str(uuid4()),
        examples=["5d23c165-3f16-4b6f-8e09-32c7592c6e8a"],
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
    conversation_id: str
    route: str | None = None
    sources: list[ChatSource] = Field(default_factory=list)
