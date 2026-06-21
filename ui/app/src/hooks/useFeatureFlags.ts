import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/featureFlagApi";
import { FeatureFlag, FeatureFlagListResponse } from "@/types/featureFlag";

// Query keys
export const FEATURE_FLAGS_QUERY_KEY = ["feature-flags"];
export const FEATURE_FLAG_STATS_QUERY_KEY = ["feature-flag-stats"];

// Error types
export interface ApiError {
  message: string;
  status?: number;
  code?: string;
}

// Retry configuration
const RETRY_CONFIG = {
  default: {
    retry: 3,
    retryDelay: (attemptIndex: number) =>
      Math.min(1000 * 2 ** attemptIndex, 30000),
  },
  mutations: {
    retry: 2,
    retryDelay: 1000,
  },
};

// Filter and sort types
export interface FilterOptions {
  sport?: string;
  site?: string;
  enabled?: "all" | "enabled" | "disabled";
  sortBy?: "updated_at" | "sport" | "site" | "created_at";
  sortOrder?: "asc" | "desc";
}

export function useFeatureFlags(filterOptions: FilterOptions = {}) {
  return useQuery({
    queryKey: [...FEATURE_FLAGS_QUERY_KEY, filterOptions],
    queryFn: async () => {
      try {
        const data = await apiClient.getFeatureFlags(
          filterOptions.sport,
          filterOptions.site,
        );
        return data;
      } catch (error) {
        console.error("Failed to fetch feature flags:", error);
        throw new Error(
          error instanceof Error
            ? error.message
            : "Failed to fetch feature flags. Please try again.",
        );
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 30 * 1000, // 30 seconds for real-time updates
    retry: RETRY_CONFIG.default.retry,
    retryDelay: RETRY_CONFIG.default.retryDelay,
    select: (data: FeatureFlagListResponse) => {
      if (!data?.data) return data;

      let filteredFlags = [...data.data];

      // Apply filters
      if (filterOptions.sport) {
        const sport = filterOptions.sport;
        filteredFlags = filteredFlags.filter((flag) =>
          flag.sport.toLowerCase().includes(sport.toLowerCase()),
        );
      }

      if (filterOptions.site) {
        const site = filterOptions.site;
        filteredFlags = filteredFlags.filter((flag) =>
          flag.site?.toLowerCase().includes(site.toLowerCase()),
        );
      }

      if (filterOptions.enabled !== "all") {
        const isEnabled = filterOptions.enabled === "enabled";
        filteredFlags = filteredFlags.filter(
          (flag) => flag.enabled === isEnabled,
        );
      }

      // Apply sorting
      if (filterOptions.sortBy) {
        filteredFlags.sort((a, b) => {
          let aValue: any = a[filterOptions.sortBy as keyof FeatureFlag];
          let bValue: any = b[filterOptions.sortBy as keyof FeatureFlag];

          // Handle date sorting
          if (
            filterOptions.sortBy === "updated_at" ||
            filterOptions.sortBy === "created_at"
          ) {
            aValue = new Date(aValue).getTime();
            bValue = new Date(bValue).getTime();
          }

          if (filterOptions.sortOrder === "desc") {
            return aValue < bValue ? 1 : -1;
          } else {
            return aValue > bValue ? 1 : -1;
          }
        });
      }

      return { ...data, data: filteredFlags, count: filteredFlags.length };
    },
  });
}

export function useFeatureFlagStats() {
  return useQuery({
    queryKey: FEATURE_FLAG_STATS_QUERY_KEY,
    queryFn: () => apiClient.getFeatureFlagStats(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 30 * 1000, // 30 seconds for real-time updates
  });
}

export function useToggleFeatureFlag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      sport,
      site,
      enabled,
    }: {
      sport: string;
      site?: string;
      enabled: boolean;
    }) => {
      try {
        await apiClient.toggleFeatureFlag(sport, site, enabled);
        return { success: true };
      } catch (error) {
        console.error("Failed to toggle feature flag:", error);
        throw new Error(
          error instanceof Error
            ? error.message
            : "Failed to toggle feature flag. Please try again.",
        );
      }
    },
    retry: RETRY_CONFIG.mutations.retry,
    retryDelay: RETRY_CONFIG.mutations.retryDelay,
    onSuccess: () => {
      // Invalidate queries to trigger refetch
      queryClient.invalidateQueries({ queryKey: FEATURE_FLAGS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: FEATURE_FLAG_STATS_QUERY_KEY });
    },
    onError: (error) => {
      console.error("Toggle mutation error:", error);
      // Optional: Show toast notification
      // toast.error('Failed to toggle feature flag. Please try again.')
    },
  });
}

export function useCreateFeatureFlag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      sport,
      site,
      enabled,
      description,
    }: {
      sport: string;
      site?: string;
      enabled: boolean;
      description?: string;
    }) => {
      try {
        await apiClient.createFeatureFlag(sport, site, enabled, description);
        return { success: true };
      } catch (error) {
        console.error("Failed to create feature flag:", error);
        throw new Error(
          error instanceof Error
            ? error.message
            : "Failed to create feature flag. Please try again.",
        );
      }
    },
    retry: RETRY_CONFIG.mutations.retry,
    retryDelay: RETRY_CONFIG.mutations.retryDelay,
    onSuccess: () => {
      // Invalidate queries to trigger refetch
      queryClient.invalidateQueries({ queryKey: FEATURE_FLAGS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: FEATURE_FLAG_STATS_QUERY_KEY });
    },
    onError: (error) => {
      console.error("Create mutation error:", error);
      // Optional: Show toast notification
      // toast.error('Failed to create feature flag. Please try again.')
    },
  });
}

export function useDeleteFeatureFlag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ sport, site }: { sport: string; site?: string }) => {
      try {
        await apiClient.deleteFeatureFlag(sport, site);
        return { success: true };
      } catch (error) {
        console.error("Failed to delete feature flag:", error);
        throw new Error(
          error instanceof Error
            ? error.message
            : "Failed to delete feature flag. Please try again.",
        );
      }
    },
    retry: RETRY_CONFIG.mutations.retry,
    retryDelay: RETRY_CONFIG.mutations.retryDelay,
    onSuccess: () => {
      // Invalidate queries to trigger refetch
      queryClient.invalidateQueries({ queryKey: FEATURE_FLAGS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: FEATURE_FLAG_STATS_QUERY_KEY });
    },
    onError: (error) => {
      console.error("Delete mutation error:", error);
      // Optional: Show toast notification
      // toast.error('Failed to delete feature flag. Please try again.')
    },
  });
}
