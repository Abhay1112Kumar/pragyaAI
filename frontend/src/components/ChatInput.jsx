import { Send } from "lucide-react";
import { useState } from "react";

export default function ChatInput({ onSend, loading, initialValue = "" }) {
  const [message, setMessage] = useState(initialValue);

  function handleSubmit(event) {
    event.preventDefault();

    const cleanedMessage = message.trim();

    if (!cleanedMessage || loading) {
      return;
    }

    onSend(cleanedMessage);
    setMessage("");
  }

  return (
    <form className="chat-input-container" onSubmit={handleSubmit}>
      <textarea
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        placeholder="Ask PragyaAI something..."
        rows={1}
        disabled={loading}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            handleSubmit(event);
          }
        }}
      />

      <button
        type="submit"
        className="send-button"
        disabled={!message.trim() || loading}
        aria-label="Send message"
      >
        <Send size={19} />
      </button>
    </form>
  );
}