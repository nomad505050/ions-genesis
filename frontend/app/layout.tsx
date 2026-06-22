import type { Metadata } from "next";
import { Space_Grotesk, Inter, JetBrains_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["300", "400", "500", "600", "700"],
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["300", "400", "500"],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "IONS — Intelligence Operating Network System",
  description: "A protocol for cognitive composition at scale",
};

const NAV_ITEMS = [
  { href: "/",           icon: "⬡", label: "Explorer",  section: "Network" },
  { href: "/graph",      icon: "◎", label: "Graph",      section: "Network" },
  { href: "/contribute", icon: "+", label: "Add CBB",    section: "Contribute" },
  { href: "/workbench",  icon: "⚙", label: "Workbench",  section: "Contribute" },
  { href: "/rights",     icon: "◈", label: "Rights",     section: "Protocol" },
  { href: "/node",       icon: "◉", label: "Node",       section: "Protocol" },
  { href: "/settings",   icon: "◐", label: "Settings",   section: "Protocol" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${spaceGrotesk.variable} ${inter.variable} ${jetbrainsMono.variable}`}>
      <body>
        <div className="app">

          {/* SIDEBAR */}
          <aside className="sidebar">
            <div className="sidebar-logo">
              <span className="logo-mark">IONS</span>
              <span className="logo-sub">Intelligence Network</span>
            </div>

            <div className="sidebar-stats">
              <div className="stat-row">
                <span className="stat-label">CBBs</span>
                <span className="stat-value">
                  <span className="pulse" />
                  <span id="live-cbbs">—</span>
                </span>
              </div>

              <div className="stat-row">
                <span className="stat-label">NSIs</span>
                <span className="stat-value">
                  <span id="live-clusters">—</span>
                </span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Nodes</span>
                <span className="stat-value">
                  <span id="live-nodes">1</span>
                </span>
              </div>
            </div>

            <nav className="sidebar-nav">
              {["Network", "Contribute", "Protocol"].map((section) => (
                <div key={section}>
                  <div className="nav-section-label">{section}</div>
                  {NAV_ITEMS.filter((n) => n.section === section).map((item) => (
                    <Link key={item.href} href={item.href} className="nav-item">
                      <span className="nav-icon">{item.icon}</span>
                      <span>{item.label}</span>
                    </Link>
                  ))}
                  <div className="nav-divider" />
                </div>
              ))}
            </nav>

            <div className="sidebar-footer">
              <span className="version-tag">genesis v0.1</span> · open protocol
            </div>
          </aside>

          {/* MAIN */}
          <main className="main">
            {children}
          </main>

        </div>
      </body>
    </html>
  );
}

