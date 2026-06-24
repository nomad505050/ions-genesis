"use client";

import { useState, useEffect } from "react";

const API_DEFAULT = "http://localhost:8000";

function getIonsAPI(): string {
  if (typeof window === "undefined") return API_DEFAULT;
  try {
    const s = JSON.parse(localStorage.getItem("ions_settings") || "{}");
    return s.ionsApiUrl || API_DEFAULT;
  } catch {
    return API_DEFAULT;
  }
}

type NodeStats = {
  cbbs: number;
  relationships: number;
  paths: number;
  healthy: boolean;
};

export default function NodePage() {
  const [apiUrl, setApiUrl] = useState(API_DEFAULT);
  const [stats, setStats] = useState<NodeStats>({ cbbs: 0, relationships: 0, paths: 0, healthy: false });
  const [registeredNodes, setRegisteredNodes] = useState<{node_id: string; public_api_base: string; status: string; domains: string[]; cbb_count?: number; description?: string; last_seen?: string}[]>([]);
  const [loading, setLoading] = useState(true);
  const [uptime, setUptime] = useState("—");

  async function loadStats(url: string) {
    setLoading(true);
    try {
      const start = Date.now();
      const healthResp = await fetch(`${url}/health`);
      const latency = Date.now() - start;

      const statsResp = await fetch(`${url}/stats`);
      let cbbCount = 0;
      if (statsResp.ok) {
        const statsData = await statsResp.json();
        cbbCount = statsData.published_cbbs || 0;
      }

      setStats({
        cbbs: cbbCount,
        relationships: 0,
        paths: 0,
        healthy: healthResp.ok,
      });
      setUptime(`${latency}ms`);
    } catch {
      setStats({ cbbs: 0, relationships: 0, paths: 0, healthy: false });
      setUptime("unreachable");
    }
    setLoading(false);
  }

  async function loadNodes(url: string) {
    try {
      const resp = await fetch(`${url}/nodes`);
      if (resp.ok) {
        const data = await resp.json();
        setRegisteredNodes(Array.isArray(data) ? data : []);
      }
    } catch { /* silent */ }
  }

  useEffect(() => {
    const url = getIonsAPI();
    setApiUrl(url);
    loadStats(url);
    loadNodes(url);
  }, []);

  const nodeManifest = {
    node_id: "genesis_node",
    protocol_version: "ions-genesis-0.1",
    supported_cbb_types: ["claim"],
    supported_relationship_types: [
      "supports", "contradicts", "depends_on", "causes",
      "correlates_with", "extends", "refines", "references"
    ],
    capabilities: [
      "publish_cbb",
      "publish_relationship",
      "query",
      "traverse",
      "path_registry"
    ],
    public_api_base: apiUrl,
    status: stats.healthy ? "active" : "unreachable",
  };

  const endpoints = [
    { method: "POST", path: "/cbb", desc: "Publish a CBB", status: "live" },
    { method: "GET",  path: "/cbb/{id}", desc: "Retrieve a CBB", status: "live" },
    { method: "GET",  path: "/cbb", desc: "Search / filter CBBs", status: "live" },
    { method: "POST", path: "/cbb/{id}/deprecate", desc: "Deprecate a CBB", status: "live" },
    { method: "POST", path: "/relationship", desc: "Create a relationship", status: "live" },
    { method: "GET",  path: "/relationship", desc: "Search relationships", status: "live" },
    { method: "POST", path: "/query", desc: "Run traversal · returns answer + paths", status: "live" },
    { method: "GET",  path: "/path/{id}", desc: "Retrieve a reasoning path", status: "soon" },
    { method: "GET",  path: "/health", desc: "Node health check", status: "live" },
    { method: "GET",  path: "/.well-known/ions-node.json", desc: "Node manifest", status: "live" },
  ];

  function methodColor(method: string) {
    if (method === "POST") return "var(--emerald)";
    if (method === "GET")  return "var(--indigo2)";
    return "var(--slate)";
  }

  return (
    <>
      <div className="topbar">
        <span className="topbar-title">Node</span>
        <span className="topbar-sub">Genesis node · ions-genesis-0.1 · open protocol</span>
        <div className="topbar-actions">
          <a
            href={`${apiUrl}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-ghost"
          >
            API docs ↗
          </a>
        </div>
      </div>

      <div className="page-content">

        {/* Health banner */}
        <div className="node-health" style={{
          background: stats.healthy ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)",
          borderColor: stats.healthy ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)",
          color: stats.healthy ? "var(--emerald)" : "var(--red)",
        }}>
          <span className="pulse" style={{ background: stats.healthy ? "var(--emerald)" : "var(--red)" }} />
          {loading
            ? "Checking node status..."
            : stats.healthy
            ? `Node healthy · API responding · latency ${uptime} · traversal engine active`
            : `Node unreachable at ${apiUrl} · start with: docker compose up -d`}
        </div>

        {/* Stats */}
        <div className="grid-3">
          {[
            { value: stats.cbbs > 0 ? stats.cbbs.toLocaleString() : "—", label: "Published CBBs", delta: "live from network" },
            { value: "—", label: "NSI Clusters", delta: "auto-grouped by LLM" },
            { value: "0.547", label: "Avg Path Confidence", delta: "threshold: 0.600" },
          ].map((s) => (
            <div key={s.label} className="stat-card">
              <div className="stat-card-value">{s.value}</div>
              <div className="stat-card-label">{s.label}</div>
              <div className="stat-card-delta">{s.delta}</div>
            </div>
          ))}
        </div>

        <div className="grid-2">

          {/* Node manifest */}
          <div className="card">
            <div className="card-label">Node manifest</div>
            <pre style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color: "var(--slate)",
              lineHeight: 1.8,
              overflow: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}>
              {JSON.stringify(nodeManifest, null, 2)}
            </pre>
          </div>

          {/* API endpoints */}
          <div className="card">
            <div className="card-label">API endpoints</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {endpoints.map((ep) => (
                <div
                  key={`${ep.method}-${ep.path}`}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    padding: "7px 10px",
                    background: "var(--bg3)",
                    borderRadius: "5px",
                    fontSize: "11px",
                  }}
                >
                  <span style={{
                    fontFamily: "var(--font-mono)",
                    color: methodColor(ep.method),
                    minWidth: "36px",
                    fontSize: "10px",
                    fontWeight: 600,
                  }}>
                    {ep.method}
                  </span>
                  <span style={{ fontFamily: "var(--font-mono)", color: "var(--text2)", flex: 1 }}>
                    {ep.path}
                  </span>
                  <span className={`tag tag-${ep.status === "live" ? "emerald" : "amber"}`}>
                    {ep.status}
                  </span>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Protocol info */}
        <div className="grid-2">

          <div className="card">
            <div className="card-label">About this node</div>
            <div style={{ fontSize: "13px", color: "var(--slate)", lineHeight: 1.75 }}>
              This is the IONS Genesis reference node — the first implementation of the Intelligence Operating Network System protocol. It runs a single-node IONS network with a PostgreSQL registry, bounded depth-first traversal engine, and LLM-assisted answer synthesis.
              <br /><br />
              Any developer can run a compatible node using the open protocol specification. Compatible nodes implement the same API contract and can federate with other nodes to form a distributed knowledge network.
            </div>
          </div>

          <div className="card">
            <div className="card-label">Run your own node</div>
            <div style={{ fontSize: "13px", color: "var(--slate)", lineHeight: 1.75, marginBottom: "14px" }}>
              The Genesis reference implementation is open source. Clone the repository, configure your environment, and start a compatible IONS node in minutes.
            </div>
            <pre style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color: "var(--indigo2)",
              lineHeight: 1.8,
              background: "var(--bg3)",
              padding: "12px",
              borderRadius: "6px",
              overflowX: "auto",
            }}>
              {`git clone https://github.com/nomad505050/ions-genesis\ncd ions-genesis\ncp .env.example .env\ndocker compose up -d\n# Node running at localhost:8000`}
            </pre>
            <div style={{ marginTop: "14px", display: "flex", gap: "8px" }}>
              <a
                href="https://github.com/nomad505050/ions-genesis"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary btn-sm"
              >
                GitHub →
              </a>
              <button className="btn btn-ghost btn-sm">Node specification</button>
            </div>
          </div>

        </div>

        {/* Benchmark results */}
        <div className="card">
          <div className="card-label">Genesis benchmark results</div>
          <div style={{ fontSize: "13px", color: "var(--slate)", lineHeight: 1.6, marginBottom: "16px" }}>
            Three-way comparison: Raw Llama 3.1 8B · 8B + CBB Traversal · Claude Sonnet 4.5 (frontier baseline) · 8 domain-general queries
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px" }}>
            {[
              { label: "Raw 8B alone", result: "Weakest on all 8 queries", color: "var(--red)", detail: "Generic answers, wrong domain context on 2 queries" },
              { label: "8B + CBB Traversal", result: "Matched or exceeded frontier on 5-6 of 8", color: "var(--indigo2)", detail: "Domain-specific, grounded, causal chains visible" },
              { label: "Claude Sonnet 4.5", result: "Strongest on broad general questions", color: "var(--emerald)", detail: "Richer synthesis, better on multi-domain queries" },
            ].map((r) => (
              <div key={r.label} style={{
                padding: "14px",
                background: "var(--bg3)",
                borderRadius: "8px",
                border: "1px solid var(--border)",
              }}>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: r.color, marginBottom: "6px", letterSpacing: "0.5px" }}>
                  {r.label}
                </div>
                <div style={{ fontSize: "13px", color: "var(--text2)", fontWeight: 600, marginBottom: "6px" }}>
                  {r.result}
                </div>
                <div style={{ fontSize: "11px", color: "var(--slate2)" }}>{r.detail}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Registered Nodes */}
        <div>
          <div className="card-label" style={{ marginBottom: "12px" }}>
            Registered Nodes ({registeredNodes.length + 1})
          </div>

          {/* This node */}
          <div style={{
            padding: "14px 18px",
            background: "rgba(99,102,241,0.06)",
            border: "1px solid var(--indigo)",
            borderRadius: "8px",
            marginBottom: "8px",
            display: "flex",
            alignItems: "center",
            gap: "14px",
          }}>
            <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--emerald)", flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: "13px", color: "var(--text2)", fontWeight: 500, marginBottom: "2px" }}>
                genesis_node <span style={{ fontSize: "10px", color: "var(--indigo2)", fontFamily: "var(--font-mono)", marginLeft: "8px" }}>this node</span>
              </div>
              <div style={{ fontSize: "11px", color: "var(--slate2)", fontFamily: "var(--font-mono)" }}>
                {apiUrl} · {stats.cbbs} CBBs
              </div>
            </div>
            <span className="tag tag-emerald">active</span>
          </div>

          {/* Remote nodes */}
          {registeredNodes.length === 0 ? (
            <div style={{
              padding: "20px 18px",
              background: "var(--bg2)",
              border: "1px dashed var(--border)",
              borderRadius: "8px",
              textAlign: "center",
            }}>
              <div style={{ fontSize: "13px", color: "var(--slate)", marginBottom: "8px" }}>
                No other nodes registered yet
              </div>
              <div style={{ fontSize: "11px", color: "var(--slate2)", lineHeight: 1.6, marginBottom: "12px" }}>
                When another node runs IONS Genesis and registers with this node, it will appear here and participate in federated traversal.
              </div>
              <code style={{ fontSize: "11px", color: "var(--indigo2)", background: "var(--bg3)", padding: "6px 12px", borderRadius: "4px" }}>
                {'POST /nodes/register { "node_id": "...", "public_api_base": "https://..." }'}
              </code>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {registeredNodes.map(node => (
                <div key={node.node_id} style={{
                  padding: "14px 18px",
                  background: "var(--bg2)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  display: "flex",
                  alignItems: "center",
                  gap: "14px",
                }}>
                  <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: node.status === "active" ? "var(--emerald)" : "var(--red)", flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: "13px", color: "var(--text2)", fontWeight: 500, marginBottom: "2px" }}>{node.node_id}</div>
                    <div style={{ fontSize: "11px", color: "var(--slate2)", fontFamily: "var(--font-mono)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {node.public_api_base} · {node.domains?.length || 0} domains
                    </div>
                  </div>
                  <span className={`tag tag-${node.status === "active" ? "emerald" : "red"}`}>{node.status}</span>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </>
  );
}
