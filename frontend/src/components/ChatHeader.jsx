import { Bot } from "lucide-react";

export default function ChatHeader() {
  return (
    <header className="chat-header">
      <div className="header-logo">
        <Bot size={24} />
      </div>

      <div className="header-content">
        <h1>PragyaAI</h1>
        <p>Local AI assistant with document-aware chat</p>
      </div>
    </header>
  );
}
