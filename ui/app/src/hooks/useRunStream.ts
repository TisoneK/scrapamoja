import { useEffect, useRef, useCallback } from "react";
import type { RunState, RunEventType } from "../types/runs";
import { streamUrl } from "../api/runsApi";

interface RunEvent {
  run_id: string;
  timestamp: number;
  [key: string]: unknown;
}

interface UseRunStreamOptions {
  onStateChanged?: (state: RunState) => void;
  onProgress?: (data: RunEvent) => void;
  onRecord?: (data: RunEvent) => void;
  onWarning?: (data: RunEvent) => void;
  onError?: (data: RunEvent) => void;
  onLog?: (data: RunEvent) => void;
  onTerminal?: (state: RunState) => void;
}

export function useRunStream(runId: string | null, opts: UseRunStreamOptions) {
  const esRef = useRef<EventSource | null>(null);
  const optsRef = useRef(opts);
  optsRef.current = opts;

  const connect = useCallback(() => {
    if (!runId) return;
    if (esRef.current) esRef.current.close();

    const es = new EventSource(streamUrl(runId));
    esRef.current = es;

    const handle = (type: RunEventType) => (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as RunEvent;
        switch (type) {
          case "state_changed": optsRef.current.onStateChanged?.(data as unknown as RunState); break;
          case "progress":       optsRef.current.onProgress?.(data); break;
          case "record_extracted": optsRef.current.onRecord?.(data); break;
          case "warning":        optsRef.current.onWarning?.(data); break;
          case "error":          optsRef.current.onError?.(data); break;
          case "log":            optsRef.current.onLog?.(data); break;
          case "run_completed":
          case "run_failed":
          case "run_cancelled":
            optsRef.current.onTerminal?.(data as unknown as RunState);
            es.close();
            break;
        }
      } catch {}
    };

    const types: RunEventType[] = [
      "state_changed","progress","record_extracted","warning",
      "error","log","checkpoint_saved","run_completed","run_failed","run_cancelled"
    ];
    types.forEach(t => es.addEventListener(t, handle(t)));

    es.onerror = () => {
      es.close();
      setTimeout(connect, 3000);
    };
  }, [runId]);

  useEffect(() => {
    connect();
    return () => { esRef.current?.close(); };
  }, [connect]);

  return { disconnect: () => esRef.current?.close() };
}
