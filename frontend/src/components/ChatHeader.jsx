import { Bot, Circle } from "lucide-react";

export default function ChatHeader() {
  return (
    <header className="chat-header">
      <div className="brand-icon">
        <Bot size={24} />
      </div>

      <div className="brand-content">
        <h1>PragyaAI</h1>

        <div className="status">
          <Circle size={8} fill="currentColor" />
          <span>Local AI assistant</span>
        </div>
      </div>
    </header>
  );
}