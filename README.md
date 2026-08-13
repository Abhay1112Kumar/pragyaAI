PragyaAI
========

PragyaAI is a local-first AI assistant with PDF-aware chat. The backend is a
FastAPI application, the frontend is a Vite/React app, and Phase 3 introduces
LangGraph orchestration with short-term conversation memory.

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

Conversation memory is stored with LangGraph's `InMemorySaver` in this phase.
Each request includes a `conversation_id`, which is used as the LangGraph thread
identifier. This backend memory is process-local and resets when the backend
restarts; it is not durable storage.

The browser stores the active conversation ID, visible messages, and selected
PDF metadata in `localStorage` under `pragyaai.activeConversation.v1`. This
restores the current chat after a browser reload, including the selected
`document_id`, but it does not persist LangGraph memory across a backend
restart. The PDF file itself is not stored in the browser.

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
