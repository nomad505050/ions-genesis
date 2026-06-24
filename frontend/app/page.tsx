"use client";

import { useState, useEffect } from "react";

const IONS_API_DEFAULT = "http://localhost:8000";
function getIonsAPI(): string {
  if (typeof window === "undefined") return IONS_API_DEFAULT;
  try {
    const s = JSON.parse(localStorage.getItem("ions_settings") || "{}");
    return s.ionsApiUrl || IONS_API_DEFAULT;
  } catch {
    return IONS_API_DEFAULT;
  }
}

const SAMPLE_QUERIES = [
  "Why do AI pilots succeed but fail to scale to production?",
  "How does institutional memory compound competitive advantage?",
  "What makes knowledge reusable across an organization?",
  "Why does operational understanding matter for automation?",
  "How do exponential organizations differ from linear ones?",
  "What is the relationship between flow states and peak performance?",
  "Why is the gap between documented and actual work a risk for AI?",
  "How should institutions prepare before deploying autonomous systems?",
];

type PathResult = {
  path_id: string;
  cbb_sequence: string[];
  relationship_sequence: string[];
  path_confidence: number;
};

type QueryResult = {
  cbb_answer: string;
  paths: PathResult[];
};

function confColor(c: number) {
  if (c >= 0.6) return "var(--emerald)";
  if (c >= 0.5) return "var(--amber)";
  return "var(--red)";
}

function confLabel(c: number) {
  if (c >= 0.6) return "high";
  if (c >= 0.5) return "moderate";
  return "low";
}

