import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.modules.graph.chat_graph import PragyaChatGraph
from app.modules.memory.store import ConversationMemoryStore
from app.services.semantic_cache_service import SemanticCacheService
from app.shared.config import settings


class FakeProvider:
    def __init__(self, model_name: str = "fake-model") -> None:
        self.model_name = model_name
        self.prompts: list[str] = []

    def generate(self, system_prompt: str, user_message: str) -> str:
        self.prompts.append(user_message)
        return f"generated answer {len(self.prompts)}"


class Phase7PersistenceAndCacheTests(unittest.TestCase):
    def test_conversation_memory_survives_graph_recreation(self) -> None:
        provider = FakeProvider()

        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "memory.sqlite3"
            first_store = ConversationMemoryStore(database_path)
            first_graph = PragyaChatGraph(
                memory_store=first_store,
                semantic_cache=None,
            )

            with patch(
                "app.modules.graph.chat_graph.get_llm_provider",
                return_value=provider,
            ):
                first_graph.invoke(
                    query="My name is Abhay.",
                    conversation_id="durable-thread",
                )

            first_store.close()
            second_store = ConversationMemoryStore(database_path)
            second_graph = PragyaChatGraph(
                memory_store=second_store,
                semantic_cache=None,
            )

            with patch(
                "app.modules.graph.chat_graph.get_llm_provider",
                return_value=provider,
            ):
                second_graph.invoke(
                    query="What is my name?",
                    conversation_id="durable-thread",
                )

            second_store.close()

        self.assertIn("My name is Abhay.", provider.prompts[1])

    def test_semantic_cache_matches_similar_prompt_in_same_namespace(self) -> None:
        def embed_query(text: str) -> list[float]:
            lowered = text.lower()
            if "france" in lowered or "french" in lowered:
                return [1.0, 0.0]
            return [0.0, 1.0]

        cache = SemanticCacheService(
            database_path=":memory:",
            embed_query=embed_query,
            threshold=0.9,
        )
        cache.put(
            prompt="What is the capital of France?",
            namespace="general",
            answer="Paris",
        )

        self.assertEqual(
            cache.get(
                prompt="Name the French capital.",
                namespace="general",
            ),
            "Paris",
        )
        self.assertIsNone(
            cache.get(
                prompt="Name the French capital.",
                namespace="different-document",
            )
        )
        cache.close()

    def test_graph_reuses_cached_answer_without_second_llm_call(self) -> None:
        provider = FakeProvider(model_name=settings.active_model)
        memory_store = ConversationMemoryStore(":memory:")
        cache = SemanticCacheService(
            database_path=":memory:",
            embed_query=lambda _text: [1.0, 0.0],
            threshold=0.9,
        )
        graph = PragyaChatGraph(
            memory_store=memory_store,
            semantic_cache=cache,
        )

        with patch(
            "app.modules.graph.chat_graph.get_llm_provider",
            return_value=provider,
        ):
            first = graph.invoke(
                query="Explain semantic caching.",
                conversation_id="cache-thread",
            )
            second = graph.invoke(
                query="Explain the semantic cache again.",
                conversation_id="cache-thread",
            )

        self.assertEqual(len(provider.prompts), 1)
        self.assertEqual(second["answer"], first["answer"])
        cache.close()
        memory_store.close()


if __name__ == "__main__":
    unittest.main()
