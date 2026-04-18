import { create } from "zustand";
import type { RunState, RunSummary } from "../types/runs";

interface LogEntry {
  id: string;
  level: "info" | "warning" | "error";
  message: string;
  timestamp: number;
}

interface RunsStore {
  runs: RunSummary[];
  activeRun: RunState | null;
  logs: LogEntry[];
  selectedRunId: string | null;

  setRuns: (runs: RunSummary[]) => void;
  upsertRun: (run: RunState | RunSummary) => void;
  setActiveRun: (run: RunState | null) => void;
  setSelectedRunId: (id: string | null) => void;
  appendLog: (entry: Omit<LogEntry, "id">) => void;
  clearLogs: () => void;
}

export const useRunsStore = create<RunsStore>((set) => ({
  runs: [],
  activeRun: null,
  logs: [],
  selectedRunId: null,

  setRuns: (runs) => set({ runs }),

  upsertRun: (run) => set((state) => {
    const idx = state.runs.findIndex(r => r.run_id === run.run_id);
    const summary: RunSummary = {
      run_id: run.run_id, scraper_id: run.scraper_id,
      scraper_name: run.scraper_name, status: run.status,
      stage: run.stage, progress: run.progress,
      records_extracted: run.records_extracted,
      warning_count: run.warning_count, error_count: run.error_count,
      duration_seconds: run.duration_seconds, started_at: run.started_at,
      queued_at: run.queued_at,
    };
    const runs = idx >= 0
      ? state.runs.map((r, i) => i === idx ? summary : r)
      : [summary, ...state.runs];
    const activeRun = state.activeRun?.run_id === run.run_id
      ? { ...state.activeRun, ...run } as RunState
      : state.activeRun;
    return { runs, activeRun };
  }),

  setActiveRun: (run) => set({ activeRun: run }),
  setSelectedRunId: (id) => set({ selectedRunId: id }),

  appendLog: (entry) => set((state) => ({
    logs: [
      ...state.logs.slice(-499),
      { ...entry, id: `${Date.now()}-${Math.random()}` }
    ]
  })),
  clearLogs: () => set({ logs: [] }),
}));
