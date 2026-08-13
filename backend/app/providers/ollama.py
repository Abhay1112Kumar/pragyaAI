from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

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

        response = self.client.invoke(messages)

        if isinstance(response.content, str):
            return response.content

        return str(response.content)
