import {
  Activity,
  Database,
  Gauge,
  MessagesSquare,
  SearchCheck,
  Users,
} from "lucide-react";
import { useEffect, useState } from "react";

import { fetchAdminMetrics, runRetrievalEvaluation } from "../services/api";

function MetricCard({ icon: Icon, label, value, detail }) {
  return (
    <article className="metric-card">
      <div className="metric-icon"><Icon size={19} /></div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        {detail && <small>{detail}</small>}
      </div>
    </article>
  );
}

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [expectedTerms, setExpectedTerms] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [evaluation, setEvaluation] = useState(null);
  const [evaluating, setEvaluating] = useState(false);

  useEffect(() => {
    let active = true;
    fetchAdminMetrics()
      .then((result) => {
        if (active) setMetrics(result);
      })
      .catch((requestError) => {
        if (active) {
          setError(
            requestError.response?.data?.detail ||
              "Unable to load administration metrics.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleEvaluate(event) {
    event.preventDefault();
    const terms = expectedTerms
      .split(",")
      .map((term) => term.trim())
      .filter(Boolean);

    if (!query.trim() || terms.length === 0) {
      setError("Enter a query and at least one expected keyword.");
      return;
    }

    setError("");
    setEvaluating(true);
    setEvaluation(null);

    try {
      const result = await runRetrievalEvaluation({
        cases: [{
          query: query.trim(),
          expected_terms: terms,
          document_id: documentId.trim() || null,
          limit: 4,
        }],
      });
      setEvaluation(result);
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
          "Unable to run the retrieval evaluation.",
      );
    } finally {
      setEvaluating(false);
    }
  }

  if (loading) {
    return <div className="admin-loading">Loading real system metrics…</div>;
  }

  return (
    <section className="admin-dashboard">
      <div className="admin-title">
        <span>Phase 9</span>
        <h2>System metrics and RAG evaluation</h2>
      </div>

      {error && <div className="auth-error">{error}</div>}

      {metrics && (
        <>
          <div className="metric-grid">
            <MetricCard
              icon={Users}
              label="Active users"
              value={metrics.users.total}
              detail={metrics.users.admins + " administrators"}
            />
            <MetricCard
              icon={Activity}
              label="Chat requests"
              value={metrics.usage.total_requests}
              detail={metrics.usage.requests_24h + " in the last 24 hours"}
            />
            <MetricCard
              icon={Gauge}
              label="Average latency"
              value={metrics.usage.average_latency_ms + " ms"}
              detail={metrics.usage.success_rate + "% success"}
            />
            <MetricCard
              icon={MessagesSquare}
              label="Conversations"
              value={metrics.memory.conversations}
              detail={metrics.memory.messages + " stored messages"}
            />
            <MetricCard
              icon={Database}
              label="Knowledge base"
              value={metrics.documents.documents}
              detail={metrics.documents.chunks + " indexed chunks"}
            />
            <MetricCard
              icon={SearchCheck}
              label="Semantic cache"
              value={metrics.cache.entries}
              detail={metrics.cache.hits + " cache hits"}
            />
          </div>

          <div className="route-summary">
            <h3>Graph routes</h3>
            {Object.keys(metrics.usage.route_counts).length ? (
              Object.entries(metrics.usage.route_counts).map(
                ([route, count]) => (
                  <div key={route}>
                    <span>{route.replaceAll("_", " ")}</span>
                    <strong>{count}</strong>
                  </div>
                ),
              )
            ) : (
              <p>No authenticated chat requests recorded yet.</p>
            )}
          </div>
        </>
      )}

      <form className="evaluation-panel" onSubmit={handleEvaluate}>
        <div>
          <span>Retrieval evaluation</span>
          <h3>Test whether hybrid search finds expected information</h3>
        </div>
        <label>
          Evaluation query
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="What does the document say about refunds?"
          />
        </label>
        <label>
          Expected keywords, separated by commas
          <input
            value={expectedTerms}
            onChange={(event) => setExpectedTerms(event.target.value)}
            placeholder="refund, settlement, timeline"
          />
        </label>
        <label>
          Document ID (optional)
          <input
            value={documentId}
            onChange={(event) => setDocumentId(event.target.value)}
            placeholder="Use the uploaded document ID"
          />
        </label>
        <button type="submit" disabled={evaluating}>
          {evaluating ? "Evaluating…" : "Run evaluation"}
        </button>
      </form>

      {evaluation && (
        <div className="evaluation-result">
          <div><span>Pass rate</span><strong>{evaluation.pass_rate}%</strong></div>
          <div><span>Recall</span><strong>{evaluation.average_recall}</strong></div>
          <div><span>MRR</span><strong>{evaluation.mean_reciprocal_rank}</strong></div>
          <div><span>Latency</span><strong>{evaluation.average_latency_ms} ms</strong></div>
          <p>
            {evaluation.results[0].passed
              ? "All expected keywords were found."
              : "Missing: " + evaluation.results[0].missing_terms.join(", ")}
          </p>
        </div>
      )}
    </section>
  );
}
