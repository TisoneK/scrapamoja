import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import { FeatureFlagList } from "@/components/FeatureFlagList";
import { FeatureFlag } from "@/types/featureFlag";
import { useFeatureFlags, useToggleFeatureFlag } from "@/hooks/useFeatureFlags";

// Mock the API hooks
vi.mock("@/hooks/useFeatureFlags", () => ({
  useFeatureFlags: vi.fn(),
  useToggleFeatureFlag: vi.fn(() => ({
    mutateAsync: vi.fn().mockResolvedValue(undefined),
  })),
}));

// Mock the WebSocket hook to avoid real connections in tests
vi.mock("@/hooks/useWebSocket", () => ({
  useWebSocket: vi.fn(() => ({
    isConnected: false,
    lastMessage: null,
    sendMessage: vi.fn(),
  })),
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const renderWithQueryClient = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{component}</QueryClientProvider>,
  );
};

describe("FeatureFlagList", () => {
  const mockFlags: FeatureFlag[] = [
    {
      id: 1,
      sport: "basketball",
      site: null,
      enabled: true,
      created_at: "2026-03-06T10:00:00Z",
      updated_at: "2026-03-06T10:00:00Z",
    },
    {
      id: 2,
      sport: "tennis",
      site: "flashscore",
      enabled: false,
      created_at: "2026-03-05T15:30:00Z",
      updated_at: "2026-03-05T15:30:00Z",
    },
  ];

  it("displays loading state", () => {
    vi.mocked(useFeatureFlags).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any);

    const { container } = renderWithQueryClient(<FeatureFlagList />);

    // Loading state renders skeleton placeholders, not text
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("displays feature flags when data is loaded", () => {
    vi.mocked(useFeatureFlags).mockReturnValue({
      data: { data: mockFlags, count: 2 },
      isLoading: false,
      error: null,
    } as any);

    renderWithQueryClient(<FeatureFlagList />);

    expect(screen.getByText("basketball")).toBeInTheDocument();
    expect(screen.getByText("tennis")).toBeInTheDocument();
    expect(screen.getByText("flashscore")).toBeInTheDocument();
    expect(screen.getByText("Enabled")).toBeInTheDocument();
    expect(screen.getByText("Disabled")).toBeInTheDocument();
  });

  it("displays empty state when no flags", () => {
    vi.mocked(useFeatureFlags).mockReturnValue({
      data: { data: [], count: 0 },
      isLoading: false,
      error: null,
    } as any);

    renderWithQueryClient(<FeatureFlagList />);

    expect(screen.getByText("No feature flags found")).toBeInTheDocument();
  });

  it("displays error state", () => {
    vi.mocked(useFeatureFlags).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Network error"),
    } as any);

    renderWithQueryClient(<FeatureFlagList />);

    expect(screen.getByText("Error loading feature flags")).toBeInTheDocument();
  });
});
