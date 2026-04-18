export type RunStatus =
  | "queued" | "starting" | "running" | "paused"
  | "stopping" | "completed" | "failed" | "cancelled";

export type RunStage =
  | "initialising" | "navigating" | "handling_consent" | "extracting"
  | "normalising" | "paginating" | "retrying" | "checkpointing"
  | "storing" | "finishing";

export type FailureSeverityLevel = "low" | "medium" | "high" | "critical";

export type RunEventType =
  | "state_changed" | "progress" | "record_extracted" | "warning"
  | "error" | "log" | "checkpoint_saved" | "run_completed"
  | "run_failed" | "run_cancelled";

export interface RunWarning {
  code: string; message: string; stage: RunStage;
  timestamp: number; context: Record<string, unknown>;
}
export interface RunError {
  code: string; message: string; stage: RunStage;
  severity: FailureSeverityLevel; retryable: boolean;
  timestamp: number; context: Record<string, unknown>;
}
export interface RunState {
  run_id: string; scraper_id: string; scraper_name: string;
  status: RunStatus; stage: RunStage;
  progress: number; records_extracted: number; records_stored: number;
  pages_visited: number; pages_total: number | null;
  warnings: RunWarning[]; errors: RunError[];
  warning_count: number; error_count: number;
  retry_count: number; retry_max: number;
  queued_at: number; started_at: number | null;
  updated_at: number; completed_at: number | null;
  duration_seconds: number | null;
  target_url: string;
  extraction_mode: "dom" | "api" | "network" | "hybrid";
  proxy_enabled: boolean; stealth_enabled: boolean;
  scheduled: boolean; schedule_expr: string | null;
  resumable: boolean; checkpoint_path: string | null;
}
export type RunSummary = Pick<RunState,
  "run_id"|"scraper_id"|"scraper_name"|"status"|"stage"|"progress"
  |"records_extracted"|"warning_count"|"error_count"|"duration_seconds"
  |"started_at"|"queued_at">;

export interface StartRunRequest {
  scraper_id: string; scraper_name: string; target_url: string;
  extraction_mode?: "dom" | "api" | "network" | "hybrid";
  proxy_enabled?: boolean; stealth_enabled?: boolean;
  schedule_expr?: string; priority?: number; resume_from?: string;
}

export const STATUS_COLOR: Record<RunStatus, string> = {
  queued:"#5f5d7a", starting:"#EF9F27", running:"#1D9E75",
  paused:"#378ADD", stopping:"#EF9F27", completed:"#1D9E75",
  failed:"#E24B4A", cancelled:"#5f5d7a",
};
export const STAGE_LABEL: Record<RunStage, string> = {
  initialising:"Starting up", navigating:"Navigating",
  handling_consent:"Handling consent", extracting:"Extracting data",
  normalising:"Normalising", paginating:"Paginating",
  retrying:"Retrying", checkpointing:"Checkpointing",
  storing:"Storing", finishing:"Finishing",
};
export const canPause  = (s: RunStatus) => s === "running";
export const canResume = (s: RunStatus) => s === "paused";
export const canStop   = (s: RunStatus) => ["queued","starting","running","paused"].includes(s);
export const isTerminal = (s: RunStatus) => ["completed","failed","cancelled"].includes(s);
