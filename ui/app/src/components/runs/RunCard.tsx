import type { RunSummary } from "../../types/runs";
import { STAGE_LABEL, canStop, isTerminal } from "../../types/runs";
import { StatusBadge } from "../ui/StatusBadge";

interface RunCardProps {
  run: RunSummary;
  active: boolean;
  onClick: () => void;
  onStop?: () => void;
}

function fmt(secs: number | null) {
  if (secs === null) return "—";
  if (secs < 60) return `${Math.round(secs)}s`;
  return `${Math.floor(secs/60)}m ${Math.round(secs%60)}s`;
}

export function RunCard({ run, active, onClick, onStop }: RunCardProps) {
  return (
    <div
      onClick={onClick}
      style={{
        padding:"11px 14px", cursor:"pointer",
        background: active ? "var(--accent-bg)" : "transparent",
        borderLeft: `3px solid ${active ? "var(--accent)" : "transparent"}`,
        borderBottom: "1px solid var(--border-0)",
        transition: "all 0.1s",
      }}
      onMouseEnter={e => { if (!active) (e.currentTarget as HTMLDivElement).style.background = "var(--bg-2)"; }}
      onMouseLeave={e => { if (!active) (e.currentTarget as HTMLDivElement).style.background = "transparent"; }}
    >
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:6 }}>
        <StatusBadge status={run.status}/>
        <span style={{ fontSize:12, fontWeight:600, color:"var(--text-0)", flex:1, overflow:"hidden",
          textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
          {run.scraper_name}
        </span>
        {canStop(run.status) && onStop && (
          <button className="btn btn-sm btn-ghost" onClick={e => { e.stopPropagation(); onStop(); }}
            style={{ padding:"2px 7px", fontSize:10 }}>
            Stop
          </button>
        )}
      </div>

      {/* Progress bar */}
      {!isTerminal(run.status) && (
        <div className="progress-track" style={{ marginBottom:6 }}>
          <div className="progress-fill" style={{ width: `${Math.round(run.progress * 100)}%` }}/>
        </div>
      )}

      <div style={{ display:"flex", gap:12, alignItems:"center" }}>
        <span style={{ fontSize:10, color:"var(--text-2)", fontFamily:"var(--font-mono)" }}>
          {STAGE_LABEL[run.stage]}
        </span>
        <span style={{ fontSize:10, color:"var(--text-3)", marginLeft:"auto" }}>
          {run.records_extracted} rec
        </span>
        {run.warning_count > 0 && (
          <span style={{ fontSize:10, color:"var(--amber)" }}>⚠ {run.warning_count}</span>
        )}
        {run.error_count > 0 && (
          <span style={{ fontSize:10, color:"var(--red)" }}>✕ {run.error_count}</span>
        )}
        <span style={{ fontSize:10, color:"var(--text-3)", fontFamily:"var(--font-mono)" }}>
          {fmt(run.duration_seconds)}
        </span>
      </div>
    </div>
  );
}
