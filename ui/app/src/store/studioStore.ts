import { create } from "zustand";
import type { ScraperConfig, Entity } from "../types/studio";

interface StudioStore {
  config: ScraperConfig | null;
  activeEntityId: string | null;
  hoveredEntityId: string | null;
  mode: "visual" | "expert";

  setConfig: (config: ScraperConfig) => void;
  setActiveEntityId: (id: string | null) => void;
  setHoveredEntityId: (id: string | null) => void;
  setMode: (mode: "visual" | "expert") => void;
  upsertEntity: (entity: Entity) => void;
  removeEntity: (id: string) => void;
}

const DEMO_CONFIG: ScraperConfig = {
  id: "flashscore-basketball",
  name: "Flashscore Basketball",
  target_url: "https://www.flashscore.com/basketball/",
  entities: [
    {
      id: "match_card",
      name: "match_card",
      purpose: "Live match card container",
      strategies: [
        { type: "css",   selector: ".event__match--live",  priority: 1, confidence: 0.92 },
        { type: "xpath", selector: "//div[@data-live-id]", priority: 2, confidence: 0.67 },
        { type: "text",  selector: "LIVE",                 priority: 3, confidence: 0.41 },
        { type: "attr",  selector: '[data-event="live"]',  priority: 4, confidence: 0.35 },
      ],
      threshold: 0.70, timeout_ms: 1500, fallback_enabled: true, matches_found: 12,
    },
    {
      id: "team_name",
      name: "team_name",
      purpose: "Team name text",
      strategies: [
        { type: "css",   selector: ".event__participant",   priority: 1, confidence: 0.89 },
        { type: "xpath", selector: "//span[@class='team']", priority: 2, confidence: 0.72 },
      ],
      threshold: 0.70, timeout_ms: 1500, fallback_enabled: true, matches_found: 24,
    },
    {
      id: "score",
      name: "score",
      purpose: "Match score",
      strategies: [
        { type: "css",   selector: ".event__score", priority: 1, confidence: 0.71 },
        { type: "xpath", selector: "//div[@class='score']", priority: 2, confidence: 0.60 },
      ],
      threshold: 0.65, timeout_ms: 2000, fallback_enabled: true, matches_found: 12,
    },
    {
      id: "match_time",
      name: "match_time",
      purpose: "Current game clock",
      strategies: [
        { type: "css",   selector: ".event__stage", priority: 1, confidence: 0.43 },
        { type: "text",  selector: "Q1|Q2|Q3|Q4",  priority: 2, confidence: 0.38 },
      ],
      threshold: 0.70, timeout_ms: 2000, fallback_enabled: false, matches_found: 0,
    },
    {
      id: "match_url",
      name: "match_url",
      purpose: "Link to match detail",
      strategies: [
        { type: "attr", selector: "a[href*='/match/']", priority: 1, confidence: 0.95 },
      ],
      threshold: 0.80, timeout_ms: 1000, fallback_enabled: false, matches_found: 12,
    },
    {
      id: "status",
      name: "status",
      purpose: "Live/Finished/Scheduled",
      strategies: [
        { type: "attr", selector: "[data-status]",       priority: 1, confidence: 0.68 },
        { type: "css",  selector: ".event__stage--live", priority: 2, confidence: 0.55 },
      ],
      threshold: 0.60, timeout_ms: 1500, fallback_enabled: true, matches_found: 12,
    },
  ],
};

export const useStudioStore = create<StudioStore>((set) => ({
  config: DEMO_CONFIG,
  activeEntityId: "match_card",
  hoveredEntityId: null,
  mode: "visual",

  setConfig: (config) => set({ config }),
  setActiveEntityId: (id) => set({ activeEntityId: id }),
  setHoveredEntityId: (id) => set({ hoveredEntityId: id }),
  setMode: (mode) => set({ mode }),

  upsertEntity: (entity) => set((state) => {
    if (!state.config) return {};
    const entities = state.config.entities.find(e => e.id === entity.id)
      ? state.config.entities.map(e => e.id === entity.id ? entity : e)
      : [...state.config.entities, entity];
    return { config: { ...state.config, entities } };
  }),

  removeEntity: (id) => set((state) => {
    if (!state.config) return {};
    return {
      config: { ...state.config, entities: state.config.entities.filter(e => e.id !== id) },
      activeEntityId: state.activeEntityId === id ? null : state.activeEntityId,
    };
  }),
}));
