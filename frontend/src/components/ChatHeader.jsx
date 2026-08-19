import {
  BarChart3,
  Bot,
  LogOut,
  MessageSquarePlus,
} from "lucide-react";

export default function ChatHeader({
  onNewChat,
  onLogout,
  onToggleAdmin,
  adminOpen,
  user,
  disabled = false,
}) {
  return (
    <header className="chat-header">
      <div className="header-logo">
        <Bot size={24} />
      </div>

      <div className="header-content">
        <h1>PragyaAI</h1>
        <p>Document-aware AI assistant</p>
      </div>

      <div className="header-user">
        <span>{user.username}</span>
        <small>{user.role}</small>
      </div>

      {user.role === "admin" && (
        <button
          type="button"
          className={"admin-toggle-button " + (adminOpen ? "active" : "")}
          onClick={onToggleAdmin}
          disabled={disabled}
          title="Administration dashboard"
          aria-label="Toggle administration dashboard"
        >
          <BarChart3 size={18} />
        </button>
      )}

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

      <button
        type="button"
        className="logout-button"
        onClick={onLogout}
        disabled={disabled}
        title="Sign out"
        aria-label="Sign out"
      >
        <LogOut size={18} />
      </button>
    </header>
  );
}
