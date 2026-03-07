import { useState } from "react";
import { ToggleSwitch } from "@/components/ui/ToggleSwitch";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { ConfirmationDialog } from "@/components/ui/ConfirmationDialog";
import { useFeatureFlags, useToggleFeatureFlag } from "@/hooks/useFeatureFlags";
import { useWebSocket } from "@/hooks/useWebSocket";
import { FeatureFlag } from "@/types/featureFlag";
import { formatRelativeTime } from "@/utils";
import { useQueryClient } from "@tanstack/react-query";

interface FeatureFlagListProps {
  sport?: string;
  site?: string;
}

export function FeatureFlagList({ sport, site }: FeatureFlagListProps) {
  const queryClient = useQueryClient();
  const {
    data: flagsData,
    isLoading,
    error,
  } = useFeatureFlags({ sport, site });
  const toggleMutation = useToggleFeatureFlag();
  const [togglingId, setTogglingId] = useState<number | null>(null);
  const [confirmationDialog, setConfirmationDialog] = useState<{
    isOpen: boolean;
    flag: FeatureFlag | null;
    newEnabled: boolean;
  }>({ isOpen: false, flag: null, newEnabled: false });

  // WebSocket for real-time updates
  const { isConnected, lastMessage, sendMessage } = useWebSocket({
    url: `ws://localhost:8000/ws/feature-flags`,
    onMessage: (data) => {
      if (data.type === "flag_updated") {
        // Invalidate queries to trigger refetch
        queryClient.invalidateQueries({ queryKey: ["feature-flags"] });
      }
    },
  });

  const isCriticalFlag = (flag: FeatureFlag): boolean => {
    // Define critical flags - these require confirmation
    const criticalFlags = [
      "adaptive_selector_system",
      "production_mode",
      "emergency_override",
    ];
    return (
      criticalFlags.includes(flag.sport.toLowerCase()) ||
      (flag.sport.toLowerCase() === "football" && flag.site === "flashscore")
    );
  };

  const handleToggle = async (flag: FeatureFlag) => {
    const newEnabled = !flag.enabled;

    // Check if confirmation is needed
    if (isCriticalFlag(flag)) {
      setConfirmationDialog({
        isOpen: true,
        flag,
        newEnabled,
      });
      return;
    }

    performToggle(flag, newEnabled);
  };

  const performToggle = async (flag: FeatureFlag, newEnabled: boolean) => {
    setTogglingId(flag.id);

    // Optimistic update - update UI immediately
    const originalFlags = flagsData?.data || [];
    const updatedFlag = { ...flag, enabled: newEnabled };
    const updatedFlags = originalFlags.map((f: FeatureFlag) =>
      f.id === flag.id ? updatedFlag : f,
    );

    // Update React Query cache immediately
    queryClient.setQueryData(["feature-flags"], {
      ...flagsData,
      data: updatedFlags,
      count: updatedFlags.length,
    });

    try {
      await toggleMutation.mutateAsync({
        sport: flag.sport,
        site: flag.site || undefined,
        enabled: newEnabled,
      });

      // Send WebSocket notification
      sendMessage({
        type: "flag_toggled",
        data: {
          flag_id: flag.id,
          sport: flag.sport,
          site: flag.site,
          old_enabled: flag.enabled,
          new_enabled: newEnabled,
          timestamp: new Date().toISOString(),
        },
      });
    } catch (error) {
      // Rollback on error
      queryClient.setQueryData(["feature-flags"], {
        ...flagsData,
        data: originalFlags,
        count: originalFlags.length,
      });
      console.error("Failed to toggle flag:", error);
    } finally {
      setTogglingId(null);
    }
  };

  const handleConfirmToggle = () => {
    if (confirmationDialog.flag) {
      performToggle(confirmationDialog.flag, confirmationDialog.newEnabled);
    }
  };

  const handleCancelConfirmation = () => {
    setConfirmationDialog({ isOpen: false, flag: null, newEnabled: false });
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="h-20 bg-gray-200 rounded-lg"></div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-red-600">
            <p className="font-medium">Error loading feature flags</p>
            <p className="text-sm mt-1">Please try again later</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const flags = flagsData?.data || [];

  if (flags.length === 0) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-gray-500">
            <p className="font-medium">No feature flags found</p>
            <p className="text-sm mt-1">
              {sport || site
                ? "Try adjusting your filters"
                : "Create your first feature flag to get started"}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <div className="space-y-4">
        {flags.map((flag) => (
          <Card key={flag.id}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3">
                    <h3 className="font-medium text-gray-900">{flag.sport}</h3>
                    {flag.site && (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {flag.site}
                      </span>
                    )}
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        flag.enabled
                          ? "bg-green-100 text-green-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {flag.enabled ? "Enabled" : "Disabled"}
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-gray-500">
                    <p>Last updated: {formatRelativeTime(flag.updated_at)}</p>
                    <p>Created: {formatRelativeTime(flag.created_at)}</p>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <ToggleSwitch
                    checked={flag.enabled}
                    onCheckedChange={() => handleToggle(flag)}
                    disabled={togglingId === flag.id}
                    aria-label={`Toggle ${flag.sport} ${flag.site || "global"} flag`}
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleToggle(flag)}
                    disabled={togglingId === flag.id}
                  >
                    {togglingId === flag.id
                      ? "Saving..."
                      : flag.enabled
                        ? "Disable"
                        : "Enable"}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Confirmation Dialog */}
      {confirmationDialog.isOpen && confirmationDialog.flag && (
        <ConfirmationDialog
          isOpen={confirmationDialog.isOpen}
          onClose={handleCancelConfirmation}
          onConfirm={handleConfirmToggle}
          title="Confirm Flag Toggle"
          message={`Are you sure you want to ${confirmationDialog.newEnabled ? "enable" : "disable"} the "${confirmationDialog.flag.sport}" feature flag? This is a critical flag that may affect system behavior.`}
          confirmText={confirmationDialog.newEnabled ? "Enable" : "Disable"}
          cancelText="Cancel"
          variant="danger"
        />
      )}
    </>
  );
}
