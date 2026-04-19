import { Link, useLocation } from "react-router-dom";
import { Flag, AlertTriangle, ScrollText, Zap, User, LayoutGrid, Play, BarChart2 } from "lucide-react";
import { cn } from "@/utils";

const FULLBLEED = ["/studio", "/", "/runs", "/results"];

const workbenchNav = [
  { name:"Studio",  href:"/studio",  icon:LayoutGrid, match:["/studio","/"] },
  { name:"Runs",    href:"/runs",    icon:Play,        match:["/runs"] },
  { name:"Results", href:"/results", icon:BarChart2,   match:["/results"] },
];
const adminNav = [
  { name:"Feature Flags", href:"/feature-flags", icon:Flag,          match:["/feature-flags"] },
  { name:"Escalation",    href:"/escalation",    icon:AlertTriangle, match:["/escalation"] },
  { name:"Audit Log",     href:"/audit-log",     icon:ScrollText,    match:["/audit-log"] },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();
  const allNav = [...workbenchNav, ...adminNav];
  const current = allNav.find(n => n.match.includes(pathname));
  const isFullBleed = FULLBLEED.includes(pathname);

  return (
    <div className="flex h-screen overflow-hidden" style={{ background:"#0d0c11", fontFamily:"system-ui, sans-serif" }}>

      {/* ── Sidebar ── */}
      <aside style={{ width:220, flexShrink:0, background:"#13121a",
        borderRight:"1px solid rgba(255,255,255,0.09)",
        display:"flex", flexDirection:"column" }}>

        {/* Brand */}
        <div style={{ height:50, display:"flex", alignItems:"center", gap:10,
          padding:"0 16px", borderBottom:"1px solid rgba(255,255,255,0.05)" }}>
          <div style={{ width:26, height:26, background:"#6366f1", borderRadius:7,
            display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
            <Zap style={{ width:13, height:13, color:"white" }}/>
          </div>
          <div>
            <p style={{ color:"#e8e6f0", fontWeight:600, fontSize:13, lineHeight:1.2 }}>Scrapamoja</p>
            <p style={{ color:"#5f5d7a", fontSize:11 }}>Desktop</p>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex:1, padding:"10px 8px", overflowY:"auto", display:"flex", flexDirection:"column", gap:2 }}>
          <p style={{ fontSize:9, fontWeight:600, color:"#3a3850", letterSpacing:"0.1em",
            textTransform:"uppercase", padding:"0 8px", marginBottom:4 }}>Workbench</p>
          {workbenchNav.map(item => {
            const active = item.match.includes(pathname);
            const Icon = item.icon;
            return (
              <Link key={item.href} to={item.href} style={{ textDecoration:"none" }}>
                <div style={{ display:"flex", alignItems:"center", gap:10, padding:"7px 10px",
                  borderRadius:8, cursor:"pointer", fontSize:12, fontWeight:500,
                  transition:"all 0.12s",
                  background: active ? "#1e1c2e" : "transparent",
                  color: active ? "#a5b4fc" : "#5f5d7a",
                  border: `1px solid ${active ? "#3d3775" : "transparent"}` }}>
                  <Icon style={{ width:15, height:15, flexShrink:0 }}/>
                  {item.name}
                </div>
              </Link>
            );
          })}

          <div style={{ height:1, background:"rgba(255,255,255,0.05)", margin:"8px 6px" }}/>
          <p style={{ fontSize:9, fontWeight:600, color:"#3a3850", letterSpacing:"0.1em",
            textTransform:"uppercase", padding:"0 8px", marginBottom:4 }}>System</p>
          {adminNav.map(item => {
            const active = item.match.includes(pathname);
            const Icon = item.icon;
            return (
              <Link key={item.href} to={item.href} style={{ textDecoration:"none" }}>
                <div style={{ display:"flex", alignItems:"center", gap:10, padding:"7px 10px",
                  borderRadius:8, cursor:"pointer", fontSize:12, fontWeight:500,
                  transition:"all 0.12s",
                  background: active ? "#1e1c2e" : "transparent",
                  color: active ? "#a5b4fc" : "#5f5d7a",
                  border: `1px solid ${active ? "#3d3775" : "transparent"}` }}>
                  <Icon style={{ width:15, height:15, flexShrink:0 }}/>
                  {item.name}
                </div>
              </Link>
            );
          })}
        </nav>

        {/* User */}
        <div style={{ padding:"10px 12px", borderTop:"1px solid rgba(255,255,255,0.05)" }}>
          <div style={{ display:"flex", alignItems:"center", gap:10, padding:"6px 8px" }}>
            <div style={{ width:26, height:26, borderRadius:"50%", background:"#1e1c2e",
              display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0,
              border:"1px solid #3d3775" }}>
              <User style={{ width:13, height:13, color:"#a5b4fc" }}/>
            </div>
            <div style={{ minWidth:0 }}>
              <p style={{ color:"#c8c4d8", fontSize:12, fontWeight:500, lineHeight:1.2 }}>System Admin</p>
              <p style={{ color:"#3a3850", fontSize:11 }}>Administrator</p>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Main ── */}
      <div style={{ flex:1, display:"flex", flexDirection:"column", minWidth:0, overflow:"hidden" }}>
        {/* Topbar — shown for admin pages */}
        {!isFullBleed && (
          <header style={{ height:50, background:"#13121a",
            borderBottom:"1px solid rgba(255,255,255,0.09)",
            padding:"0 24px", display:"flex", alignItems:"center",
            justifyContent:"space-between", flexShrink:0 }}>
            <div style={{ display:"flex", alignItems:"center", gap:8, fontSize:13 }}>
              <span style={{ color:"#3a3850" }}>Scrapamoja</span>
              <span style={{ color:"#3a3850" }}>/</span>
              <span style={{ color:"#e8e6f0", fontWeight:600 }}>{current?.name ?? "Dashboard"}</span>
            </div>
            <span style={{ display:"inline-flex", alignItems:"center", gap:6, fontSize:11,
              color:"#5f5d7a", background:"#1a1920", border:"1px solid rgba(255,255,255,0.09)",
              borderRadius:20, padding:"3px 10px" }}>
              <span style={{ width:6, height:6, borderRadius:"50%", background:"#EF9F27",
                animation:"pulse-dot 1.4s ease-in-out infinite" }}/>
              API Offline
            </span>
          </header>
        )}

        <main style={{ flex:1, overflow:"hidden" }}>
          {isFullBleed ? (
            <div style={{ height:"100%", display:"flex", flexDirection:"column" }}>{children}</div>
          ) : (
            <div style={{ height:"100%", overflowY:"auto", padding:24 }}>{children}</div>
          )}
        </main>
      </div>
    </div>
  );
}
