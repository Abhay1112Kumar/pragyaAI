import { Bot, User } from "lucide-react";

export default function ChatMessage({ role, content, sources = [] }) {
  const isUser = role === "user";
  const visibleSources = isUser ? [] : sources;

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

        {visibleSources.length > 0 && (
          <div className="message-sources">
            <span className="sources-title">Sources</span>

            {visibleSources.map((source, index) => (
              <span
                key={`${source.filename}-${source.page}-${source.chunk_index}-${index}`}
                className="source-chip"
              >
                {source.filename || "Document"}
                {source.page ? `, page ${source.page}` : ""}
              </span>
            ))}
          </div>
        )}
      </div>

      {isUser && (
        <div className="message-avatar user-avatar">
          <User size={18} />
        </div>
      )}
    </div>
  );
}
