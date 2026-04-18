import type { RunStatus } from "../../types/runs";

export function StatusDot({ status }: { status: RunStatus }) {
  const colors: Record<RunStatus, string> = {
    queued:"#5f5d7a", starting:"#EF9F27", running:"#1D9E75",
    paused:"#378ADD", stopping:"#EF9F27", completed:"#1D9E75",
    failed:"#E24B4A", cancelled:"#5f5d7a",
  };
  return (
    <div style={{
      width:7, height:7, borderRadius:"50%", flexShrink:0,
      background: colors[status],
      animation: status === "running" ? "pulse-dot 1.4s ease-in-out infinite" : "none",
    }}/>
  );
}

export function StatusBadge({ status }: { status: RunStatus }) {
  return (
    <span className={`status-pill status-${status}`}>
      <StatusDot status={status}/>
      {status}
    </span>
  );
}
