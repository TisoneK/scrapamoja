import { useEffect, useRef } from "react";
import { useRunsStore } from "../../store/runsStore";

export function LiveLogStream() {
  const logs = useRunsStore(s => s.logs);
  const clearLogs = useRunsStore(s => s.clearLogs);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior:"smooth" });
  }, [logs.length]);

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%" }}>
      <div className="panel-header">
        <span className="panel-title">Live log</span>
        <button className="btn btn-ghost btn-sm" onClick={clearLogs}
          style={{ fontSize:10, padding:"2px 8px" }}>
          Clear
        </button>
      </div>
      <div style={{ flex:1, overflowY:"auto", padding:"4px 0" }}>
        {logs.length === 0 ? (
          <div style={{ padding:"20px 14px", fontSize:11, color:"var(--text-3)",
            fontFamily:"var(--font-mono)", textAlign:"center" }}>
            Waiting for log events…
          </div>
        ) : (
          logs.map(log => (
            <div key={log.id} className="log-line">
              <span className="log-time">
                {new Date(log.timestamp * 1000).toLocaleTimeString("en-GB", { hour12:false })}
              </span>
              <span className={`log-level-${log.level}`}>[{log.level.toUpperCase()}]</span>
              <span className="log-msg">{log.message}</span>
            </div>
          ))
        )}
        <div ref={bottomRef}/>
      </div>
    </div>
  );
}
