import { useState } from "react";
import { useStudioStore } from "../../store/studioStore";
import type { StrategyType } from "../../types/studio";

const TYPE_COLORS: Record<StrategyType, { bg: string; text: string; border: string }> = {
  css:   { bg: "#EEF4FF", text: "#2563EB", border: "#BFDBFE" },
  xpath: { bg: "#F0FDF4", text: "#16A34A", border: "#BBF7D0" },
  text:  { bg: "#FFFBEB", text: "#D97706", border: "#FDE68A" },
  attr:  { bg: "#FDF4FF", text: "#9333EA", border: "#E9D5FF" },
};

const SAMPLE_DATA: Record<string, string> = {
  match_card: "div.event",
  team_name:  "Boston Celtics",
  score:      "88–74",
  status:     "LIVE",
  match_time: "Q3 28'",
  match_url:  "/match/abc123",
};

function TypeBadge({ type }: { type: StrategyType }) {
  const c = TYPE_COLORS[type];
  return (
    <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 7px", borderRadius: 20,
      background: c.bg, color: c.text, border: `1px solid ${c.border}`,
      letterSpacing: "0.06em", textTransform: "uppercase" }}>
      {type.toUpperCase()}
    </span>
  );
}

function ConfBar({ value }: { value: number }) {
  const color = value >= 0.80 ? "#16A34A" : value >= 0.60 ? "#D97706" : "#DC2626";
  const bg    = value >= 0.80 ? "#DCFCE7" : value >= 0.60 ? "#FEF9C3" : "#FEE2E2";
  return (
    <div style={{ height: 3, borderRadius: 2, background: bg, overflow: "hidden", flex: 1 }}>
      <div style={{ height: "100%", width: `${Math.round(value * 100)}%`,
        background: color, borderRadius: 2, transition: "width 0.4s ease" }} />
    </div>
  );
}

