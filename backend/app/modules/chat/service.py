from collections.abc import Iterator
from queue import Queue
from threading import Thread

from app.modules.chat.streaming import capture_tokens
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

    def stream_response(
        self,
        message: str,
        conversation_id: str,
        document_id: str | None = None,
    ) -> Iterator[tuple[str, dict]]:
        events: Queue[tuple[str, object]] = Queue()

        def run_graph() -> None:
            try:
                with capture_tokens(
                    lambda token: events.put(("token", token))
                ):
                    result = self.generate_response(
                        message=message,
                        conversation_id=conversation_id,
                        document_id=document_id,
                    )
                events.put(("result", result))
            except Exception as error:
                events.put(("error", error))

        Thread(target=run_graph, daemon=True).start()
        emitted_content = False

        while True:
            event_type, payload = events.get()

            if event_type == "token":
                emitted_content = True
                yield "token", {"content": str(payload)}
                continue

            if event_type == "error":
                if isinstance(payload, Exception):
                    raise payload
                raise RuntimeError(str(payload))

            if not isinstance(payload, dict):
                raise RuntimeError("Chat graph returned an invalid result.")

            if not emitted_content and payload["response"]:
                yield "token", {"content": payload["response"]}

            yield "metadata", {
                key: value
                for key, value in payload.items()
                if key != "response"
            }
            yield "done", {"status": "complete"}
            return


chat_service = ChatService()
