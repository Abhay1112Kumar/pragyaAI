import { Bot, User } from "lucide-react";

export default function ChatMessage({ role, content, streaming = false }) {
  const isUser = role === "user";

  return (
    <div className={`message-row ${isUser ? "user-row" : "assistant-row"}`}>
      {!isUser && (
        <div className="message-avatar">
          <Bot size={18} />
        </div>
      )}

      <div className="message-content">
        <div className={`message-bubble ${isUser ? "user-message" : "ai-message"}`}>
          {content ? <p>{content}</p> : null}
          {streaming && (
            <span className="streaming-cursor" aria-label="Generating response" />
          )}
        </div>
      </div>

      {isUser && (
        <div className="message-avatar user-avatar">
          <User size={18} />
        </div>
      )}
    </div>
  );
}
