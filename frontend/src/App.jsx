import { useEffect, useState } from "react";

import ChatHeader from "./components/ChatHeader";
import ChatInput from "./components/ChatInput";
import ChatMessage from "./components/ChatMessage";
import EmptyState from "./components/EmptyState";
import { sendMessage } from "./services/api";

import "./App.css";

const ACTIVE_CONVERSATION_STORAGE_KEY = "pragyaai.activeConversation.v1";
const DOCUMENT_METADATA_KEYS = [
  "document_id",
  "filename",
  "file_size",
  "page_count",
  "character_count",
  "chunk_count",
];

function createClientId(prefix = "id") {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }

  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function createConversationId() {
  return createClientId("conversation");
}

function readStoredConversation() {
  try {
    const rawState = globalThis.localStorage?.getItem(
      ACTIVE_CONVERSATION_STORAGE_KEY,
    );

    if (!rawState) {
      return null;
    }

    const parsedState = JSON.parse(rawState);

    if (!parsedState || typeof parsedState !== "object") {
      return null;
    }

    const conversationId =
      typeof parsedState.conversationId === "string" &&
      parsedState.conversationId.trim()
        ? parsedState.conversationId
        : createConversationId();

    return {
      conversationId,
      messages: normalizeMessages(parsedState.messages),
      document: normalizeDocument(parsedState.document),
    };
  } catch {
    return null;
  }
}

function writeStoredConversation(state) {
  try {
    globalThis.localStorage?.setItem(
      ACTIVE_CONVERSATION_STORAGE_KEY,
      JSON.stringify(state),
    );
  } catch {
    // Browser storage may be unavailable or full. The active chat can still run.
  }
}

function normalizeMessages(messages) {
  if (!Array.isArray(messages)) {
    return [];
  }

  return messages
    .filter((message) => {
      return (
        message &&
        typeof message === "object" &&
        typeof message.id === "string" &&
        (message.role === "user" || message.role === "assistant") &&
        typeof message.content === "string"
      );
    })
    .map((message) => ({
      id: message.id,
      role: message.role,
      content: message.content,
    }));
}

function normalizeDocument(document) {
  if (
    !document ||
    typeof document !== "object" ||
    typeof document.document_id !== "string" ||
    !document.document_id.trim() ||
    typeof document.filename !== "string" ||
    !document.filename.trim() ||
    typeof document.chunk_count !== "number"
  ) {
    return null;
  }

  return DOCUMENT_METADATA_KEYS.reduce((metadata, key) => {
    const value = document[key];

    if (
      typeof value === "string" ||
      typeof value === "number" ||
      typeof value === "boolean" ||
      value === null
    ) {
      metadata[key] = value;
    }

    return metadata;
  }, {});
}

const initialConversation = readStoredConversation();

export default function App() {
  const [messages, setMessages] = useState(
    () => initialConversation?.messages ?? [],
  );
  const [document, setDocument] = useState(
    () => initialConversation?.document ?? null,
  );
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(
    () => initialConversation?.conversationId ?? createConversationId(),
  );

  useEffect(() => {
    writeStoredConversation({
      conversationId,
      messages: normalizeMessages(messages),
      document: normalizeDocument(document),
    });
  }, [conversationId, document, messages]);

  function handleNewChat() {
    const nextConversationId = createConversationId();

    setMessages([]);
    setDocument(null);
    setConversationId(nextConversationId);
    writeStoredConversation({
      conversationId: nextConversationId,
      messages: [],
      document: null,
    });
  }

  function handleDocumentUploaded(uploadedDocument) {
    const normalizedDocument = normalizeDocument(uploadedDocument);

    setDocument(normalizedDocument);
    writeStoredConversation({
      conversationId,
      messages: normalizeMessages(messages),
      document: normalizedDocument,
    });
  }

  function handleDocumentClear() {
    setDocument(null);
    writeStoredConversation({
      conversationId,
      messages: normalizeMessages(messages),
      document: null,
    });
  }

  async function handleSend(message) {
    const userMessage = {
      id: createClientId("message"),
      role: "user",
      content: message,
    };

    setMessages((currentMessages) => [
      ...currentMessages,
      userMessage,
    ]);

    setLoading(true);

    try {
      const result = await sendMessage(
        message,
        conversationId,
        document?.document_id ?? null,
      );

      const assistantMessage = {
        id: createClientId("message"),
        role: "assistant",
        content: result.response,
      };

      if (result.conversation_id && result.conversation_id !== conversationId) {
        setConversationId(result.conversation_id);
      }

      setMessages((currentMessages) => [
        ...currentMessages,
        assistantMessage,
      ]);
    } catch (error) {
      const detail =
        error.response?.data?.detail ||
        "Unable to contact the AI service. Check that FastAPI and Ollama are running.";

      const errorMessage = {
        id: createClientId("message"),
        role: "assistant",
        content: detail,
      };

      setMessages((currentMessages) => [
        ...currentMessages,
        errorMessage,
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <main className="chat-card">
        <ChatHeader onNewChat={handleNewChat} disabled={loading} />

        <section className="messages-container">
          {messages.length === 0 ? (
            <EmptyState onSelect={handleSend} />
          ) : (
            <div className="messages-list">
              {messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  role={message.role}
                  content={message.content}
                />
              ))}

              {loading && (
                <div className="message-row assistant-row">
                  <div className="message-avatar">AI</div>

                  <div className="message-bubble ai-message typing-message">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        <footer className="input-section">
          <ChatInput
            key={conversationId}
            onSend={handleSend}
            loading={loading}
            document={document}
            onDocumentUploaded={handleDocumentUploaded}
            onDocumentClear={handleDocumentClear}
          />

          <p className="footer-note">
            Using the configured AI provider
          </p>
        </footer>
      </main>
    </div>
  );
}
