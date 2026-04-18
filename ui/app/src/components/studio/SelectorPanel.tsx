import { useState } from "react";
import { useStudioStore } from "../../store/studioStore";
import type { StrategyType } from "../../types/studio";

const TYPE_LABELS: Record<StrategyType, string> = { css:"CSS", xpath:"XPath", text:"Text", attr:"Attr" };

const TYPE_COLORS: Record<StrategyType, { bg: string; text: string; border: string }> = {
  css:   { bg:"#EEF4FF", text:"#2563EB", border:"#BFDBFE" },
  xpath: { bg:"#F0FDF4", text:"#16A34A", border:"#BBF7D0" },
  text:  { bg:"#FFFBEB", text:"#D97706", border:"#FDE68A" },
  attr:  { bg:"#FDF4FF", text:"#9333EA", border:"#E9D5FF" },
};

type Tab = "selector" | "validation" | "yaml" | "preview";

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.80 ? "#16A34A" : value >= 0.60 ? "#D97706" : "#DC2626";
  const bg    = value >= 0.80 ? "#F0FDF4" : value >= 0.60 ? "#FFFBEB" : "#FEF2F2";
  const border= value >= 0.80 ? "#BBF7D0" : value >= 0.60 ? "#FDE68A" : "#FECACA";
  return (
    <span style={{
      fontSize:11, fontWeight:600, padding:"2px 8px",
      borderRadius:20, fontFamily:"monospace",
      background:bg, color, border:`1px solid ${border}`,
    }}>{pct}%</span>
  );
}

function ConfBar({ value }: { value: number }) {
  const color = value >= 0.80 ? "#16A34A" : value >= 0.60 ? "#D97706" : "#DC2626";
  const trackBg = value >= 0.80 ? "#DCFCE7" : value >= 0.60 ? "#FEF9C3" : "#FEE2E2";
  return (
    <div style={{ height:4, borderRadius:4, background:trackBg, overflow:"hidden" }}>
      <div style={{ height:"100%", width:`${Math.round(value*100)}%`, background:color, borderRadius:4, transition:"width 0.4s ease" }}/>
    </div>
  );
}

