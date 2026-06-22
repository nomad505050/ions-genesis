"use client";

import { useState, useEffect } from "react";

export const SETTINGS_KEY = "ions_settings";

export type IONSSettings = {
  openrouterKey: string;
  model: string;
  customModel: string;
  ionsApiUrl: string;
};

export const DEFAULT_SETTINGS: IONSSettings = {
  openrouterKey: "",
  model: "meta-llama/llama-3.1-8b-instruct",
  customModel: "",
  ionsApiUrl: "http://localhost:8000",
};

export function loadSettings(): IONSSettings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    const stored = localStorage.getItem(SETTINGS_KEY);
    return stored ? { ...DEFAULT_SETTINGS, ...JSON.parse(stored) } : DEFAULT_SETTINGS;
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function saveSettings(s: IONSSettings) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
}

export function getActiveModel(s: IONSSettings): string {
  return s.model === "custom" ? s.customModel : s.model;
}

const PRESET_MODELS = [
  { value: "meta-llama/llama-3.1-8b-instruct",   label: "Llama 3.1 8B — lightweight, fast" },
  { value: "meta-llama/llama-3.1-70b-instruct",  label: "Llama 3.1 70B — stronger reasoning" },
  { value: "meta-llama/llama-3.3-70b-instruct",  label: "Llama 3.3 70B — latest Llama" },
  { value: "mistralai/mistral-7b-instruct",       label: "Mistral 7B — efficient" },
  { value: "mistralai/mixtral-8x7b-instruct",     label: "Mixtral 8x7B — MoE" },
  { value: "anthropic/claude-sonnet-4-5",         label: "Claude Sonnet 4.5 — frontier" },
  { value: "openai/gpt-4o-mini",                  label: "GPT-4o mini — OpenAI lightweight" },
  { value: "openai/gpt-4o",                       label: "GPT-4o — OpenAI frontier" },
  { value: "google/gemini-flash-1.5",             label: "Gemini Flash 1.5 — fast" },
  { value: "custom",                               label: "Custom model string..." },
];

