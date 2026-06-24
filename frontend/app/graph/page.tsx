"use client";

import { useEffect, useState } from "react";

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

type CBB = {
  cbb_id: string;
  content: string;
  confidence: number;
  domain: string;
};

type SubDomain = {
  name: string;
  displayName: string;
  count: number;
  cbbs: CBB[];
};

type NSI = {
  name: string;
  displayName: string;
  color: string;
  subdomains: SubDomain[];
  totalCount: number;
};

const PALETTE = [
  "#6366f1", "#10b981", "#f59e0b", "#06b6d4", "#8b5cf6",
  "#ec4899", "#f97316", "#14b8a6", "#f43f5e", "#84cc16",
  "#818cf8", "#34d399", "#fbbf24", "#38bdf8", "#e879f9",
];

export default function GraphPage() {
  const [nsis, setNsis] = useState<NSI[]>([]);
  const [selectedNSI, setSelectedNSI] = useState<NSI | null>(null);
  const [selectedSubdomain, setSelectedSubdomain] = useState<SubDomain | null>(null);
  const [selectedCBB, setSelectedCBB] = useState<CBB | null>(null);
  const [hoveredNSI, setHoveredNSI] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reclustering, setReclustering] = useState(false);
  const [totalCBBs, setTotalCBBs] = useState(0);
  const [view, setView] = useState<"nsi" | "subdomains" | "cbbs">("nsi");
  const [search, setSearch] = useState("");
  const [nsiConnections, setNsiConnections] = useState<Record<string, number>>({});

  useEffect(() => {
    loadFromServer();
  }, []);

  async function loadFromServer() {
    setLoading(true);
    const url = getIonsAPI();

    try {
      // Fetch server-side NSI clusters
      const clusterResp = await fetch(`${url}/nsi/clusters`);
      if (!clusterResp.ok) throw new Error("NSI clusters not available");
      const clusters = await clusterResp.json();

      if (!clusters || clusters.length === 0) {
        setLoading(false);
        return;
      }

      // Fetch all CBBs
      const allCBBs: CBB[] = [];
      let offset = 0;
      while (true) {
        const resp = await fetch(`${url}/cbb?status=published&limit=500&offset=${offset}`);
        if (!resp.ok) break;
        const batch = await resp.json();
        if (!batch || batch.length === 0) break;
        allCBBs.push(...batch);
        if (batch.length < 500) break;
        offset += 500;
      }
      setTotalCBBs(allCBBs.length);

      // Build domain -> CBB map
      const domainMap: Record<string, CBB[]> = {};
      for (const cbb of allCBBs) {
        const d = (cbb.domain || "unknown").toLowerCase().trim();
        if (!domainMap[d]) domainMap[d] = [];
        domainMap[d].push(cbb);
      }

      // Build NSI list from server clusters
      const nsiList: NSI[] = clusters.map((cluster: {
        cluster_id: string;
        label: string;
        color: string;
        domains: { domain: string; cbb_count: number }[];
        cbb_count: number;
      }, i: number) => {
        const subdomains: SubDomain[] = (cluster.domains || []).map((d: { domain: string }) => ({
          name: d.domain,
          displayName: d.domain.replace(/_/g, " ").replace(/ and /g, " & "),
          count: domainMap[d.domain.toLowerCase()]?.length || 0,
          cbbs: domainMap[d.domain.toLowerCase()] || [],
        })).filter((s: SubDomain) => s.count > 0)
          .sort((a: SubDomain, b: SubDomain) => b.count - a.count);

        const totalCount = subdomains.reduce((s: number, d: SubDomain) => s + d.count, 0);

        return {
          name: cluster.label,
          displayName: cluster.label,
          color: cluster.color || PALETTE[i % PALETTE.length],
          subdomains,
          totalCount,
        };
      }).filter((n: NSI) => n.totalCount > 0)
        .sort((a: NSI, b: NSI) => b.totalCount - a.totalCount);

      // Build cross-NSI connections from relationships
      const domainToNSI: Record<string, string> = {};
      nsiList.forEach(nsi => {
        nsi.subdomains.forEach(sub => {
          sub.cbbs.forEach(cbb => {
            domainToNSI[cbb.cbb_id] = nsi.name;
          });
        });
      });

      const connections: Record<string, number> = {};
      try {
        const relResp = await fetch(`${url}/relationship?limit=500`);
        if (relResp.ok) {
          const rels = await relResp.json();
          for (const rel of rels) {
            const srcNSI = domainToNSI[rel.source_cbb_id];
            const tgtNSI = domainToNSI[rel.target_cbb_id];
            if (srcNSI && tgtNSI && srcNSI !== tgtNSI) {
              const key = [srcNSI, tgtNSI].sort().join("|");
              connections[key] = (connections[key] || 0) + 1;
            }
          }
        }
      } catch { /* use empty connections */ }

      setNsiConnections(connections);
      setNsis(nsiList);
      const nsiEl = document.getElementById("live-clusters");
      if (nsiEl) nsiEl.textContent = String(nsiList.length);

    } catch (err) {
      console.error("Failed to load NSI clusters:", err);
    }
    setLoading(false);
  }

  async function triggerRecluster() {
    setReclustering(true);
    const url = getIonsAPI();
    try {
      const resp = await fetch(`${url}/nsi/cluster`, { method: "POST" });
      const { job_id } = await resp.json();
      while (true) {
        await new Promise(r => setTimeout(r, 2000));
        const poll = await fetch(`${url}/nsi/jobs/${job_id}`);
        const job = await poll.json();
        if (job.status === "done" || job.status === "error") break;
      }
      await loadFromServer();
    } catch (err) {
      console.error("Recluster failed:", err);
    }
    setReclustering(false);
  }

  function backToNSI() {
    setView("nsi");
    setSelectedNSI(null);
    setSelectedSubdomain(null);
    setSelectedCBB(null);
    setSearch("");
  }

  function backToSubdomains() {
    setView("subdomains");
    setSelectedSubdomain(null);
    setSelectedCBB(null);
    setSearch("");
  }

  const maxCount = nsis[0]?.totalCount || 1;
  const filteredNSIs = search
    ? nsis.filter(n => n.displayName.toLowerCase().includes(search.toLowerCase()))
    : nsis;

  return (
    <>
      <div className="topbar">
        <span className="topbar-title">Graph</span>
        <span className="topbar-sub">
          {view === "nsi"
            ? `${nsis.length} NSI clusters · ${totalCBBs.toLocaleString()} CBBs · ${nsis.reduce((s, n) => s + n.subdomains.length, 0)} sub-domains`
            : view === "subdomains"
            ? `${selectedNSI?.displayName} · ${selectedNSI?.subdomains.length} sub-domains · ${selectedNSI?.totalCount} CBBs`
            : `${selectedSubdomain?.displayName} · ${selectedSubdomain?.count} CBBs`}
        </span>
        <div className="topbar-actions">
          {view !== "nsi" && (
            <button className="btn btn-ghost" onClick={view === "subdomains" ? backToNSI : backToSubdomains}>
              ← {view === "subdomains" ? "All NSIs" : selectedNSI?.displayName}
            </button>
          )}
          <button className="btn btn-ghost" onClick={triggerRecluster} disabled={reclustering}>
            {reclustering ? "Reclustering..." : "↻ Recluster"}
          </button>
        </div>
      </div>

      <div className="page-content">

        {/* Breadcrumb */}
        {view !== "nsi" && (
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px" }}>
            <button onClick={backToNSI} style={{ background: "none", border: "none", color: "var(--indigo2)", cursor: "pointer", fontSize: "12px", padding: 0, fontFamily: "var(--font-display)" }}>
              All NSIs
            </button>
            {selectedNSI && <>
              <span style={{ color: "var(--slate2)" }}>→</span>
              <button onClick={backToSubdomains} style={{ background: "none", border: "none", color: view === "cbbs" ? "var(--indigo2)" : "var(--text2)", cursor: view === "cbbs" ? "pointer" : "default", fontSize: "12px", padding: 0, fontFamily: "var(--font-display)" }}>
                {selectedNSI.displayName}
              </button>
            </>}
            {selectedSubdomain && <>
              <span style={{ color: "var(--slate2)" }}>→</span>
              <span style={{ color: "var(--text2)" }}>{selectedSubdomain.displayName}</span>
              <span className="tag tag-indigo">{selectedSubdomain.count} CBBs</span>
            </>}
          </div>
        )}

        {/* Search */}
        <input
          className="form-input"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder={
            view === "nsi" ? "Filter NSI clusters..." :
            view === "subdomains" ? "Filter sub-domains..." :
            "Search CBBs..."
          }
          style={{ maxWidth: "400px" }}
        />

        {/* Loading */}
        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: "12px", color: "var(--slate)", fontSize: "13px", padding: "40px 0", justifyContent: "center" }}>
            <div className="spinner" />
            Loading network...
          </div>
        )}

        {/* NSI VIEW — Level 1 */}
        {view === "nsi" && !loading && (
          <>
            {/* Positioned NSI network map with SVG connections */}
            {(() => {
              const W = 100, H = 100;
              const sorted = [...filteredNSIs].sort((a, b) => b.totalCount - a.totalCount);
              const positions: Record<string, { x: number; y: number }> = {};
              if (sorted.length > 0) {
                positions[sorted[0].name] = { x: 50, y: 48 };
                const rest = sorted.slice(1);
                rest.forEach((nsi, i) => {
                  const angle = (i / rest.length) * Math.PI * 2 - Math.PI / 2;
                  const radius = rest.length <= 6 ? 32 : rest.length <= 10 ? 36 : 38;
                  positions[nsi.name] = {
                    x: 50 + Math.cos(angle) * radius,
                    y: 48 + Math.sin(angle) * radius,
                  };
                });
              }

              return (
                <div style={{
                  background: "var(--bg2)",
                  border: "1px solid var(--border)",
                  borderRadius: "12px",
                  position: "relative",
                  overflow: "hidden",
                  height: "620px",
                }}>
                  <div style={{ position: "absolute", inset: 0, opacity: 0.03, backgroundImage: "radial-gradient(circle, #6366f1 1px, transparent 1px)", backgroundSize: "32px 32px" }} />

                  <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
                    {Object.entries(nsiConnections).map(([key, count]) => {
                      const [aName, bName] = key.split("|");
                      const posA = positions[aName];
                      const posB = positions[bName];
                      if (!posA || !posB) return null;
                      const isHighlighted = hoveredNSI === aName || hoveredNSI === bName;
                      const nsiA = filteredNSIs.find(n => n.name === aName);
                      const strength = Math.min(1, count / 20);
                      return (
                        <line
                          key={key}
                          x1={`${posA.x}%`} y1={`${posA.y}%`}
                          x2={`${posB.x}%`} y2={`${posB.y}%`}
                          stroke={isHighlighted ? (nsiA?.color || "#6366f1") : "#818cf8"}
                          strokeWidth={isHighlighted ? Math.max(1.5, strength * 3) : Math.max(0.5, strength * 1.2)}
                          strokeOpacity={isHighlighted ? 0.8 : Math.max(0.15, strength * 0.4)}
                          strokeDasharray={isHighlighted ? "none" : "5 4"}
                        />
                      );
                    })}
                  </svg>

                  {filteredNSIs.map(nsi => {
                    const pos = positions[nsi.name];
                    if (!pos) return null;
                    const size = Math.max(60, Math.min(140, (nsi.totalCount / maxCount) * 140));
                    const isHovered = hoveredNSI === nsi.name;
                    return (
                      <div
                        key={nsi.name}
                        onClick={() => { setSelectedNSI(nsi); setView("subdomains"); setSearch(""); }}
                        onMouseEnter={() => setHoveredNSI(nsi.name)}
                        onMouseLeave={() => setHoveredNSI(null)}
                        style={{
                          position: "absolute",
                          left: `${pos.x}%`, top: `${pos.y}%`,
                          transform: "translate(-50%, -50%)",
                          width: `${size}px`, height: `${size}px`,
                          borderRadius: "50%",
                          background: `radial-gradient(circle at 35% 35%, ${nsi.color}40, ${nsi.color}10)`,
                          border: `${isHovered ? 2 : 1}px solid ${nsi.color}${isHovered ? "cc" : "60"}`,
                          cursor: "pointer",
                          display: "flex", flexDirection: "column",
                          alignItems: "center", justifyContent: "center",
                          transition: "all 0.2s",
                          zIndex: isHovered ? 10 : 1,
                          boxShadow: isHovered ? `0 0 20px ${nsi.color}40` : "none",
                        }}
                      >
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: size > 90 ? "18px" : "13px", fontWeight: 700, color: nsi.color, lineHeight: 1 }}>
                          {nsi.totalCount}
                        </div>
                        {size > 70 && (
                          <div style={{ fontSize: "9px", color: "var(--slate)", textAlign: "center", padding: "0 6px", lineHeight: 1.3, marginTop: "3px" }}>
                            {nsi.displayName.length > Math.floor(size / 7) ? nsi.displayName.substring(0, Math.floor(size / 7)) + "…" : nsi.displayName}
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {hoveredNSI && (() => {
                    const nsi = nsis.find(n => n.name === hoveredNSI);
                    if (!nsi) return null;
                    return (
                      <div style={{
                        position: "absolute", bottom: "16px", left: "50%", transform: "translateX(-50%)",
                        padding: "8px 16px", background: "var(--bg3)", border: `1px solid ${nsi.color}`,
                        borderRadius: "8px", fontSize: "12px", color: "var(--text2)",
                        display: "flex", alignItems: "center", gap: "10px", whiteSpace: "nowrap",
                        zIndex: 20, boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
                      }}>
                        <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: nsi.color }} />
                        <strong style={{ color: nsi.color }}>{nsi.displayName}</strong>
                        <span style={{ color: "var(--slate2)" }}>·</span>
                        <span style={{ fontFamily: "var(--font-mono)" }}>{nsi.totalCount} CBBs</span>
                        <span style={{ color: "var(--slate2)" }}>·</span>
                        <span style={{ color: "var(--slate2)" }}>{nsi.subdomains.length} sub-domains</span>
                        <span style={{ color: "var(--slate2)", fontSize: "11px" }}>click to explore →</span>
                      </div>
                    );
                  })()}
                </div>
              );
            })()}

            {/* Collapsible NSI list */}
            <details style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "10px", overflow: "hidden" }}>
              <summary style={{
                padding: "14px 18px", cursor: "pointer", display: "flex",
                alignItems: "center", justifyContent: "space-between",
                fontSize: "12px", color: "var(--slate)", fontFamily: "var(--font-display)",
                listStyle: "none", userSelect: "none",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span style={{ color: "var(--indigo2)", fontWeight: 600 }}>NSI Clusters</span>
                  <span className="tag tag-indigo">{filteredNSIs.length}</span>
                </div>
                <span style={{ color: "var(--slate2)", fontSize: "11px" }}>click to expand ▾</span>
              </summary>
              <div style={{ padding: "0 16px 16px", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "8px" }}>
                {filteredNSIs.map(nsi => (
                  <div
                    key={nsi.name}
                    onClick={() => { setSelectedNSI(nsi); setView("subdomains"); setSearch(""); }}
                    style={{ padding: "10px 14px", background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: "8px", cursor: "pointer", transition: "all 0.15s", display: "flex", alignItems: "center", gap: "10px" }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = nsi.color; (e.currentTarget as HTMLElement).style.background = nsi.color + "0a"; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border)"; (e.currentTarget as HTMLElement).style.background = "var(--bg3)"; }}
                  >
                    <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: nsi.color, flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: "11px", color: "var(--text2)", fontFamily: "var(--font-display)", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{nsi.displayName}</div>
                      <div style={{ fontSize: "10px", color: "var(--slate2)", marginTop: "1px" }}>{nsi.subdomains.length} sub-domains</div>
                    </div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: nsi.color, fontWeight: 600, flexShrink: 0 }}>{nsi.totalCount}</div>
                  </div>
                ))}
              </div>
            </details>
          </>
        )}

        {/* SUBDOMAIN VIEW — Level 2 */}
        {view === "subdomains" && selectedNSI && !loading && (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <div className="card-label" style={{ marginBottom: "4px" }}>
              Sub-domains in {selectedNSI.displayName} ({selectedNSI.subdomains.length})
            </div>
            {selectedNSI.subdomains
              .filter(s => !search || s.displayName.toLowerCase().includes(search.toLowerCase()))
              .map(sub => (
                <div
                  key={sub.name}
                  onClick={() => { setSelectedSubdomain(sub); setView("cbbs"); setSearch(""); }}
                  style={{ padding: "12px 16px", background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "8px", cursor: "pointer", transition: "all 0.15s", display: "flex", alignItems: "center", gap: "12px" }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = selectedNSI.color; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border)"; }}
                >
                  <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: selectedNSI.color, flexShrink: 0 }} />
                  <div style={{ flex: 1, fontSize: "13px", color: "var(--text2)" }}>{sub.displayName}</div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: selectedNSI.color, flexShrink: 0 }}>{sub.count}</div>
                </div>
              ))}
          </div>
        )}

        {/* CBB VIEW — Level 3 */}
        {view === "cbbs" && selectedSubdomain && (
          <>
            {selectedCBB && (
              <div className="card" style={{ borderColor: selectedNSI?.color }}>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "16px" }}>
                  <div style={{ flex: 1 }}>
                    <div className="card-label" style={{ marginBottom: "8px" }}>CBB · <span style={{ fontFamily: "var(--font-mono)", fontSize: "10px" }}>{selectedCBB.cbb_id}</span></div>
                    <div style={{ fontSize: "14px", color: "var(--text2)", lineHeight: 1.75 }}>"{selectedCBB.content}"</div>
                    <div style={{ display: "flex", gap: "8px", marginTop: "10px", flexWrap: "wrap" }}>
                      <span className="tag tag-emerald">published</span>
                      <span className="tag tag-amber">conf: {selectedCBB.confidence?.toFixed(2)}</span>
                      <span className="tag tag-slate">{selectedCBB.domain}</span>
                    </div>
                    <div style={{ marginTop: "12px" }}>
                      <a href="/" className="btn btn-primary btn-sm">Query this domain</a>
                    </div>
                  </div>
                  <button className="btn btn-ghost btn-sm" onClick={() => setSelectedCBB(null)}>✕</button>
                </div>
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {selectedSubdomain.cbbs
                .filter(c => !search || c.content.toLowerCase().includes(search.toLowerCase()))
                .map(cbb => (
                  <div
                    key={cbb.cbb_id}
                    onClick={() => setSelectedCBB(cbb)}
                    style={{
                      padding: "12px 16px",
                      background: selectedCBB?.cbb_id === cbb.cbb_id ? (selectedNSI?.color || "var(--indigo)") + "10" : "var(--bg2)",
                      border: `1px solid ${selectedCBB?.cbb_id === cbb.cbb_id ? (selectedNSI?.color || "var(--indigo)") : "var(--border)"}`,
                      borderRadius: "8px", cursor: "pointer", transition: "all 0.15s",
                      display: "flex", alignItems: "center", gap: "12px",
                    }}
                  >
                    <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: selectedNSI?.color || "var(--indigo)", flexShrink: 0 }} />
                    <div style={{ flex: 1, fontSize: "13px", color: "var(--text2)", lineHeight: 1.5 }}>{cbb.content}</div>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--slate2)", flexShrink: 0 }}>{cbb.confidence?.toFixed(2)}</span>
                  </div>
                ))}
            </div>
          </>
        )}

      </div>
    </>
  );
}
