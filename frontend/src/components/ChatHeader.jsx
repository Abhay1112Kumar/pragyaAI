import { Bot, MessageSquarePlus } from "lucide-react";

export default function ChatHeader({ onNewChat, disabled = false }) {
  return (
    <header className="chat-header">
      <div className="header-logo">
        <Bot size={24} />
      </div>

      <div className="header-content">
        <h1>PragyaAI</h1>
        <p>Document-aware AI assistant</p>
      </div>

      <button
        type="button"
        className="new-chat-button"
        onClick={onNewChat}
        disabled={disabled}
        title="New chat"
        aria-label="Start a new chat"
      >
        <MessageSquarePlus size={18} />
        <span>New Chat</span>
      </button>
    </header>
  );
}
