import { useState } from "react";
import { useStudioStore } from "../../store/studioStore";
import type { StrategyType } from "../../types/studio";

const D = {
  bg0:"#0d0c11", bg1:"#13121a", bg2:"#1a1920", bg3:"#21202b",
  border0:"rgba(255,255,255,0.05)", border1:"rgba(255,255,255,0.09)",
  text0:"#e8e6f0", text1:"#9f9bc4", text2:"#5f5d7a", text3:"#3a3850",
  accent:"#6366f1", accentBg:"#1e1c2e", accentBorder:"#3d3775",
  green:"#1D9E75", greenBg:"#0a2018", greenBorder:"rgba(29,158,117,0.25)",
  amber:"#EF9F27", amberBg:"#1a1200", amberBorder:"rgba(239,159,39,0.25)",
  red:"#E24B4A", redBg:"#1a0808", redBorder:"rgba(226,75,74,0.25)",
  blue:"#378ADD",
};

const TYPE_STYLES: Record<StrategyType,{bg:string;text:string;border:string}> = {
  css:  {bg:"#111827",text:"#60a5fa",border:"rgba(96,165,250,0.25)"},
  xpath:{bg:"#0a2018",text:"#34d399",border:"rgba(52,211,153,0.25)"},
  text: {bg:"#1a1200",text:"#fbbf24",border:"rgba(251,191,36,0.25)"},
  attr: {bg:"#1a0a1a",text:"#c084fc",border:"rgba(192,132,252,0.25)"},
};

const SAMPLE_DATA: Record<string,string> = {
  match_card:"div.event", team_name:"Boston Celtics", score:"88–74",
  status:"LIVE", match_time:"Q3 28'", match_url:"/match/abc123",
};

function TypeBadge({type}:{type:StrategyType}) {
  const s = TYPE_STYLES[type];
  return (
    <span style={{ fontSize:9, fontWeight:700, padding:"2px 7px", borderRadius:20,
      background:s.bg, color:s.text, border:`1px solid ${s.border}`,
      letterSpacing:"0.06em", textTransform:"uppercase" }}>
      {type.toUpperCase()}
    </span>
  );
}

function ConfBar({value}:{value:number}) {
  const fg = value>=0.80 ? D.green : value>=0.60 ? D.amber : D.red;
  return (
    <div style={{ height:3, borderRadius:2, background:"rgba(255,255,255,0.06)", overflow:"hidden", flex:1 }}>
      <div style={{ height:"100%", width:`${Math.round(value*100)}%`,
        background:fg, borderRadius:2, transition:"width 0.4s ease" }} />
    </div>
  );
}

function ConfBadge({value}:{value:number}) {
  const [color,bg,border] = value>=0.80
    ? [D.green,D.greenBg,D.greenBorder]
    : value>=0.60
    ? [D.amber,D.amberBg,D.amberBorder]
    : [D.red,D.redBg,D.redBorder];
  return (
    <span style={{ fontSize:10, fontWeight:600, padding:"2px 8px", borderRadius:20,
      fontFamily:"monospace", background:bg, color, border:`1px solid ${border}` }}>
      {Math.round(value*100)}%
    </span>
  );
}

type Tab = "selector"|"validation"|"yaml";