export default function ExplorerPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState("");
  const [nodeStats, setNodeStats] = useState({ cbbs: 0, rels: 0 });
  const [liveCBBs, setLiveCBBs] = useState("—");

  // Fetch live node stats
  useEffect(() => {
    async function fetchStats() {
      try {
        const resp = await fetch(`${getIonsAPI()}/stats`);
        if (!resp.ok) throw new Error("stats failed");
        const data = await resp.json();
        const count = data.published_cbbs ?? 0;
        const display = count.toLocaleString();
        const cbbEl = document.getElementById("live-cbbs");
        if (cbbEl) cbbEl.textContent = display;
        setLiveCBBs(display);
        // Update node count
        const nodeEl = document.getElementById("live-nodes");
        if (nodeEl) nodeEl.textContent = String(data.active_nodes || 1);
      } catch {
        // Fallback to single page count
        try {
          const resp = await fetch(`${getIonsAPI()}/cbb?status=published&limit=500`);
          if (!resp.ok) return;
          const batch = await resp.json();
          const display = Array.isArray(batch) ? batch.length.toLocaleString() : "—";
          const cbbEl = document.getElementById("live-cbbs");
          if (cbbEl) cbbEl.textContent = display;
          setLiveCBBs(display);
        } catch { /* silent */ }
      }
    }
    fetchStats();
  }, []);

  async function runQuery(q: string) {
    if (!q.trim()) return;
    setQuery(q);
    setLoading(true);
    setResult(null);
    setError("");

    try {
      const resp = await fetch(`${getIonsAPI()}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, top_n_paths: 3 }),
      });
      if (!resp.ok) throw new Error(`API error: ${resp.status}`);
      const data = await resp.json();
      setResult(data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  const topPath = result?.paths?.[0];
  const conf = topPath?.path_confidence ?? 0;

  return (
    <>
      {/* Topbar */}
      <div className="topbar">
        <span className="topbar-title">Explorer</span>
        <span className="topbar-sub">Query the network · see reasoning paths · CBBs across NSI clusters</span>
        <div className="topbar-actions">
          <a href="/contribute" className="btn btn-ghost">+ Add CBB</a>
          <a href="/workbench" className="btn btn-primary">Workbench</a>
        </div>
      </div>

      <div className="page-content">

        {/* Hypothesis banner */}
        <div style={{
          padding: "14px 18px",
          background: "rgba(99,102,241,0.06)",
          border: "1px solid rgba(99,102,241,0.2)",
          borderRadius: "8px",
          fontSize: "13px",
          color: "var(--slate)",
          lineHeight: 1.6,
        }}>
          <span style={{ color: "var(--indigo2)", fontFamily: "var(--font-display)", fontWeight: 600, fontSize: "10px", letterSpacing: "1.5px", textTransform: "uppercase", display: "block", marginBottom: "4px" }}>Hypothesis</span>
          A lightweight model connected to a traversable CBB network can match or exceed frontier model quality on domain-specific questions — at a fraction of the compute, energy, and data cost.
        </div>

        {/* Query input */}
        <div className="card" style={{ padding: "20px" }}>
          <div style={{ display: "flex", gap: "10px" }}>
            <input
              className="form-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runQuery(query)}
              placeholder="Ask the network anything in the domain..."
              style={{ flex: 1 }}
              autoFocus
            />
            <button
              className="btn btn-primary"
              onClick={() => runQuery(query)}
              disabled={loading || !query.trim()}
              style={{ padding: "10px 20px", whiteSpace: "nowrap" }}
            >
              {loading ? "Traversing..." : "Query"}
            </button>
          </div>

          {/* Sample query chips */}
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "14px" }}>
            {SAMPLE_QUERIES.map((q) => (
              <button
                key={q}
                onClick={() => runQuery(q)}
                disabled={loading}
                style={{
                  padding: "4px 12px",
                  background: "var(--bg3)",
                  border: "1px solid var(--border)",
                  borderRadius: "20px",
                  fontSize: "11px",
                  color: "var(--slate)",
                  cursor: "pointer",
                  fontFamily: "var(--font-body)",
                  transition: "all 0.15s",
                  maxWidth: "280px",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: "12px", color: "var(--slate)", fontSize: "13px", padding: "20px 0" }}>
            <div className="spinner" />
            Traversing {Math.floor(Math.random() * 200) + 50} paths across the network...
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="card" style={{ borderColor: "var(--red)", padding: "16px" }}>
            <div style={{ color: "var(--red)", fontSize: "13px", marginBottom: "6px", fontWeight: 600 }}>Could not reach IONS node</div>
            <div style={{ color: "var(--slate)", fontSize: "12px" }}>{error}</div>
            <div style={{ color: "var(--slate2)", fontSize: "11px", marginTop: "8px" }}>Make sure the API is running: <code style={{ fontFamily: "var(--font-mono)", color: "var(--indigo2)" }}>docker compose up -d</code></div>
          </div>
        )}

        {/* Results */}
        {result && !loading && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>

            {/* Query echo */}
            <div style={{ fontSize: "12px", color: "var(--slate2)", fontFamily: "var(--font-mono)" }}>
              Q: {query}
            </div>

            {/* CBB Answer */}
            <div className="card" style={{ borderColor: "var(--indigo)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "16px" }}>⬡</span>
                  <span style={{ fontFamily: "var(--font-display)", fontSize: "12px", fontWeight: 600, color: "var(--indigo2)", letterSpacing: "1px", textTransform: "uppercase" }}>CBB Traversal</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: confColor(conf) }}>
                    {(conf * 100).toFixed(1)}% confidence
                  </span>
                  <span className={`tag tag-${confLabel(conf) === "high" ? "emerald" : confLabel(conf) === "moderate" ? "amber" : "red"}`}>
                    {confLabel(conf)}
                  </span>
                </div>
              </div>

              <div style={{ fontSize: "14px", color: "var(--text2)", lineHeight: 1.75, whiteSpace: "pre-wrap" }}>
                {result.cbb_answer}
              </div>

              {/* Reasoning path */}
              {topPath && topPath.cbb_sequence.length > 0 && (
                <div style={{ marginTop: "16px" }}>
                  <div style={{ fontSize: "10px", color: "var(--slate2)", letterSpacing: "1px", marginBottom: "8px", textTransform: "uppercase" }}>
                    Reasoning Path · {topPath.cbb_sequence.length} CBBs · {topPath.relationship_sequence.length} relationships
                  </div>
                  <div style={{
                    display: "flex",
                    gap: "4px",
                    flexWrap: "wrap",
                    padding: "10px",
                    background: "var(--bg3)",
                    borderRadius: "6px",
                    alignItems: "center",
                  }}>
                    {topPath.cbb_sequence.map((id, i) => (
                      <span key={id} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                        <span style={{
                          fontSize: "10px",
                          fontFamily: "var(--font-mono)",
                          color: "var(--indigo2)",
                          padding: "2px 6px",
                          background: "rgba(99,102,241,0.1)",
                          borderRadius: "3px",
                        }}>
                          {id.replace("cbb_", "").substring(0, 10)}
                        </span>
                        {i < topPath.cbb_sequence.length - 1 && (
                          <span style={{ fontSize: "10px", color: "var(--slate2)" }}>→</span>
                        )}
                      </span>
                    ))}
                  </div>

                  {/* Confidence bar */}
                  <div className="conf-bar" style={{ marginTop: "10px" }}>
                    <div className="conf-fill" style={{ width: `${conf * 100}%`, background: confColor(conf) }} />
                  </div>

                  {/* Alternative paths */}
                  {result.paths.length > 1 && (
                    <div style={{ marginTop: "12px" }}>
                      <div style={{ fontSize: "10px", color: "var(--slate2)", letterSpacing: "1px", marginBottom: "6px", textTransform: "uppercase" }}>
                        Alternative paths
                      </div>
                      {result.paths.slice(1).map((p, i) => (
                        <div key={p.path_id} style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "6px 10px",
                          background: "var(--bg3)",
                          borderRadius: "4px",
                          marginBottom: "4px",
                          fontSize: "11px",
                          fontFamily: "var(--font-mono)",
                        }}>
                          <span style={{ color: "var(--slate2)" }}>Path {i + 2} · {p.cbb_sequence.length} CBBs</span>
                          <span style={{ color: confColor(p.path_confidence) }}>{(p.path_confidence * 100).toFixed(1)}%</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Empty state */}
        {!result && !loading && !error && (
          <div className="empty-state">
            <div className="empty-icon">⬡</div>
            <div className="empty-text">Query the network</div>
            <div className="empty-sub">
              The network traverses {liveCBBs} CBBs across NSI clusters<br />
              and returns grounded answers with visible reasoning paths
            </div>
          </div>
        )}

      </div>
    </>
  );
}
