"use client";

import { useState, useEffect } from "react";
import { loadSettings, getActiveModel } from "../settings/page";

function getIonsAPI(): string {
  if (typeof window === "undefined") return "http://localhost:8000";
  try {
    const s = JSON.parse(localStorage.getItem("ions_settings") || "{}");
    return s.ionsApiUrl || "http://localhost:8000";
  } catch {
    return "http://localhost:8000";
  }
}
const IONS_API = getIonsAPI();

type CBB = {
  cbb_id: string;
  content: string;
  domain: string;
  confidence: number;
  status: string;
  tags: string[];
  evidence: { source_type: string; source_id: string }[];
  created_at: string;
};

function confColor(c: number) {
  if (c >= 0.8) return "var(--emerald)";
  if (c >= 0.6) return "var(--amber)";
  return "var(--red)";
}

function timeAgo(dateStr: string) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const h = Math.floor(diff / 3600000);
  const d = Math.floor(diff / 86400000);
  if (d > 0) return `${d}d ago`;
  if (h > 0) return `${h}h ago`;
  return "just now";
}

export default function WorkbenchPage() {
  const [candidates, setCandidates] = useState<CBB[]>([]);
  const [published, setPublished] = useState<CBB[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [genProgress, setGenProgress] = useState<{ processed: number; created: number; total: number } | null>(null);
  const [genDone, setGenDone] = useState(false);
  const [tab, setTab] = useState<"queue" | "published" | "relationships">("queue");
  const [acting, setActing] = useState<string | null>(null);
  const [counts, setCounts] = useState({ candidate: 0, published: 0, rejected: 0 });

  // Relationship builder state
  const [apiKey, setApiKey] = useState("");
  const [activeModel, setActiveModel] = useState("meta-llama/llama-3.1-8b-instruct");

  useEffect(() => {
    loadData();
    const s = loadSettings();
    setApiKey(s.openrouterKey);
    setActiveModel(getActiveModel(s));
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [candResp, pubResp] = await Promise.all([
        fetch(`${IONS_API}/cbb?status=candidate&limit=50&order=created_at.desc`),
        fetch(`${IONS_API}/cbb?status=published&limit=50&order=created_at.desc`),
      ]);
      const cands = await candResp.json();
      const pubs = await pubResp.json();
      const sortByDate = (a: CBB, b: CBB) =>
        new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
      setCandidates(Array.isArray(cands) ? [...cands].sort(sortByDate) : []);
      setPublished(Array.isArray(pubs) ? [...pubs].sort(sortByDate) : []);
      setCounts({
        candidate: Array.isArray(cands) ? cands.length : 0,
        published: Array.isArray(pubs) ? pubs.length : 0,
        rejected: 0,
      });
    } catch {
      setCandidates([]); setPublished([]);
    }
    setLoading(false);
  }

  async function approve(cbb: CBB) {
    setActing(cbb.cbb_id);
    try {
      // Post new published CBB (strip server-assigned fields)
      const { cbb_id, hash, created_at, updated_at, ...rest } = cbb as any;
      const postResp = await fetch(`${IONS_API}/cbb`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...rest, status: "published" }),
      });
      if (!postResp.ok) {
        console.error("Approve failed:", await postResp.text());
        setActing(null);
        return;
      }
      // Deprecate the candidate so it won't reappear
      await fetch(`${IONS_API}/cbb/${cbb.cbb_id}/deprecate`, { method: "POST" });
      setCandidates(prev => prev.filter(c => c.cbb_id !== cbb.cbb_id));
      setCounts(prev => ({ ...prev, candidate: prev.candidate - 1, published: prev.published + 1 }));
    } catch (e) {
      console.error("Approve error:", e);
    }
    setActing(null);
  }

  async function reject(cbb: CBB) {
    setActing(cbb.cbb_id);
    try {
      await fetch(`${IONS_API}/cbb/${cbb.cbb_id}/deprecate`, { method: "POST" });
    } catch (e) {
      console.error("Reject error:", e);
    }
    setCandidates(prev => prev.filter(c => c.cbb_id !== cbb.cbb_id));
    setCounts(prev => ({ ...prev, candidate: prev.candidate - 1, rejected: prev.rejected + 1 }));
    setActing(null);
  }

  async function generateRelationships() {
    setGenerating(true);
    setGenDone(false);
    setGenProgress({ processed: 0, created: 0, total: 0 });

    try {
      const startResp = await fetch(`${IONS_API}/relationship/generate`, { method: "POST" });
      if (!startResp.ok) {
        const err = await startResp.json();
        throw new Error(err.detail || "Generation failed to start");
      }
      const { job_id } = await startResp.json();

      while (true) {
        await new Promise(r => setTimeout(r, 2000));
        const pollResp = await fetch(`${IONS_API}/relationship/generate/${job_id}`);
        if (!pollResp.ok) break;
        const job = await pollResp.json();
        setGenProgress({ processed: job.processed || 0, created: job.created || 0, total: job.total || 0 });
        if (job.status === "done" || job.status === "error") {
          setGenDone(job.status === "done");
          break;
        }
      }
    } catch (e) {
      console.error("Generation error:", e);
    }
    setGenerating(false);
  }

  return (
    <>
      <div className="topbar">
        <span className="topbar-title">Workbench</span>
        <span className="topbar-sub">Review queue · approve · reject · build relationships</span>
        <div className="topbar-actions">
          <button className="btn btn-ghost" onClick={loadData}>↻ Refresh</button>
          <a href="/contribute" className="btn btn-primary">+ Add CBB</a>
        </div>
      </div>

      <div className="page-content">

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <span className="tag tag-amber">{counts.candidate} pending review</span>
          <span className="tag tag-emerald">{counts.published}+ published</span>
          <span className="tag tag-red">{counts.rejected} rejected this session</span>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: "4px", borderBottom: "1px solid var(--border)" }}>
          {([
            { key: "queue", label: `Review Queue (${counts.candidate})` },
            { key: "published", label: "Published" },
            { key: "relationships", label: "Activity" },
          ] as const).map(t => (
            <button key={t.key} onClick={() => setTab(t.key)} style={{
              padding: "8px 16px", background: "transparent", border: "none",
              borderBottom: tab === t.key ? "2px solid var(--indigo)" : "2px solid transparent",
              color: tab === t.key ? "var(--indigo2)" : "var(--slate2)",
              fontFamily: "var(--font-display)", fontSize: "13px",
              fontWeight: tab === t.key ? 600 : 400, cursor: "pointer",
              transition: "all 0.15s", marginBottom: "-1px",
            }}>
              {t.label}
            </button>
          ))}
        </div>

        {/* QUEUE TAB */}
        {tab === "queue" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {loading && <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "var(--slate)", fontSize: "13px", padding: "20px 0" }}><div className="spinner" /> Loading...</div>}
            {!loading && candidates.length === 0 && (
              <div className="empty-state">
                <div className="empty-icon">✓</div>
                <div className="empty-text">Review queue is empty</div>
                <div className="empty-sub">All submissions have been reviewed</div>
              </div>
            )}
            {candidates.map(cbb => (
              <div key={cbb.cbb_id} className="queue-item">
                <div className="queue-content">
                  <div className="queue-claim">"{cbb.content}"</div>
                  <div className="queue-meta">
                    <span className="tag tag-indigo">{cbb.domain?.replace(/_/g, " ")}</span>
                    <span className="tag tag-amber">conf: {cbb.confidence?.toFixed(2)}</span>
                    {cbb.evidence?.[0] && <span className="tag tag-slate">{cbb.evidence[0].source_type}</span>}
                    {cbb.created_at && <span className="tag tag-slate">{timeAgo(cbb.created_at)}</span>}
                  </div>
                </div>
                <div className="queue-actions">
                  <button className="btn-sm btn-approve" onClick={() => approve(cbb)} disabled={acting === cbb.cbb_id}>
                    {acting === cbb.cbb_id ? "..." : "✓ Approve"}
                  </button>
                  <button className="btn-sm btn-reject" onClick={() => reject(cbb)} disabled={acting === cbb.cbb_id}>✕ Reject</button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* PUBLISHED TAB */}
        {tab === "published" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {loading && <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "var(--slate)", fontSize: "13px", padding: "20px 0" }}><div className="spinner" /> Loading...</div>}
            {published.map(cbb => (
              <div key={cbb.cbb_id} style={{ padding: "12px 16px", background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "8px", display: "flex", gap: "12px", alignItems: "flex-start" }}>
                <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: confColor(cbb.confidence), flexShrink: 0, marginTop: "4px" }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: "13px", color: "var(--text2)", lineHeight: 1.6, marginBottom: "6px" }}>{cbb.content}</div>
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                    <span className="tag tag-emerald">published</span>
                    <span className="tag tag-indigo">{cbb.domain?.replace(/_/g, " ")}</span>
                  </div>
                </div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: confColor(cbb.confidence), flexShrink: 0 }}>{cbb.confidence?.toFixed(2)}</div>
              </div>
            ))}
            {!loading && published.length === 50 && (
              <div style={{ fontSize: "12px", color: "var(--slate2)", textAlign: "center", padding: "10px" }}>Showing first 50 published CBBs</div>
            )}
          </div>
        )}

        {/* ACTIVITY TAB */}
        {tab === "relationships" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>

            {/* Pipeline status */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "10px" }}>
              {[
                { label: "In review queue", value: counts.candidate, color: "var(--amber)", desc: "Submitted · awaiting approval" },
                { label: "Published", value: counts.published + "+", color: "var(--emerald)", desc: "Live on the network" },
              ].map(s => (
                <div key={s.label} style={{
                  padding: "14px 16px",
                  background: "var(--bg2)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                }}>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: "22px", color: s.color, fontWeight: 600, marginBottom: "4px" }}>
                    {s.value}
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text2)", fontFamily: "var(--font-display)", fontWeight: 500 }}>{s.label}</div>
                  <div style={{ fontSize: "10px", color: "var(--slate2)", marginTop: "2px" }}>{s.desc}</div>
                </div>
              ))}
            </div>

            {/* Relationship generation */}
            <div style={{
              padding: "16px 20px",
              background: "var(--bg2)",
              border: "1px solid var(--border)",
              borderRadius: "10px",
            }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
                <div>
                  <div style={{ fontFamily: "var(--font-display)", fontSize: "14px", fontWeight: 600, color: "var(--text)", marginBottom: "3px" }}>
                    Generate Relationships
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--slate2)" }}>
                    Connects recently published CBBs to existing network knowledge
                  </div>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={generateRelationships}
                  disabled={generating}
                  style={{ flexShrink: 0 }}
                >
                  {generating ? "Generating..." : "⬡ Generate relationships"}
                </button>
              </div>

              <div style={{ fontSize: "12px", color: "var(--slate2)", marginTop: "8px" }}>
                  Relationship generation runs server-side using the node&apos;s configured LLM.
                </div>

              {generating && genProgress && (
                <div style={{ marginTop: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "var(--slate)", marginBottom: "6px" }}>
                    <span>Processing {genProgress.processed} of {genProgress.total} CBBs</span>
                    <span style={{ color: "var(--emerald)", fontFamily: "var(--font-mono)" }}>{genProgress.created} relationships created</span>
                  </div>
                  <div className="conf-bar">
                    <div className="conf-fill" style={{
                      width: genProgress.total > 0 ? `${(genProgress.processed / genProgress.total) * 100}%` : "0%",
                      background: "var(--indigo)",
                      transition: "width 0.4s ease",
                    }} />
                  </div>
                </div>
              )}

              {genDone && genProgress && (
                <div style={{ marginTop: "12px", padding: "10px 14px", background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)", borderRadius: "6px", fontSize: "12px", color: "var(--emerald)" }}>
                  ✓ Done — {genProgress.created} relationships created across {genProgress.total} CBBs
                </div>
              )}
            </div>

            {/* Pending review */}
            {candidates.length > 0 && (
              <div>
                <div className="card-label" style={{ marginBottom: "10px" }}>
                  Pending review ({candidates.length}) · <span style={{ color: "var(--amber)" }}>awaiting curator approval</span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  {candidates.slice(0, 10).map(cbb => (
                    <div key={cbb.cbb_id} style={{
                      padding: "12px 16px",
                      background: "var(--bg2)",
                      border: "1px solid rgba(245,158,11,0.2)",
                      borderRadius: "8px",
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                    }}>
                      <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--amber)", flexShrink: 0 }} />
                      <div style={{ flex: 1, fontSize: "13px", color: "var(--text2)", lineHeight: 1.5 }}>{cbb.content}</div>
                      <span className="tag tag-amber">pending</span>
                    </div>
                  ))}
                  {candidates.length > 10 && (
                    <div style={{ fontSize: "12px", color: "var(--slate2)", padding: "6px 0", textAlign: "center" }}>
                      +{candidates.length - 10} more in queue · <button onClick={() => setTab("queue")} style={{ background: "none", border: "none", color: "var(--indigo2)", cursor: "pointer", fontSize: "12px" }}>Review all →</button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Recently published */}
            <div>
              <div className="card-label" style={{ marginBottom: "10px" }}>
                Recently published · <span style={{ color: "var(--emerald)" }}>live on network</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {published.slice(0, 15).map(cbb => (
                  <div key={cbb.cbb_id} style={{
                    padding: "12px 16px",
                    background: "var(--bg2)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                  }}>
                    <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--emerald)", flexShrink: 0 }} />
                    <div style={{ flex: 1, fontSize: "13px", color: "var(--text2)", lineHeight: 1.5 }}>{cbb.content}</div>
                    <div style={{ display: "flex", gap: "6px", flexShrink: 0, alignItems: "center" }}>
                      <span className="tag tag-indigo">{cbb.domain?.replace(/_/g, " ").substring(0, 18)}</span>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--slate2)" }}>{cbb.confidence?.toFixed(2)}</span>
                    </div>
                  </div>
                ))}
                {published.length === 0 && !loading && (
                  <div className="empty-state">
                    <div className="empty-icon">⬡</div>
                    <div className="empty-text">No published CBBs yet</div>
                    <div className="empty-sub">Approve candidates in the Review Queue to publish them</div>
                  </div>
                )}
              </div>
            </div>

          </div>
        )}
      </div>
    </>
  );
}