export default function SettingsPage() {
  const [settings, setSettings] = useState<IONSSettings>(DEFAULT_SETTINGS);
  const [saved, setSaved] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<"ok" | "fail" | null>(null);

  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  function update(key: keyof IONSSettings, value: string) {
    setSettings(prev => ({ ...prev, [key]: value }));
    setSaved(false);
    setTestResult(null);
  }

  function handleSave() {
    saveSettings(settings);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function testConnection() {
    setTesting(true);
    setTestResult(null);
    try {
      const resp = await fetch(`${settings.ionsApiUrl}/health`);
      setTestResult(resp.ok ? "ok" : "fail");
    } catch {
      setTestResult("fail");
    }
    setTesting(false);
  }

  async function testModel() {
    if (!settings.openrouterKey) return;
    setTesting(true);
    setTestResult(null);
    try {
      const model = getActiveModel(settings);
      const resp = await fetch("https://openrouter.ai/api/v1/chat/completions", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${settings.openrouterKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model,
          messages: [{ role: "user", content: "Reply with one word: ready" }],
          max_tokens: 10,
        }),
      });
      setTestResult(resp.ok ? "ok" : "fail");
    } catch {
      setTestResult("fail");
    }
    setTesting(false);
  }

  const activeModel = getActiveModel(settings);

  return (
    <>
      <div className="topbar">
        <span className="topbar-title">Settings</span>
        <span className="topbar-sub">API key · model selection · node URL · stored in your browser only</span>
        <div className="topbar-actions">
          <button
            className="btn btn-primary"
            onClick={handleSave}
            style={{ minWidth: "80px" }}
          >
            {saved ? "✓ Saved" : "Save"}
          </button>
        </div>
      </div>

      <div className="page-content">

        {/* Key notice */}
        <div style={{
          padding: "14px 18px",
          background: "rgba(245,158,11,0.08)",
          border: "1px solid rgba(245,158,11,0.25)",
          borderRadius: "8px",
          fontSize: "13px",
          color: "var(--slate)",
          lineHeight: 1.6,
        }}>
          <span style={{ color: "var(--amber)", fontFamily: "var(--font-display)", fontWeight: 600, fontSize: "10px", letterSpacing: "1.5px", textTransform: "uppercase", display: "block", marginBottom: "4px" }}>
            Required for extraction & relationship suggestions
          </span>
          An OpenRouter API key is needed to extract CBBs from documents and auto-suggest relationships. Get one free at{" "}
          <a href="https://openrouter.ai" target="_blank" rel="noopener noreferrer" style={{ color: "var(--amber)" }}>openrouter.ai</a>.
          Your key is stored in your browser only — it is never sent to the IONS node or any server other than OpenRouter.
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "20px" }}>

          {/* Left — main settings */}
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>

            {/* API Key */}
            <div className="card">
              <div className="card-label">OpenRouter API Key</div>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <div className="form-group">
                  <input
                    className="form-input"
                    type="password"
                    value={settings.openrouterKey}
                    onChange={e => update("openrouterKey", e.target.value)}
                    placeholder="sk-or-v1-..."
                    style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}
                  />
                  <span className="form-hint">
                    {settings.openrouterKey
                      ? `Key set · ${settings.openrouterKey.substring(0, 8)}...`
                      : "No key set — extraction and auto-suggest disabled"}
                  </span>
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={testModel}
                    disabled={testing || !settings.openrouterKey}
                  >
                    {testing ? "Testing..." : "Test connection"}
                  </button>
                  {testResult === "ok" && <span style={{ fontSize: "12px", color: "var(--emerald)", alignSelf: "center" }}>✓ Connected</span>}
                  {testResult === "fail" && <span style={{ fontSize: "12px", color: "var(--red)", alignSelf: "center" }}>✕ Failed — check key</span>}
                </div>
              </div>
            </div>

            {/* Model selection */}
            <div className="card">
              <div className="card-label">Model</div>
              <div style={{ fontSize: "13px", color: "var(--slate)", lineHeight: 1.6, marginBottom: "14px" }}>
                IONS is model-agnostic — any model that can follow instructions can traverse the network. The choice of model affects extraction quality and relationship suggestion accuracy, not the CBBs themselves.
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <div className="form-group">
                  <label className="form-label">Select model</label>
                  <select
                    className="form-select"
                    value={settings.model}
                    onChange={e => update("model", e.target.value)}
                  >
                    {PRESET_MODELS.map(m => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </div>

                {settings.model === "custom" && (
                  <div className="form-group">
                    <label className="form-label">Custom model string</label>
                    <input
                      className="form-input"
                      value={settings.customModel}
                      onChange={e => update("customModel", e.target.value)}
                      placeholder="provider/model-name e.g. cohere/command-r-plus"
                      style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}
                    />
                    <span className="form-hint">Any model available on OpenRouter · see openrouter.ai/models</span>
                  </div>
                )}

                {activeModel && (
                  <div style={{
                    padding: "10px 12px",
                    background: "var(--bg3)",
                    borderRadius: "6px",
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                    color: "var(--indigo2)",
                  }}>
                    Active model: {activeModel}
                  </div>
                )}
              </div>
            </div>

            {/* IONS Node URL */}
            <div className="card">
              <div className="card-label">IONS Node URL</div>
              <div style={{ fontSize: "13px", color: "var(--slate)", lineHeight: 1.6, marginBottom: "14px" }}>
                Point to any compatible IONS node. Default is your local Genesis node. Change this to connect to a remote or community node.
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <div className="form-group">
                  <input
                    className="form-input"
                    value={settings.ionsApiUrl}
                    onChange={e => update("ionsApiUrl", e.target.value)}
                    placeholder="http://localhost:8000"
                    style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}
                  />
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={testConnection}
                    disabled={testing}
                  >
                    {testing ? "Testing..." : "Test node connection"}
                  </button>
                  {testResult === "ok" && <span style={{ fontSize: "12px", color: "var(--emerald)", alignSelf: "center" }}>✓ Node healthy</span>}
                  {testResult === "fail" && <span style={{ fontSize: "12px", color: "var(--red)", alignSelf: "center" }}>✕ Node unreachable</span>}
                </div>
              </div>
            </div>

          </div>

          {/* Right — info */}
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>

            <div className="card">
              <div className="card-label">Why model choice matters</div>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "13px", color: "var(--slate)", lineHeight: 1.7 }}>
                <div>
                  <span style={{ color: "var(--text2)", fontWeight: 600 }}>Lightweight models (7B–8B)</span> — fast, low cost, good for extraction and traversal on well-structured CBBs. This is the core IONS thesis: a small model connected to a rich CBB network can match frontier quality on specific domains.
                </div>
                <div>
                  <span style={{ color: "var(--text2)", fontWeight: 600 }}>Mid-size models (70B)</span> — better reasoning, more accurate relationship suggestions, stronger synthesis. Good if you're curating a high-quality NSI.
                </div>
                <div>
                  <span style={{ color: "var(--text2)", fontWeight: 600 }}>Frontier models (Claude, GPT-4o)</span> — highest accuracy for extraction and suggestion, but higher cost. Use for initial NSI seeding, then switch to lightweight for traversal.
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-label">Privacy</div>
              <div style={{ fontSize: "13px", color: "var(--slate)", lineHeight: 1.7 }}>
                Your API key and settings are stored in your browser's localStorage only. They are never sent to the IONS node. Only the text you explicitly submit for extraction is sent to OpenRouter using your own key.
              </div>
            </div>

            <div className="card">
              <div className="card-label">Current settings</div>
              <pre style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--slate)", lineHeight: 1.8 }}>
{`key:   ${settings.openrouterKey ? settings.openrouterKey.substring(0, 12) + "..." : "not set"}
model: ${activeModel || "not set"}
node:  ${settings.ionsApiUrl}`}
              </pre>
            </div>

            <button
              className="btn btn-primary"
              onClick={handleSave}
              style={{ width: "100%", padding: "12px", fontSize: "14px" }}
            >
              {saved ? "✓ Settings saved" : "Save settings"}
            </button>

          </div>
        </div>
      </div>
    </>
  );
}
