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
    <div style={{ display:"flex", height:"100vh", overflow:"hidden",
      background:"#111318", fontFamily:"system-ui, sans-serif" }}>

      {/* ── Sidebar — noticeably darker than content ── */}
      <aside style={{ width:220, flexShrink:0,
        background:"#08090c",           /* near-black, clearly distinct */
        borderRight:"1px solid #1e2028",
        display:"flex", flexDirection:"column" }}>

        {/* Brand */}
        <div style={{ height:52, display:"flex", alignItems:"center", gap:10,
          padding:"0 16px", borderBottom:"1px solid #1a1b22" }}>
          <div style={{ width:28, height:28, background:"#4f46e5", borderRadius:8,
            display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
            <Zap style={{ width:14, height:14, color:"white" }}/>
          </div>
          <div>
            <p style={{ color:"#e2e2e8", fontWeight:600, fontSize:13, lineHeight:1.3, margin:0 }}>Scrapamoja</p>
            <p style={{ color:"#454554", fontSize:11, margin:0 }}>Desktop</p>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex:1, padding:"12px 8px", display:"flex", flexDirection:"column",
          gap:1, overflowY:"auto" }}>
          <p style={{ fontSize:9, fontWeight:700, color:"#2e2e3a", letterSpacing:"0.12em",
            textTransform:"uppercase", padding:"0 8px 6px", margin:0 }}>Workbench</p>

          {workbenchNav.map(item => {
            const active = item.match.includes(pathname);
            const Icon = item.icon;
            return (
              <Link key={item.href} to={item.href} style={{ textDecoration:"none" }}>
                <div style={{ display:"flex", alignItems:"center", gap:9, padding:"7px 10px",
                  borderRadius:7, fontSize:12, fontWeight:500, cursor:"pointer",
                  transition:"all 0.12s",
                  background: active ? "#1a1a2e" : "transparent",
                  color: active ? "#818cf8" : "#4a4a5e",
                  border:`1px solid ${active ? "#2d2b5a" : "transparent"}` }}>
                  <Icon style={{ width:15, height:15, flexShrink:0 }}/>
                  {item.name}
                </div>
              </Link>
            );
          })}

          <div style={{ height:1, background:"#14151c", margin:"8px 4px" }}/>
          <p style={{ fontSize:9, fontWeight:700, color:"#2e2e3a", letterSpacing:"0.12em",
            textTransform:"uppercase", padding:"0 8px 6px", margin:0 }}>System</p>

          {adminNav.map(item => {
            const active = item.match.includes(pathname);
            const Icon = item.icon;
            return (
              <Link key={item.href} to={item.href} style={{ textDecoration:"none" }}>
                <div style={{ display:"flex", alignItems:"center", gap:9, padding:"7px 10px",
                  borderRadius:7, fontSize:12, fontWeight:500, cursor:"pointer",
                  transition:"all 0.12s",
                  background: active ? "#1a1a2e" : "transparent",
                  color: active ? "#818cf8" : "#4a4a5e",
                  border:`1px solid ${active ? "#2d2b5a" : "transparent"}` }}
                  onMouseEnter={e => { if(!active)(e.currentTarget as HTMLElement).style.background="#111218"; (e.currentTarget as HTMLElement).style.color="#7070a0"; }}
                  onMouseLeave={e => { if(!active)(e.currentTarget as HTMLElement).style.background="transparent"; (e.currentTarget as HTMLElement).style.color="#4a4a5e"; }}>
                  <Icon style={{ width:15, height:15, flexShrink:0 }}/>
                  {item.name}
                </div>
              </Link>
            );
          })}
        </nav>

        {/* User */}
        <div style={{ padding:"10px 12px", borderTop:"1px solid #1a1b22" }}>
          <div style={{ display:"flex", alignItems:"center", gap:10, padding:"6px 8px" }}>
            <div style={{ width:28, height:28, borderRadius:"50%", background:"#151525",
              display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0,
              border:"1px solid #2d2b5a" }}>
              <User style={{ width:14, height:14, color:"#818cf8" }}/>
            </div>
            <div>
              <p style={{ color:"#c8c8d8", fontSize:12, fontWeight:500, margin:0, lineHeight:1.3 }}>System Admin</p>
              <p style={{ color:"#3a3a4e", fontSize:11, margin:0 }}>Administrator</p>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Main content ── */}
      <div style={{ flex:1, display:"flex", flexDirection:"column", minWidth:0, overflow:"hidden" }}>

        {/* Topbar — only for non-fullbleed (admin) pages */}
        {!isFullBleed && (
          <header style={{ height:52, background:"#0e0f14",
            borderBottom:"1px solid #1e2028",
            padding:"0 24px", display:"flex", alignItems:"center",
            justifyContent:"space-between", flexShrink:0 }}>
            <div style={{ display:"flex", alignItems:"center", gap:8, fontSize:13 }}>
              <span style={{ color:"#333344" }}>Scrapamoja</span>
              <span style={{ color:"#2a2a38" }}>/</span>
              <span style={{ color:"#d4d4e0", fontWeight:600 }}>{current?.name ?? "Dashboard"}</span>
            </div>
            <span style={{ display:"inline-flex", alignItems:"center", gap:6, fontSize:11,
              color:"#555566", background:"#111318", border:"1px solid #1e2028",
              borderRadius:20, padding:"3px 12px" }}>
              <span style={{ width:6, height:6, borderRadius:"50%", background:"#EF9F27",
                display:"inline-block" }}/>
              API Offline
            </span>
          </header>
        )}

        <main style={{ flex:1, overflow:"hidden", background:"#111318" }}>
          {isFullBleed
            ? <div style={{ height:"100%", display:"flex", flexDirection:"column" }}>{children}</div>
            : <div style={{ height:"100%", overflowY:"auto", padding:24 }}>{children}</div>}
        </main>
      </div>
    </div>
  );
}
