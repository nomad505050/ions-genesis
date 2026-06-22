"use client";



export default function RightsPage() {


  return (
    <>
      <div className="topbar">
        <span className="topbar-title">Rights & Attribution</span>
        <span className="topbar-sub">Provenance chain · attribution · reward escrow · <span style={{ color: "var(--amber)", fontFamily: "var(--font-mono)", fontSize: "11px" }}>EXPERIMENTAL</span></span>
      </div>

      <div className="page-content">

        {/* Intro */}
        <div style={{
          padding: "16px 20px",
          background: "rgba(99,102,241,0.06)",
          border: "1px solid rgba(99,102,241,0.15)",
          borderRadius: "8px",
          fontSize: "13px",
          color: "var(--slate)",
          lineHeight: 1.7,
        }}>
          <span style={{ color: "var(--indigo2)", fontFamily: "var(--font-display)", fontWeight: 600, fontSize: "10px", letterSpacing: "1.5px", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>
            Core principle
          </span>
          IONS rewards original cognitive contribution rather than simple replication. The protocol distinguishes between attribution, contribution, ownership, and rights — and preserves a permanent provenance chain so every CBB, relationship, and reasoning path can be traced to its origin.
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>

          {/* Left — How it works */}
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div className="card-label">How attribution works</div>

            {[
              {
                num: "1",
                title: "Contributor publishes a CBB",
                desc: "The contributor's identity (public key) is recorded permanently in the provenance chain. Attribution is immutable and cannot be removed.",
              },
              {
                num: "2",
                title: "Original source is recorded",
                desc: "If the CBB is derived from a book, paper, or other source, the original author and source are recorded in the evidence field. Attribution is not the same as rights.",
              },
              {
                num: "3",
                title: "Rights holder files a claim",
                desc: "The original author or publisher can file a rights claim asserting reward eligibility for CBBs derived from their work.",
              },
              {
                num: "4",
                title: "Rewards held in escrow",
                desc: "Until a rights claim is verified, rewards from third-party-derived CBBs are held in escrow. The contributor retains attribution credit throughout.",
              },
              {
                num: "5",
                title: "Claim verified or challenged",
                desc: "Claims can be supported by verifiable credentials or challenged by other participants. The protocol records all claims, evidence, and outcomes transparently.",
              },
            ].map((step) => (
              <div key={step.num} className="rights-step">
                <div className="step-num">{step.num}</div>
                <div className="step-content">
                  <div className="step-title">{step.title}</div>
                  <div className="step-desc">{step.desc}</div>
                </div>
              </div>
            ))}

            {/* Provenance chain */}
            <div className="card" style={{ marginTop: "4px" }}>
              <div className="card-label">Cognitive provenance chain</div>
              <div style={{ fontSize: "12px", color: "var(--slate)", lineHeight: 1.8 }}>
                Every CBB, relationship, and reasoning path is traceable through its full lineage. The network can answer:
              </div>
              <div style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "6px" }}>
                {[
                  "Where did this knowledge originate?",
                  "Who contributed to its evolution?",
                  "Who validated it?",
                  "Who is entitled to attribution?",
                  "Who is entitled to rewards?",
                ].map((q) => (
                  <div key={q} style={{ display: "flex", gap: "8px", fontSize: "12px", color: "var(--slate)" }}>
                    <span style={{ color: "var(--indigo2)", flexShrink: 0 }}>→</span>
                    {q}
                  </div>
                ))}
              </div>
            </div>

            {/* Distinction table */}
            <div className="card">
              <div className="card-label">Key distinctions</div>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {[
                  { term: "Attribution", def: "Who contributed this CBB to the network — permanent, immutable." },
                  { term: "Contribution", def: "The act of publishing, curating, or validating a CBB." },
                  { term: "Ownership", def: "Legal rights to the underlying knowledge or source." },
                  { term: "Rights claim", def: "Assertion by a rights holder to reward eligibility for derived CBBs." },
                ].map((item) => (
                  <div key={item.term} style={{ display: "flex", gap: "12px", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--indigo2)", minWidth: "100px", flexShrink: 0 }}>{item.term}</div>
                    <div style={{ fontSize: "12px", color: "var(--slate)", lineHeight: 1.5 }}>{item.def}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right — Claim form + escrow */}
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>

            <div className="card" style={{ textAlign: "center", padding: "40px 24px" }}>
              <div style={{ fontSize: "11px", color: "var(--amber)", fontFamily: "var(--font-display)", fontWeight: 700, letterSpacing: "2px", textTransform: "uppercase", marginBottom: "16px", padding: "4px 12px", background: "rgba(245,158,11,0.1)", borderRadius: "4px", display: "inline-block" }}>
                Experimental · Coming Soon
              </div>
              <div style={{ fontSize: "36px", marginBottom: "16px", opacity: 0.4 }}>◈</div>
              <div style={{ fontFamily: "var(--font-display)", fontSize: "16px", fontWeight: 600, color: "var(--text)", marginBottom: "10px" }}>
                Rights Claims
              </div>
              <div style={{ fontSize: "13px", color: "var(--slate)", lineHeight: 1.7, maxWidth: "340px", margin: "0 auto 20px" }}>
                The rights claim system is under development. A verification methodology must be established before claims can be filed. The provenance chain and attribution framework are active — reward mechanics are coming in a future protocol version.
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxWidth: "300px", margin: "0 auto" }}>
                {[
                  "Claim submission · coming soon",
                  "Verification methodology · in design",
                  "Reward escrow · coming soon",
                  "Dispute resolution · future protocol",
                ].map(item => (
                  <div key={item} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "var(--slate2)" }}>
                    <span style={{ color: "var(--border2)" }}>○</span>
                    {item}
                  </div>
                ))}
              </div>
            </div>

            {/* Escrow */}
            <div className="card">
              <div className="card-label">Reward escrow</div>
              <div style={{ fontSize: "13px", color: "var(--slate)", lineHeight: 1.7, marginBottom: "14px" }}>
                When the original rights holder is unknown or unverified, rewards associated with third-party-derived CBBs are placed into escrow. Escrowed rewards remain associated with the attributed source until a valid claim is established.
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {[
                  { label: "Original contribution", status: "Participates immediately", color: "var(--emerald)" },
                  { label: "Third-party derived", status: "Rewards in escrow until claim", color: "var(--amber)" },
                  { label: "Verified rights claim", status: "Escrow released to rights holder", color: "var(--indigo2)" },
                  { label: "Disputed claim", status: "Held pending resolution", color: "var(--red)" },
                ].map((row) => (
                  <div key={row.label} style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px 12px",
                    background: "var(--bg3)",
                    borderRadius: "6px",
                    fontSize: "12px",
                  }}>
                    <span style={{ color: "var(--slate)" }}>{row.label}</span>
                    <span style={{ color: row.color, fontFamily: "var(--font-mono)", fontSize: "10px" }}>{row.status}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Claim & challenge */}
            <div className="card">
              <div className="card-label">Claim & challenge model</div>
              <div style={{ fontSize: "12px", color: "var(--slate)", lineHeight: 1.7 }}>
                Genesis adopts a claim-and-challenge model. Participants may submit rights claims. Claims may be challenged by other participants. Disputed claims remain unresolved until sufficient evidence is provided.
                <br /><br />
                The protocol does not adjudicate intellectual property law. It provides a transparent mechanism for recording claims, evidence, challenges, and outcomes — permanently and publicly.
              </div>
            </div>

          </div>
        </div>
      </div>
    </>
  );
}
