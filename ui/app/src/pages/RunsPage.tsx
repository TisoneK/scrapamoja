import { useEffect, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { runsApi } from "../api/runsApi";
import { useRunsStore } from "../store/runsStore";
import { useRunStream } from "../hooks/useRunStream";
import { RunCard } from "../components/runs/RunCard";
import { RunDetailPanel } from "../components/runs/RunDetailPanel";
import { LiveLogStream } from "../components/runs/LiveLogStream";
import type { RunState } from "../types/runs";

function StartRunModal({ onClose, onStart }: { onClose: () => void; onStart: (v: { scraper_id: string; scraper_name: string; target_url: string }) => void }) {
  const [form, setForm] = useState({ scraper_id:"flashscore-basketball", scraper_name:"Flashscore Basketball", target_url:"https://www.flashscore.com/basketball/" });
  return (
    <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.6)", zIndex:100,
      display:"flex", alignItems:"center", justifyContent:"center" }} onClick={onClose}>
      <div style={{ background:"var(--bg-2)", border:"1px solid var(--border-2)",
        borderRadius:12, padding:24, width:420, maxWidth:"90vw" }} onClick={e => e.stopPropagation()}>
        <div style={{ fontSize:14, fontWeight:600, color:"var(--text-0)", marginBottom:16 }}>
          Start new run
        </div>
        {[
          ["Scraper ID",   "scraper_id",   "flashscore-basketball"],
          ["Scraper name", "scraper_name", "Flashscore Basketball"],
          ["Target URL",   "target_url",   "https://…"],
        ].map(([label, key, placeholder]) => (
          <div key={key} style={{ marginBottom:12 }}>
            <label style={{ fontSize:10, color:"var(--text-2)", display:"block", marginBottom:4 }}>{label}</label>
            <input value={(form as any)[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
              placeholder={placeholder}
              style={{ width:"100%", background:"var(--bg-3)", border:"1px solid var(--border-2)",
                borderRadius:6, padding:"7px 10px", fontSize:12, color:"var(--text-0)",
                fontFamily:"var(--font-mono)", outline:"none" }}/>
          </div>
        ))}
        <div style={{ display:"flex", gap:8, marginTop:16 }}>
          <button className="btn" style={{ flex:1, justifyContent:"center" }} onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" style={{ flex:1, justifyContent:"center" }}
            onClick={() => { onStart(form); onClose(); }}>
            Run
          </button>
        </div>
      </div>
    </div>
  );
}

export function RunsPage() {
  const { runs, activeRun, selectedRunId, setRuns, setActiveRun, setSelectedRunId, upsertRun, appendLog } = useRunsStore();
  const [showModal, setShowModal] = useState(false);
  const [filter, setFilter] = useState<string>("all");

  const { data, refetch } = useQuery({
    queryKey: ["runs", filter],
    queryFn: () => runsApi.list(filter !== "all" ? { status: filter } : undefined),
    refetchInterval: 5000,
  });

  useEffect(() => { if (data) setRuns(data); }, [data, setRuns]);

  const startMutation = useMutation({
    mutationFn: runsApi.start,
    onSuccess: (run) => { upsertRun(run); setSelectedRunId(run.run_id); setActiveRun(run); refetch(); },
  });

  const selectedRun = runs.find(r => r.run_id === selectedRunId);

  // Stream active run
  useRunStream(selectedRunId, {
    onStateChanged: (s) => { upsertRun(s); if (selectedRunId === s.run_id) setActiveRun(s); },
    onLog: (d) => appendLog({ level: (d.level as any) ?? "info", message: String(d.message ?? ""), timestamp: d.timestamp }),
    onTerminal: (s) => { upsertRun(s); setActiveRun(s); },
  });

  const handleSelect = async (runId: string) => {
    setSelectedRunId(runId);
    try { const r = await runsApi.get(runId); setActiveRun(r as RunState); } catch {}
  };

  const FILTERS = ["all","running","queued","completed","failed"];

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%", overflow:"hidden" }}>
      {/* Top bar */}
      <div style={{ height:44, background:"var(--bg-1)", borderBottom:"1px solid var(--border-1)",
        display:"flex", alignItems:"center", padding:"0 16px", gap:12, flexShrink:0 }}>
        <span style={{ fontSize:11, fontWeight:600, color:"var(--text-2)",
          letterSpacing:"0.08em", textTransform:"uppercase" }}>
          Runs
        </span>
        <div style={{ display:"flex", gap:2, marginLeft:8 }}>
          {FILTERS.map(f => (
            <button key={f} className={`btn btn-sm ${filter === f ? "btn-primary" : "btn-ghost"}`}
              style={{ padding:"3px 9px", fontSize:10 }}
              onClick={() => setFilter(f)}>
              {f}
            </button>
          ))}
        </div>
        <div style={{ marginLeft:"auto", display:"flex", gap:8, alignItems:"center" }}>
          <span style={{ fontSize:10, color:"var(--text-3)", fontFamily:"var(--font-mono)" }}>
            {runs.length} job{runs.length !== 1 ? "s" : ""}
          </span>
          <button className="btn btn-primary btn-sm" onClick={() => setShowModal(true)}>
            + New run
          </button>
        </div>
      </div>

      {/* Body: 3 columns */}
      <div style={{ flex:1, display:"grid", gridTemplateColumns:"220px 1fr 260px", overflow:"hidden" }}>
        {/* Run list */}
        <div style={{ borderRight:"1px solid var(--border-1)", overflowY:"auto", background:"var(--bg-1)" }}>
          {runs.length === 0 ? (
            <div style={{ padding:24, textAlign:"center", color:"var(--text-3)", fontSize:11 }}>
              No runs yet.<br/>
              <button className="btn btn-sm" style={{ marginTop:10 }} onClick={() => setShowModal(true)}>
                Start one
              </button>
            </div>
          ) : (
            runs.map(run => (
              <RunCard key={run.run_id} run={run}
                active={run.run_id === selectedRunId}
                onClick={() => handleSelect(run.run_id)}
                onStop={() => runsApi.stop(run.run_id).then(r => upsertRun(r as RunState))}
              />
            ))
          )}
        </div>

        {/* Log stream */}
        <div style={{ background:"var(--bg-0)", overflow:"hidden", display:"flex", flexDirection:"column" }}>
          <div className="panel" style={{ flex:1, borderRadius:0, border:"none",
            borderRight:"1px solid var(--border-1)", display:"flex", flexDirection:"column" }}>
            <LiveLogStream/>
          </div>
        </div>

        {/* Run detail */}
        <div style={{ background:"var(--bg-1)", borderLeft:"1px solid var(--border-1)", overflowY:"auto" }}>
          {activeRun ? (
            <RunDetailPanel run={activeRun}/>
          ) : (
            <div style={{ padding:24, textAlign:"center", color:"var(--text-3)", fontSize:11, paddingTop:40 }}>
              Select a run to inspect
            </div>
          )}
        </div>
      </div>

      {showModal && (
        <StartRunModal
          onClose={() => setShowModal(false)}
          onStart={(v) => startMutation.mutate({ ...v, extraction_mode:"dom", stealth_enabled:true })}
        />
      )}
    </div>
  );
}
