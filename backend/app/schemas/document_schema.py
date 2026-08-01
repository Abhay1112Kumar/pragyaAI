from typing import Any

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    message: str
    document_id: str
    filename: str
    file_size: int
    page_count: int
    character_count: int
    chunk_count: int


class DocumentSearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=2,
        max_length=1000,
    )
    document_id: str | None = None
    limit: int = Field(
        default=4,
        ge=1,
        le=10,
    )


class RetrievedChunk(BaseModel):
    content: str
    metadata: dict[str, Any]
    score: float | None = None


class DocumentSearchResponse(BaseModel):
    query: str
    results: list[RetrievedChunk]