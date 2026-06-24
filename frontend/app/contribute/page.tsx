"use client";

import { useState, useRef, useEffect } from "react";
import { loadSettings, getActiveModel } from "../settings/page";

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
const IONS_API = typeof window !== "undefined" ? getIonsAPI() : IONS_API_DEFAULT;
const OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions";
const MODEL = "meta-llama/llama-3.1-8b-instruct";

const SOURCE_TYPES = [
  { value: "original", label: "Original research or observation" },
  { value: "book", label: "Book" },
  { value: "paper", label: "Research paper" },
  { value: "article", label: "Article or blog post" },
  { value: "document", label: "Document or report" },
  { value: "conversation", label: "Conversation or interview" },
];

type Candidate = {
  content: string;
  domain: string;
  confidence: number;
  assumptions: string[];
  scope: string[];
  selected: boolean;
};

const EXTRACT_PROMPT = `Extract Cognitive Building Blocks from the text. Return ONLY a JSON object. No explanation. No preamble. No markdown. Start your response with { and end with }.

Each CBB is one atomic assertable claim. Focus on causal claims, named concepts, failure patterns, and design principles.

Assign a domain that accurately describes the subject matter. Use specific, descriptive domain names like: ai_regulation, organizational_intelligence, monetary_economics, blockchain_technology, peak_performance, exponential_technology, platform_strategy, neuroscience, physics, network_states, fintech, marketing, digital_transformation, healthcare_ai, legal_frameworks, climate_technology — or create a new domain name that fits the content. Do NOT force content into an ill-fitting domain.

JSON format (respond with this exact structure):
{"candidates":[{"content":"claim text","domain":"domain_name","confidence":0.80,"assumptions":["context"],"scope":["area"]}]}`;

