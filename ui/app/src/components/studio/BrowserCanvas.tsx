import { useStudioStore } from "../../store/studioStore";

const D = {
  bg0:"#0e0f14", bg2:"#171820", bg3:"#1c1d27",
  border0:"#1a1b22", border1:"#22232e",
  text0:"#e2e2e8", text1:"#a0a0b4", text2:"#565668", text3:"#32333e",
  accent:"#4f46e5", green:"#1D9E75", greenBg:"#0a2018", greenBorder:"rgba(29,158,117,0.25)",
  blue:"#378ADD", blueBg:"#081828", blueBorder:"rgba(55,138,221,0.25)",
  amber:"#EF9F27",
};

const DEMO_MATCHES = [
  { home:"Boston Celtics",    away:"LA Lakers",        score:"88–74", time:"Q3 28'", live:true  },
  { home:"Golden State",      away:"Miami Heat",        score:"41–39", time:"Q2 14'", live:true  },
  { home:"Chicago Bulls",     away:"NY Knicks",         score:"—",     time:"21:30",  live:false },
  { home:"Dallas Mavericks",  away:"Phoenix Suns",      score:"—",     time:"22:00",  live:false },
];

export function BrowserCanvas() {
  const { config, activeEntityId, mode } = useStudioStore();
  const activeEntity = config?.entities.find(e => e.id === activeEntityId);

  return (
    <div style={{ height:"100%", display:"flex", flexDirection:"column", background: D.bg0 }}>
      {/* Browser chrome */}
      <div style={{ height:32, background: D.bg2, borderBottom:`1px solid ${D.border1}`,
        display:"flex", alignItems:"center", padding:"0 10px", gap:8, flexShrink:0 }}>
        <div style={{ display:"flex", gap:4 }}>
          {["#E24B4A","#EF9F27","#1D9E75"].map(c => (
            <div key={c} style={{ width:8, height:8, borderRadius:"50%", background:c }} />
          ))}
        </div>
        <div style={{ flex:1, background: D.bg0, border:`1px solid ${D.border0}`,
          borderRadius:5, padding:"3px 10px", fontSize:10, color: D.text3, fontFamily:"monospace" }}>
          {config?.target_url ?? "https://…"}
        </div>
        <span style={{ fontSize:9, color: D.text3 }}>
          {mode==="visual" ? "hover to inspect" : "expert mode"}
        </span>
      </div>

      {/* Page */}
      <div style={{ flex:1, overflowY:"auto", padding:16 }}>
        {/* Nav bar */}
        <div style={{ background: D.bg2, borderRadius:6, padding:"6px 14px",
          marginBottom:12, display:"flex", gap:16, border:`1px solid ${D.border0}` }}>
          {["Live","Finished","Scheduled","NBA","EuroLeague"].map((t,i) => (
            <span key={t} style={{ fontSize:10, cursor:"pointer",
              color: i===0 ? D.text0 : D.text3, fontWeight: i===0 ? 600 : 400 }}>{t}</span>
          ))}
        </div>

        {/* Matches */}
        {DEMO_MATCHES.map((m,i) => {
          const isSelected = activeEntity?.name==="match_card" && i===0;
          return (
            <div key={i} style={{ background: isSelected ? "rgba(99,102,241,0.07)" : D.bg2,
              border:`1px solid ${isSelected ? D.accent : D.border0}`,
              borderRadius:8, padding:"10px 14px", marginBottom:6,
              display:"flex", alignItems:"center", gap:12, cursor:"pointer", position:"relative",
              transition:"all 0.15s",
              boxShadow: isSelected ? "0 0 0 3px rgba(99,102,241,0.1)" : "none" }}>
              {isSelected && (
                <>
                  <div style={{ position:"absolute", top:-9, left:10,
                    background: D.accent, color:"white",
                    fontSize:9, fontWeight:600, padding:"1px 7px", borderRadius:4 }}>
                    match_card · {activeEntity?.strategies[0]?.confidence.toFixed(2)}
                  </div>
                  <div style={{ position:"absolute", inset:-2, borderRadius:9,
                    border:`1.5px solid ${D.accent}`, pointerEvents:"none" }} />
                </>
              )}
              <span style={{ fontSize:10, color: m.live ? D.green : D.text3,
                fontFamily:"monospace", width:40, flexShrink:0 }}>{m.time}</span>
              <div style={{ flex:1 }}>
                <div style={{ fontSize:12, color: D.text0, marginBottom:2 }}>{m.home}</div>
                <div style={{ fontSize:12, color: D.text1 }}>{m.away}</div>
              </div>
              <div style={{ fontSize:14, fontWeight:600, color: D.text0,
                fontFamily:"monospace", width:44, textAlign:"center" }}>
                {m.score==="—" ? <span style={{ color: D.text3 }}>–</span> : m.score}
              </div>
              {m.live
                ? <span style={{ fontSize:9, fontWeight:600, padding:"2px 7px",
                    background: D.greenBg, color: D.green,
                    border:`1px solid ${D.greenBorder}`, borderRadius:4 }}>LIVE</span>
                : <span style={{ fontSize:9, fontWeight:600, padding:"2px 7px",
                    background: D.blueBg, color: D.blue,
                    border:`1px solid ${D.blueBorder}`, borderRadius:4 }}>SCH</span>}
            </div>
          );
        })}

        <div style={{ fontSize:9, color: D.text3, textAlign:"right", marginTop:6,
          fontFamily:"monospace" }}>
          {activeEntity?.matches_found ?? 0} matches · selector active
        </div>

        <div style={{ position:"sticky", bottom:12, left:"50%", transform:"translateX(-50%)",
          background:"rgba(0,0,0,0.75)", color: D.text0,
          fontSize:11, padding:"5px 14px", borderRadius:20,
          width:"fit-content", margin:"0 auto",
          backdropFilter:"blur(8px)", border:`1px solid ${D.border1}` }}>
          {mode==="visual" ? "Click any element to capture selector" : "Expert mode — edit YAML directly"}
        </div>
      </div>
    </div>
  );
}
