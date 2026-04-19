import { useEffect, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { runsApi } from "../api/runsApi";
import { useRunsStore } from "../store/runsStore";
import { useRunStream } from "../hooks/useRunStream";
import type { RunState } from "../types/runs";
import { STAGE_LABEL, canStop, canPause, canResume, isTerminal } from "../types/runs";

const D = {
  bg0:"#0e0f14", bg1:"#111318", bg2:"#171820", bg3:"#1c1d27",
  border0:"#1a1b22", border1:"#22232e",
  text0:"#e2e2e8", text1:"#a0a0b4", text2:"#565668", text3:"#32333e",
  accent:"#4f46e5", accentBg:"#15152a", accentBorder:"#2d2b5a",
  green:"#1D9E75", greenBg:"#0a2018", greenBorder:"rgba(29,158,117,0.25)",
  amber:"#EF9F27", amberBg:"#1a1200", amberBorder:"rgba(239,159,39,0.25)",
  red:"#E24B4A", redBg:"#1a0808", redBorder:"rgba(226,75,74,0.25)",
  blue:"#378ADD", blueBg:"#081828", blueBorder:"rgba(55,138,221,0.25)",
};

const STATUS_COLOR: Record<string,string> = {
  queued:D.text2, starting:D.amber, running:D.green,
  paused:D.blue, stopping:D.amber, completed:D.green,
  failed:D.red, cancelled:D.text2,
};
const STATUS_BG: Record<string,string> = {
  queued:D.bg3, starting:D.amberBg, running:D.greenBg,
  paused:D.blueBg, stopping:D.amberBg, completed:D.greenBg,
  failed:D.redBg, cancelled:D.bg3,
};

function StatusDot({status}:{status:string}) {
  return <div style={{ width:7,height:7,borderRadius:"50%",background:STATUS_COLOR[status]??D.text2,flexShrink:0,
    animation:status==="running"?"pulse-dot 1.4s ease-in-out infinite":"none" }}/>;
}

function StatusPill({status}:{status:string}) {
  return (
    <span style={{ display:"inline-flex",alignItems:"center",gap:5,padding:"2px 9px",borderRadius:20,
      fontSize:10,fontWeight:600,
      background:STATUS_BG[status]??D.bg3,
      color:STATUS_COLOR[status]??D.text2,
      border:`1px solid ${STATUS_COLOR[status]??D.text2}40` }}>
      <StatusDot status={status}/>{status}
    </span>
  );
}

function fmt(secs:number|null){
  if(secs===null)return"—";
  if(secs<60)return`${Math.round(secs)}s`;
  return`${Math.floor(secs/60)}m ${Math.round(secs%60)}s`;
}

function StartRunModal({onClose,onStart}:{onClose:()=>void;onStart:(v:{scraper_id:string;scraper_name:string;target_url:string})=>void}) {
  const [form,setForm]=useState({scraper_id:"flashscore-basketball",scraper_name:"Flashscore Basketball",target_url:"https://www.flashscore.com/basketball/"});
  return (
    <div style={{ position:"fixed",inset:0,background:"rgba(0,0,0,0.7)",zIndex:100,
      display:"flex",alignItems:"center",justifyContent:"center" }} onClick={onClose}>
      <div style={{ background:D.bg2,border:`1px solid ${D.border1}`,borderRadius:12,
        padding:24,width:420,maxWidth:"90vw" }} onClick={e=>e.stopPropagation()}>
        <div style={{ fontSize:14,fontWeight:600,color:D.text0,marginBottom:16 }}>Start new run</div>
        {[["Scraper ID","scraper_id"],["Scraper name","scraper_name"],["Target URL","target_url"]].map(([label,key])=>(
          <div key={key} style={{ marginBottom:12 }}>
            <label style={{ fontSize:10,color:D.text2,display:"block",marginBottom:4,textTransform:"uppercase",letterSpacing:"0.06em" }}>{label}</label>
            <input value={(form as any)[key]} onChange={e=>setForm(f=>({...f,[key]:e.target.value}))}
              style={{ width:"100%",background:D.bg3,border:`1px solid ${D.border1}`,borderRadius:7,
                padding:"7px 10px",fontSize:12,color:D.text0,fontFamily:"monospace",outline:"none" }}/>
          </div>
        ))}
        <div style={{ display:"flex",gap:8,marginTop:16 }}>
          <button onClick={onClose} style={{ flex:1,padding:"8px 0",border:`1px solid ${D.border1}`,borderRadius:8,
            background:"transparent",color:D.text1,cursor:"pointer",fontSize:12 }}>Cancel</button>
          <button onClick={()=>{onStart(form);onClose();}} style={{ flex:1,padding:"8px 0",border:"none",
            borderRadius:8,background:D.accent,color:"white",cursor:"pointer",fontSize:12,fontWeight:600 }}>Run</button>
        </div>
      </div>
    </div>
  );
}

export function RunsPage() {
  const { runs,activeRun,selectedRunId,setRuns,setActiveRun,setSelectedRunId,upsertRun,appendLog,logs,clearLogs } = useRunsStore();
  const [showModal,setShowModal]=useState(false);
  const [filter,setFilter]=useState("all");

  const {data,refetch}=useQuery({
    queryKey:["runs",filter],
    queryFn:()=>runsApi.list(filter!=="all"?{status:filter}:undefined),
    refetchInterval:5000,
  });
  useEffect(()=>{ if(data)setRuns(data); },[data,setRuns]);

  const startMutation=useMutation({
    mutationFn:runsApi.start,
    onSuccess:(run)=>{ upsertRun(run);setSelectedRunId(run.run_id);setActiveRun(run);refetch(); },
  });

  useRunStream(selectedRunId,{
    onStateChanged:(s)=>{ upsertRun(s);if(selectedRunId===s.run_id)setActiveRun(s); },
    onLog:(d)=>appendLog({level:(d.level as any)??"info",message:String(d.message??""),timestamp:d.timestamp}),
    onTerminal:(s)=>{ upsertRun(s);setActiveRun(s); },
  });

  const handleSelect=async(runId:string)=>{
    setSelectedRunId(runId);
    try{const r=await runsApi.get(runId);setActiveRun(r as RunState);}catch{}
  };

  const FILTERS=["all","running","queued","completed","failed"];

  return (
    <div style={{ display:"flex",flexDirection:"column",height:"100%",overflow:"hidden",
      background:D.bg0,fontFamily:"system-ui, sans-serif",color:D.text0 }}>

      {/* Topbar */}
      <div style={{ height:50,background:D.bg1,borderBottom:`1px solid ${D.border1}`,
        display:"flex",alignItems:"center",padding:"0 16px",gap:10,flexShrink:0 }}>
        <span style={{ fontSize:13,fontWeight:600,color:D.text0 }}>Runs</span>
        <div style={{ width:1,height:18,background:D.border1 }}/>
        <div style={{ display:"flex",gap:2 }}>
          {FILTERS.map(f=>(
            <button key={f} onClick={()=>setFilter(f)}
              style={{ padding:"4px 10px",fontSize:11,fontWeight:500,borderRadius:6,border:"none",
                cursor:"pointer",
                background:filter===f?D.accent:"transparent",
                color:filter===f?"white":D.text2,
                transition:"all 0.12s" }}>{f}</button>
          ))}
        </div>
        <div style={{ marginLeft:"auto",display:"flex",gap:8,alignItems:"center" }}>
          <span style={{ fontSize:10,color:D.text3,fontFamily:"monospace" }}>
            {runs.length} job{runs.length!==1?"s":""}
          </span>
          <button onClick={()=>setShowModal(true)}
            style={{ padding:"6px 14px",fontSize:12,fontWeight:600,border:"none",
              borderRadius:8,background:D.accent,color:"white",cursor:"pointer",
              display:"flex",alignItems:"center",gap:6 }}>
            <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
              <line x1="5.5" y1="1" x2="5.5" y2="10" stroke="white" strokeWidth="1.4" strokeLinecap="round"/>
              <line x1="1" y1="5.5" x2="10" y2="5.5" stroke="white" strokeWidth="1.4" strokeLinecap="round"/>
            </svg>
            New run
          </button>
        </div>
      </div>

      {/* 3-column body */}
      <div style={{ flex:1,display:"grid",gridTemplateColumns:"220px 1fr 280px",overflow:"hidden" }}>

        {/* Run list */}
        <div style={{ background:D.bg1,borderRight:`1px solid ${D.border1}`,overflowY:"auto" }}>
          {runs.length===0 ? (
            <div style={{ padding:28,textAlign:"center",color:D.text3,fontSize:12 }}>
              No runs yet.
              <br/>
              <button onClick={()=>setShowModal(true)}
                style={{ marginTop:10,padding:"6px 14px",border:`1px solid ${D.border1}`,
                  borderRadius:8,background:"transparent",color:D.text1,cursor:"pointer",fontSize:11 }}>
                Start one
              </button>
            </div>
          ) : runs.map(run=>{
            const active=run.run_id===selectedRunId;
            return (
              <div key={run.run_id} onClick={()=>handleSelect(run.run_id)}
                style={{ padding:"11px 14px",cursor:"pointer",
                  background:active?D.accentBg:"transparent",
                  borderLeft:`3px solid ${active?D.accent:"transparent"}`,
                  borderBottom:`1px solid ${D.border0}`,transition:"all 0.1s" }}>
                <div style={{ display:"flex",alignItems:"center",gap:8,marginBottom:6 }}>
                  <StatusPill status={run.status}/>
                  <span style={{ fontSize:12,fontWeight:600,color:D.text0,flex:1,
                    overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap" }}>
                    {run.scraper_name}
                  </span>
                </div>
                {!isTerminal(run.status as any)&&(
                  <div style={{ height:3,borderRadius:2,background:"rgba(255,255,255,0.06)",overflow:"hidden",marginBottom:5 }}>
                    <div style={{ height:"100%",width:`${Math.round(run.progress*100)}%`,
                      background:D.accent,borderRadius:2,transition:"width 0.4s ease" }}/>
                  </div>
                )}
                <div style={{ display:"flex",gap:10,alignItems:"center" }}>
                  <span style={{ fontSize:10,color:D.text2 }}>{STAGE_LABEL[run.stage]}</span>
                  <span style={{ fontSize:10,color:D.text3,marginLeft:"auto",fontFamily:"monospace" }}>
                    {run.records_extracted} rec
                  </span>
                  {run.warning_count>0&&<span style={{ fontSize:10,color:D.amber }}>⚠{run.warning_count}</span>}
                  {run.error_count>0&&<span style={{ fontSize:10,color:D.red }}>✕{run.error_count}</span>}
                  <span style={{ fontSize:10,color:D.text3,fontFamily:"monospace" }}>{fmt(run.duration_seconds)}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Log stream */}
        <div style={{ background:D.bg0,overflow:"hidden",display:"flex",flexDirection:"column",
          borderRight:`1px solid ${D.border1}` }}>
          <div style={{ height:44,padding:"0 14px",borderBottom:`1px solid ${D.border1}`,
            display:"flex",alignItems:"center",justifyContent:"space-between",flexShrink:0 }}>
            <span style={{ fontSize:11,fontWeight:600,color:D.text2,
              letterSpacing:"0.07em",textTransform:"uppercase" }}>Live log</span>
            <button onClick={clearLogs} style={{ fontSize:10,color:D.text2,border:`1px solid ${D.border0}`,
              background:"transparent",borderRadius:6,padding:"3px 8px",cursor:"pointer" }}>Clear</button>
          </div>
          <div style={{ flex:1,overflowY:"auto",padding:"4px 0" }}>
            {logs.length===0 ? (
              <div style={{ padding:"20px 14px",fontSize:11,color:D.text3,
                fontFamily:"monospace",textAlign:"center" }}>Waiting for log events…</div>
            ) : logs.map(log=>(
              <div key={log.id} style={{ padding:"2px 14px",fontSize:11,
                fontFamily:"monospace",lineHeight:1.6,borderBottom:`1px solid ${D.border0}`,
                display:"flex",gap:10 }}>
                <span style={{ color:D.text3,flexShrink:0 }}>
                  {new Date(log.timestamp*1000).toLocaleTimeString("en-GB",{hour12:false})}
                </span>
                <span style={{ color:log.level==="error"?D.red:log.level==="warning"?D.amber:D.blue }}>
                  [{log.level.toUpperCase()}]
                </span>
                <span style={{ color:D.text1 }}>{log.message}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Run detail */}
        <div style={{ background:D.bg1,overflowY:"auto" }}>
          {activeRun ? (
            <div style={{ padding:14 }}>
              <div style={{ marginBottom:14 }}>
                <div style={{ display:"flex",alignItems:"center",gap:8,marginBottom:4 }}>
                  <StatusPill status={activeRun.status}/>
                </div>
                <div style={{ fontSize:15,fontWeight:600,color:D.text0,marginBottom:2 }}>
                  {activeRun.scraper_name}
                </div>
                <div style={{ fontSize:10,color:D.text2,fontFamily:"monospace",
                  overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap" }}>
                  {activeRun.target_url}
                </div>
              </div>

              {/* Progress */}
              <div style={{ marginBottom:14 }}>
                <div style={{ display:"flex",justifyContent:"space-between",marginBottom:5 }}>
                  <span style={{ fontSize:10,color:D.text2 }}>{STAGE_LABEL[activeRun.stage]}</span>
                  <span style={{ fontSize:10,color:D.accent,fontFamily:"monospace" }}>
                    {Math.round(activeRun.progress*100)}%
                  </span>
                </div>
                <div style={{ height:4,borderRadius:2,background:"rgba(255,255,255,0.06)",overflow:"hidden" }}>
                  <div style={{ height:"100%",width:`${Math.round(activeRun.progress*100)}%`,
                    background:activeRun.status==="completed"?D.green:D.accent,
                    borderRadius:2,transition:"width 0.4s ease" }}/>
                </div>
              </div>

              {/* Stats */}
              <div style={{ display:"grid",gridTemplateColumns:"1fr 1fr",gap:6,marginBottom:14 }}>
                {[["Records",activeRun.records_extracted],["Stored",activeRun.records_stored],
                  ["Pages",activeRun.pages_visited],["Retries",activeRun.retry_count],
                  ["Warnings",activeRun.warning_count],["Errors",activeRun.error_count]
                ].map(([label,val])=>(
                  <div key={String(label)} style={{ background:D.bg2,borderRadius:6,padding:"8px 10px",
                    border:`1px solid ${D.border0}` }}>
                    <div style={{ fontSize:9,color:D.text3,marginBottom:2 }}>{label}</div>
                    <div style={{ fontSize:18,fontWeight:600,color:D.text0,fontFamily:"monospace" }}>{val}</div>
                  </div>
                ))}
              </div>

              {/* Meta */}
              <div style={{ marginBottom:14 }}>
                {[["Mode",activeRun.extraction_mode],["Proxy",String(activeRun.proxy_enabled)],
                  ["Stealth",String(activeRun.stealth_enabled)],
                  ["Run ID",activeRun.run_id.slice(0,8)+"…"]
                ].map(([k,v])=>(
                  <div key={String(k)} style={{ display:"flex",justifyContent:"space-between",
                    alignItems:"center",padding:"5px 0",borderBottom:`1px solid ${D.border0}` }}>
                    <span style={{ fontSize:10,color:D.text2 }}>{k}</span>
                    <span style={{ fontSize:11,color:D.text1,fontFamily:"monospace" }}>{v}</span>
                  </div>
                ))}
              </div>

              {/* Controls */}
              <div style={{ display:"flex",flexDirection:"column",gap:6 }}>
                {canPause(activeRun.status as any)&&(
                  <button onClick={()=>runsApi.pause(activeRun.run_id).then(r=>setActiveRun(r as RunState))}
                    style={{ padding:"8px",borderRadius:8,fontSize:12,fontWeight:500,
                      border:`1px solid ${D.border1}`,background:D.bg2,color:D.text1,cursor:"pointer" }}>
                    Pause
                  </button>
                )}
                {canResume(activeRun.status as any)&&(
                  <button onClick={()=>runsApi.resume(activeRun.run_id).then(r=>setActiveRun(r as RunState))}
                    style={{ padding:"8px",borderRadius:8,fontSize:12,fontWeight:600,
                      border:"none",background:D.accent,color:"white",cursor:"pointer" }}>
                    Resume
                  </button>
                )}
                {canStop(activeRun.status as any)&&(
                  <button onClick={()=>runsApi.stop(activeRun.run_id).then(r=>setActiveRun(r as RunState))}
                    style={{ padding:"8px",borderRadius:8,fontSize:12,fontWeight:500,
                      border:`1px solid ${D.redBorder}`,background:D.redBg,color:D.red,cursor:"pointer" }}>
                    Stop run
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div style={{ padding:28,textAlign:"center",color:D.text3,fontSize:12,paddingTop:48 }}>
              Select a run to inspect
            </div>
          )}
        </div>
      </div>

      {showModal&&(
        <StartRunModal onClose={()=>setShowModal(false)}
          onStart={(v)=>startMutation.mutate({...v,extraction_mode:"dom",stealth_enabled:true})}/>
      )}
    </div>
  );
}
