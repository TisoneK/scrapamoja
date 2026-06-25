import axios, { AxiosInstance, AxiosError } from "axios";
import {
  FeatureFlag,
  FeatureFlagListResponse,
  FeatureFlagCreateRequest,
  FeatureFlagUpdateRequest,
  FeatureFlagToggleRequest,
  FeatureFlagCheckRequest,
  FeatureFlagCheckResponse,
  EnabledSportsResponse,
  FeatureFlagStatsResponse,
  ApiError,
  AuditLogResponse,
} from "@/types/featureFlag";

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: "/api/feature-flags",
      timeout: 10000,
      headers: {
        "Content-Type": "application/json",
      },
    });

    // Add request interceptor for API key authentication (if needed)
    this.client.interceptors.request.use(
      (config) => {
        // Add API key if available in localStorage or environment
        const apiKey =
          localStorage.getItem("api_key") ||
          (import.meta as unknown as { env: Record<string, string> }).env
            .VITE_API_KEY;
        if (apiKey) {
          config.headers.Authorization = `Bearer ${apiKey}`;
        }
        return config;
      },
      (error) => Promise.reject(error),
    );

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        // Handle common error scenarios
        if (error.response?.status === 401) {
          // Handle unauthorized - maybe redirect to login
          console.error("Unauthorized access - please check API key");
        } else if (error.response?.status === 403) {
          console.error("Forbidden - insufficient permissions");
        } else if ((error.response?.status ?? 0) >= 500) {
          console.error("Server error - please try again later");
        }
        return Promise.reject(error);
      },
    );
  }

  // Feature flag endpoints
  async getFeatureFlags(
    sport?: string,
    site?: string,
  ): Promise<FeatureFlagListResponse> {
    const params = new URLSearchParams();
    if (sport) params.append("sport", sport);
    if (site) params.append("site", site);

    const response = await this.client.get(``, { params });
    return response.data;
  }

  async getFeatureFlag(
    sport: string,
    site?: string,
  ): Promise<FeatureFlag | null> {
    try {
      if (site) {
        const response = await this.client.get(`/${sport}/sites/${site}`);
        return response.data;
      } else {
        const response = await this.client.get(`/${sport}`);
        const flags = response.data.data || response.data;
        return flags.length > 0 ? flags[0] : null;
      }
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  }

  async getSportFeatureFlags(sport: string): Promise<FeatureFlagListResponse> {
    const response = await this.client.get(`/${sport}`);
    return response.data;
  }

  async getSiteFlags(): Promise<FeatureFlagListResponse> {
    const response = await this.client.get(`/sites`);
    return response.data;
  }

  async createFeatureFlag(
    sport: string,
    site?: string,
    enabled: boolean = true,
    description?: string,
  ): Promise<FeatureFlag> {
    const data: FeatureFlagCreateRequest = { sport, enabled };
    if (site) data.site = site;
    if (description !== undefined) (data as any).description = description;
    const response = await this.client.post(``, data);
    return response.data;
  }

  async toggleFeatureFlag(
    sport: string,
    site: string | undefined,
    enabled: boolean,
  ): Promise<FeatureFlag> {
    if (site) {
      const response = await this.client.patch(`/${sport}/sites/${site}`, {
        enabled,
      });
      return response.data;
    } else {
      const response = await this.client.patch(`/${sport}`, { enabled });
      return response.data;
    }
  }

  async updateFeatureFlag(
    sport: string,
    site: string | null,
    data: FeatureFlagUpdateRequest,
  ): Promise<FeatureFlag> {
    if (site) {
      const response = await this.client.patch(`/${sport}/sites/${site}`, data);
      return response.data;
    } else {
      const response = await this.client.patch(`/${sport}`, data);
      return response.data;
    }
  }

  async toggleSportFlag(
    sport: string,
    data: FeatureFlagToggleRequest,
  ): Promise<FeatureFlag> {
    const response = await this.client.patch(`/${sport}`, data);
    return response.data;
  }

  async deleteFeatureFlag(sport: string, site?: string): Promise<void> {
    if (site) {
      await this.client.delete(`/${sport}/sites/${site}`);
    } else {
      await this.client.delete(`/${sport}`);
    }
  }

  async checkFeatureFlag(
    data: FeatureFlagCheckRequest,
  ): Promise<FeatureFlagCheckResponse> {
    const params = new URLSearchParams();
    params.append("sport", data.sport);
    if (data.site) params.append("site", data.site);

    const response = await this.client.get(`/check`, { params });
    return response.data;
  }

  async getEnabledSports(): Promise<EnabledSportsResponse> {
    const response = await this.client.get(`/enabled-sports`);
    return response.data;
  }

  async getFeatureFlagStats(): Promise<FeatureFlagStatsResponse> {
    const response = await this.client.get(`/stats`);
    return response.data;
  }

  // Audit log endpoints (to be implemented based on Epic 6)
  async getAuditLog(
    limit?: number,
    offset?: number,
  ): Promise<AuditLogResponse> {
    const params = new URLSearchParams();
    if (limit) params.append("limit", limit.toString());
    if (offset) params.append("offset", offset.toString());

    // This endpoint would need to be implemented in the backend
    const response = await this.client.get(`/audit-log`, { params });
    return response.data;
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
export default apiClient;
