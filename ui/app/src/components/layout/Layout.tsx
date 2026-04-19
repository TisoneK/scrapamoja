import { Link, useLocation } from "react-router-dom";
import { cn } from "../../utils";

interface LayoutProps { children: React.ReactNode; }

const NAV = [
  {
    href: "/studio", label: "Studio", match: ["/", "/studio"],
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3">
        <rect x="1.5" y="1.5" width="5.5" height="5.5" rx="1.2"/>
        <rect x="9" y="1.5" width="5.5" height="5.5" rx="1.2"/>
        <rect x="1.5" y="9" width="5.5" height="5.5" rx="1.2"/>
        <rect x="9" y="9" width="5.5" height="5.5" rx="1.2"/>
      </svg>
    ),
  },
  {
    href: "/runs", label: "Runs", match: ["/runs"],
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3">
        <circle cx="8" cy="8" r="6.5"/>
        <path d="M6 5.2l5 2.8-5 2.8V5.2z" fill="currentColor" stroke="none"/>
      </svg>
    ),
  },
  {
    href: "/results", label: "Results", match: ["/results"],
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3">
        <rect x="1.5" y="1.5" width="13" height="13" rx="1.5"/>
        <path d="M4 10l2.5-3.5L9 8.5 11.5 5"/>
      </svg>
    ),
  },
];

const SYSTEM_NAV = [
  {
    href: "/feature-flags", label: "Feature flags", match: ["/feature-flags"],
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3">
        <path d="M2.5 2.5v11M2.5 2.5h9l-2 3.5 2 3.5H2.5"/>
      </svg>
    ),
  },
  {
    href: "/escalation", label: "Failures", match: ["/escalation"],
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3">
        <path d="M8 1.5L14.5 14H1.5L8 1.5z"/>
        <line x1="8" y1="6" x2="8" y2="9.5"/>
        <circle cx="8" cy="11.5" r="0.7" fill="currentColor" stroke="none"/>
      </svg>
    ),
  },
  {
    href: "/audit-log", label: "Audit log", match: ["/audit-log"],
    icon: (
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3">
        <path d="M2 4h12M2 8h12M2 12h7"/>
      </svg>
    ),
  },
];

export function Layout({ children }: LayoutProps) {
  const { pathname } = useLocation();

  return (
    <div style={{ display:"flex", height:"100vh", background:"var(--bg-0)", overflow:"hidden" }}>
      {/* ── Sidebar ── */}
      <aside style={{
        width: 200, flexShrink: 0,
        background: "var(--bg-1)",
        borderRight: "1px solid var(--border-1)",
        display: "flex", flexDirection: "column",
        padding: "0",
      }}>
        {/* Brand */}
        <div style={{
          height: 48, display:"flex", alignItems:"center", gap: 10,
          padding: "0 14px",
          borderBottom: "1px solid var(--border-0)",
        }}>
          <div style={{
            width: 24, height: 24, background: "var(--accent)",
            borderRadius: 7, display:"flex", alignItems:"center", justifyContent:"center",
            flexShrink: 0,
          }}>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <circle cx="6" cy="6" r="4.5" stroke="white" strokeWidth="1.2"/>
              <line x1="6" y1="1.5" x2="6" y2="10.5" stroke="white" strokeWidth="1"/>
              <line x1="1.5" y1="6" x2="10.5" y2="6" stroke="white" strokeWidth="1"/>
            </svg>
          </div>
          <span style={{ fontSize: 13, fontWeight: 600, color:"var(--text-0)", letterSpacing:"0.01em" }}>
            scrapamoja
          </span>
        </div>

        {/* Main nav */}
        <nav style={{ padding: "10px 8px", flex: 1, display:"flex", flexDirection:"column", gap: 2 }}>
          <div style={{ fontSize:9, fontWeight:600, letterSpacing:"0.1em", textTransform:"uppercase",
            color:"var(--text-3)", padding:"0 6px", marginBottom: 4 }}>
            Workbench
          </div>
          {NAV.map(item => {
            const active = item.match.includes(pathname);
            return (
              <Link key={item.href} to={item.href} style={{ textDecoration:"none" }}>
                <div className={cn("nav-item", active && "active")}>
                  {item.icon}
                  {item.label}
                </div>
              </Link>
            );
          })}

          <div style={{ height: 1, background:"var(--border-0)", margin:"10px 6px 8px" }}/>
          <div style={{ fontSize:9, fontWeight:600, letterSpacing:"0.1em", textTransform:"uppercase",
            color:"var(--text-3)", padding:"0 6px", marginBottom: 4 }}>
            System
          </div>
          {SYSTEM_NAV.map(item => {
            const active = item.match.includes(pathname);
            return (
              <Link key={item.href} to={item.href} style={{ textDecoration:"none" }}>
                <div className={cn("nav-item", active && "active")}>
                  {item.icon}
                  {item.label}
                </div>
              </Link>
            );
          })}
        </nav>

        {/* Status bar */}
        <div style={{
          padding:"8px 14px", borderTop:"1px solid var(--border-0)",
          display:"flex", alignItems:"center", gap: 6,
        }}>
          <div style={{ width:6, height:6, borderRadius:"50%", background:"var(--green)", flexShrink:0 }}
               className="pulse"/>
          <span style={{ fontSize:10, color:"var(--text-2)" }}>v1.1.0 · connected</span>
        </div>
      </aside>

      {/* ── Main ── */}
      <main style={{ flex:1, overflow:"hidden", display:"flex", flexDirection:"column" }}>
        {children}
      </main>
    </div>
  );
}
