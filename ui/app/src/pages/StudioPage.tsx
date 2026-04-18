import { useState } from "react";
import { useStudioStore } from "../store/studioStore";
import { EntityRail } from "../components/studio/EntityRail";
import { BrowserCanvas } from "../components/studio/BrowserCanvas";
import { SelectorPanel } from "../components/studio/SelectorPanel";
import { ConfidenceHeatmap } from "../components/studio/ConfidenceHeatmap";

export function StudioPage() {
  const { config, mode, setMode } = useStudioStore();
  const [panelOpen, setPanelOpen] = useState(true);

  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "100%",
      overflow: "hidden", background: "#F8FAFC", fontFamily: "system-ui, sans-serif",
    }}>

      {/* ── Topbar ── */}
      <div style={{
        height: 52, background: "white",
        borderBottom: "1px solid #E2E8F0",
        display: "flex", alignItems: "center",
        padding: "0 16px", gap: 0, flexShrink: 0,
      }}>
        {/* Breadcrumb */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginRight: 20 }}>
          <span style={{ fontSize: 13, color: "#94A3B8" }}>Scrapamoja</span>
          <span style={{ color: "#CBD5E1", fontSize: 13 }}>/</span>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#0F172A" }}>Studio</span>
        </div>

        {/* Divider */}
        <div style={{ width: 1, height: 20, background: "#E2E8F0", marginRight: 16 }} />

        {/* Project name */}
        <span style={{ fontSize: 13, color: "#475569", marginRight: 8 }}>
          {config?.name ?? "No project"}
        </span>

        {/* URL pill */}
        <div style={{
          display: "flex", alignItems: "center", gap: 6,
          background: "#F1F5F9", border: "1px solid #E2E8F0",
          borderRadius: 20, padding: "3px 10px",
        }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#F59E0B" }} />
          <span style={{ fontSize: 11, color: "#64748B", fontFamily: "monospace" }}>
            {config?.target_url?.replace("https://", "") ?? ""}
          </span>
        </div>

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Visual / Expert toggle */}
        <div style={{
          display: "flex", background: "#F1F5F9",
          border: "1px solid #E2E8F0", borderRadius: 8,
          padding: 3, gap: 2, marginRight: 10,
        }}>
          {(["Visual", "Expert"] as const).map(m => {
            const active = mode === m.toLowerCase();
            return (
              <button key={m}
                onClick={() => setMode(m.toLowerCase() as "visual" | "expert")}
                style={{
                  padding: "5px 14px", fontSize: 12, fontWeight: 500,
                  borderRadius: 6, border: "none", cursor: "pointer",
                  background: active ? "white" : "transparent",
                  color: active ? "#4F46E5" : "#94A3B8",
                  boxShadow: active ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
                  transition: "all 0.15s",
                }}>
                {m}
              </button>
            );
          })}
        </div>

        {/* Add entity */}
        <button style={{
          padding: "7px 14px", fontSize: 12, fontWeight: 500,
          border: "1px solid #E2E8F0", borderRadius: 8,
          background: "white", color: "#475569", cursor: "pointer",
          display: "flex", alignItems: "center", gap: 6, marginRight: 8,
        }}>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <line x1="6" y1="1" x2="6" y2="11" stroke="#475569" strokeWidth="1.4" strokeLinecap="round"/>
            <line x1="1" y1="6" x2="11" y2="6" stroke="#475569" strokeWidth="1.4" strokeLinecap="round"/>
          </svg>
          Add Entity
        </button>

        {/* Stop */}
        <button style={{
          padding: "7px 14px", fontSize: 12, fontWeight: 500,
          border: "1px solid #FECACA", borderRadius: 8,
          background: "#FEF2F2", color: "#DC2626", cursor: "pointer",
          marginRight: 8,
        }}>
          Stop
        </button>

        {/* Run scrape */}
        <button style={{
          padding: "7px 16px", fontSize: 12, fontWeight: 600,
          border: "none", borderRadius: 8,
          background: "#4F46E5", color: "white", cursor: "pointer",
          display: "flex", alignItems: "center", gap: 6,
        }}>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M3 2l7 4-7 4V2z" fill="white"/>
          </svg>
          Run Scrape
        </button>
      </div>

      {/* ── Workspace ── */}
      <div style={{
        flex: 1, display: "grid",
        gridTemplateColumns: `220px 1fr ${panelOpen ? "320px" : "0px"}`,
        gridTemplateRows: "1fr auto",
        overflow: "hidden",
        transition: "grid-template-columns 0.2s ease",
      }}>

        {/* Left rail */}
        <div style={{
          gridRow: "1/3", background: "white",
          borderRight: "1px solid #E2E8F0",
          overflow: "hidden", display: "flex", flexDirection: "column",
        }}>
          <EntityRail />
        </div>

        {/* Browser canvas */}
        <div style={{ gridRow: 1, overflow: "hidden", background: "#F8FAFC" }}>
          <BrowserCanvas />
        </div>

        {/* Right panel — Extraction Details */}
        {panelOpen && (
          <div style={{
            gridRow: "1/3", background: "white",
            borderLeft: "1px solid #E2E8F0",
            overflow: "hidden", display: "flex", flexDirection: "column",
          }}>
            {/* Panel header */}
            <div style={{
              height: 48, padding: "0 16px",
              borderBottom: "1px solid #E2E8F0",
              display: "flex", alignItems: "center", justifyContent: "space-between",
              flexShrink: 0,
            }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "#0F172A" }}>
                Extraction Details
              </span>
              <button onClick={() => setPanelOpen(false)}
                style={{ border: "none", background: "none", cursor: "pointer",
                  color: "#94A3B8", fontSize: 18, lineHeight: 1, padding: "2px 4px" }}>
                ×
              </button>
            </div>
            <div style={{ flex: 1, overflow: "hidden" }}>
              <SelectorPanel />
            </div>
          </div>
        )}

        {/* Confidence heatmap bottom bar */}
        <div style={{ gridRow: 2, gridColumn: 2 }}>
          <ConfidenceHeatmap />
        </div>
      </div>

      {/* Re-open panel button if closed */}
      {!panelOpen && (
        <button
          onClick={() => setPanelOpen(true)}
          style={{
            position: "fixed", right: 16, top: "50%", transform: "translateY(-50%)",
            background: "#4F46E5", color: "white", border: "none",
            borderRadius: "0 8px 8px 0", padding: "12px 6px",
            cursor: "pointer", fontSize: 11, writingMode: "vertical-rl",
            letterSpacing: "0.05em",
          }}>
          Details
        </button>
      )}
    </div>
  );
}
