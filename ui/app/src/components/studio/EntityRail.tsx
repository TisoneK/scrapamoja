import { useStudioStore } from "../../store/studioStore";

const D = {
  bg0:"#0e0f14", bg1:"#111318", bg2:"#171820", bg3:"#1c1d27",
  border0:"#1a1b22", border1:"#22232e",
  text0:"#e2e2e8", text1:"#a0a0b4", text2:"#565668", text3:"#32333e",
  accent:"#4f46e5", accentBg:"#15152a", accentBorder:"#2d2b5a",
  green:"#1D9E75", amber:"#EF9F27", red:"#E24B4A",
};

const maxConf = (e: { strategies: { confidence: number }[] }) =>
  e.strategies.length ? Math.max(...e.strategies.map(s => s.confidence)) : 0;

function ConfDot({ conf }: { conf: number }) {
  const c = conf >= 0.80 ? D.green : conf >= 0.60 ? D.amber : D.red;
  return <div style={{ width:7, height:7, borderRadius:"50%", background:c, flexShrink:0 }} />;
}

function MiniBar({ conf }: { conf: number }) {
  const fg = conf >= 0.80 ? D.green : conf >= 0.60 ? D.amber : D.red;
  return (
    <div style={{ height:3, borderRadius:2, background:"rgba(255,255,255,0.06)", overflow:"hidden", width:"100%" }}>
      <div style={{ height:"100%", width:`${Math.round(conf*100)}%`, background:fg, borderRadius:2 }} />
    </div>
  );
}

export function EntityRail() {
  const { config, activeEntityId, setActiveEntityId } = useStudioStore();
  if (!config) return null;

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%", overflow:"hidden",
      fontFamily:"system-ui, sans-serif" }}>

      <div style={{ padding:"10px 14px 8px", borderBottom:`1px solid ${D.border0}`,
        display:"flex", alignItems:"center", justifyContent:"space-between", flexShrink:0 }}>
        <span style={{ fontSize:10, fontWeight:600, color: D.text2,
          letterSpacing:"0.08em", textTransform:"uppercase" }}>Entities</span>
        <button style={{ width:22, height:22, borderRadius:6, border:`1px solid ${D.border1}`,
          background:"transparent", cursor:"pointer", color: D.text1,
          display:"flex", alignItems:"center", justifyContent:"center", fontSize:16, lineHeight:1 }}
          onClick={() => {
            const name = prompt("Entity name:");
            if (!name) return;
            useStudioStore.getState().upsertEntity({
              id:name, name, purpose:"", strategies:[],
              threshold:0.70, timeout_ms:1500, fallback_enabled:true,
            });
          }}>+</button>
      </div>

      <div style={{ flex:1, overflowY:"auto", padding:"6px 8px" }}>
        {config.entities.map(entity => {
          const active = entity.id === activeEntityId;
          const conf = maxConf(entity);
          return (
            <div key={entity.id} onClick={() => setActiveEntityId(entity.id)}
              style={{ padding:"9px 10px", borderRadius:8, cursor:"pointer", marginBottom:2,
                background: active ? D.accentBg : "transparent",
                border:`1px solid ${active ? D.accentBorder : "transparent"}`,
                transition:"all 0.1s" }}
              onMouseEnter={e => { if(!active)(e.currentTarget as HTMLDivElement).style.background = D.bg2; }}
              onMouseLeave={e => { if(!active)(e.currentTarget as HTMLDivElement).style.background = "transparent"; }}>
              <div style={{ display:"flex", alignItems:"center", gap:7, marginBottom:5 }}>
                <ConfDot conf={conf} />
                <span style={{ fontSize:12, fontWeight:600,
                  color: active ? "#a5b4fc" : D.text0, flex:1,
                  overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                  {entity.name}
                </span>
                <span style={{ fontSize:10, fontWeight:600, fontFamily:"monospace",
                  color: conf>=0.80 ? D.green : conf>=0.60 ? D.amber : D.red }}>
                  {Math.round(conf*100)}%
                </span>
              </div>
              <MiniBar conf={conf} />
              <div style={{ display:"flex", justifyContent:"space-between", marginTop:4 }}>
                <span style={{ fontSize:10, color: D.text3, fontFamily:"monospace",
                  overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap", maxWidth:"78%" }}>
                  {entity.strategies[0]?.selector ?? "—"}
                </span>
                {entity.matches_found !== undefined && (
                  <span style={{ fontSize:10, color: D.text3, flexShrink:0 }}>
                    {entity.matches_found}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ padding:"10px 14px", borderTop:`1px solid ${D.border0}`, flexShrink:0 }}>
        <div style={{ fontSize:10, fontWeight:600, color: D.text2,
          letterSpacing:"0.08em", textTransform:"uppercase", marginBottom:8 }}>Schema Fields</div>
        <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
          {config.entities.slice(0,5).map(e => (
            <div key={e.id} style={{ display:"flex", alignItems:"center", gap:6 }}>
              <span style={{ fontSize:10, fontFamily:"monospace", background: D.bg3,
                border:`1px solid ${D.border1}`, padding:"1px 7px", borderRadius:4, color: D.text1 }}>
                {e.name}
              </span>
              <span style={{ fontSize:9, color: D.text3, textTransform:"uppercase", letterSpacing:"0.04em" }}>
                {e.strategies[0]?.type ?? "—"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
