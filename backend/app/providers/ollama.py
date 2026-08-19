from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from app.modules.chat.streaming import emit_token
from app.providers.base import BaseLLMProvider
from app.shared.config import settings


class OllamaProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.client = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.3,
        )

    @property
    def model_name(self) -> str:
        return settings.ollama_model

    def generate(self, system_prompt: str, user_message: str) -> str:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        chunks: list[str] = []

        for response_chunk in self.client.stream(messages):
            content = response_chunk.content
            text = content if isinstance(content, str) else str(content)
            if text:
                chunks.append(text)
                emit_token(text)

        return "".join(chunks)
