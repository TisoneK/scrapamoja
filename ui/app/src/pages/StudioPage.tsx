import { useState } from "react";
import { useStudioStore } from "../store/studioStore";
import { EntityRail } from "../components/studio/EntityRail";
import { BrowserCanvas } from "../components/studio/BrowserCanvas";
import { SelectorPanel } from "../components/studio/SelectorPanel";
import { ConfidenceHeatmap } from "../components/studio/ConfidenceHeatmap";

const D = {
  bg0: "#0d0c11", bg1: "#13121a", bg2: "#1a1920", bg3: "#21202b",
  border0: "rgba(255,255,255,0.05)", border1: "rgba(255,255,255,0.09)",
  text0: "#e8e6f0", text1: "#9f9bc4", text2: "#5f5d7a", text3: "#3a3850",
  accent: "#6366f1", accentBg: "#1e1c2e", accentBorder: "#3d3775",
  green: "#1D9E75", amber: "#EF9F27", red: "#E24B4A",
};

export function StudioPage() {
  const { config, mode, setMode } = useStudioStore();
  const [panelOpen, setPanelOpen] = useState(true);

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%", overflow:"hidden",
      background: D.bg0, fontFamily:"system-ui, sans-serif", color: D.text0 }}>

      {/* ── Topbar ── */}
      <div style={{ height:50, background: D.bg1, borderBottom:`1px solid ${D.border1}`,
        display:"flex", alignItems:"center", padding:"0 16px", gap:12, flexShrink:0 }}>

        {/* Breadcrumb */}
        <span style={{ fontSize:13, color: D.text2 }}>Scrapamoja</span>
        <span style={{ color: D.text3 }}>/</span>
        <span style={{ fontSize:13, fontWeight:600, color: D.text0 }}>Studio</span>

        <div style={{ width:1, height:18, background: D.border1, margin:"0 4px" }} />

        <span style={{ fontSize:12, color: D.text1 }}>{config?.name ?? "No project"}</span>

        {/* URL pill */}
        <div style={{ display:"flex", alignItems:"center", gap:6, background: D.bg3,
          border:`1px solid ${D.border1}`, borderRadius:20, padding:"3px 10px" }}>
          <div style={{ width:6, height:6, borderRadius:"50%", background: D.amber }} />
          <span style={{ fontSize:11, color: D.text2, fontFamily:"monospace" }}>
            {config?.target_url?.replace("https://","") ?? ""}
          </span>
        </div>

        <div style={{ flex:1 }} />

        {/* Visual / Expert */}
        <div style={{ display:"flex", background: D.bg0, border:`1px solid ${D.border1}`,
          borderRadius:8, padding:3, gap:2 }}>
          {(["Visual","Expert"] as const).map(m => {
            const active = mode === m.toLowerCase();
            return (
              <button key={m} onClick={() => setMode(m.toLowerCase() as "visual"|"expert")}
                style={{ padding:"5px 14px", fontSize:12, fontWeight:500,
                  borderRadius:6, border:"none", cursor:"pointer",
                  background: active ? D.accent : "transparent",
                  color: active ? "white" : D.text2,
                  transition:"all 0.15s" }}>
                {m}
              </button>
            );
          })}
        </div>

        <button style={{ padding:"7px 13px", fontSize:12, fontWeight:500,
          border:`1px solid ${D.border1}`, borderRadius:8,
          background:"transparent", color: D.text1, cursor:"pointer",
          display:"flex", alignItems:"center", gap:6 }}>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <line x1="6" y1="1" x2="6" y2="11" stroke={D.text1} strokeWidth="1.4" strokeLinecap="round"/>
            <line x1="1" y1="6" x2="11" y2="6" stroke={D.text1} strokeWidth="1.4" strokeLinecap="round"/>
          </svg>
          Add Entity
        </button>

        <button style={{ padding:"7px 13px", fontSize:12, fontWeight:500,
          border:"1px solid rgba(226,75,74,0.3)", borderRadius:8,
          background:"rgba(226,75,74,0.08)", color: D.red, cursor:"pointer" }}>
          Stop
        </button>

        <button style={{ padding:"7px 16px", fontSize:12, fontWeight:600,
          border:"none", borderRadius:8,
          background: D.accent, color:"white", cursor:"pointer",
          display:"flex", alignItems:"center", gap:6 }}>
          <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
            <path d="M2.5 1.5l7 4-7 4V1.5z" fill="white"/>
          </svg>
          Run Scrape
        </button>
      </div>

      {/* ── Workspace ── */}
      <div style={{ flex:1, display:"grid",
        gridTemplateColumns:`220px 1fr ${panelOpen ? "320px" : "0"}`,
        gridTemplateRows:"1fr auto", overflow:"hidden",
        transition:"grid-template-columns 0.2s ease" }}>

        {/* Left rail */}
        <div style={{ gridRow:"1/3", background: D.bg1,
          borderRight:`1px solid ${D.border1}`,
          overflow:"hidden", display:"flex", flexDirection:"column" }}>
          <EntityRail />
        </div>

        {/* Browser canvas */}
        <div style={{ gridRow:1, overflow:"hidden", background: D.bg0 }}>
          <BrowserCanvas />
        </div>

        {/* Right panel */}
        {panelOpen && (
          <div style={{ gridRow:"1/3", background: D.bg1,
            borderLeft:`1px solid ${D.border1}`,
            overflow:"hidden", display:"flex", flexDirection:"column" }}>
            <div style={{ height:48, padding:"0 16px", borderBottom:`1px solid ${D.border0}`,
              display:"flex", alignItems:"center", justifyContent:"space-between", flexShrink:0 }}>
              <span style={{ fontSize:13, fontWeight:600, color: D.text0 }}>Extraction Details</span>
              <button onClick={() => setPanelOpen(false)}
                style={{ border:"none", background:"none", cursor:"pointer",
                  color: D.text2, fontSize:18, lineHeight:1, padding:"2px 6px",
                  borderRadius:4 }}>×</button>
            </div>
            <div style={{ flex:1, overflow:"hidden" }}>
              <SelectorPanel />
            </div>
          </div>
        )}

        {/* Heatmap */}
        <div style={{ gridRow:2, gridColumn:2 }}>
          <ConfidenceHeatmap />
        </div>
      </div>

      {!panelOpen && (
        <button onClick={() => setPanelOpen(true)}
          style={{ position:"fixed", right:0, top:"50%", transform:"translateY(-50%)",
            background: D.accent, color:"white", border:"none",
            borderRadius:"8px 0 0 8px", padding:"14px 7px", cursor:"pointer",
            fontSize:11, writingMode:"vertical-rl", letterSpacing:"0.06em", fontWeight:500 }}>
          Details
        </button>
      )}
    </div>
  );
}
