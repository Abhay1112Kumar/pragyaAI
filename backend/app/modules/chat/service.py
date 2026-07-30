from app.modules.chat.prompts import SYSTEM_PROMPT
from app.providers.factory import get_llm_provider
from app.shared.config import settings


class ChatService:
    def __init__(self) -> None:
        self.provider = get_llm_provider()

    def generate_response(self, message: str) -> dict[str, str]:
        answer = self.provider.generate(
            system_prompt=SYSTEM_PROMPT,
            user_message=message,
        )

        return {
            "response": answer,
            "provider": settings.llm_provider,
            "model": settings.ollama_model,
        }


chat_service = ChatService()