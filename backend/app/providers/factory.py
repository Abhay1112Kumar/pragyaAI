from functools import lru_cache

from app.providers.base import BaseLLMProvider
from app.providers.ollama import OllamaProvider
from app.shared.config import settings


@lru_cache
def get_llm_provider() -> BaseLLMProvider:
    provider_name = settings.llm_provider.lower()

    if provider_name == "ollama":
        return OllamaProvider()

    raise ValueError(
        f"Unsupported LLM provider: {settings.llm_provider}"
    )