export function SelectorPanel() {
  const { config, activeEntityId } = useStudioStore();
  const [tab, setTab] = useState<Tab>("selector");
  const [copied, setCopied] = useState(false);

  const entity = config?.entities.find(e => e.id === activeEntityId);

  if (!entity) return (
    <div style={{ height:"100%", display:"flex", flexDirection:"column",
      alignItems:"center", justifyContent:"center", gap:10, padding:24,
      fontFamily:"system-ui, sans-serif" }}>
      <div style={{ width:40, height:40, borderRadius:10, background: D.bg3,
        display:"flex", alignItems:"center", justifyContent:"center" }}>
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <circle cx="9" cy="9" r="7" stroke={D.text2} strokeWidth="1.5"/>
          <path d="M9 5v4M9 11v.5" stroke={D.text2} strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
      </div>
      <span style={{ fontSize:12, color: D.text2, textAlign:"center", lineHeight:1.6 }}>
        Select an entity to view<br/>extraction details
      </span>
    </div>
  );

  const sorted = [...entity.strategies].sort((a,b) => b.confidence - a.confidence);
  const best = sorted[0];

  const yaml = `name: ${entity.name}
purpose: ${entity.purpose||"—"}
threshold: ${entity.threshold}
timeout_ms: ${entity.timeout_ms}
fallback_enabled: ${entity.fallback_enabled}
strategies:
${entity.strategies.map(s=>`  - type: ${s.type}\n    selector: "${s.selector}"\n    priority: ${s.priority}`).join("\n")}`;

  const copyYaml = () => {
    navigator.clipboard.writeText(yaml).then(()=>{
      setCopied(true); setTimeout(()=>setCopied(false),2000);
    });
  };

  const TABS = [
    {id:"selector" as Tab, label:"Field Extraction"},
    {id:"validation" as Tab, label:"Checks"},
    {id:"yaml" as Tab, label:"YAML"},
  ];

  return (
    <div style={{ height:"100%", display:"flex", flexDirection:"column",
      fontFamily:"system-ui, sans-serif", overflow:"hidden", background: D.bg1 }}>

      {/* Entity header */}
      <div style={{ padding:"12px 16px", borderBottom:`1px solid ${D.border0}`, flexShrink:0 }}>
        <div style={{ fontSize:11, color: D.text2, marginBottom:6 }}>
          <span style={{ color:"#a5b4fc", fontWeight:600 }}>{entity.name}</span>
          {" "}Element Analysis
        </div>

        {/* Primary selector */}
        <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8,
          background: D.bg2, border:`1px solid ${D.border1}`, borderRadius:8, padding:"7px 10px" }}>
          <TypeBadge type={best?.type ?? "css"} />
          <span style={{ fontSize:11, fontFamily:"monospace", color: D.text0,
            flex:1, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
            {best?.selector ?? "—"}
          </span>
          <span style={{ fontSize:10, color: D.text3 }}>p:{best?.priority ?? 1}</span>
        </div>

        {/* Confidence label */}
        <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:10 }}>
          <div style={{ fontSize:10, fontWeight:500, padding:"2px 10px", borderRadius:20,
            background: (best?.confidence??0)>=0.80 ? D.greenBg : (best?.confidence??0)>=0.60 ? D.amberBg : D.redBg,
            color: (best?.confidence??0)>=0.80 ? D.green : (best?.confidence??0)>=0.60 ? D.amber : D.red,
            border:`1px solid ${(best?.confidence??0)>=0.80 ? D.greenBorder : (best?.confidence??0)>=0.60 ? D.amberBorder : D.redBorder}` }}>
            {(best?.confidence??0)>=0.80 ? "High Confidence" : (best?.confidence??0)>=0.60 ? "Moderate Confidence" : "Low Confidence — Review"}
          </div>
        </div>

        {/* Schema tree */}
        <div style={{ display:"flex", alignItems:"flex-start", gap:8 }}>
          <div style={{ background: D.accentBg, border:`1px solid ${D.accentBorder}`,
            borderRadius:6, padding:"3px 10px", fontSize:11, fontWeight:600, color:"#a5b4fc" }}>
            {entity.name}
          </div>
          <div style={{ display:"flex", alignItems:"center", gap:4 }}>
            <div style={{ width:14, height:1, background: D.border1 }} />
            <div style={{ display:"flex", flexDirection:"column", gap:3 }}>
              {["time","teams","score","status"].map(f => (
                <div key={f} style={{ display:"flex", alignItems:"center", gap:4 }}>
                  <div style={{ width:10, height:1, background: D.border0 }} />
                  <span style={{ fontSize:10, color: D.text2 }}>{f}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display:"flex", borderBottom:`1px solid ${D.border1}`, flexShrink:0, background: D.bg1 }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            style={{ flex:1, padding:"8px 4px", fontSize:11, fontWeight:500,
              border:"none", cursor:"pointer", background:"transparent",
              color: tab===t.id ? "#a5b4fc" : D.text2,
              borderBottom:`2px solid ${tab===t.id ? D.accent : "transparent"}`,
              transition:"all 0.1s" }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Body */}
      <div style={{ flex:1, overflowY:"auto" }}>

        {/* ── FIELD EXTRACTION ── */}
        {tab==="selector" && (
          <div>
            {/* Table header */}
            <div style={{ display:"grid", gridTemplateColumns:"1fr 90px 56px 28px",
              padding:"6px 14px", borderBottom:`1px solid ${D.border0}`, background: D.bg2 }}>
              {["Field Name","Sample Data","Rule",""].map(h => (
                <span key={h} style={{ fontSize:10, fontWeight:600, color: D.text2,
                  letterSpacing:"0.05em", textTransform:"uppercase" }}>{h}</span>
              ))}
            </div>

            {entity.strategies.map((s,i) => {
              const sample = i===0 ? (SAMPLE_DATA[entity.name]??"—") : "—";
              return (
                <div key={i} style={{ display:"grid", gridTemplateColumns:"1fr 90px 56px 28px",
                  padding:"8px 14px", borderBottom:`1px solid ${D.border0}`,
                  alignItems:"center", background: i===0 ? "rgba(99,102,241,0.04)" : "transparent" }}>
                  <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                    {i===0 && (
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <circle cx="6" cy="6" r="5" fill={D.accent} opacity="0.2"/>
                        <path d="M3.5 6l1.8 1.8L8.5 4" stroke={D.accent} strokeWidth="1.2" strokeLinecap="round"/>
                      </svg>
                    )}
                    <span style={{ fontSize:12, color: D.text0, fontWeight: i===0 ? 500 : 400 }}>
                      {i===0 ? entity.name : `${entity.name}_alt_${i}`}
                    </span>
                  </div>
                  <span style={{ fontSize:10, fontFamily:"monospace",
                    background: i===0 ? D.greenBg : D.bg3,
                    color: i===0 ? D.green : D.text2,
                    padding:"2px 7px", borderRadius:4,
                    border:`1px solid ${i===0 ? D.greenBorder : D.border0}`,
                    overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                    {sample}
                  </span>
                  <TypeBadge type={s.type} />
                  <button style={{ border:"none", background:"none", cursor:"pointer",
                    color: D.text2, padding:"2px", borderRadius:4 }}>
                    <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                      <path d="M2 9.5L9 2.5l1.5 1.5-7 7H2V9.5z" stroke={D.text2} strokeWidth="0.9"/>
                    </svg>
                  </button>
                </div>
              );
            })}

            {/* Optimization Strategy */}
            <div style={{ margin:"10px 14px", background: D.bg2,
              border:`1px solid ${D.border1}`, borderRadius:10, overflow:"hidden" }}>
              <div style={{ padding:"10px 12px", borderBottom:`1px solid ${D.border0}`,
                display:"flex", alignItems:"center", gap:8 }}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M7 1l1.5 3.5L12 5l-2.5 2.5.5 3.5L7 9.5 4 11l.5-3.5L2 5l3.5-.5L7 1z"
                    stroke="#a5b4fc" strokeWidth="1.1" strokeLinejoin="round"/>
                </svg>
                <span style={{ fontSize:12, fontWeight:600, color: D.text0 }}>Optimization Strategy</span>
              </div>
              <div style={{ padding:"8px 12px 10px" }}>
                <div style={{ fontSize:11, color: D.text2, marginBottom:8, lineHeight:1.5 }}>
                  Analyzes all rules and prioritizes validated statuses.
                </div>
                <div style={{ fontSize:11, fontWeight:600, color: D.text1, marginBottom:6 }}>
                  Extracted data fields
                </div>
                <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
                  {sorted.slice(0,3).map((s,i) => (
                    <div key={i} style={{ display:"flex", alignItems:"center", gap:8,
                      background: D.bg3, borderRadius:7, padding:"6px 10px",
                      border:`1px solid ${D.border0}` }}>
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                        <circle cx="5" cy="5" r="4.5" fill={D.accentBg}/>
                        <path d="M2.5 5l1.8 1.8L7.5 3.5" stroke={D.accent} strokeWidth="1.1" strokeLinecap="round"/>
                      </svg>
                      <span style={{ fontSize:11, color: D.text1, fontFamily:"monospace",
                        flex:1, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                        {s.selector}
                      </span>
                      <span style={{ fontSize:9, fontWeight:600, color:"#a5b4fc",
                        background: D.accentBg, padding:"1px 6px", borderRadius:4,
                        border:`1px solid ${D.accentBorder}` }}>P{i+1}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div style={{ padding:"0 14px 14px", display:"flex", flexDirection:"column", gap:6 }}>
              {[
                { label:"Auto-select best strategy", accent:true, icon:"M4 6.5l2 2L9.5 4.5" },
                { label:"Adjust priority order",     accent:false, icon:"M2 4h9M2 6.5h6M2 9h4" },
                { label:"Add fallback rule",          accent:false, icon:"M6.5 2v9M2 6.5h9" },
              ].map(({label,accent,icon}) => (
                <button key={label} style={{ padding:"9px 12px", borderRadius:8,
                  fontSize:12, fontWeight:500, cursor:"pointer", textAlign:"left",
                  display:"flex", alignItems:"center", gap:8,
                  background: accent ? D.accentBg : D.bg2,
                  border:`1px solid ${accent ? D.accentBorder : D.border1}`,
                  color: accent ? "#a5b4fc" : D.text1 }}>
                  <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                    <path d={icon} stroke={accent ? "#a5b4fc" : D.text1} strokeWidth="1.1" strokeLinecap="round"/>
                  </svg>
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── VALIDATION ── */}
        {tab==="validation" && (
          <div style={{ padding:14, display:"flex", flexDirection:"column", gap:8 }}>
            {[
              { label:"Confidence threshold",
                detail:`Best at ${Math.round((best?.confidence??0)*100)}% — threshold ${Math.round(entity.threshold*100)}%`,
                pass:(best?.confidence??0)>=entity.threshold },
              { label:"Match count",
                detail:entity.matches_found ? `${entity.matches_found} element(s) found` : "No matches",
                pass:(entity.matches_found??0)>0 },
              { label:"Fallback coverage",
                detail:entity.strategies.length>1 ? `${entity.strategies.length} strategies` : "Single strategy — add fallback",
                pass:entity.strategies.length>1 },
              { label:"Selector stability",
                detail:(best?.confidence??0)>=0.80 ? "Primary selector stable" : "Below 80% — consider alternatives",
                pass:(best?.confidence??0)>=0.80 },
            ].map(({label,detail,pass})=>(
              <div key={label} style={{ background: D.bg2, borderRadius:8, padding:"10px 12px",
                border:`1px solid ${pass ? D.greenBorder : D.redBorder}`,
                display:"flex", gap:10, alignItems:"flex-start" }}>
                <div style={{ width:20, height:20, borderRadius:"50%", flexShrink:0, marginTop:1,
                  background: pass ? D.greenBg : D.redBg,
                  display:"flex", alignItems:"center", justifyContent:"center" }}>
                  {pass
                    ? <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 5l2 2 4-4" stroke={D.green} strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg>
                    : <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M3 3l4 4M7 3l-4 4" stroke={D.red} strokeWidth="1.3" strokeLinecap="round"/></svg>}
                </div>
                <div>
                  <div style={{ fontSize:12, fontWeight:500, color: D.text0, marginBottom:2 }}>{label}</div>
                  <div style={{ fontSize:11, color: D.text1 }}>{detail}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── YAML ── */}
        {tab==="yaml" && (
          <div style={{ padding:14 }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
              <span style={{ fontSize:11, color: D.text2 }}>
                Config for <strong style={{ color: D.text0 }}>{entity.name}</strong>
              </span>
              <button onClick={copyYaml} style={{ padding:"4px 10px", fontSize:10, fontWeight:500,
                border:`1px solid ${copied ? D.greenBorder : D.border1}`, borderRadius:6,
                background: copied ? D.greenBg : D.bg3,
                color: copied ? D.green : D.text1, cursor:"pointer",
                display:"flex", alignItems:"center", gap:5 }}>
                {copied ? "✓ Copied" : "Copy"}
              </button>
            </div>
            <pre style={{ background: D.bg0, borderRadius:10, padding:"14px 16px",
              fontSize:11, fontFamily:"monospace", color: D.text1,
              overflowX:"auto", whiteSpace:"pre-wrap", lineHeight:1.7, margin:0,
              border:`1px solid ${D.border1}` }}>
              {yaml.split("\n").map((line,i)=>{
                const isKey=/^\w+:/.test(line);
                const isItem=line.trimStart().startsWith("- type:");
                return <span key={i} style={{ color:isItem?"#7DD3FC":isKey?"#c084fc":D.text1 }}>{line}{"\n"}</span>;
              })}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
