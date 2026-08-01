import { BrainCircuit } from "lucide-react";

const suggestions = [
  "Explain RAG in simple language",
  "What is an embedding?",
  "How does an AI agent use tools?",
];

export default function EmptyState({ onSelect }) {
  return (
    <section className="empty-state">
      <div className="empty-icon">
        <BrainCircuit size={34} />
      </div>

      <h2>How can I help you?</h2>

      <p>
        Ask a question to start a conversation with your locally running AI
        model.
      </p>

      <div className="suggestions">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            className="suggestion-button"
            onClick={() => onSelect(suggestion)}
          >
            {suggestion}
          </button>
        ))}
      </div>
    </section>
  );
}