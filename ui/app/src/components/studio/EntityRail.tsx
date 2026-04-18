import { useStudioStore } from "../../store/studioStore";

function HealthDot({ confidence }: { confidence: number }) {
  const color = confidence >= 0.80 ? "var(--green)" : confidence >= 0.60 ? "var(--amber)" : "var(--red)";
  return <div style={{ width:7, height:7, borderRadius:"50%", background:color, flexShrink:0 }}/>;
}

const maxConf = (e: { strategies: { confidence: number }[] }) =>
  Math.max(...e.strategies.map(s => s.confidence), 0);

export function EntityRail() {
  const { config, activeEntityId, setActiveEntityId, removeEntity } = useStudioStore();
  if (!config) return null;

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%", overflow:"hidden" }}>
      <div className="panel-header">
        <span className="panel-title">Entities</span>
        <button className="btn btn-ghost btn-sm" style={{ fontSize:16, padding:"0 4px", lineHeight:1 }}
          onClick={() => {
            const name = prompt("Entity name:");
            if (!name) return;
            const { upsertEntity } = useStudioStore.getState();
            upsertEntity({
              id: name, name, purpose: "", strategies: [], threshold:0.70,
              timeout_ms:1500, fallback_enabled:true,
            });
          }}>+</button>
      </div>

      <div style={{ flex:1, overflowY:"auto", padding:"6px" }}>
        {config.entities.map(entity => {
          const active = entity.id === activeEntityId;
          const conf = maxConf(entity);
          return (
            <div key={entity.id} className={`entity-item ${active ? "active" : ""}`}
              onClick={() => setActiveEntityId(entity.id)}>
              <div style={{ display:"flex", alignItems:"center", gap:7, marginBottom:3 }}>
                <HealthDot confidence={conf}/>
                <span style={{ fontSize:12, fontWeight:500,
                  color: active ? "var(--accent-bright)" : "var(--text-0)",
                  flex:1, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                  {entity.name}
                </span>
                <span style={{ fontSize:9, fontFamily:"var(--font-mono)",
                  color: conf >= 0.80 ? "var(--green)" : conf >= 0.60 ? "var(--amber)" : "var(--red)" }}>
                  {Math.round(conf * 100)}%
                </span>
              </div>
              <div style={{ fontSize:10, color:"var(--text-3)", fontFamily:"var(--font-mono)",
                paddingLeft:14, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                {entity.strategies[0]?.selector ?? "—"}
              </div>
              {entity.matches_found !== undefined && (
                <div style={{ fontSize:9, color:"var(--text-3)", paddingLeft:14, marginTop:2 }}>
                  {entity.matches_found} matches
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Schema fields */}
      <div style={{ padding:"10px 10px", borderTop:"1px solid var(--border-0)" }}>
        <div style={{ fontSize:9, fontWeight:600, letterSpacing:"0.08em", textTransform:"uppercase",
          color:"var(--text-3)", marginBottom:6 }}>
          Schema fields
        </div>
        {config.entities.slice(0,5).map(e => (
          <div key={e.id} style={{ display:"flex", gap:6, alignItems:"center", marginBottom:4 }}>
            <span style={{ fontSize:10, fontFamily:"var(--font-mono)",
              background:"var(--bg-3)", padding:"1px 6px", borderRadius:4,
              color:"var(--text-2)", border:"1px solid var(--border-1)" }}>
              {e.name}
            </span>
            <span style={{ fontSize:9, color:"var(--text-3)" }}>
              {e.strategies[0]?.type ?? "—"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
