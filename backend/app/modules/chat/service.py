from app.providers.factory import get_llm_provider
from app.modules.graph import pragya_chat_graph
from app.shared.config import settings


class ChatService:
    def generate_response(
        self,
        message: str,
        conversation_id: str,
        document_id: str | None = None,
    ) -> dict:
        provider = get_llm_provider()
        result = pragya_chat_graph.invoke(
            query=message,
            conversation_id=conversation_id,
            document_id=document_id,
        )

        return {
            "response": result["answer"],
            "provider": settings.llm_provider,
            "model": provider.model_name,
            "conversation_id": conversation_id,
            "route": result["route"],
            "sources": result["sources"],
        }


chat_service = ChatService()
