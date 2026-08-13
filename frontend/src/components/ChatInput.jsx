import { Send } from "lucide-react";
import { useState } from "react";

import DocumentUpload from "./DocumentUpload";

const DEFAULT_DOCUMENT_PROMPT =
  "Summarize and explain this document in simple language.";

export default function ChatInput({
  onSend,
  loading,
  initialValue = "",
  document,
  onDocumentUploaded,
  onDocumentClear,
}) {
  const [message, setMessage] = useState(initialValue);

  function handleSubmit(event) {
    event.preventDefault();

    const cleanedMessage = message.trim();
    const messageToSend =
      cleanedMessage || (document ? DEFAULT_DOCUMENT_PROMPT : "");

    if (!messageToSend || loading) {
      return;
    }

    onSend(messageToSend);
    setMessage("");
  }

  return (
    <form className="chat-input-form" onSubmit={handleSubmit}>
      <DocumentUpload
        document={document}
        onUploaded={onDocumentUploaded}
        onClear={onDocumentClear}
        disabled={loading}
      />

      <textarea
        className="chat-input"
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
        disabled={loading || (!message.trim() && !document)}
        aria-label="Send message"
      >
        <Send size={19} />
      </button>
    </form>
  );
}
