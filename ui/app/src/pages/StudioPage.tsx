import { useStudioStore } from "../store/studioStore";
import { EntityRail } from "../components/studio/EntityRail";
import { BrowserCanvas } from "../components/studio/BrowserCanvas";
import { SelectorPanel } from "../components/studio/SelectorPanel";
import { ConfidenceHeatmap } from "../components/studio/ConfidenceHeatmap";

export function StudioPage() {
  const { config, mode, setMode } = useStudioStore();

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%", overflow:"hidden" }}>
      {/* Top bar */}
      <div style={{ height:44, background:"var(--bg-1)", borderBottom:"1px solid var(--border-1)",
        display:"flex", alignItems:"center", padding:"0 16px", gap:12, flexShrink:0 }}>
        <span style={{ fontSize:11, fontWeight:600, color:"var(--text-2)",
          letterSpacing:"0.08em", textTransform:"uppercase" }}>
          Studio
        </span>
        <span style={{ fontSize:12, color:"var(--text-1)", fontWeight:500 }}>
          {config?.name ?? "No project"}
        </span>
        <div style={{ fontSize:10, color:"var(--text-3)", fontFamily:"var(--font-mono)",
          background:"var(--bg-3)", padding:"2px 8px", borderRadius:5,
          border:"1px solid var(--border-1)" }}>
          {config?.target_url}
        </div>

        {/* Mode toggle */}
        <div style={{ display:"flex", background:"var(--bg-0)", border:"1px solid var(--border-1)",
          borderRadius:6, padding:2, gap:2 }}>
          {(["visual","expert"] as const).map(m => (
            <button key={m} onClick={() => setMode(m)}
              style={{
                padding:"3px 12px", fontSize:10, fontWeight:500,
                borderRadius:4, border:"none", cursor:"pointer",
                fontFamily:"var(--font-ui)", letterSpacing:"0.03em",
                background: mode === m ? "var(--accent)" : "transparent",
                color: mode === m ? "white" : "var(--text-2)",
                transition:"all 0.12s",
              }}>
              {m.charAt(0).toUpperCase() + m.slice(1)}
            </button>
          ))}
        </div>

        <div style={{ marginLeft:"auto", display:"flex", gap:8 }}>
          <button className="btn btn-sm">+ Add entity</button>
          <button className="btn btn-sm btn-danger">Stop</button>
          <button className="btn btn-sm btn-primary">Run scrape</button>
        </div>
      </div>

      {/* 4-quadrant workspace */}
      <div style={{ flex:1, display:"grid",
        gridTemplateColumns:"200px 1fr 260px",
        gridTemplateRows:"1fr auto",
        overflow:"hidden" }}>

        {/* Left rail — entities + schema */}
        <div style={{ gridRow:"1/3", background:"var(--bg-1)",
          borderRight:"1px solid var(--border-1)", overflow:"hidden",
          display:"flex", flexDirection:"column" }}>
          <EntityRail/>
        </div>

        {/* Browser canvas */}
        <div style={{ gridRow:1, overflow:"hidden" }}>
          <BrowserCanvas/>
        </div>

        {/* Selector intelligence panel */}
        <div style={{ gridRow:"1/3", background:"var(--bg-1)",
          borderLeft:"1px solid var(--border-1)", overflow:"hidden" }}>
          <SelectorPanel/>
        </div>

        {/* Confidence heatmap — bottom bar */}
        <div style={{ gridRow:2, gridColumn:2 }}>
          <ConfidenceHeatmap/>
        </div>
      </div>
    </div>
  );
}
