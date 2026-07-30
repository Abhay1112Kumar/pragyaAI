from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=5000,
        examples=["Explain artificial intelligence in simple language."],
    )


class ChatResponse(BaseModel):
    response: str
    provider: str
    model: str