/**
 * React Query hooks for failures API.
 * 
 * Provides data fetching and caching for the failures API endpoints
 * using React Query for server state management.
 * 
 * Story: 4.1 - View Proposed Selectors with Visual Preview
 * 
 * @usage
 * ```tsx
 * const { data, isLoading, error } = useFailures({ sport: 'basketball' });
 * const { data: detail } = useFailureDetail(failureId);
 * const { mutate: approve } = useApproveSelector();
 * ```
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Types matching API schemas
export interface BlastRadiusInfo {
  affected_count: number;
  affected_sports: string[];
  severity: 'low' | 'medium' | 'high' | 'critical';
  container_path: string;
}

export interface AlternativeSelector {
  selector: string;
  strategy: 'css' | 'xpath' | 'text' | 'attribute';
  confidence_score: number;
  blast_radius?: BlastRadiusInfo;
  highlight_css?: string;
  // Custom selector fields (Story 4.4)
  is_custom?: boolean;
  custom_notes?: string;
}

export interface FailureDetail {
  failure_id: number;
  selector_id: string;
  failed_selector: string;
  recipe_id?: string;
  sport?: string;
  site?: string;
  timestamp: string;
  error_type: string;
  failure_reason?: string;
  severity: string;
  snapshot_id?: number;
  alternatives: AlternativeSelector[];
  flagged?: boolean;
  flag_note?: string;
  flagged_at?: string;
}

export interface FailureListItem {
  failure_id: number;
  selector_id: string;
  failed_selector: string;
  sport?: string;
  site?: string;
  timestamp: string;
  error_type: string;
  severity: string;
  has_alternatives: boolean;
  alternative_count: number;
  flagged?: boolean;
  flag_note?: string;
}

export interface FailureListResponse {
  data: FailureListItem[];
  total: number;
  page: number;
  page_size: number;
  filters: Record<string, unknown>;
}

export interface ApprovalResponse {
  success: boolean;
  message: string;
  selector: string;
  failure_id: number;
  timestamp: string;
}

export interface ApprovalRequest {
  selector: string;
  notes?: string;
}

export interface RejectionRequest {
  selector: string;
  reason: string;
  suggested_alternative?: string;
}

export interface FlagRequest {
  note: string;
}

export interface FlagResponse {
  success: boolean;
  message: string;
  failure_id: number;
  flagged: boolean;
  flag_note: string;
  flagged_at: string;
}

// Custom selector request/response types (Story 4.4)
export interface CustomSelectorRequest {
  selector_string: string;
  strategy_type: string;
  notes?: string;
}

export interface CustomSelectorResponse {
  success: boolean;
  message: string;
  failure_id: number;
  selector: string;
  strategy_type: string;
  is_custom: boolean;
  created_at: string;
}

// API base URL - could be from env
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Fetch failures list with filters
 */
async function fetchFailures(filters: {
  sport?: string;
  site?: string;
  error_type?: string;
  severity?: string;
  flagged?: boolean;
  page?: number;
  page_size?: number;
}): Promise<FailureListResponse> {
  const params = new URLSearchParams();
  
  if (filters.sport) params.set('sport', filters.sport);
  if (filters.site) params.set('site', filters.site);
  if (filters.error_type) params.set('error_type', filters.error_type);
  if (filters.severity) params.set('severity', filters.severity);
  if (filters.flagged !== undefined) params.set('flagged', String(filters.flagged));
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));
  
  const response = await fetch(`${API_BASE_URL}/failures?${params.toString()}`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch failures');
  }
  
  return response.json();
}

/**
 * Fetch single failure detail
 */
async function fetchFailureDetail(failureId: number): Promise<{ data: FailureDetail }> {
  const response = await fetch(`${API_BASE_URL}/failures/${failureId}`);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch failure detail');
  }
  
  return response.json();
}

/**
 * Approve a selector alternative
 */
