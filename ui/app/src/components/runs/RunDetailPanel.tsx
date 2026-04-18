import type { RunState } from "../../types/runs";
import { STAGE_LABEL, canPause, canResume, canStop } from "../../types/runs";
import { StatusBadge } from "../ui/StatusBadge";
import { runsApi } from "../../api/runsApi";
import { useRunsStore } from "../../store/runsStore";

interface RunDetailPanelProps { run: RunState; }

function MetaRow({ label, value, mono = false }: { label: string; value: string | number | boolean | null; mono?: boolean }) {
  return (
    <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
      padding:"5px 0", borderBottom:"1px solid var(--border-0)" }}>
      <span style={{ fontSize:10, color:"var(--text-2)" }}>{label}</span>
      <span style={{ fontSize:11, color:"var(--text-1)",
        fontFamily: mono ? "var(--font-mono)" : "var(--font-ui)" }}>
        {value === null ? "—" : String(value)}
      </span>
    </div>
  );
}

export function RunDetailPanel({ run }: RunDetailPanelProps) {
  const setActiveRun = useRunsStore(s => s.setActiveRun);
  const upsertRun = useRunsStore(s => s.upsertRun);

  const act = async (fn: () => Promise<RunState>) => {
    try { const r = await fn(); setActiveRun(r); upsertRun(r); } catch {}
  };

  const pct = Math.round(run.progress * 100);

  return (
    <div style={{ height:"100%", display:"flex", flexDirection:"column", overflowY:"auto", padding:"14px" }}>
      {/* Header */}
      <div style={{ marginBottom:14 }}>
        <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:4 }}>
          <StatusBadge status={run.status}/>
        </div>
        <div style={{ fontSize:15, fontWeight:600, color:"var(--text-0)", marginBottom:2 }}>
          {run.scraper_name}
        </div>
        <div style={{ fontSize:10, color:"var(--text-2)", fontFamily:"var(--font-mono)",
          overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
          {run.target_url}
        </div>
      </div>

      {/* Progress */}
      <div style={{ marginBottom:14 }}>
        <div style={{ display:"flex", justifyContent:"space-between", marginBottom:5 }}>
          <span style={{ fontSize:10, color:"var(--text-2)" }}>
            {STAGE_LABEL[run.stage]}
          </span>
          <span style={{ fontSize:10, color:"var(--accent)", fontFamily:"var(--font-mono)" }}>
            {pct}%
          </span>
        </div>
        <div className="progress-track">
          <div className={`progress-fill ${run.status === "completed" ? "green" : ""}`}
            style={{ width:`${pct}%` }}/>
        </div>
      </div>

      {/* Stats grid */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:6, marginBottom:14 }}>
        {[
          ["Records", run.records_extracted],
          ["Stored",  run.records_stored],
          ["Pages",   run.pages_visited],
          ["Retries", run.retry_count],
          ["Warnings",run.warning_count],
          ["Errors",  run.error_count],
        ].map(([label, val]) => (
          <div key={String(label)} style={{
            background:"var(--bg-2)", borderRadius:6,
            padding:"8px 10px", border:"1px solid var(--border-0)"
          }}>
            <div style={{ fontSize:9, color:"var(--text-3)", marginBottom:2 }}>{label}</div>
            <div style={{ fontSize:18, fontWeight:600, color:"var(--text-0)",
              fontFamily:"var(--font-mono)" }}>
              {val}
            </div>
          </div>
        ))}
      </div>

      {/* Meta */}
      <div style={{ marginBottom:14 }}>
        <MetaRow label="Mode"    value={run.extraction_mode} mono/>
        <MetaRow label="Proxy"   value={String(run.proxy_enabled)}/>
        <MetaRow label="Stealth" value={String(run.stealth_enabled)}/>
        <MetaRow label="Run ID"  value={run.run_id.slice(0,8)+"…"} mono/>
      </div>

      {/* Controls */}
      <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
        {canPause(run.status) && (
          <button className="btn" style={{ width:"100%", justifyContent:"center" }}
            onClick={() => act(() => runsApi.pause(run.run_id))}>
            Pause
          </button>
        )}
        {canResume(run.status) && (
          <button className="btn btn-primary" style={{ width:"100%", justifyContent:"center" }}
            onClick={() => act(() => runsApi.resume(run.run_id))}>
            Resume
          </button>
        )}
        {canStop(run.status) && (
          <button className="btn btn-danger" style={{ width:"100%", justifyContent:"center" }}
            onClick={() => act(() => runsApi.stop(run.run_id))}>
            Stop run
          </button>
        )}
      </div>

      {/* Errors */}
      {run.errors.length > 0 && (
        <div style={{ marginTop:14 }}>
          <div style={{ fontSize:10, fontWeight:600, color:"var(--text-2)",
            letterSpacing:"0.07em", textTransform:"uppercase", marginBottom:6 }}>
            Errors
          </div>
          {run.errors.map((e, i) => (
            <div key={i} style={{ background:"var(--red-bg)", borderRadius:6,
              padding:"8px 10px", border:"1px solid rgba(226,75,74,.2)", marginBottom:4 }}>
              <div style={{ fontSize:11, color:"var(--red)", fontWeight:500, marginBottom:2 }}>
                {e.code}
              </div>
              <div style={{ fontSize:10, color:"var(--text-2)" }}>{e.message}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
