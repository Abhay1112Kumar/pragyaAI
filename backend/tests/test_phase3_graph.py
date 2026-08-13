import unittest
from unittest.mock import patch

from app.modules.chat.schemas import ChatRequest
from app.modules.graph.chat_graph import PragyaChatGraph


class FakeProvider:
    model_name = "fake-model"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, system_prompt: str, user_message: str) -> str:
        self.prompts.append(user_message)
        return f"answer {len(self.prompts)}"


class Phase3GraphTests(unittest.TestCase):
    def test_chat_request_generates_conversation_id(self) -> None:
        request = ChatRequest(message="Hello")

        self.assertTrue(request.conversation_id)
        self.assertIsNone(request.document_id)

    def test_general_route_without_document(self) -> None:
        provider = FakeProvider()
        graph = PragyaChatGraph()

        with patch(
            "app.modules.graph.chat_graph.get_llm_provider",
            return_value=provider,
        ):
            result = graph.invoke(
                query="Hello",
                conversation_id="general-thread",
            )

        self.assertEqual(result["route"], "general")
        self.assertEqual(result["sources"], [])

    def test_document_route_reuses_existing_vector_search(self) -> None:
        provider = FakeProvider()
        graph = PragyaChatGraph()
        chunks = [
            {
                "content": "The document explains renewable energy.",
                "metadata": {
                    "filename": "energy.pdf",
                    "page": 2,
                    "chunk_index": 3,
                },
                "score": 0.12,
            }
        ]

        with (
            patch(
                "app.modules.graph.chat_graph.get_llm_provider",
                return_value=provider,
            ),
            patch(
                "app.modules.graph.chat_graph.vector_store_service.search",
                return_value=chunks,
            ) as search,
        ):
            result = graph.invoke(
                query="What is this about?",
                conversation_id="rag-thread",
                document_id="document-1",
            )

        self.assertEqual(result["route"], "document_rag")
        self.assertEqual(result["sources"][0]["filename"], "energy.pdf")
        search.assert_called_once()
        self.assertEqual(search.call_args.kwargs["document_id"], "document-1")

    def test_memory_is_isolated_by_conversation_id(self) -> None:
        provider = FakeProvider()
        graph = PragyaChatGraph()

        with patch(
            "app.modules.graph.chat_graph.get_llm_provider",
            return_value=provider,
        ):
            graph.invoke(
                query="My name is Abhay.",
                conversation_id="conversation-a",
            )
            graph.invoke(
                query="What is my name?",
                conversation_id="conversation-a",
            )
            graph.invoke(
                query="What is my name?",
                conversation_id="conversation-b",
            )

        self.assertIn("My name is Abhay.", provider.prompts[1])
        self.assertNotIn("My name is Abhay.", provider.prompts[2])


if __name__ == "__main__":
    unittest.main()
