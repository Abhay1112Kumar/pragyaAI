"""Optional Google Gemini LLM provider."""

from app.providers.base import BaseLLMProvider
from app.shared.config import settings


class GeminiProvider(BaseLLMProvider):
    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER is gemini.")

        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        self.client = genai.GenerativeModel(settings.gemini_model)

    @property
    def model_name(self) -> str:
        return settings.gemini_model

    def generate(self, system_prompt: str, user_message: str) -> str:
        response = self.client.generate_content(
            f"{system_prompt}\n\nUser message:\n{user_message}"
        )

        if response.text:
            return response.text

        raise RuntimeError("Gemini returned an empty response.")
