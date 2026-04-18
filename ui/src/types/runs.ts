/**
 * Run contract types — Electron / React side
 *
 * These are the exact TypeScript mirrors of run_state.py and run_controller.py.
 * Keep in sync with the Python definitions. The FastAPI /runs endpoints
 * return these shapes; the SSE stream emits RunEvent payloads.
 *
 * Place at: ui/src/types/runs.ts
 */

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export type RunStatus =
  | "queued"
  | "starting"
  | "running"
  | "paused"
  | "stopping"
  | "completed"
  | "failed"
  | "cancelled";

export type RunStage =
  | "initialising"
  | "navigating"
  | "handling_consent"
  | "extracting"
  | "normalising"
  | "paginating"
  | "retrying"
  | "checkpointing"
  | "storing"
  | "finishing";

export type FailureSeverityLevel = "low" | "medium" | "high" | "critical";

export type RunEventType =
  | "state_changed"
  | "progress"
  | "record_extracted"
  | "warning"
  | "error"
  | "log"
  | "checkpoint_saved"
  | "run_completed"
  | "run_failed"
  | "run_cancelled";

// ---------------------------------------------------------------------------
// Structured problem records
// ---------------------------------------------------------------------------

export interface RunWarning {
  code: string;
  message: string;
  stage: RunStage;
  timestamp: number;
  context: Record<string, unknown>;
}

export interface RunError {
  code: string;
  message: string;
  stage: RunStage;
  severity: FailureSeverityLevel;
  retryable: boolean;
  timestamp: number;
  context: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// RunState — the full state object returned by GET /runs/{run_id}
// ---------------------------------------------------------------------------

export interface RunState {
  // Identity
  run_id: string;
  scraper_id: string;
  scraper_name: string;

  // Lifecycle
  status: RunStatus;
  stage: RunStage;

  // Progress
  progress: number;            // 0.0 → 1.0
  records_extracted: number;
  records_stored: number;
  pages_visited: number;
  pages_total: number | null;

  // Health
  warnings: RunWarning[];
  errors: RunError[];
  warning_count: number;
  error_count: number;
  retry_count: number;
  retry_max: number;

  // Timing
  queued_at: number;
  started_at: number | null;
  updated_at: number;
  completed_at: number | null;
  duration_seconds: number | null;

  // Config snapshot
  target_url: string;
  extraction_mode: "dom" | "api" | "network" | "hybrid";
  proxy_enabled: boolean;
  stealth_enabled: boolean;
  scheduled: boolean;
  schedule_expr: string | null;
  resumable: boolean;
  checkpoint_path: string | null;
}

// Lightweight version for list views
export type RunSummary = Pick<
  RunState,
  | "run_id"
  | "scraper_id"
  | "scraper_name"
  | "status"
  | "stage"
  | "progress"
  | "records_extracted"
  | "warning_count"
  | "error_count"
  | "duration_seconds"
  | "started_at"
  | "queued_at"
>;

// ---------------------------------------------------------------------------
// SSE Event payloads
// ---------------------------------------------------------------------------

export interface RunEvent<T = Record<string, unknown>> {
  run_id: string;
  timestamp: number;
  data: T;
}

export type RunEventMap = {
  state_changed:      RunState;
  progress:           { progress: number; pages_visited: number; pages_total: number | null };
  record_extracted:   { records_extracted: number; record: unknown };
  warning:            { code: string; message: string };
  error:              { code: string; message: string; severity: FailureSeverityLevel; retryable: boolean };
  log:                { level: "debug" | "info" | "warning" | "error"; message: string };
  checkpoint_saved:   { checkpoint_path: string };
  run_completed:      RunState;
  run_failed:         RunState;
  run_cancelled:      RunState;
};

// ---------------------------------------------------------------------------
// API request types
// ---------------------------------------------------------------------------

export interface StartRunRequest {
  scraper_id: string;
  scraper_name: string;
  target_url: string;
  extraction_mode?: "dom" | "api" | "network" | "hybrid";
  proxy_enabled?: boolean;
  stealth_enabled?: boolean;
  schedule_expr?: string;
  priority?: number;
  resume_from?: string;
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

/** Map RunStatus to a display colour token for the Runs UI */
export const STATUS_COLOR: Record<RunStatus, string> = {
  queued:    "#888780",   // gray
  starting:  "#EF9F27",   // amber
  running:   "#1D9E75",   // teal
  paused:    "#378ADD",   // blue
  stopping:  "#EF9F27",   // amber
  completed: "#639922",   // green
  failed:    "#E24B4A",   // red
  cancelled: "#888780",   // gray
};

/** Human-readable stage labels for the live progress indicator */
export const STAGE_LABEL: Record<RunStage, string> = {
  initialising:     "Starting up...",
  navigating:       "Navigating to page",
  handling_consent: "Handling consent",
  extracting:       "Extracting data",
  normalising:      "Normalising records",
  paginating:       "Moving to next page",
  retrying:         "Retrying after failure",
  checkpointing:    "Saving checkpoint",
  storing:          "Writing to storage",
  finishing:        "Finishing up",
};

/** Returns true if a run can be paused from the UI */
export const canPause = (status: RunStatus): boolean =>
  status === "running";

/** Returns true if a run can be resumed from the UI */
export const canResume = (status: RunStatus): boolean =>
  status === "paused";

/** Returns true if a run can be stopped from the UI */
export const canStop = (status: RunStatus): boolean =>
  ["queued", "starting", "running", "paused"].includes(status);

/** Returns true if the run is in a terminal state */
export const isTerminal = (status: RunStatus): boolean =>
  ["completed", "failed", "cancelled"].includes(status);
