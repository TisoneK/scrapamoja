import { useStudioStore } from "../../store/studioStore";

const D = {
  bg1:"#111318", bg2:"#171820", border0:"#1a1b22",
  text2:"#565668", text3:"#32333e",
  green:"#1D9E75", greenBg:"#0a2018", greenBorder:"rgba(29,158,117,0.25)",
  amber:"#EF9F27", amberBg:"#1a1200", amberBorder:"rgba(239,159,39,0.25)",
  red:"#E24B4A",   redBg:"#1a0808",   redBorder:"rgba(226,75,74,0.25)",
};

const maxConf = (e:{strategies:{confidence:number}[]}) =>
  e.strategies.length ? Math.max(...e.strategies.map(s=>s.confidence)) : 0;

export function ConfidenceHeatmap() {
  const { config, setActiveEntityId } = useStudioStore();
  if (!config) return null;

  return (
    <div style={{ padding:"8px 12px 10px", borderTop:`1px solid ${D.border0}`,
      background: D.bg1, flexShrink:0 }}>
      <div style={{ fontSize:9, fontWeight:600, letterSpacing:"0.08em", textTransform:"uppercase",
        color: D.text2, marginBottom:6 }}>Confidence heatmap — all entities</div>
      <div style={{ display:"flex", gap:4, marginBottom:6 }}>
        {config.entities.map(entity => {
          const conf = maxConf(entity);
          const [fg,bg,border] = conf>=0.80
            ? [D.green,D.greenBg,D.greenBorder]
            : conf>=0.60
            ? [D.amber,D.amberBg,D.amberBorder]
            : [D.red,D.redBg,D.redBorder];
          return (
            <div key={entity.id} onClick={() => setActiveEntityId(entity.id)}
              style={{ flex:1, borderRadius:6, padding:"7px 8px", cursor:"pointer",
                background:bg, border:`1px solid ${border}`,
                display:"flex", flexDirection:"column", gap:2,
                transition:"filter 0.12s" }}
              onMouseEnter={e=>(e.currentTarget as HTMLDivElement).style.filter="brightness(1.2)"}
              onMouseLeave={e=>(e.currentTarget as HTMLDivElement).style.filter="brightness(1)"}>
              <span style={{ fontSize:9, color:fg, overflow:"hidden",
                textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{entity.name}</span>
              <span style={{ fontSize:11, fontFamily:"monospace", fontWeight:600, color:fg }}>
                {Math.round(conf*100)}%
              </span>
            </div>
          );
        })}
      </div>
      <div style={{ display:"flex", gap:12 }}>
        {[[D.green,"≥ 0.80"],[D.amber,"0.60–0.79"],[D.red,"< 0.60"]].map(([c,l])=>(
          <div key={l} style={{ display:"flex", alignItems:"center", gap:5,
            fontSize:9, color: D.text3 }}>
            <div style={{ width:6, height:6, borderRadius:"50%", background:c }}/>
            {l}
          </div>
        ))}
      </div>
    </div>
  );
}
