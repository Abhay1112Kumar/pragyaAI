import { useEffect, useState } from "react";

import AuthScreen from "./components/AuthScreen";
import ChatHeader from "./components/ChatHeader";
import ChatInput from "./components/ChatInput";
import ChatMessage from "./components/ChatMessage";
import EmptyState from "./components/EmptyState";
import { setAccessToken, streamMessage } from "./services/api";

import "./App.css";

const ACTIVE_CONVERSATION_STORAGE_KEY = "pragyaai.activeConversation.v1";
const AUTH_STORAGE_KEY = "pragyaai.auth.v1";

function readStoredAuth() {
  try {
    const stored = JSON.parse(
      globalThis.localStorage?.getItem(AUTH_STORAGE_KEY) || "null",
    );
    if (
      typeof stored?.access_token === "string" &&
      typeof stored?.user?.username === "string"
    ) {
      return stored;
    }
  } catch {
    // Invalid or unavailable local storage means the user signs in again.
  }
  return null;
}

const initialAuth = readStoredAuth();
setAccessToken(initialAuth?.access_token);
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
  const [auth, setAuth] = useState(initialAuth);
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

  function handleAuthenticated(result) {
    setAccessToken(result.access_token);
    setAuth(result);
    globalThis.localStorage?.setItem(AUTH_STORAGE_KEY, JSON.stringify(result));
  }

  function handleLogout() {
    setAccessToken(null);
    setAuth(null);
    setMessages([]);
    setDocument(null);
    globalThis.localStorage?.removeItem(AUTH_STORAGE_KEY);
    globalThis.localStorage?.removeItem(ACTIVE_CONVERSATION_STORAGE_KEY);
  }

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

    const assistantMessageId = createClientId("message");
    const assistantMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      streaming: true,
    };

    setMessages((currentMessages) => [
      ...currentMessages,
      userMessage,
      assistantMessage,
    ]);
    setLoading(true);

    try {
      const metadata = await streamMessage(
        message,
        conversationId,
        document?.document_id ?? null,
        {
          onToken(token) {
            setMessages((currentMessages) =>
              currentMessages.map((currentMessage) =>
                currentMessage.id === assistantMessageId
                  ? {
                      ...currentMessage,
                      content: currentMessage.content + token,
                    }
                  : currentMessage,
              ),
            );
          },
        },
      );

      if (
        metadata?.conversation_id &&
        metadata.conversation_id !== conversationId
      ) {
        setConversationId(metadata.conversation_id);
      }
    } catch (error) {
      const detail =
        error.message ||
        "Unable to contact the AI service. Check that FastAPI and Ollama are running.";

      setMessages((currentMessages) =>
        currentMessages.map((currentMessage) =>
          currentMessage.id === assistantMessageId
            ? {
                ...currentMessage,
                content: currentMessage.content || detail,
              }
            : currentMessage,
        ),
      );
    } finally {
      setMessages((currentMessages) =>
        currentMessages.map((currentMessage) =>
          currentMessage.id === assistantMessageId
            ? { ...currentMessage, streaming: false }
            : currentMessage,
        ),
      );
      setLoading(false);
    }
  }

  if (!auth) {
    return <AuthScreen onAuthenticated={handleAuthenticated} />;
  }

  return (
    <div className="app-shell">
      <main className="chat-card">
        <ChatHeader
          onNewChat={handleNewChat}
          onLogout={handleLogout}
          user={auth.user}
          disabled={loading}
        />

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
                  streaming={message.streaming}
                />
              ))}
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
