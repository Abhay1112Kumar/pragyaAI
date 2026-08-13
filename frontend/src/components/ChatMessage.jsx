import { Bot, User } from "lucide-react";

export default function ChatMessage({ role, content }) {
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
          <p>{content}</p>
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
