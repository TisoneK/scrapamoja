// Feature flag types matching backend Pydantic schemas

export interface FeatureFlag {
  id: number
  sport: string
  site: string | null
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface FeatureFlagListResponse {
  data: FeatureFlag[]
  count: number
}

export interface FeatureFlagCreateRequest {
  sport: string
  site?: string
  enabled: boolean
}

export interface FeatureFlagUpdateRequest {
  enabled: boolean
}

export interface FeatureFlagToggleRequest {
  enabled: boolean
}

export interface FeatureFlagCheckRequest {
  sport: string
  site?: string
}

export interface FeatureFlagCheckResponse {
  sport: string
  site: string | null
  enabled: boolean
  flag_exists: boolean
}

export interface EnabledSportsResponse {
  sports: string[]
  count: number
}

export interface FeatureFlagStatsResponse {
  total_flags: number
  enabled_flags: number
  disabled_flags: number
  global_flags: number
  site_specific_flags: number
  unique_sports: number
}

// API error response type
export interface ApiError {
  detail: string
  status?: number
}

// Audit log types (to be implemented based on Epic 6)
export interface AuditLogEntry {
  id: number
  action: string
  resource_type: string
  resource_id: string
  user_id: string
  timestamp: string
  details?: Record<string, any>
}

export interface AuditLogResponse {
  data: AuditLogEntry[]
  count: number
  has_more: boolean
}
