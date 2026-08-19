import { Network } from "lucide-react";
import { useState } from "react";

import { queryKnowledgeGraph } from "../services/api";

export default function KnowledgeGraphExplorer() {
  const [query, setQuery] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [graph, setGraph] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!query.trim()) {
      setError("Enter an entity or technical term.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      setGraph(await queryKnowledgeGraph(query.trim(), documentId.trim()));
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to query the knowledge graph.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="graph-explorer">
      <div className="graph-explorer-title">
        <Network size={20} />
        <div>
          <span>Phase 11</span>
          <h3>Knowledge graph explorer</h3>
        </div>
      </div>
      <form onSubmit={handleSubmit}>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search an entity, e.g. FastAPI"
        />
        <input
          value={documentId}
          onChange={(event) => setDocumentId(event.target.value)}
          placeholder="Document ID (optional)"
        />
        <button type="submit" disabled={loading}>
          {loading ? "Exploring…" : "Explore graph"}
        </button>
      </form>
      {error && <div className="auth-error">{error}</div>}
      {graph && (
        <div className="graph-results">
          <div>
            <h4>Entities</h4>
            {graph.entities.length ? graph.entities.map((entity) => (
              <span className="graph-node" key={entity.document_id + entity.name}>
                {entity.name} · {entity.mentions}
              </span>
            )) : <p>No matching entities found.</p>}
          </div>
          <div>
            <h4>Relationships</h4>
            {graph.relations.length ? graph.relations.map((relation) => (
              <div className="graph-edge" key={
                relation.document_id + relation.source + relation.target
              }>
                <strong>{relation.source}</strong>
                <span>→ weight {relation.weight} →</span>
                <strong>{relation.target}</strong>
              </div>
            )) : <p>No relationships found.</p>}
          </div>
        </div>
      )}
    </section>
  );
}
