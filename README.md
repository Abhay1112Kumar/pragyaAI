PragyaAI
========

PragyaAI is a local-first AI assistant with PDF-aware chat. The backend is a
FastAPI application, the frontend is a Vite/React app, and Phase 3 introduces
LangGraph orchestration with short-term conversation memory. Phase 4 adds MCP
tool discovery and execution. Phase 5 adds hybrid document retrieval, and Phase 6\nstreams responses to the UI in real time.

Phase 7
-------

Phase 7 makes conversation memory and repeated-answer caching durable across
backend restarts. Conversation turns are stored in
`backend/data/memory/conversations.sqlite3` and loaded by `conversation_id`
before each LangGraph execution. The most recent 20 messages are included to
keep prompts bounded.

A persistent semantic cache stores prompt embeddings and completed answers in
`backend/data/memory/semantic_cache.sqlite3`. Before calling the LLM, PragyaAI
compares the complete generated prompt with cached prompts using cosine
similarity. A match at or above `0.92` reuses the answer and streams it through
the Phase 6 SSE path without another LLM call.

Cache entries are isolated by provider, model, graph route, document ID, and
system-prompt version. Entries expire after seven days, and the least recently
used entries are pruned above 500 records. If the embedding service or cache is
unavailable, PragyaAI logs the problem and safely falls back to normal LLM
generation.

Phase 6
-------

Phase 6 adds real-time response streaming over Server-Sent Events (SSE).
The React client sends chat requests to `POST /api/v1/chat/stream` and renders
each token as Ollama or Gemini generates it, instead of waiting for the complete
answer. The existing `POST /api/v1/chat` JSON endpoint remains available for
backward compatibility.

The stream uses named SSE events:

- `token`: the next piece of generated response text.
- `metadata`: provider, model, conversation ID, graph route, and RAG sources.
- `done`: successful completion of the response.
- `error`: a safe error message if generation fails after streaming begins.

LangGraph remains responsible for routing, conversation memory, document RAG,
and MCP execution. Streaming is captured inside the configured provider, so a
streamed response is stored in the same conversation history as a normal
response. MCP and other non-token-producing routes fall back to one complete
`token` event followed by metadata and completion.

Phase 5
-------

Phase 5 combines BM25 keyword retrieval with ChromaDB semantic vector search.
Each query collects candidates from both retrievers and merges their rankings
with Reciprocal Rank Fusion (RRF). This lets exact names, identifiers, and
technical terms compete fairly with passages that match the query's meaning.

Hybrid retrieval is used by both `POST /api/v1/documents/search` and the
LangGraph `retrieve_document` node. Results include a fused relevance `score`
and `retrieval_methods` showing whether a chunk was found by `semantic`,
`bm25`, or both. Existing document filters are applied to both retrievers.

Phase 4
-------

Phase 4 connects PragyaAI to MCP servers over JSON-RPC. A built-in
`workspace` server is available automatically at
`POST /api/v1/mcp/protocol`. It is restricted to this repository and exposes
`list_files`, `read_file`, `search_code`, and read-only `git_status`.

Discover tools with `GET /api/v1/mcp/tools`. Execute a tool through the chat
graph using an explicit, auditable command:

```text
/tool workspace.search_code {"query":"LangGraph"}
```

Tool commands are routed to the new `mcp_tool` LangGraph node. The endpoint
supports `initialize`, `tools/list`, and `tools/call`; the client uses the tool
methods for discovery and execution,
surfaces connection and protocol errors safely, and never sends MCP output
through the LLM. General chat and document RAG behavior remain unchanged.

Additional HTTP MCP servers can replace or extend the default through
`MCP_SERVERS_JSON`, for example
`{"workspace":"http://127.0.0.1:8000/api/v1/mcp/protocol","other":"http://127.0.0.1:9000/mcp"}`.

Phase 3
-------

Phase 3 adds a real LangGraph workflow around the existing Phase 2 chat and
RAG capabilities. Ollama/Qwen remains the default local LLM provider, and the
existing PDF extraction, chunking, `nomic-embed-text` embeddings, ChromaDB
persistence, retrieval, and source metadata behavior are preserved.

The graph state contains:

- `messages`
- `query`
- `conversation_id`
- `document_id`
- `route`
- `retrieved_context`
- `sources`
- `answer`

The graph has these nodes:

- `router`: deterministically routes to document RAG when a `document_id` is
  selected, otherwise to general chat.
- `general_chat`: answers normal conversational questions using the configured
  provider abstraction and LangGraph thread history.
- `retrieve_document`: reuses the existing ChromaDB/vector store service.
- `rag_answer`: answers from retrieved PDF context while preserving citations.

```text
React UI
   |
   | POST /chat
   v
FastAPI
   |
   v
Chat Service
   |
   v
LangGraph
   |
   v
Router
 /     \
General  RAG
 Chat    Retrieval
   \       |
    \      v
     \   ChromaDB
      \     |
       \    v
        --> LLM
             |
             v
          Response
```

Phase 3 originally stored conversation memory with LangGraph's
`InMemorySaver`. Phase 7 replaces that process-local checkpoint with durable
SQLite storage. Each request still includes a `conversation_id`, which isolates
and restores the corresponding conversation history after backend restarts.

The browser stores the active conversation ID, visible messages, and selected
PDF metadata in `localStorage` under `pragyaai.activeConversation.v1`. This
restores the current chat after a browser reload, including the selected
`document_id`. Phase 7 independently persists backend conversation memory in
SQLite. The PDF file itself is not stored in the browser.

Starting a New Chat in the UI creates a new conversation ID, clears visible
messages, clears the selected document, updates browser storage, and starts an
isolated LangGraph thread. It does not delete uploaded PDFs or ChromaDB vectors
from the backend.

When a PDF is selected, submitting an empty input sends:

```text
Summarize and explain this document in simple language.
```

Without a selected PDF, empty submissions remain disabled. Backend RAG responses
still return `sources` for future use, but the current chat UI does not display
source headings, filenames, page chips, or citation lists.

Backend request example:

```json
{
  "message": "Explain this section",
  "conversation_id": "5d23c165-3f16-4b6f-8e09-32c7592c6e8a",
  "document_id": "0f84b868-1925-4ef7-a019-3d77346da63f"
}
```

Local runtime requirements:

- Ollama running locally.
- Chat model installed, by default `qwen2.5:3b`.
- Embedding model installed, by default `nomic-embed-text`.
- Python dependencies from `backend/requirements.txt`.
- Node dependencies from `frontend/package-lock.json`.