export default function ContributePage() {
  const [mode, setMode] = useState<"extract" | "single">("extract");
  const [text, setText] = useState("");
  const [sourceType, setSourceType] = useState("original");
  const [sourceRef, setSourceRef] = useState("");
  const [contributorId, setContributorId] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [activeModel, setActiveModel] = useState("meta-llama/llama-3.1-8b-instruct");

  useEffect(() => {
    const s = loadSettings();
    setApiKey(s.openrouterKey);
    setActiveModel(getActiveModel(s));
  }, []);
  const [extracting, setExtracting] = useState(false);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(0);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  // Single mode state
  const [singleContent, setSingleContent] = useState("");

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");

    const ext = file.name.split(".").pop()?.toLowerCase();

    // Plain text files
    if (ext === "txt" || ext === "md" || ext === "csv") {
      const reader = new FileReader();
      reader.onload = ev => setText((ev.target?.result as string || "").substring(0, 8000));
      reader.onerror = () => setError("Could not read file.");
      reader.readAsText(file);
      return;
    }

    // DOCX — extract text via mammoth loaded from CDN
    if (ext === "docx" || ext === "doc") {
      try {
        // Dynamically load mammoth if not available
        if (!(window as any).mammoth) {
          await new Promise<void>((resolve, reject) => {
            const script = document.createElement("script");
            script.src = "https://cdnjs.cloudflare.com/ajax/libs/mammoth/1.6.0/mammoth.browser.min.js";
            script.onload = () => resolve();
            script.onerror = () => reject(new Error("Failed to load mammoth"));
            document.head.appendChild(script);
          });
        }
        const arrayBuffer = await file.arrayBuffer();
        const result = await (window as any).mammoth.extractRawText({ arrayBuffer });
        setText(result.value.substring(0, 8000));
      } catch {
        setError("Could not parse .docx file. Try copying and pasting the text instead.");
      }
      return;
    }

    // PDF — tell user to paste
    if (ext === "pdf") {
      setError("PDF extraction coming soon. Please copy and paste the text from your PDF.");
      return;
    }

    setError("Unsupported file type. Try .txt, .md, or .docx");
  }

  async function extractCBBs() {
    if (!text.trim()) { setError("Paste some text or upload a document first"); return; }
    if (!apiKey) { setError("OpenRouter API key required for extraction"); return; }
    setError("");
    setExtracting(true);
    setCandidates([]);

    try {
      // Split into chunks if long
      const chunks = [];
      const chunkSize = 4000;
      for (let i = 0; i < text.length; i += chunkSize) {
        chunks.push(text.slice(i, i + chunkSize));
      }

      const allCandidates: Candidate[] = [];

      for (const chunk of chunks.slice(0, 6)) { // max 6 chunks
        const resp = await fetch(OPENROUTER_API, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${apiKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model: activeModel,
            messages: [
              { role: "system", content: EXTRACT_PROMPT },
              { role: "user", content: `Extract CBBs from this text:\n\n${chunk}` },
            ],
            max_tokens: 3000,
            temperature: 0.2,
          }),
        });

        const data = await resp.json();
        let raw = data.choices?.[0]?.message?.content?.trim() || "{}";
        // Strip markdown fences
        raw = raw.replace(/```json|```/g, "").trim();
        // Find the JSON object - look for first { to last }
        const firstBrace = raw.indexOf("{");
        const lastBrace = raw.lastIndexOf("}");
        if (firstBrace === -1 || lastBrace === -1) {
          console.warn("No JSON found in response:", raw.substring(0, 100));
          continue;
        }
        const jsonStr = raw.substring(firstBrace, lastBrace + 1);
        let parsed;
        try {
          parsed = JSON.parse(jsonStr);
        } catch {
          console.warn("JSON parse failed:", jsonStr.substring(0, 100));
          continue;
        }
        const extracted = parsed.candidates || [];

        for (const c of extracted) {
          if (c.content && c.content.length > 20) {
            allCandidates.push({ ...c, selected: true });
          }
        }
      }

      setCandidates(allCandidates);
      if (allCandidates.length === 0) {
        setError("No CBBs could be extracted. Try a longer or more specific text.");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Extraction failed");
    }
    setExtracting(false);
  }

  function toggleCandidate(i: number) {
    setCandidates(prev => prev.map((c, idx) => idx === i ? { ...c, selected: !c.selected } : c));
  }

  async function submitSelected() {
    const selected = candidates.filter(c => c.selected);
    if (selected.length === 0) { setError("Select at least one CBB to submit"); return; }
    setSubmitting(true);
    setError("");
    let count = 0;

    for (const c of selected) {
      try {
        const resp = await fetch(`${IONS_API}/cbb`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            type: "claim",
            domain: c.domain || "ai_systems_org_cognition",
            content: c.content,
            confidence: c.confidence || 0.75,
            assumptions: c.assumptions || [],
            scope: c.scope || [],
            evidence: [{
              source_type: sourceType,
              source_id: sourceRef || "contributor_submitted",
              visibility: "public",
            }],
            tags: ["contributor_submitted", sourceType],
            status: "candidate",
          }),
        });
        if (resp.ok) count++;
      } catch { /* continue */ }
    }

    setSubmitted(count);
    setSubmitting(false);
    setCandidates([]);
    setText("");
  }

  async function submitSingle() {
    if (!singleContent.trim()) { setError("Claim is required"); return; }
    setSubmitting(true);
    setError("");

    try {
      let domain = "ai_systems_org_cognition";
      let confidence = 0.75;

      if (apiKey) {
        try {
          const resp = await fetch(OPENROUTER_API, {
            method: "POST",
            headers: { "Authorization": `Bearer ${apiKey}`, "Content-Type": "application/json" },
            body: JSON.stringify({
              model: activeModel,
              messages: [{ role: "user", content: `Classify this claim and return ONLY JSON with domain (descriptive name like ai_regulation, peak_performance, blockchain_technology, etc — be specific, do not force into a broad category) and confidence (0-1): "${singleContent}"` }],
              max_tokens: 100,
              temperature: 0.1,
            }),
          });
          const data = await resp.json();
          const raw = data.choices?.[0]?.message?.content?.trim() || "{}";
          const parsed = JSON.parse(raw.replace(/```json|```/g, "").trim());
          domain = parsed.domain || domain;
          confidence = parsed.confidence || confidence;
        } catch { /* use defaults */ }
      }

      const resp = await fetch(`${IONS_API}/cbb`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "claim",
          domain,
          content: singleContent.trim(),
          confidence,
          assumptions: [],
          scope: [],
          evidence: [{ source_type: sourceType, source_id: sourceRef || "contributor_submitted", visibility: "public" }],
          tags: ["contributor_submitted", sourceType],
          status: "candidate",
        }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      setSubmitted(1);
      setSingleContent("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Submission failed");
    }
    setSubmitting(false);
  }

  if (submitted > 0) {
    return (
      <>
        <div className="topbar">
          <span className="topbar-title">Add CBB</span>
          <span className="topbar-sub">Contribute knowledge to the network</span>
        </div>
        <div className="page-content" style={{ alignItems: "center", justifyContent: "center" }}>
          <div style={{ textAlign: "center", maxWidth: "480px", padding: "60px 20px" }}>
            <div style={{ fontSize: "48px", marginBottom: "20px" }}>⬡</div>
            <div style={{ fontFamily: "var(--font-display)", fontSize: "22px", fontWeight: 600, color: "var(--text)", marginBottom: "8px" }}>
              {submitted} CBB{submitted > 1 ? "s" : ""} submitted
            </div>
            <div style={{ fontSize: "14px", color: "var(--slate)", lineHeight: 1.6, marginBottom: "28px" }}>
              {submitted > 1
                ? `${submitted} Cognitive Building Blocks have entered the review queue. Domain and confidence were auto-assigned. Once approved they'll be published to the network and available for traversal.`
                : "Your Cognitive Building Block has entered the review queue. Once approved it will be published to the network."}
            </div>
            <div style={{ display: "flex", gap: "10px", justifyContent: "center" }}>
              <button className="btn btn-primary" onClick={() => setSubmitted(0)}>Contribute more</button>
              <a href="/workbench" className="btn btn-ghost">View queue</a>
            </div>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="topbar">
        <span className="topbar-title">Add CBB</span>
        <span className="topbar-sub">Extract from a document · or add a single claim · domain auto-assigned</span>
        <div className="topbar-actions">
          <a href="/workbench" className="btn btn-ghost">View queue</a>
        </div>
      </div>

      <div className="page-content">

        {/* Mode tabs */}
        <div style={{ display: "flex", gap: "4px", borderBottom: "1px solid var(--border)", paddingBottom: "0" }}>
          {([
            { key: "extract", label: "Extract from document" },
            { key: "single",  label: "Add single claim" },
          ] as const).map(t => (
            <button
              key={t.key}
              onClick={() => { setMode(t.key); setError(""); setCandidates([]); }}
              style={{
                padding: "8px 16px",
                background: "transparent",
                border: "none",
                borderBottom: mode === t.key ? "2px solid var(--indigo)" : "2px solid transparent",
                color: mode === t.key ? "var(--indigo2)" : "var(--slate2)",
                fontFamily: "var(--font-display)",
                fontSize: "13px",
                fontWeight: mode === t.key ? 600 : 400,
                cursor: "pointer",
                transition: "all 0.15s",
                marginBottom: "-1px",
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Settings status */}
        <div style={{
          padding: "10px 16px",
          background: apiKey ? "rgba(16,185,129,0.06)" : "rgba(245,158,11,0.08)",
          border: `1px solid ${apiKey ? "rgba(16,185,129,0.2)" : "rgba(245,158,11,0.25)"}`,
          borderRadius: "8px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          fontSize: "12px",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ color: apiKey ? "var(--emerald)" : "var(--amber)" }}>
              {apiKey ? "✓ API key set" : "⚠ No API key set"}
            </span>
            {apiKey && <span style={{ color: "var(--slate2)", fontFamily: "var(--font-mono)" }}>model: {activeModel.split("/")[1] || activeModel}</span>}
          </div>
          <a href="/settings" className="btn btn-ghost btn-sm">
            {apiKey ? "Change settings" : "Add API key in Settings →"}
          </a>
        </div>

        {/* ── EXTRACT MODE ── */}
        {mode === "extract" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div className="card">
              <div className="card-label">Source</div>
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>

                {/* Upload or paste */}
                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    className="btn btn-ghost"
                    onClick={() => fileRef.current?.click()}
                    style={{ flexShrink: 0 }}
                  >
                    ↑ Upload file
                  </button>
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".txt,.md,.docx,.doc,.csv"
                    style={{ display: "none" }}
                    onChange={handleFileUpload}
                  />
                  <span style={{ fontSize: "12px", color: "var(--slate2)", alignSelf: "center" }}>
                    .txt, .md, .docx supported · or paste text below
                  </span>
                </div>

                <textarea
                  className="form-textarea"
                  value={text}
                  onChange={e => setText(e.target.value)}
                  placeholder="Paste your document, notes, article, or book excerpt here..."
                  style={{ minHeight: "180px" }}
                />
                <span className="form-hint">{text.length.toLocaleString()} characters · extraction processes up to 9,000 chars</span>

                <div className="grid-2">
                  <div className="form-group">
                    <label className="form-label">Source type</label>
                    <select className="form-select" value={sourceType} onChange={e => setSourceType(e.target.value)}>
                      {SOURCE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Source reference</label>
                    <input
                      className="form-input"
                      value={sourceRef}
                      onChange={e => setSourceRef(e.target.value)}
                      placeholder="Title, URL, or description"
                    />
                  </div>
                </div>

                <button
                  className="btn btn-primary"
                  onClick={extractCBBs}
                  disabled={extracting || !text.trim()}
                  style={{ alignSelf: "flex-start", padding: "10px 24px" }}
                >
                  {extracting ? "Extracting CBBs..." : "Extract CBBs →"}
                </button>
              </div>
            </div>

            {/* Candidates */}
            {candidates.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontFamily: "var(--font-display)", fontSize: "14px", fontWeight: 600, color: "var(--text)" }}>
                      {candidates.length} CBBs extracted
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--slate2)", marginTop: "2px" }}>
                      {candidates.filter(c => c.selected).length} selected · deselect any you don't want
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button className="btn btn-ghost btn-sm" onClick={() => setCandidates(c => c.map(x => ({ ...x, selected: true })))}>Select all</button>
                    <button className="btn btn-ghost btn-sm" onClick={() => setCandidates(c => c.map(x => ({ ...x, selected: false })))}>Deselect all</button>
                  </div>
                </div>

                {candidates.map((c, i) => (
                  <div
                    key={i}
                    onClick={() => toggleCandidate(i)}
                    style={{
                      padding: "14px 16px",
                      background: c.selected ? "rgba(99,102,241,0.06)" : "var(--bg2)",
                      border: `1px solid ${c.selected ? "var(--indigo)" : "var(--border)"}`,
                      borderRadius: "8px",
                      cursor: "pointer",
                      transition: "all 0.15s",
                      display: "flex",
                      gap: "14px",
                      alignItems: "flex-start",
                    }}
                  >
                    {/* Checkbox */}
                    <div style={{
                      width: "18px", height: "18px", borderRadius: "4px", flexShrink: 0, marginTop: "2px",
                      background: c.selected ? "var(--indigo)" : "transparent",
                      border: `2px solid ${c.selected ? "var(--indigo)" : "var(--border2)"}`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                    }}>
                      {c.selected && <span style={{ color: "#fff", fontSize: "11px" }}>✓</span>}
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: "13px", color: "var(--text2)", lineHeight: 1.6, marginBottom: "8px" }}>
                        {c.content}
                      </div>
                      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                        <span className="tag tag-indigo">{c.domain?.replace(/_/g, " ")}</span>
                        <span className="tag tag-amber">conf: {c.confidence?.toFixed(2)}</span>
                        {c.assumptions?.[0] && (
                          <span className="tag tag-slate">{c.assumptions[0].substring(0, 40)}</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {error && (
                  <div style={{ padding: "10px 14px", background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: "6px", fontSize: "12px", color: "var(--red)" }}>
                    {error}
                  </div>
                )}

                <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                  <button
                    className="btn btn-primary"
                    onClick={submitSelected}
                    disabled={submitting || candidates.filter(c => c.selected).length === 0}
                    style={{ padding: "10px 24px", fontSize: "14px" }}
                  >
                    {submitting ? "Submitting..." : `Submit ${candidates.filter(c => c.selected).length} CBBs to review queue`}
                  </button>
                  <span style={{ fontSize: "11px", color: "var(--slate2)" }}>curator approval required before publication</span>
                </div>
              </div>
            )}

            {error && candidates.length === 0 && (
              <div style={{ padding: "10px 14px", background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: "6px", fontSize: "12px", color: "var(--red)" }}>
                {error}
              </div>
            )}
          </div>
        )}

        {/* ── SINGLE MODE ── */}
        {mode === "single" && (
          <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: "20px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div className="card">
                <div className="card-label">Single claim</div>
                <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                  <div className="form-group">
                    <textarea
                      className="form-textarea"
                      value={singleContent}
                      onChange={e => setSingleContent(e.target.value)}
                      placeholder="State one atomic, assertable claim..."
                      style={{ minHeight: "120px" }}
                      autoFocus
                    />
                    <span className="form-hint">
                      {singleContent.length}/800 chars
                      {singleContent.includes(" and ") && singleContent.length > 40 ? " · ⚠ may contain multiple claims" : ""}
                    </span>
                  </div>
                  <div className="grid-2">
                    <div className="form-group">
                      <label className="form-label">Source type</label>
                      <select className="form-select" value={sourceType} onChange={e => setSourceType(e.target.value)}>
                        {SOURCE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">Source reference</label>
                      <input className="form-input" value={sourceRef} onChange={e => setSourceRef(e.target.value)} placeholder="Title, URL, or description" />
                    </div>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Contributor identity (optional)</label>
                    <input className="form-input" value={contributorId} onChange={e => setContributorId(e.target.value)} placeholder="Public key or handle" style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }} />
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div className="card">
                <div className="card-label">Auto-classification</div>
                <div style={{ fontSize: "13px", color: "var(--slate)", lineHeight: 1.6, marginBottom: "12px" }}>
                  Domain, confidence, assumptions, and scope are automatically assigned. Provide an API key to enable live classification.
                </div>
                <div style={{ padding: "10px 12px", background: "var(--bg3)", borderRadius: "6px", fontSize: "11px", color: "var(--slate2)", fontFamily: "var(--font-mono)" }}>
                  domain: auto · confidence: auto · scope: auto
                </div>
              </div>

              {error && (
                <div style={{ padding: "10px 14px", background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: "6px", fontSize: "12px", color: "var(--red)" }}>
                  {error}
                </div>
              )}

              <button
                className="btn btn-primary"
                onClick={submitSingle}
                disabled={submitting || !singleContent.trim()}
                style={{ width: "100%", padding: "12px", fontSize: "14px" }}
              >
                {submitting ? "Submitting..." : "Submit to Review Queue"}
              </button>
              <div style={{ fontSize: "11px", color: "var(--slate2)", textAlign: "center" }}>
                Curator approval required before publication
              </div>
            </div>
          </div>
        )}

      </div>
    </>
  );
}