export function SelectorPanel() {
  const { config, activeEntityId } = useStudioStore();
  const [tab, setTab] = useState<Tab>("selector");
  const [copied, setCopied] = useState(false);

  const entity = config?.entities.find(e => e.id === activeEntityId);

  if (!entity) {
    return (
      <div style={{ height:"100%", display:"flex", flexDirection:"column", alignItems:"center",
        justifyContent:"center", gap:12, padding:24 }}>
        <div style={{ width:40, height:40, borderRadius:10, background:"#F1F5F9",
          display:"flex", alignItems:"center", justifyContent:"center" }}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <circle cx="9" cy="9" r="7" stroke="#94A3B8" strokeWidth="1.5"/>
            <path d="M9 5v4M9 11v.5" stroke="#94A3B8" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </div>
        <span style={{ fontSize:12, color:"#94A3B8", textAlign:"center", lineHeight:1.5 }}>
          Select an entity from the left<br/>to inspect its selectors
        </span>
      </div>
    );
  }

  const sorted = [...entity.strategies].sort((a, b) => b.confidence - a.confidence);
  const best = sorted[0];
  const lowConf = entity.strategies.filter(s => s.confidence < 0.60);

  const yaml = `name: ${entity.name}
purpose: ${entity.purpose || "—"}
threshold: ${entity.threshold}
timeout_ms: ${entity.timeout_ms}
fallback_enabled: ${entity.fallback_enabled}
strategies:
${entity.strategies.map(s =>
  `  - type: ${s.type}\n    selector: "${s.selector}"\n    priority: ${s.priority}`
).join("\n")}`;

  const copyYaml = () => {
    navigator.clipboard.writeText(yaml).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const overallHealth = entity.strategies.reduce((sum, s) => sum + s.confidence, 0) / entity.strategies.length;

  const TABS: { id: Tab; label: string }[] = [
    { id:"selector",   label:"Selector" },
    { id:"validation", label:"Checks" },
    { id:"yaml",       label:"YAML" },
    { id:"preview",    label:"Preview" },
  ];

  return (
    <div style={{ height:"100%", display:"flex", flexDirection:"column", background:"#FAFAFA",
      fontFamily:"system-ui, -apple-system, sans-serif" }}>

      {/* ── Entity identity card ── */}
      <div style={{ padding:"14px 16px 0", background:"white",
        borderBottom:"1px solid #F1F5F9", flexShrink:0 }}>
        <div style={{ display:"flex", alignItems:"flex-start", gap:10, marginBottom:12 }}>
          <div style={{ flex:1, minWidth:0 }}>
            <div style={{ fontSize:14, fontWeight:600, color:"#0F172A",
              overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
              {entity.name}
            </div>
            <div style={{ fontSize:11, color:"#64748B", marginTop:1 }}>
              {entity.purpose || "No description set"}
            </div>
          </div>
          <ConfidenceBadge value={overallHealth}/>
        </div>

        {/* Stats row */}
        <div style={{ display:"flex", gap:0, marginBottom:12,
          background:"#F8FAFC", borderRadius:8, padding:"8px 0",
          border:"1px solid #F1F5F9" }}>
          {[
            ["Strategies", entity.strategies.length],
            ["Matches",    entity.matches_found ?? "—"],
            ["Threshold",  `${Math.round(entity.threshold * 100)}%`],
          ].map(([label, val], i) => (
            <div key={String(label)} style={{
              flex:1, textAlign:"center",
              borderRight: i < 2 ? "1px solid #E2E8F0" : "none",
              padding:"0 8px",
            }}>
              <div style={{ fontSize:15, fontWeight:600, color:"#0F172A", lineHeight:1.2 }}>{val}</div>
              <div style={{ fontSize:10, color:"#94A3B8", marginTop:2, textTransform:"uppercase",
                letterSpacing:"0.05em" }}>{label}</div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div style={{ display:"flex", gap:2, marginBottom:-1 }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              style={{
                padding:"6px 12px", fontSize:11, fontWeight:500,
                border:"none", cursor:"pointer", borderRadius:"6px 6px 0 0",
                background: tab === t.id ? "#FAFAFA" : "transparent",
                color: tab === t.id ? "#3B4EFF" : "#94A3B8",
                borderBottom: tab === t.id ? "2px solid #3B4EFF" : "2px solid transparent",
                transition:"all 0.1s",
              }}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Tab content ── */}
      <div style={{ flex:1, overflowY:"auto", padding:"14px 16px" }}>

        {/* ── SELECTOR TAB ── */}
        {tab === "selector" && (
          <div style={{ display:"flex", flexDirection:"column", gap:8 }}>

            {/* Low confidence alert */}
            {lowConf.length > 0 && (
              <div style={{ background:"#FFFBEB", border:"1px solid #FDE68A",
                borderRadius:8, padding:"9px 12px", display:"flex", gap:10, alignItems:"flex-start" }}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ flexShrink:0, marginTop:1 }}>
                  <path d="M7 1L13 12H1L7 1z" fill="#FEF9C3" stroke="#D97706" strokeWidth="1.2"/>
                  <line x1="7" y1="5" x2="7" y2="8" stroke="#D97706" strokeWidth="1.2" strokeLinecap="round"/>
                  <circle cx="7" cy="9.5" r="0.5" fill="#D97706"/>
                </svg>
                <div>
                  <div style={{ fontSize:11, fontWeight:600, color:"#92400E", marginBottom:2 }}>
                    {lowConf.length} weak {lowConf.length === 1 ? "strategy" : "strategies"} detected
                  </div>
                  <div style={{ fontSize:10, color:"#B45309" }}>
                    {lowConf.map(s => s.type.toUpperCase()).join(", ")} below 60% confidence.
                    Consider adding a fallback selector.
                  </div>
                </div>
              </div>
            )}

            {/* Strategy cards */}
            {entity.strategies.map((s, i) => {
              const tc = TYPE_COLORS[s.type];
              const isBest = s.selector === best?.selector;
              return (
                <div key={i} style={{
                  background:"white", borderRadius:10,
                  border:`1px solid ${isBest ? "#C7D2FE" : "#E2E8F0"}`,
                  padding:"11px 12px",
                  boxShadow: isBest ? "0 0 0 3px rgba(99,102,241,0.06)" : "none",
                }}>
                  <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8 }}>
                    {/* Type badge */}
                    <span style={{
                      fontSize:9, fontWeight:700, padding:"2px 7px", borderRadius:20,
                      background:tc.bg, color:tc.text, border:`1px solid ${tc.border}`,
                      letterSpacing:"0.06em", textTransform:"uppercase",
                    }}>{TYPE_LABELS[s.type]}</span>

                    {/* Priority */}
                    <span style={{ fontSize:9, color:"#CBD5E1",
                      background:"#F8FAFC", border:"1px solid #E2E8F0",
                      padding:"1px 6px", borderRadius:4 }}>
                      p:{s.priority}
                    </span>

                    {/* Best badge */}
                    {isBest && (
                      <span style={{ marginLeft:"auto", display:"flex", alignItems:"center", gap:4,
                        fontSize:9, fontWeight:600, color:"#4F46E5",
                        background:"#EEF2FF", border:"1px solid #C7D2FE",
                        padding:"2px 7px", borderRadius:20 }}>
                        <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                          <circle cx="4" cy="4" r="3.5" fill="#4F46E5"/>
                          <path d="M2.5 4l1 1L5.5 3" stroke="white" strokeWidth="0.9" strokeLinecap="round"/>
                        </svg>
                        Best
                      </span>
                    )}
                    <ConfidenceBadge value={s.confidence}/>
                  </div>

                  {/* Selector string */}
                  <div style={{ fontFamily:"monospace", fontSize:11, color:"#334155",
                    background:"#F8FAFC", border:"1px solid #E2E8F0", borderRadius:6,
                    padding:"5px 9px", marginBottom:8,
                    overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                    {s.selector}
                  </div>

                  <ConfBar value={s.confidence}/>
                </div>
              );
            })}

            {/* Action buttons — real affordance now */}
            <div style={{ display:"flex", flexDirection:"column", gap:6, marginTop:4 }}>
              <button style={{
                padding:"9px 14px", borderRadius:8, fontSize:12, fontWeight:500,
                border:"1px solid #C7D2FE", background:"#EEF2FF", color:"#4338CA",
                cursor:"pointer", textAlign:"left", display:"flex", alignItems:"center", gap:8,
              }}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <circle cx="7" cy="7" r="5.5" stroke="#4338CA" strokeWidth="1.2"/>
                  <path d="M4.5 7l1.8 1.8L9.5 5" stroke="#4338CA" strokeWidth="1.2" strokeLinecap="round"/>
                </svg>
                Auto-select best strategy
              </button>
              <button style={{
                padding:"9px 14px", borderRadius:8, fontSize:12, fontWeight:500,
                border:"1px solid #E2E8F0", background:"white", color:"#475569",
                cursor:"pointer", textAlign:"left", display:"flex", alignItems:"center", gap:8,
              }}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M2 4h10M2 7h7M2 10h4" stroke="#475569" strokeWidth="1.2" strokeLinecap="round"/>
                </svg>
                Adjust priority order
              </button>
              <button style={{
                padding:"9px 14px", borderRadius:8, fontSize:12, fontWeight:500,
                border:"1px solid #E2E8F0", background:"white", color:"#475569",
                cursor:"pointer", textAlign:"left", display:"flex", alignItems:"center", gap:8,
              }}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <line x1="7" y1="2" x2="7" y2="12" stroke="#475569" strokeWidth="1.2" strokeLinecap="round"/>
                  <line x1="2" y1="7" x2="12" y2="7" stroke="#475569" strokeWidth="1.2" strokeLinecap="round"/>
                </svg>
                Add fallback rule
              </button>
            </div>

            {/* Config meta */}
            <div style={{ background:"white", borderRadius:8, border:"1px solid #F1F5F9",
              overflow:"hidden", marginTop:4 }}>
              {[
                ["Timeout",          `${entity.timeout_ms}ms`],
                ["Fallback enabled", entity.fallback_enabled ? "Yes" : "No"],
                ["Matches found",    entity.matches_found ?? "—"],
              ].map(([k, v], i, arr) => (
                <div key={String(k)} style={{
                  display:"flex", justifyContent:"space-between", alignItems:"center",
                  padding:"8px 12px",
                  borderBottom: i < arr.length - 1 ? "1px solid #F1F5F9" : "none",
                }}>
                  <span style={{ fontSize:11, color:"#64748B" }}>{k}</span>
                  <span style={{ fontSize:11, fontFamily:"monospace", color:"#0F172A", fontWeight:500 }}>{v}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── VALIDATION TAB ── */}
        {tab === "validation" && (
          <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
            <div style={{ fontSize:11, color:"#94A3B8", marginBottom:4 }}>
              Health checks for <strong style={{ color:"#0F172A" }}>{entity.name}</strong>
            </div>
            {[
              {
                label: "Confidence threshold",
                detail: `Best strategy at ${Math.round(best?.confidence * 100)}% — threshold is ${Math.round(entity.threshold * 100)}%`,
                pass: best?.confidence >= entity.threshold,
              },
              {
                label: "Match count",
                detail: entity.matches_found ? `Found ${entity.matches_found} element${entity.matches_found !== 1 ? "s" : ""}` : "No matches detected",
                pass: (entity.matches_found ?? 0) > 0,
              },
              {
                label: "Fallback coverage",
                detail: entity.strategies.length > 1 ? `${entity.strategies.length} strategies available` : "Single strategy — add a fallback",
                pass: entity.strategies.length > 1,
              },
              {
                label: "Selector stability",
                detail: best?.confidence >= 0.80 ? "Primary selector is stable" : "Primary selector below 80% — consider alternatives",
                pass: best?.confidence >= 0.80,
              },
            ].map(({ label, detail, pass }) => (
              <div key={label} style={{
                background:"white", borderRadius:8, padding:"10px 12px",
                border:`1px solid ${pass ? "#BBF7D0" : "#FECACA"}`,
                display:"flex", gap:10, alignItems:"flex-start",
              }}>
                <div style={{
                  width:20, height:20, borderRadius:"50%", flexShrink:0, marginTop:1,
                  background: pass ? "#F0FDF4" : "#FEF2F2",
                  display:"flex", alignItems:"center", justifyContent:"center",
                }}>
                  {pass ? (
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                      <path d="M2 5l2 2 4-4" stroke="#16A34A" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  ) : (
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                      <path d="M3 3l4 4M7 3l-4 4" stroke="#DC2626" strokeWidth="1.3" strokeLinecap="round"/>
                    </svg>
                  )}
                </div>
                <div>
                  <div style={{ fontSize:12, fontWeight:500, color:"#0F172A", marginBottom:2 }}>{label}</div>
                  <div style={{ fontSize:11, color:"#64748B" }}>{detail}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── YAML TAB ── */}
        {tab === "yaml" && (
          <div>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
              <span style={{ fontSize:11, color:"#64748B" }}>
                Config for <strong style={{ color:"#0F172A" }}>{entity.name}</strong>
              </span>
              <button onClick={copyYaml} style={{
                padding:"4px 10px", fontSize:10, fontWeight:500,
                border:"1px solid #E2E8F0", borderRadius:6,
                background: copied ? "#F0FDF4" : "white",
                color: copied ? "#16A34A" : "#475569",
                cursor:"pointer", display:"flex", alignItems:"center", gap:5,
              }}>
                {copied ? (
                  <><svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <path d="M2 5l2 2 4-4" stroke="#16A34A" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg> Copied</>
                ) : (
                  <><svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <rect x="1" y="3" width="6" height="6" rx="1" stroke="#475569" strokeWidth="0.9"/>
                    <path d="M3 3V2a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H7" stroke="#475569" strokeWidth="0.9"/>
                  </svg> Copy</>
                )}
              </button>
            </div>
            <pre style={{
              background:"#0F172A", borderRadius:10, padding:"14px 16px",
              fontSize:11, fontFamily:"monospace", color:"#94A3B8",
              overflowX:"auto", whiteSpace:"pre-wrap", lineHeight:1.7, margin:0,
              border:"1px solid #1E293B",
            }}>
              {yaml.split("\n").map((line, i) => {
                const isKey = line.match(/^(\w+):/);
                const isListItem = line.trimStart().startsWith("- type:");
                const color = isListItem ? "#7DD3FC" : isKey ? "#C4B5FD" : "#94A3B8";
                return <span key={i} style={{ color }}>{line}{"\n"}</span>;
              })}
            </pre>
          </div>
        )}

        {/* ── PREVIEW TAB ── */}
        {tab === "preview" && (
          <div style={{ textAlign:"center", paddingTop:32 }}>
            <div style={{ width:48, height:48, borderRadius:12, background:"#F1F5F9",
              display:"flex", alignItems:"center", justifyContent:"center", margin:"0 auto 12px" }}>
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
                <rect x="2" y="4" width="18" height="14" rx="2" stroke="#94A3B8" strokeWidth="1.4"/>
                <circle cx="11" cy="11" r="3" stroke="#94A3B8" strokeWidth="1.4"/>
                <line x1="11" y1="2" x2="11" y2="4" stroke="#94A3B8" strokeWidth="1.4" strokeLinecap="round"/>
              </svg>
            </div>
            <div style={{ fontSize:13, fontWeight:500, color:"#0F172A", marginBottom:6 }}>
              Live preview
            </div>
            <div style={{ fontSize:11, color:"#94A3B8", marginBottom:16, lineHeight:1.6 }}>
              Requires an active browser session.<br/>
              Connect to see live extraction results.
            </div>
            <button style={{
              padding:"9px 18px", borderRadius:8, fontSize:12, fontWeight:500,
              background:"#4F46E5", color:"white", border:"none", cursor:"pointer",
            }}>
              Connect browser
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