async function approveSelector(
  failureId: number, 
  request: ApprovalRequest
): Promise<ApprovalResponse> {
  const response = await fetch(`${API_BASE_URL}/failures/${failureId}/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to approve selector');
  }
  
  return response.json();
}

/**
 * Reject a selector alternative
 */
async function rejectSelector(
  failureId: number, 
  request: RejectionRequest
): Promise<ApprovalResponse> {
  const response = await fetch(`${API_BASE_URL}/failures/${failureId}/reject`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to reject selector');
  }
  
  return response.json();
}

/**
 * Flag a selector for developer review
 */
async function flagSelector(
  failureId: number, 
  request: FlagRequest
): Promise<FlagResponse> {
  const response = await fetch(`${API_BASE_URL}/failures/${failureId}/flag`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to flag selector');
  }
  
  return response.json();
}

/**
 * Remove flag from a selector
 */
async function unflagSelector(
  failureId: number
): Promise<FlagResponse> {
  const response = await fetch(`${API_BASE_URL}/failures/${failureId}/flag`, {
    method: 'DELETE',
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to unflag selector');
  }
  
  return response.json();
}

/**
 * Create a custom selector for a failure (Story 4.4)
 */
async function createCustomSelector(
  failureId: number,
  request: CustomSelectorRequest
): Promise<CustomSelectorResponse> {
  const response = await fetch(`${API_BASE_URL}/failures/${failureId}/custom-selector`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create custom selector');
  }
  
  return response.json();
}

// Query keys for cache management
export const queryKeys = {
  failures: (filters: Record<string, unknown>) => ['failures', filters] as const,
  failureDetail: (id: number) => ['failure', id] as const,
};

/**
 * Hook to fetch list of failures with optional filters
 */
export function useFailures(filters: {
  sport?: string;
  site?: string;
  error_type?: string;
  severity?: string;
  flagged?: boolean;
  page?: number;
  page_size?: number;
} = {}) {
  return useQuery({
    queryKey: queryKeys.failures(filters),
    queryFn: () => fetchFailures(filters),
    staleTime: 30000, // 30 seconds
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook to fetch single failure detail
 */
export function useFailureDetail(failureId: number | null) {
  return useQuery({
    queryKey: queryKeys.failureDetail(failureId ?? -1),
    queryFn: () => fetchFailureDetail(failureId!),
    enabled: failureId !== null,
    staleTime: 30000,
  });
}

/**
 * Hook to approve a selector alternative
 */
export function useApproveSelector() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ failureId, request }: { failureId: number; request: ApprovalRequest }) =>
      approveSelector(failureId, request),
    onSuccess: () => {
      // Invalidate failures list cache
      queryClient.invalidateQueries({ queryKey: ['failures'] });
    },
  });
}

/**
 * Hook to reject a selector alternative
 */
export function useRejectSelector() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ failureId, request }: { failureId: number; request: RejectionRequest }) =>
      rejectSelector(failureId, request),
    onSuccess: () => {
      // Invalidate failures list cache
      queryClient.invalidateQueries({ queryKey: ['failures'] });
    },
  });
}

/**
 * Hook to flag a selector for developer review
 */
export function useFlagSelector() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ failureId, request }: { failureId: number; request: FlagRequest }) =>
      flagSelector(failureId, request),
    onSuccess: () => {
      // Invalidate failures list cache
      queryClient.invalidateQueries({ queryKey: ['failures'] });
    },
  });
}

/**
 * Hook to unflag a selector
 */
export function useUnflagSelector() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ failureId }: { failureId: number }) =>
      unflagSelector(failureId),
    onSuccess: () => {
      // Invalidate failures list cache
      queryClient.invalidateQueries({ queryKey: ['failures'] });
    },
  });
}

/**
 * Hook to create a custom selector (Story 4.4)
 */
export function useCreateCustomSelector() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ failureId, request }: { failureId: number; request: CustomSelectorRequest }) =>
      createCustomSelector(failureId, request),
    onSuccess: () => {
      // Invalidate failures list and detail cache
      queryClient.invalidateQueries({ queryKey: ['failures'] });
    },
  });
}

export default {
  useFailures,
  useFailureDetail,
  useApproveSelector,
  useRejectSelector,
  useFlagSelector,
  useUnflagSelector,
  useCreateCustomSelector,
};
