"use client";

import { useEffect, useState } from "react";

const apiURL_DEFAULT = "http://localhost:8000";
function getIonsAPI(): string {
  if (typeof window === "undefined") return apiURL_DEFAULT;
  try {
    const s = JSON.parse(localStorage.getItem("ions_settings") || "{}");
    return s.ionsApiUrl || apiURL_DEFAULT;
  } catch {
    return apiURL_DEFAULT;
  }
}
const apiURL = typeof window !== "undefined" ? getIonsAPI() : apiURL_DEFAULT;
const OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions";

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

function confColor(c: number) {
  if (c >= 0.8) return "var(--emerald)";
  if (c >= 0.6) return "var(--amber)";
  return "var(--red)";
}

export default function GraphPage() {
  const [nsis, setNsis] = useState<NSI[]>([]);
  const [selectedNSI, setSelectedNSI] = useState<NSI | null>(null);
  const [selectedSubdomain, setSelectedSubdomain] = useState<SubDomain | null>(null);
  const [selectedCBB, setSelectedCBB] = useState<CBB | null>(null);
  const [hoveredNSI, setHoveredNSI] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [grouping, setGrouping] = useState(false);
  const [totalCBBs, setTotalCBBs] = useState(0);
  const [view, setView] = useState<"nsi" | "subdomains" | "cbbs">("nsi");
  const [search, setSearch] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [nsiConnections, setNsiConnections] = useState<Record<string, number>>({});

  useEffect(() => {
    // Load API key from settings
    try {
      const s = JSON.parse(localStorage.getItem("ions_settings") || "{}");
      setApiKey(s.openrouterKey || "");
    } catch {}
    loadAndGroup();
  }, []);

  async function loadAndGroup(forceRegroup = false) {
    setLoading(true);

    // Load API key
    let key = "";
    try {
      const s = JSON.parse(localStorage.getItem("ions_settings") || "{}");
      key = s.openrouterKey || "";
      setApiKey(key);
    } catch {}

    // Clear cache if forced regroup
    if (forceRegroup) {
      localStorage.removeItem("ions_nsi_groupings_v2");
    }

    // Fetch all CBBs
    const allCBBs: CBB[] = [];
    let offset = 0;
    try {
      while (true) {
        const resp = await fetch(`${apiURL}/cbb?status=published&limit=500&offset=${offset}`);
        if (!resp.ok) break;
        const batch = await resp.json();
        if (!batch || batch.length === 0) break;
        allCBBs.push(...batch);
        if (batch.length < 500) break;
        offset += 500;
      }
      setTotalCBBs(allCBBs.length);
    } catch {
      setLoading(false);
      return;
    }

    // Group CBBs by exact domain
    const domainMap: Record<string, CBB[]> = {};
    for (const cbb of allCBBs) {
      const d = (cbb.domain || "unknown").toLowerCase().trim();
      if (!domainMap[d]) domainMap[d] = [];
      domainMap[d].push(cbb);
    }

    const domainNames = Object.keys(domainMap);

    // Use LLM to group domains into NSIs if API key available
    let groupings: Record<string, string> = {};

    // Use stable cache key — only regroup when forced or cache missing
    const cacheKey = `ions_nsi_groupings_v2`;
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      try { groupings = JSON.parse(cached); } catch { /* ignore */ }
    }

    if (key && domainNames.length > 0 && !cached) {
      setGrouping(true);
      try {
        const prompt = `You are organizing knowledge domains into Narrow Super Intelligence (NSI) clusters.

Group these domain names into 8-12 meaningful NSI clusters. Each cluster should represent a coherent knowledge area.

Domains to group:
${domainNames.join("\n")}

Rules:
- Create 8-12 NSI cluster names that are broad but meaningful
- Every domain must be assigned to exactly one NSI
- NSI names should be clear and descriptive (e.g. "AI & Machine Learning", "Economics & Finance", "Human Performance")
- Return ONLY valid JSON, no markdown

Output format:
{"groupings": {"domain_name": "NSI Name", "another_domain": "NSI Name"}}`;

        const resp = await fetch(OPENROUTER_API, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${key}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model: "meta-llama/llama-3.1-8b-instruct",
            messages: [{ role: "user", content: prompt }],
            max_tokens: 2000,
            temperature: 0.1,
          }),
        });

        const data = await resp.json();
        let raw = data.choices?.[0]?.message?.content?.trim() || "{}";
        raw = raw.replace(/```json|```/g, "").trim();
        const firstBrace = raw.indexOf("{");
        const lastBrace = raw.lastIndexOf("}");
        if (firstBrace !== -1 && lastBrace !== -1) {
          const parsed = JSON.parse(raw.substring(firstBrace, lastBrace + 1));
          groupings = parsed.groupings || {};
          // Cache groupings with stable key
          localStorage.setItem(cacheKey, JSON.stringify(groupings));
        }
      } catch {
        // Fall through to keyword grouping
      }
      setGrouping(false);
    }

    // Keyword fallback grouping if LLM not available or failed
    const KEYWORD_GROUPS: [string, string[]][] = [
      ["AI & Machine Learning",     ["ai", "machine learning", "neural", "llm", "deep learning", "artificial intel", "cognit", "mind"]],
      ["AI Regulation & Policy",    ["regulation", "regulatory", "governance", "legal", "compliance", "policy", "gdpr", "act", "law", "accountability", "transparency"]],
      ["Healthcare & Medicine",     ["health", "medical", "clinical", "pharma", "biotech", "patient", "hospital"]],
      ["Economics & Finance",       ["economic", "monetary", "macro", "finance", "financial", "banking", "fintech", "money", "credit", "fiscal"]],
      ["Blockchain & Crypto",       ["crypto", "blockchain", "bitcoin", "ethereum", "web3", "defi", "token"]],
      ["Peak Performance",          ["peak perform", "flow", "learning", "personal develop", "human perform", "resilience", "mindset", "sport", "athlete"]],
      ["Exponential Technology",    ["exponential", "emerging tech", "future", "metaverse", "spatial", "quantum", "nanotech"]],
      ["Platform & Strategy",       ["platform", "strategy", "innovation", "entrepreneurship", "competitive", "business model", "market"]],
      ["Neuroscience & Mind",       ["neuro", "brain", "cognitive", "psychology", "consciousness", "behavior"]],
      ["Physics & Cosmology",       ["physics", "cosmology", "math", "universe", "quantum", "relativity", "integral philosophy", "integral", "philosophy"]],
      ["Society & Governance",      ["society", "government", "political", "globalization", "sovereign", "network state", "social"]],
      ["Marketing & Creativity",    ["marketing", "brand", "creativity", "design", "communication", "media"]],
      ["Organizational Intelligence", ["organizational", "organisation", "business process", "digital transform", "leadership", "operational", "institutional", "change management", "business management", "governance and leadership"]],
    ];

    function fallbackGroup(domain: string): string {
      const lower = domain.toLowerCase();
      for (const [group, keywords] of KEYWORD_GROUPS) {
        if (keywords.some(k => lower.includes(k))) return group;
      }
      return "Other";
    }

    // Build NSI structure
    const nsiMap: Record<string, { subdomains: Record<string, CBB[]> }> = {};

    for (const domain of domainNames) {
      const nsiName = groupings[domain] || fallbackGroup(domain);
      if (!nsiMap[nsiName]) nsiMap[nsiName] = { subdomains: {} };
      nsiMap[nsiName].subdomains[domain] = domainMap[domain];
    }

    const nsiList: NSI[] = Object.entries(nsiMap)
      .map(([name, data], i) => {
        const subdomains: SubDomain[] = Object.entries(data.subdomains)
          .sort((a, b) => b[1].length - a[1].length)
          .map(([dname, cbbs]) => ({
            name: dname,
            displayName: dname.replace(/_/g, " ").replace(/ and /g, " & "),
            count: cbbs.length,
            cbbs,
          }));

        const totalCount = subdomains.reduce((s, d) => s + d.count, 0);

        return {
          name,
          displayName: name,
          color: PALETTE[i % PALETTE.length],
          subdomains,
          totalCount,
        };
      })
      .sort((a, b) => b.totalCount - a.totalCount);

    // Build cross-NSI connection map from actual relationships
    // We sample relationships and check if source/target CBBs are in different NSIs
    const domainToNSI: Record<string, string> = {};
    nsiList.forEach(nsi => {
      nsi.subdomains.forEach(sub => {
        sub.cbbs.forEach(cbb => {
          domainToNSI[cbb.cbb_id] = nsi.name;
        });
      });
    });

    // Fetch a sample of relationships to determine cross-NSI connections
    const connections: Record<string, number> = {};
    try {
      const relResp = await fetch(`${apiURL}/relationship?limit=500`);
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
    // Update sidebar NSI count
    const nsiEl = document.getElementById("live-clusters");
    if (nsiEl) nsiEl.textContent = String(nsiList.length);
    setLoading(false);
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
          <button className="btn btn-ghost" onClick={() => loadAndGroup(true)}>↻ Regroup</button>
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
        {(loading || grouping) && (
          <div style={{ display: "flex", alignItems: "center", gap: "12px", color: "var(--slate)", fontSize: "13px", padding: "40px 0", justifyContent: "center" }}>
            <div className="spinner" />
            {grouping ? "LLM grouping domains into NSI clusters..." : "Loading network..."}
          </div>
        )}

        {/* NSI VIEW — Level 1 */}
        {view === "nsi" && !loading && !grouping && (
          <>
            {!apiKey && (
              <div style={{ padding: "10px 16px", background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: "8px", fontSize: "12px", color: "var(--amber)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span>⚠ No API key — using keyword grouping. <a href="/settings" style={{ color: "var(--indigo2)" }}>Add key in Settings</a> for LLM-powered semantic grouping.</span>
              </div>
            )}

            {/* Positioned NSI network map with SVG connections */}
            {(() => {
              const W = 100, H = 100; // percentage coords
              // Place NSIs in a circle with largest in center
              const sorted = [...filteredNSIs].sort((a, b) => b.totalCount - a.totalCount);
              const positions: Record<string, { x: number; y: number }> = {};
              if (sorted.length > 0) {
                positions[sorted[0].name] = { x: 50, y: 48 }; // largest in center
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
                  {/* Dot grid */}
                  <div style={{ position: "absolute", inset: 0, opacity: 0.03, backgroundImage: "radial-gradient(circle, #6366f1 1px, transparent 1px)", backgroundSize: "32px 32px" }} />

                  {/* SVG connection lines — based on actual cross-NSI relationships */}
                  <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
                    {Object.entries(nsiConnections).map(([key, count]) => {
                      const [aName, bName] = key.split("|");
                      const posA = positions[aName];
                      const posB = positions[bName];
                      if (!posA || !posB) return null;
                      const isHighlighted = hoveredNSI === aName || hoveredNSI === bName;
                      const nsiA = filteredNSIs.find(n => n.name === aName);
                      // Normalize strength — more relationships = thicker line
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

                  {/* NSI bubble nodes */}
                  {filteredNSIs.map(nsi => {
                    const pos = positions[nsi.name];
                    if (!pos) return null;
                    const pct = nsi.totalCount / maxCount;
                    const size = Math.max(56, Math.min(130, pct * 100 + 56));
                    const isHovered = hoveredNSI === nsi.name;
                    return (
                      <div
                        key={nsi.name}
                        onClick={() => { setSelectedNSI(nsi); setView("subdomains"); setSearch(""); }}
                        onMouseEnter={() => setHoveredNSI(nsi.name)}
                        onMouseLeave={() => setHoveredNSI(null)}
                        style={{
                          position: "absolute",
                          left: `${pos.x}%`,
                          top: `${pos.y}%`,
                          width: `${size}px`,
                          height: `${size}px`,
                          transform: `translate(-50%, -50%) scale(${isHovered ? 1.08 : 1})`,
                          borderRadius: "50%",
                          background: isHovered ? nsi.color + "28" : nsi.color + "14",
                          border: `${isHovered ? 2 : 1}px solid ${nsi.color}${isHovered ? "ee" : "77"}`,
                          cursor: "pointer",
                          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                          transition: "all 0.18s ease",
                          boxShadow: isHovered ? `0 0 28px ${nsi.color}50` : `0 0 12px ${nsi.color}15`,
                          zIndex: isHovered ? 10 : 1,
                          padding: "6px",
                        }}
                      >
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: `${Math.max(10, size * 0.17)}px`, color: nsi.color, fontWeight: 700, lineHeight: 1 }}>
                          {nsi.totalCount}
                        </div>
                        {size > 65 && (
                          <div style={{ fontSize: `${Math.max(8, size * 0.09)}px`, color: isHovered ? "var(--text2)" : "var(--slate2)", textAlign: "center", marginTop: "3px", lineHeight: 1.2, padding: "0 4px" }}>
                            {nsi.displayName.length > Math.floor(size / 7) ? nsi.displayName.substring(0, Math.floor(size / 7)) + "…" : nsi.displayName}
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {/* Hover tooltip */}
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
                padding: "14px 18px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                fontSize: "12px",
                color: "var(--slate)",
                fontFamily: "var(--font-display)",
                listStyle: "none",
                userSelect: "none",
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
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: confColor(cbb.confidence), flexShrink: 0 }}>
                      {cbb.confidence?.toFixed(2)}
                    </div>
                  </div>
                ))}
            </div>
          </>
        )}

      </div>
    </>
  );
}