export function SelectorPanel() {
  const { config, activeEntityId } = useStudioStore();
  const [tab, setTab] = useState<"selector" | "validation" | "yaml">("selector");
  const [copied, setCopied] = useState(false);

  const entity = config?.entities.find(e => e.id === activeEntityId);

  if (!entity) {
    return (
      <div style={{ height: "100%", display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", gap: 10, padding: 24,
        fontFamily: "system-ui, sans-serif" }}>
        <div style={{ width: 40, height: 40, borderRadius: 10, background: "#F1F5F9",
          display: "flex", alignItems: "center", justifyContent: "center" }}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <circle cx="9" cy="9" r="7" stroke="#94A3B8" strokeWidth="1.5"/>
            <path d="M9 5v4M9 11v.5" stroke="#94A3B8" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </div>
        <span style={{ fontSize: 12, color: "#94A3B8", textAlign: "center", lineHeight: 1.6 }}>
          Select an entity to view<br/>extraction details
        </span>
      </div>
    );
  }

  const sorted = [...entity.strategies].sort((a, b) => b.confidence - a.confidence);
  const best = sorted[0];
  const avgConf = entity.strategies.reduce((s, x) => s + x.confidence, 0) / (entity.strategies.length || 1);

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
      setCopied(true); setTimeout(() => setCopied(false), 2000);
    });
  };

  // Simulated field extraction rows
  const fieldRows = entity.strategies.slice(0, 3).map((s, i) => ({
    field: i === 0 ? entity.name : `${entity.name}_${i + 1}`,
    sample: SAMPLE_DATA[entity.name] ?? "—",
    rule: s.type.toUpperCase(),
    selector: s.selector,
    confidence: s.confidence,
  }));

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column",
      fontFamily: "system-ui, sans-serif", overflow: "hidden" }}>

      {/* ── Entity identity + CSS selector ── */}
      <div style={{ padding: "12px 16px", borderBottom: "1px solid #F1F5F9", flexShrink: 0 }}>
        <div style={{ fontSize: 11, color: "#94A3B8", marginBottom: 2 }}>
          <span style={{ color: "#4F46E5", fontWeight: 600 }}>{entity.name}</span>
          {" "}Element Analysis
        </div>

        {/* Primary selector pill */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8,
          background: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: 8, padding: "7px 10px" }}>
          <TypeBadge type={best?.type ?? "css"} />
          <span style={{ fontSize: 11, fontFamily: "monospace", color: "#334155",
            flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {best?.selector ?? "—"}
          </span>
          <span style={{ fontSize: 10, color: "#94A3B8", flexShrink: 0 }}>
            p:{best?.priority ?? 1}
          </span>
        </div>

        {/* Confidence label */}
        <div style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            fontSize: 10, fontWeight: 600, padding: "2px 8px", borderRadius: 20,
            background: best?.confidence >= 0.80 ? "#F0FDF4" : best?.confidence >= 0.60 ? "#FFFBEB" : "#FEF2F2",
            color: best?.confidence >= 0.80 ? "#16A34A" : best?.confidence >= 0.60 ? "#D97706" : "#DC2626",
            border: `1px solid ${best?.confidence >= 0.80 ? "#BBF7D0" : best?.confidence >= 0.60 ? "#FDE68A" : "#FECACA"}`,
          }}>
            {best?.confidence >= 0.80 ? "Container Selector: High Confidence"
              : best?.confidence >= 0.60 ? "Moderate Confidence"
              : "Low Confidence — Review Needed"}
          </div>
        </div>

        {/* Schema tree preview */}
        <div style={{ marginTop: 10, display: "flex", alignItems: "flex-start", gap: 8 }}>
          <div style={{ background: "#EEF2FF", border: "1px solid #C7D2FE",
            borderRadius: 6, padding: "3px 10px", fontSize: 11, fontWeight: 600, color: "#4338CA" }}>
            {entity.name}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <div style={{ width: 16, height: 1, background: "#CBD5E1" }} />
            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              {["time","teams","score","status"].map(f => (
                <div key={f} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <div style={{ width: 12, height: 1, background: "#E2E8F0" }} />
                  <span style={{ fontSize: 10, color: "#64748B" }}>{f}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Tabs ── */}
      <div style={{ display: "flex", borderBottom: "1px solid #E2E8F0", flexShrink: 0,
        background: "white" }}>
        {([
          { id: "selector", label: "Field Extraction Rules" },
          { id: "validation", label: "Checks" },
          { id: "yaml", label: "YAML" },
        ] as const).map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            style={{ flex: 1, padding: "8px 4px", fontSize: 11, fontWeight: 500,
              border: "none", cursor: "pointer", background: "transparent",
              color: tab === t.id ? "#4F46E5" : "#94A3B8",
              borderBottom: `2px solid ${tab === t.id ? "#4F46E5" : "transparent"}`,
              transition: "all 0.1s" }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Tab body ── */}
      <div style={{ flex: 1, overflowY: "auto" }}>

        {/* ── FIELD EXTRACTION RULES ── */}
        {tab === "selector" && (
          <div>
            {/* Table header */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 90px 60px 32px",
              padding: "6px 14px", borderBottom: "1px solid #F1F5F9", background: "#FAFAFA" }}>
              {["Field Name","Sample Data","Rule",""].map(h => (
                <span key={h} style={{ fontSize: 10, fontWeight: 600, color: "#94A3B8",
                  letterSpacing: "0.05em", textTransform: "uppercase" }}>{h}</span>
              ))}
            </div>

            {/* Rows */}
            {entity.strategies.map((s, i) => {
              const sample = i === 0 ? (SAMPLE_DATA[entity.name] ?? "—") : "—";
              return (
                <div key={i} style={{ display: "grid",
                  gridTemplateColumns: "1fr 90px 60px 32px",
                  padding: "8px 14px", borderBottom: "1px solid #F8FAFC",
                  alignItems: "center",
                  background: i === 0 ? "#FAFFFE" : "white",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    {i === 0 && (
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <circle cx="6" cy="6" r="5" fill="#4F46E5" opacity="0.12"/>
                        <path d="M3.5 6l1.8 1.8L8.5 4" stroke="#4F46E5" strokeWidth="1.2" strokeLinecap="round"/>
                      </svg>
                    )}
                    <span style={{ fontSize: 12, color: "#0F172A", fontWeight: i === 0 ? 500 : 400 }}>
                      {i === 0 ? entity.name : `${entity.name}_alt_${i}`}
                    </span>
                  </div>
                  <span style={{
                    fontSize: 11, fontFamily: "monospace",
                    background: i === 0 ? "#F0FDF4" : "#F8FAFC",
                    color: i === 0 ? "#16A34A" : "#64748B",
                    padding: "2px 7px", borderRadius: 4,
                    border: `1px solid ${i === 0 ? "#BBF7D0" : "#F1F5F9"}`,
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  }}>{sample}</span>
                  <TypeBadge type={s.type} />
                  <div style={{ display: "flex", gap: 4 }}>
                    {/* edit */}
                    <button style={{ border: "none", background: "none", cursor: "pointer",
                      color: "#94A3B8", padding: "2px", borderRadius: 4 }}>
                      <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                        <path d="M2 9.5L9 2.5l1.5 1.5-7 7H2V9.5z" stroke="#94A3B8" strokeWidth="1"/>
                      </svg>
                    </button>
                  </div>
                </div>
              );
            })}

            {/* Optimization Strategy */}
            <div style={{ margin: "10px 14px", background: "#F8FAFC",
              border: "1px solid #E2E8F0", borderRadius: 10, overflow: "hidden" }}>
              <div style={{ padding: "10px 12px", borderBottom: "1px solid #E2E8F0",
                display: "flex", alignItems: "center", gap: 8 }}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M7 1l1.5 3.5L12 5l-2.5 2.5.5 3.5L7 9.5 4 11l.5-3.5L2 5l3.5-.5L7 1z"
                    stroke="#4F46E5" strokeWidth="1.1" strokeLinejoin="round"/>
                </svg>
                <span style={{ fontSize: 12, fontWeight: 600, color: "#0F172A" }}>
                  Optimization Strategy
                </span>
                <button style={{ marginLeft: "auto", fontSize: 10, color: "#4F46E5",
                  background: "none", border: "none", cursor: "pointer", fontWeight: 500 }}>
                  ∨
                </button>
              </div>
              <div style={{ padding: "8px 12px 4px" }}>
                <div style={{ fontSize: 11, color: "#64748B", marginBottom: 8 }}>
                  Analyzes all rules under the optimal rules, and prioritized validated statuses.
                </div>
                <div style={{ fontSize: 11, fontWeight: 600, color: "#374151", marginBottom: 6 }}>
                  Extracted data fields
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 10 }}>
                  {sorted.slice(0, 3).map((s, i) => (
                    <div key={i} style={{
                      display: "flex", alignItems: "center", gap: 8,
                      background: "white", borderRadius: 7, padding: "6px 10px",
                      border: "1px solid #E2E8F0",
                    }}>
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                        <circle cx="5" cy="5" r="4.5" fill="#EEF2FF"/>
                        <path d="M2.5 5l1.8 1.8L7.5 3.5" stroke="#4F46E5" strokeWidth="1.1" strokeLinecap="round"/>
                      </svg>
                      <span style={{ fontSize: 11, color: "#334155",
                        fontFamily: "monospace", flex: 1,
                        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {s.selector}
                      </span>
                      <span style={{ fontSize: 9, fontWeight: 600, color: "#4F46E5",
                        background: "#EEF2FF", padding: "1px 6px", borderRadius: 4 }}>
                        P{i + 1}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Action buttons */}
            <div style={{ padding: "0 14px 14px", display: "flex", flexDirection: "column", gap: 6 }}>
              <button style={{ padding: "9px 12px", borderRadius: 8, fontSize: 12, fontWeight: 500,
                border: "1px solid #C7D2FE", background: "#EEF2FF", color: "#4338CA",
                cursor: "pointer", textAlign: "left", display: "flex", alignItems: "center", gap: 8 }}>
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                  <circle cx="6.5" cy="6.5" r="5.5" stroke="#4338CA" strokeWidth="1.1"/>
                  <path d="M4 6.5l2 2L9.5 4.5" stroke="#4338CA" strokeWidth="1.1" strokeLinecap="round"/>
                </svg>
                Auto-select best strategy
              </button>
              <button style={{ padding: "9px 12px", borderRadius: 8, fontSize: 12, fontWeight: 500,
                border: "1px solid #E2E8F0", background: "white", color: "#475569",
                cursor: "pointer", textAlign: "left", display: "flex", alignItems: "center", gap: 8 }}>
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                  <path d="M2 4h9M2 6.5h6M2 9h4" stroke="#475569" strokeWidth="1.1" strokeLinecap="round"/>
                </svg>
                Adjust priority order
              </button>
              <button style={{ padding: "9px 12px", borderRadius: 8, fontSize: 12, fontWeight: 500,
                border: "1px solid #E2E8F0", background: "white", color: "#475569",
                cursor: "pointer", textAlign: "left", display: "flex", alignItems: "center", gap: 8 }}>
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                  <line x1="6.5" y1="2" x2="6.5" y2="11" stroke="#475569" strokeWidth="1.1" strokeLinecap="round"/>
                  <line x1="2" y1="6.5" x2="11" y2="6.5" stroke="#475569" strokeWidth="1.1" strokeLinecap="round"/>
                </svg>
                Add fallback rule
              </button>
            </div>
          </div>
        )}

        {/* ── VALIDATION ── */}
        {tab === "validation" && (
          <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 8 }}>
            {[
              { label: "Confidence threshold",
                detail: `Best at ${Math.round((best?.confidence ?? 0) * 100)}% — threshold ${Math.round(entity.threshold * 100)}%`,
                pass: (best?.confidence ?? 0) >= entity.threshold },
              { label: "Match count",
                detail: entity.matches_found ? `${entity.matches_found} element(s) found` : "No matches",
                pass: (entity.matches_found ?? 0) > 0 },
              { label: "Fallback coverage",
                detail: entity.strategies.length > 1 ? `${entity.strategies.length} strategies` : "Single strategy — add fallback",
                pass: entity.strategies.length > 1 },
              { label: "Selector stability",
                detail: (best?.confidence ?? 0) >= 0.80 ? "Primary selector stable" : "Below 80% — consider alternatives",
                pass: (best?.confidence ?? 0) >= 0.80 },
            ].map(({ label, detail, pass }) => (
              <div key={label} style={{ background: "white", borderRadius: 8, padding: "10px 12px",
                border: `1px solid ${pass ? "#BBF7D0" : "#FECACA"}`,
                display: "flex", gap: 10, alignItems: "flex-start" }}>
                <div style={{ width: 20, height: 20, borderRadius: "50%", flexShrink: 0, marginTop: 1,
                  background: pass ? "#F0FDF4" : "#FEF2F2",
                  display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {pass
                    ? <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 5l2 2 4-4" stroke="#16A34A" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg>
                    : <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M3 3l4 4M7 3l-4 4" stroke="#DC2626" strokeWidth="1.3" strokeLinecap="round"/></svg>
                  }
                </div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 500, color: "#0F172A", marginBottom: 2 }}>{label}</div>
                  <div style={{ fontSize: 11, color: "#64748B" }}>{detail}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── YAML ── */}
        {tab === "yaml" && (
          <div style={{ padding: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: 11, color: "#64748B" }}>
                Config for <strong style={{ color: "#0F172A" }}>{entity.name}</strong>
              </span>
              <button onClick={copyYaml} style={{ padding: "4px 10px", fontSize: 10, fontWeight: 500,
                border: "1px solid #E2E8F0", borderRadius: 6,
                background: copied ? "#F0FDF4" : "white",
                color: copied ? "#16A34A" : "#475569", cursor: "pointer",
                display: "flex", alignItems: "center", gap: 5 }}>
                {copied ? "✓ Copied" : "Copy"}
              </button>
            </div>
            <pre style={{ background: "#0F172A", borderRadius: 10, padding: "14px 16px",
              fontSize: 11, fontFamily: "monospace", color: "#94A3B8",
              overflowX: "auto", whiteSpace: "pre-wrap", lineHeight: 1.7, margin: 0,
              border: "1px solid #1E293B" }}>
              {yaml.split("\n").map((line, i) => {
                const isKey = /^\w+:/.test(line);
                const isItem = line.trimStart().startsWith("- type:");
                return (
                  <span key={i} style={{ color: isItem ? "#7DD3FC" : isKey ? "#C4B5FD" : "#94A3B8" }}>
                    {line}{"\n"}
                  </span>
                );
              })}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
