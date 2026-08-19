PragyaAI
========

PragyaAI is a local-first AI assistant with PDF-aware chat. The backend is a
FastAPI application, the frontend is a Vite/React app, and Phase 3 introduces
LangGraph orchestration with short-term conversation memory. Phase 4 adds MCP
tool discovery and execution. Phase 5 adds hybrid document retrieval. Phase 6
streams responses, Phase 7 adds durable memory and caching, Phase 8 adds access
control, Phase 9 adds operations metrics and RAG evaluation, Phase 10 adds
a local knowledge graph plus production-readiness safeguards, Phase 11
connects that graph to RAG and the administration interface, and Phase 12
prepares a free recruiter-demo deployment.

Phase 12
--------

Phase 12 supports a free Vercel frontend and Render backend. The browser API URL
comes from `VITE_API_BASE_URL`; backend CORS origins come from
`CORS_ORIGINS`; and all runtime data can be redirected with `DATA_DIR`.
Local development remains Ollama-first, while `render.yaml` selects Gemini
chat and `models/gemini-embedding-001` embeddings.

The free Render service stores SQLite, ChromaDB, uploaded PDFs, cache, and graph
data under `/tmp/pragyaai`. That storage is intentionally ephemeral and can
reset after sleeping, restarting, or redeploying. The login and application
screens display this limitation. The production manifest disables repository
MCP endpoints with `ENABLE_MCP=false`.

Deployment templates are available at `render.yaml`,
`backend/deployment.env.example`, `frontend/deployment.env.example`, and
`frontend/vercel.json`. Add `GEMINI_API_KEY` only through the Render
dashboard. After Vercel provides its final URL, set Render's `CORS_ORIGINS` to
that URL. After Render provides its final URL, set Vercel's
`VITE_API_BASE_URL` to `https://<service>.onrender.com/api/v1`.

Phase 12 raises the application version to `1.2.0`.

Phase 11
--------

Phase 11 augments document RAG with matching knowledge-graph relationships.
Hybrid BM25 and vector retrieval remains the primary evidence source; graph
relationships are appended as structured context before answer generation.
When no entities match, RAG behaves exactly as before.

The administration dashboard now includes a knowledge-graph explorer. An
administrator can search an entity across owned documents or restrict the query
to one document ID, then inspect entity mention counts and weighted
relationships. The UI uses the authenticated
`GET /api/v1/documents/graph` endpoint introduced in Phase 10.

Phase 11 raises the application version to `1.1.0`.

Phase 10
--------

Phase 10 builds a user-scoped SQLite knowledge graph whenever a new PDF is
uploaded. PragyaAI extracts explainable named and technical entities from each
page and stores weighted co-occurrence relationships in
`backend/data/memory/knowledge_graph.sqlite3`. Re-indexing the same document
replaces its graph instead of creating duplicates.

Authenticated users can inspect their own graph through
`GET /api/v1/documents/graph?query=PragyaAI&document_id=<optional-id>`.
The response contains matching entities, mention counts, related entities, and
relationship weights. Admin metrics also report total graph entity and
relationship counts. PDFs uploaded before Phase 10 must be uploaded again to
populate the graph.

Production readiness now includes `GET /api/v1/ready`, which checks the local
database and provider configuration and reports whether deployment secrets have
been replaced. The existing health endpoint remains a lightweight liveness
check. Every HTTP response includes an `X-Request-ID` for tracing as well as
`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and
`Cache-Control` security headers.

Phase 10 raises the application version to `1.0.0`.

Phase 9
-------

Phase 9 adds an administrator-only operations and RAG evaluation dashboard.
Authenticated chat calls record route, latency, success, user, and timestamp in
`backend/data/memory/metrics.sqlite3`. The dashboard combines those events with
live counts from the user, conversation-memory, semantic-cache, and ChromaDB
stores.

`GET /api/v1/admin/metrics` reports total and 24-hour requests, average
latency, success rate, graph-route distribution, active users, conversations,
messages, indexed documents/chunks, cache entries, and cache hits.

`POST /api/v1/admin/evaluations/retrieval` runs up to 50 test cases through
the real Phase 5 hybrid retriever. Each case supplies a query and expected
keywords, with an optional document ID. Results include keyword recall,
reciprocal rank, pass/fail status, missing terms, and retrieval latency. The
React admin dashboard exposes both the metrics and a one-case evaluation form.

Phase 8
-------

Phase 8 adds local authentication and role-based access control. Passwords are
hashed with bcrypt and users are stored in `backend/data/memory/users.sqlite3`.
Successful login or registration returns an eight-hour HS256 bearer token. Set
strong `AUTH_SECRET_KEY` and `MCP_INTERNAL_KEY` values in `backend/.env`
before any non-local deployment.

The first registered account is bootstrapped as `admin`; later self-registered
accounts receive the `user` role. Administrators can create users or other
administrators through `POST /api/v1/auth/users`. The React UI now provides
registration, sign-in, persisted sessions, role display, and sign-out.

Chat and document endpoints require authentication. Conversation memory,
semantic cache entries, and newly uploaded document chunks are scoped to the
authenticated user. MCP discovery and tool commands require the `admin` role.
The local workspace MCP protocol uses a separate internal key so its
server-to-server hop does not expose an administrator token.

Documents indexed before Phase 8 do not contain ownership metadata and must be
uploaded again before authenticated document search can retrieve them.

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

Cache entries are isolated by provider, model, authenticated user, graph route, document ID, and
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
