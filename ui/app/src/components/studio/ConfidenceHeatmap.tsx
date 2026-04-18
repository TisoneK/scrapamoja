import { useStudioStore } from "../../store/studioStore";

export function ConfidenceHeatmap() {
  const { config, setActiveEntityId } = useStudioStore();
  if (!config) return null;

  const maxConf = (e: { strategies: { confidence: number }[] }) =>
    Math.max(...e.strategies.map(s => s.confidence), 0);

  return (
    <div style={{ padding:"8px 12px", borderTop:"1px solid var(--border-0)", background:"var(--bg-1)", flexShrink:0 }}>
      <div style={{ fontSize:9, fontWeight:600, letterSpacing:"0.08em", textTransform:"uppercase",
        color:"var(--text-3)", marginBottom:6 }}>
        Confidence heatmap — all entities
      </div>
      <div style={{ display:"flex", gap:4, marginBottom:5 }}>
        {config.entities.map(entity => {
          const conf = maxConf(entity);
          const tier = conf >= 0.80 ? "high" : conf >= 0.60 ? "mid" : "low";
          return (
            <div key={entity.id} className={`heat-cell heat-${tier}`}
              style={{ flex:1 }} onClick={() => setActiveEntityId(entity.id)}>
              <span style={{ fontSize:9, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                {entity.name}
              </span>
              <span style={{ fontSize:10, fontFamily:"var(--font-mono)", fontWeight:600 }}>
                {conf.toFixed(2)}
              </span>
            </div>
          );
        })}
      </div>
      <div style={{ display:"flex", gap:12 }}>
        {[["high","var(--green)","≥ 0.80"],["mid","var(--amber)","0.60–0.79"],["low","var(--red)","< 0.60"]].map(([,col,label]) => (
          <div key={label} style={{ display:"flex", alignItems:"center", gap:5, fontSize:9, color:"var(--text-3)" }}>
            <div style={{ width:6, height:6, borderRadius:"50%", background:col }}/>
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}
