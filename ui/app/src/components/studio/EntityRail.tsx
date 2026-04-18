import { useStudioStore } from "../../store/studioStore";

const maxConf = (e: { strategies: { confidence: number }[] }) =>
  e.strategies.length ? Math.max(...e.strategies.map(s => s.confidence)) : 0;

function ConfDot({ conf }: { conf: number }) {
  const c = conf >= 0.80 ? "#16A34A" : conf >= 0.60 ? "#D97706" : "#DC2626";
  return <div style={{ width: 7, height: 7, borderRadius: "50%", background: c, flexShrink: 0 }} />;
}

function MiniBar({ conf }: { conf: number }) {
  const c = conf >= 0.80 ? "#16A34A" : conf >= 0.60 ? "#D97706" : "#DC2626";
  const bg = conf >= 0.80 ? "#DCFCE7" : conf >= 0.60 ? "#FEF9C3" : "#FEE2E2";
  return (
    <div style={{ height: 3, borderRadius: 2, background: bg, overflow: "hidden", width: "100%" }}>
      <div style={{ height: "100%", width: `${Math.round(conf * 100)}%`, background: c, borderRadius: 2 }} />
    </div>
  );
}

export function EntityRail() {
  const { config, activeEntityId, setActiveEntityId } = useStudioStore();
  if (!config) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden",
      fontFamily: "system-ui, sans-serif" }}>

      {/* Header */}
      <div style={{
        padding: "10px 14px 8px", borderBottom: "1px solid #F1F5F9",
        display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0,
      }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: "#94A3B8",
          letterSpacing: "0.07em", textTransform: "uppercase" }}>
          Entities
        </span>
        <button
          style={{ width: 22, height: 22, borderRadius: 6, border: "1px solid #E2E8F0",
            background: "white", cursor: "pointer", fontSize: 16, color: "#64748B",
            display: "flex", alignItems: "center", justifyContent: "center", lineHeight: 1 }}
          onClick={() => {
            const name = prompt("Entity name:");
            if (!name) return;
            useStudioStore.getState().upsertEntity({
              id: name, name, purpose: "", strategies: [],
              threshold: 0.70, timeout_ms: 1500, fallback_enabled: true,
            });
          }}>+</button>
      </div>

      {/* Entity list */}
      <div style={{ flex: 1, overflowY: "auto", padding: "6px 8px" }}>
        {config.entities.map(entity => {
          const active = entity.id === activeEntityId;
          const conf = maxConf(entity);
          return (
            <div key={entity.id}
              onClick={() => setActiveEntityId(entity.id)}
              style={{
                padding: "9px 10px", borderRadius: 8, cursor: "pointer",
                marginBottom: 2,
                background: active ? "#EEF2FF" : "transparent",
                border: `1px solid ${active ? "#C7D2FE" : "transparent"}`,
                transition: "all 0.1s",
              }}
              onMouseEnter={e => { if (!active) (e.currentTarget as HTMLDivElement).style.background = "#F8FAFC"; }}
              onMouseLeave={e => { if (!active) (e.currentTarget as HTMLDivElement).style.background = "transparent"; }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 5 }}>
                <ConfDot conf={conf} />
                <span style={{ fontSize: 12, fontWeight: 600,
                  color: active ? "#4338CA" : "#0F172A", flex: 1,
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {entity.name}
                </span>
                <span style={{ fontSize: 10, fontWeight: 600, fontFamily: "monospace",
                  color: conf >= 0.80 ? "#16A34A" : conf >= 0.60 ? "#D97706" : "#DC2626" }}>
                  {Math.round(conf * 100)}%
                </span>
              </div>
              <MiniBar conf={conf} />
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
                <span style={{ fontSize: 10, color: "#94A3B8", fontFamily: "monospace",
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "75%" }}>
                  {entity.strategies[0]?.selector ?? "—"}
                </span>
                {entity.matches_found !== undefined && (
                  <span style={{ fontSize: 10, color: "#94A3B8", flexShrink: 0 }}>
                    {entity.matches_found}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Schema fields */}
      <div style={{ padding: "10px 14px", borderTop: "1px solid #F1F5F9", flexShrink: 0 }}>
        <div style={{ fontSize: 10, fontWeight: 600, color: "#94A3B8",
          letterSpacing: "0.07em", textTransform: "uppercase", marginBottom: 8 }}>
          Schema Fields
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {config.entities.slice(0, 5).map(e => (
            <div key={e.id} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: 10, fontFamily: "monospace",
                background: "#F1F5F9", border: "1px solid #E2E8F0",
                padding: "1px 7px", borderRadius: 4, color: "#475569" }}>
                {e.name}
              </span>
              <span style={{ fontSize: 9, color: "#CBD5E1", textTransform: "uppercase",
                letterSpacing: "0.04em" }}>
                {e.strategies[0]?.type ?? "—"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
