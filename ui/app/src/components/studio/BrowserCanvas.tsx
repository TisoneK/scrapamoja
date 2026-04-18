import { useStudioStore } from "../../store/studioStore";

// Simulated page content matching Flashscore basketball
// In Electron, this will be replaced with a <webview> tag pointing to the real URL

const DEMO_MATCHES = [
  { home:"Boston Celtics",   away:"LA Lakers",            score:"88–74", time:"Q3 28'", live:true  },
  { home:"Golden State",     away:"Miami Heat",            score:"41–39", time:"Q2 14'", live:true  },
  { home:"Chicago Bulls",    away:"NY Knicks",             score:"—",     time:"21:30",  live:false },
  { home:"Dallas Mavericks", away:"Phoenix Suns",          score:"—",     time:"22:00",  live:false },
];

export function BrowserCanvas() {
  const { config, activeEntityId, mode } = useStudioStore();
  const activeEntity = config?.entities.find(e => e.id === activeEntityId);

  return (
    <div style={{ height:"100%", display:"flex", flexDirection:"column", background:"var(--bg-0)" }}>
      {/* Browser chrome */}
      <div style={{ height:32, background:"var(--bg-2)", borderBottom:"1px solid var(--border-1)",
        display:"flex", alignItems:"center", padding:"0 10px", gap:8, flexShrink:0 }}>
        <div style={{ display:"flex", gap:4 }}>
          {["#E24B4A","#EF9F27","#1D9E75"].map(c => (
            <div key={c} style={{ width:8, height:8, borderRadius:"50%", background:c }}/>
          ))}
        </div>
        <div style={{ flex:1, background:"var(--bg-0)", border:"1px solid var(--border-1)",
          borderRadius:5, padding:"3px 10px", fontSize:10,
          color:"var(--text-3)", fontFamily:"var(--font-mono)" }}>
          {config?.target_url ?? "https://…"}
        </div>
        <span style={{ fontSize:9, color:"var(--text-3)" }}>
          {mode === "visual" ? "hover to inspect" : "expert mode"}
        </span>
      </div>

      {/* Simulated page */}
      <div style={{ flex:1, overflowY:"auto", padding:16, position:"relative" }}>

        {/* Page nav */}
        <div style={{ background:"var(--bg-2)", borderRadius:6, padding:"6px 14px",
          marginBottom:12, display:"flex", gap:16, border:"1px solid var(--border-1)" }}>
          {["Live","Finished","Scheduled","NBA","EuroLeague"].map((t, i) => (
            <span key={t} style={{ fontSize:10, color: i === 0 ? "var(--text-0)" : "var(--text-3)",
              fontWeight: i === 0 ? 600 : 400, cursor:"pointer" }}>
              {t}
            </span>
          ))}
        </div>

        {/* Match rows */}
        {DEMO_MATCHES.map((m, i) => {
          const isSelected = activeEntity?.name === "match_card" && i === 0;
          return (
            <div key={i} style={{
              background: isSelected ? "rgba(127,119,221,0.08)" : "var(--bg-2)",
              border: `1px solid ${isSelected ? "var(--accent)" : "var(--border-1)"}`,
              borderRadius:8, padding:"10px 14px", marginBottom:6,
              display:"flex", alignItems:"center", gap:12,
              cursor:"pointer", position:"relative",
              transition:"all 0.15s",
            }}>
              {/* Selection badge */}
              {isSelected && (
                <div style={{
                  position:"absolute", top:-9, left:10,
                  background:"var(--accent)", color:"white",
                  fontSize:9, fontWeight:600, padding:"1px 7px", borderRadius:4,
                  fontFamily:"var(--font-ui)",
                }}>
                  match_card · {activeEntity?.strategies[0]?.confidence.toFixed(2)}
                </div>
              )}
              {/* Purple highlight ring */}
              {isSelected && (
                <div style={{
                  position:"absolute", inset:-2, borderRadius:9,
                  border:"1.5px solid var(--accent)", pointerEvents:"none",
                }}/>
              )}

              <span style={{ fontSize:10, color: m.live ? "var(--green)" : "var(--text-3)",
                fontFamily:"var(--font-mono)", width:40, flexShrink:0 }}>
                {m.time}
              </span>

              <div style={{ flex:1 }}>
                <div style={{ fontSize:12, color:"var(--text-0)", marginBottom:2 }}>{m.home}</div>
                <div style={{ fontSize:12, color:"var(--text-1)" }}>{m.away}</div>
              </div>

              <div style={{ fontSize:14, fontWeight:600, color:"var(--text-0)",
                fontFamily:"var(--font-mono)", width:44, textAlign:"center" }}>
                {m.score === "—" ? <span style={{ color:"var(--text-3)" }}>–</span> : m.score}
              </div>

              {m.live ? (
                <span style={{ fontSize:9, fontWeight:600, padding:"2px 7px",
                  background:"var(--green-bg)", color:"var(--green)",
                  border:"1px solid rgba(29,158,117,.3)", borderRadius:4 }}>
                  LIVE
                </span>
              ) : (
                <span style={{ fontSize:9, fontWeight:600, padding:"2px 7px",
                  background:"var(--blue-bg)", color:"var(--blue)",
                  border:"1px solid rgba(55,138,221,.25)", borderRadius:4 }}>
                  SCH
                </span>
              )}
            </div>
          );
        })}

        <div style={{ fontSize:9, color:"var(--text-3)", textAlign:"right", marginTop:6,
          fontFamily:"var(--font-mono)" }}>
          {activeEntity?.matches_found ?? 0} matches · selector active
        </div>

        {/* Click hint */}
        <div style={{
          position:"sticky", bottom:12, left:"50%", transform:"translateX(-50%)",
          background:"rgba(0,0,0,0.75)", color:"var(--text-0)",
          fontSize:11, padding:"5px 14px", borderRadius:20,
          width:"fit-content", margin:"0 auto", backdropFilter:"blur(8px)",
          border:"1px solid var(--border-2)",
        }}>
          {mode === "visual"
            ? "Click any element to capture selector"
            : "Expert mode — edit YAML directly"}
        </div>
      </div>
    </div>
  );
}
