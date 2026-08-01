from app.core.config import DEFAULT_RETRIEVAL_COUNT
from app.modules.chat.prompts import SYSTEM_PROMPT
from app.providers.factory import get_llm_provider
from app.services.vector_store_service import vector_store_service
from app.shared.config import settings


class ChatService:
    def __init__(self) -> None:
        self.provider = get_llm_provider()

    def generate_response(
        self,
        message: str,
        document_id: str | None = None,
    ) -> dict:
        retrieved_chunks = []
        user_message = message

        if document_id:
            retrieved_chunks = vector_store_service.search(
                query=message,
                limit=DEFAULT_RETRIEVAL_COUNT,
                document_id=document_id,
            )

            if not retrieved_chunks:
                return {
                    "response": (
                        "I could not find relevant passages in the selected "
                        "document for that question."
                    ),
                    "provider": settings.llm_provider,
                    "model": settings.ollama_model,
                    "sources": [],
                }

            context = self._format_context(retrieved_chunks)
            user_message = (
                "Use the document context below to answer the question. "
                "If the answer is not in the context, say that the "
                "document does not contain enough information.\n\n"
                f"Document context:\n{context}\n\n"
                f"Question: {message}"
            )

        answer = self.provider.generate(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
        )

        return {
            "response": answer,
            "provider": settings.llm_provider,
            "model": settings.ollama_model,
            "sources": self._format_sources(retrieved_chunks),
        }

    def _format_context(self, chunks: list[dict]) -> str:
        context_blocks = []

        for index, chunk in enumerate(chunks, start=1):
            metadata = chunk["metadata"]
            filename = metadata.get("filename", "Uploaded document")
            page = metadata.get("page", "unknown")
            content = chunk["content"].strip()

            context_blocks.append(
                f"[Source {index}: {filename}, page {page}]\n{content}"
            )

        return "\n\n".join(context_blocks)

    def _format_sources(self, chunks: list[dict]) -> list[dict]:
        sources = []

        for chunk in chunks:
            metadata = chunk["metadata"]
            sources.append(
                {
                    "filename": metadata.get("filename"),
                    "page": metadata.get("page"),
                    "chunk_index": metadata.get("chunk_index"),
                    "score": chunk["score"],
                }
            )

        return sources


chat_service = ChatService()
