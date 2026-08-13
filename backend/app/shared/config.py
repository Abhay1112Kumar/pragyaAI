import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    app_name: str = os.getenv("APP_NAME", "PragyaAI")
    app_version: str = os.getenv("APP_VERSION", "0.3.0")

    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    ollama_base_url: str = os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434",
    )

    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-pro")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")

    @property
    def active_model(self) -> str:
        provider_name = self.llm_provider.lower()

        if provider_name == "gemini":
            return self.gemini_model

        return self.ollama_model


settings = Settings()
