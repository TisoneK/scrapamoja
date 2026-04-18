import axios from "axios";
import type { RunState, RunSummary, StartRunRequest } from "../types/runs";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const api = axios.create({ baseURL: BASE, timeout: 10000 });

export const runsApi = {
  list: async (params?: { status?: string; scraper_id?: string; limit?: number }): Promise<RunSummary[]> => {
    const { data } = await api.get("/runs", { params });
    return data;
  },
  get: async (runId: string): Promise<RunState> => {
    const { data } = await api.get(`/runs/${runId}`);
    return data;
  },
  start: async (req: StartRunRequest): Promise<RunState> => {
    const { data } = await api.post("/runs", req);
    return data;
  },
  stop: async (runId: string): Promise<RunState> => {
    const { data } = await api.post(`/runs/${runId}/stop`);
    return data;
  },
  pause: async (runId: string): Promise<RunState> => {
    const { data } = await api.post(`/runs/${runId}/pause`);
    return data;
  },
  resume: async (runId: string): Promise<RunState> => {
    const { data } = await api.post(`/runs/${runId}/resume`);
    return data;
  },
  cancel: async (runId: string): Promise<RunState> => {
    const { data } = await api.delete(`/runs/${runId}`);
    return data;
  },
};

export const streamUrl = (runId: string) =>
  `${BASE}/runs/${runId}/stream`;
