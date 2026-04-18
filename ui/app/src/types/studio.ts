export type StrategyType = "css" | "xpath" | "text" | "attr";

export interface Strategy {
  type: StrategyType;
  selector: string;
  priority: number;
  confidence: number;
}

export interface Entity {
  id: string;
  name: string;
  purpose: string;
  strategies: Strategy[];
  threshold: number;
  timeout_ms: number;
  fallback_enabled: boolean;
  matches_found?: number;
}

export interface ScraperConfig {
  id: string;
  name: string;
  target_url: string;
  entities: Entity[];
}
