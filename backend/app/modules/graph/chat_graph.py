import hashlib
import json
import logging
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from app.core.config import DEFAULT_RETRIEVAL_COUNT
from app.modules.chat.prompts import SYSTEM_PROMPT
from app.modules.chat.streaming import emit_token
from app.modules.memory.store import (
    ConversationMemoryStore,
    conversation_memory_store,
)
from app.modules.mcp.client import MCPError
from app.modules.mcp.service import mcp_service
from app.providers.factory import get_llm_provider
from app.services.semantic_cache_service import (
    SemanticCacheService,
    semantic_cache_service,
)
from app.services.vector_store_service import vector_store_service
from app.shared.config import settings


logger = logging.getLogger(__name__)

Route = Literal["general", "document_rag", "mcp_tool"]


class ChatGraphState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    query: str
    conversation_id: str
    document_id: str | None
    route: Route
    retrieved_context: list[str]
    sources: list[dict]
    answer: str


class PragyaChatGraph:
    def __init__(
        self,
        memory_store: ConversationMemoryStore = conversation_memory_store,
        semantic_cache: SemanticCacheService | None = semantic_cache_service,
    ) -> None:
        self.memory_store = memory_store
        self.semantic_cache = semantic_cache
        self.graph = self._build_graph()

    def invoke(
        self,
        query: str,
        conversation_id: str,
        document_id: str | None = None,
    ) -> dict:
        history = self._load_history(conversation_id)
        initial_state: ChatGraphState = {
            "messages": [*history, HumanMessage(content=query)],
            "query": query,
            "conversation_id": conversation_id,
            "document_id": document_id,
            "route": "general",
            "retrieved_context": [],
            "sources": [],
            "answer": "",
        }

        result = self.graph.invoke(initial_state)
        self.memory_store.append_exchange(
            conversation_id=conversation_id,
            user_message=query,
            assistant_message=result["answer"],
        )

        return {
            "answer": result["answer"],
            "route": result["route"],
            "sources": result["sources"],
        }

    def _build_graph(self):
        workflow = StateGraph(ChatGraphState)

        workflow.add_node("router", self._route)
        workflow.add_node("general_chat", self._general_chat)
        workflow.add_node("retrieve_document", self._retrieve_document)
        workflow.add_node("rag_answer", self._rag_answer)
        workflow.add_node("mcp_tool", self._mcp_tool)

        workflow.set_entry_point("router")
        workflow.add_conditional_edges(
            "router",
            self._select_route,
            {
                "general": "general_chat",
                "document_rag": "retrieve_document",
                "mcp_tool": "mcp_tool",
            },
        )
        workflow.add_edge("retrieve_document", "rag_answer")
        workflow.add_edge("general_chat", END)
        workflow.add_edge("rag_answer", END)
        workflow.add_edge("mcp_tool", END)

        return workflow.compile()

    def _route(self, state: ChatGraphState) -> dict:
        if mcp_service.is_tool_command(state["query"]):
            route: Route = "mcp_tool"
        elif state.get("document_id"):
            route = "document_rag"
        else:
            route = "general"

        logger.info(
            "Chat graph routed conversation_id=%s route=%s document_id=%s",
            state["conversation_id"],
            route,
            state.get("document_id"),
        )

        return {
            "route": route,
            "retrieved_context": [],
            "sources": [],
            "answer": "",
        }

    def _select_route(self, state: ChatGraphState) -> Route:
        return state["route"]

    def _mcp_tool(self, state: ChatGraphState) -> dict:
        try:
            result = mcp_service.execute_message(state["query"])
            answer = json.dumps(result, indent=2, ensure_ascii=False)
        except MCPError as error:
            answer = f"MCP tool call failed: {error}"

        logger.info(
            "Chat graph executed MCP tool conversation_id=%s",
            state["conversation_id"],
        )
        return {
            "answer": answer,
            "messages": [AIMessage(content=answer)],
            "retrieved_context": [],
            "sources": [],
        }

    def _general_chat(self, state: ChatGraphState) -> dict:
        provider = get_llm_provider()
        user_message = self._build_general_prompt(state)
        answer = self._generate_with_cache(
            provider=provider,
            user_message=user_message,
            route="general",
            document_id=None,
        )

        logger.info(
            "Chat graph answered conversation_id=%s route=general",
            state["conversation_id"],
        )

        return {
            "answer": answer,
            "messages": [AIMessage(content=answer)],
            "retrieved_context": [],
            "sources": [],
        }

    def _retrieve_document(self, state: ChatGraphState) -> dict:
        retrieval_query = self._build_retrieval_query(state)
        chunks = vector_store_service.search(
            query=retrieval_query,
            limit=DEFAULT_RETRIEVAL_COUNT,
            document_id=state["document_id"],
        )

        logger.info(
            "Chat graph retrieved conversation_id=%s document_id=%s chunks=%s",
            state["conversation_id"],
            state.get("document_id"),
            len(chunks),
        )

        return {
            "retrieved_context": self._format_context(chunks),
            "sources": self._format_sources(chunks),
        }

    def _rag_answer(self, state: ChatGraphState) -> dict:
        if not state["retrieved_context"]:
            answer = (
                "I could not find relevant passages in the selected document "
                "for that question."
            )

            return {
                "answer": answer,
                "messages": [AIMessage(content=answer)],
                "sources": [],
            }

        provider = get_llm_provider()
        user_message = self._build_rag_prompt(state)
        answer = self._generate_with_cache(
            provider=provider,
            user_message=user_message,
            route="document_rag",
            document_id=state.get("document_id"),
        )

        logger.info(
            "Chat graph answered conversation_id=%s route=document_rag sources=%s",
            state["conversation_id"],
            len(state["sources"]),
        )

        return {
            "answer": answer,
            "messages": [AIMessage(content=answer)],
        }

    def _load_history(self, conversation_id: str) -> list[BaseMessage]:
        stored_messages = self.memory_store.load_messages(conversation_id)
        history: list[BaseMessage] = []

        for message in stored_messages:
            message_type = (
                AIMessage
                if message["role"] == "assistant"
                else HumanMessage
            )
            history.append(message_type(content=message["content"]))

        return history

    def _generate_with_cache(
        self,
        provider,
        user_message: str,
        route: Route,
        document_id: str | None,
    ) -> str:
        cache_enabled = (
            self.semantic_cache is not None
            and provider.model_name == settings.active_model
        )
        namespace = self._cache_namespace(
            route=route,
            document_id=document_id,
        )

        if cache_enabled:
            try:
                cached_answer = self.semantic_cache.get(
                    prompt=user_message,
                    namespace=namespace,
                )
                if cached_answer is not None:
                    emit_token(cached_answer)
                    logger.info(
                        "Semantic cache hit route=%s document_id=%s",
                        route,
                        document_id,
                    )
                    return cached_answer
            except Exception as error:
                logger.warning("Semantic cache lookup failed: %s", error)

        answer = provider.generate(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
        )

        if cache_enabled:
            try:
                self.semantic_cache.put(
                    prompt=user_message,
                    namespace=namespace,
                    answer=answer,
                )
            except Exception as error:
                logger.warning("Semantic cache write failed: %s", error)

        return answer

    def _cache_namespace(
        self,
        route: Route,
        document_id: str | None,
    ) -> str:
        system_prompt_hash = hashlib.sha256(
            SYSTEM_PROMPT.encode("utf-8")
        ).hexdigest()[:12]
        return "|".join(
            [
                "v1",
                settings.llm_provider,
                settings.active_model,
                route,
                document_id or "no-document",
                system_prompt_hash,
            ]
        )

    def _build_general_prompt(self, state: ChatGraphState) -> str:
        history = self._format_history(state["messages"][:-1])

        if not history:
            return state["query"]

        return (
            "Use the conversation history to answer the latest user message.\n\n"
            f"Conversation history:\n{history}\n\n"
            f"Latest user message:\n{state['query']}"
        )

    def _build_retrieval_query(self, state: ChatGraphState) -> str:
        history = self._format_history(state["messages"][-7:-1])

        if not history:
            return state["query"]

        return (
            f"Conversation history:\n{history}\n\n"
            f"Current question:\n{state['query']}"
        )

    def _build_rag_prompt(self, state: ChatGraphState) -> str:
        history = self._format_history(state["messages"][:-1])
        history_section = (
            f"Conversation history:\n{history}\n\n"
            if history
            else ""
        )

        return (
            "Use the document context below to answer the user's question. "
            "If the answer is not supported by the context, say that the "
            "document does not contain enough information.\n\n"
            f"{history_section}"
            f"Document context:\n{chr(10).join(state['retrieved_context'])}\n\n"
            f"Question: {state['query']}"
        )

    def _format_history(self, messages: list[BaseMessage], limit: int = 10) -> str:
        selected_messages = messages[-limit:]
        history_lines = []

        for message in selected_messages:
            role = "Assistant" if isinstance(message, AIMessage) else "User"
            content = str(message.content).strip()

            if content:
                history_lines.append(f"{role}: {content}")

        return "\n".join(history_lines)

    def _format_context(self, chunks: list[dict]) -> list[str]:
        context_blocks = []

        for index, chunk in enumerate(chunks, start=1):
            metadata = chunk["metadata"]
            filename = metadata.get("filename", "Uploaded document")
            page = metadata.get("page", "unknown")
            content = chunk["content"].strip()

            context_blocks.append(
                f"[Source {index}: {filename}, page {page}]\n{content}"
            )

        return context_blocks

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
                    "retrieval_methods": chunk.get("retrieval_methods", []),
                }
            )

        return sources


pragya_chat_graph = PragyaChatGraph()
