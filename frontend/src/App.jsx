import { useState } from "react";

import ChatHeader from "./components/ChatHeader";
import ChatInput from "./components/ChatInput";
import ChatMessage from "./components/ChatMessage";
import EmptyState from "./components/EmptyState";
import { sendMessage } from "./services/api";

import "./App.css";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  async function handleSend(message) {
    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: message,
    };

    setMessages((currentMessages) => [
      ...currentMessages,
      userMessage,
    ]);

    setLoading(true);

    try {
      const result = await sendMessage(message);

      const assistantMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: result.response,
      };

      setMessages((currentMessages) => [
        ...currentMessages,
        assistantMessage,
      ]);
    } catch (error) {
      const detail =
        error.response?.data?.detail ||
        "Unable to contact the AI service. Check that FastAPI and Ollama are running.";

      const errorMessage = {
        id: crypto.randomUUID(),
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
        <ChatHeader />

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
          <ChatInput onSend={handleSend} loading={loading} />

          <p className="footer-note">
            Running locally with Ollama and Qwen 2.5
          </p>
        </footer>
      </main>
    </div>
  );
}