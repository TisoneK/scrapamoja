import { useState } from "react";
import { ToggleSwitch } from "@/components/ui/ToggleSwitch";
import { ConfirmationDialog } from "@/components/ui/ConfirmationDialog";
import { useFeatureFlags, useToggleFeatureFlag } from "@/hooks/useFeatureFlags";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useQueryClient } from "@tanstack/react-query";
import { FeatureFlag } from "@/types/featureFlag";
import { formatRelativeTime } from "@/utils";
import { Flag, AlertCircle, RefreshCw } from "lucide-react";

interface FeatureFlagListProps {
  sport?: string;
  site?: string;
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
function TableSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
        <div className="h-3.5 w-24 bg-slate-100 rounded animate-pulse" />
      </div>
      <table className="min-w-full data-table">
        <thead>
          <tr>
            <th className="w-36">Sport</th>
            <th className="w-28">Site</th>
            <th className="w-24">Status</th>
            <th className="w-36">Last updated</th>
            <th className="w-16 text-center">Toggle</th>
          </tr>
        </thead>
        <tbody>
          {[...Array(5)].map((_, i) => (
            <tr key={i} className="animate-pulse">
              <td>
                <div className="h-3.5 w-24 bg-slate-100 rounded" />
              </td>
              <td>
                <div className="h-5 w-20 bg-slate-100 rounded-full" />
              </td>
              <td>
                <div className="h-5 w-16 bg-slate-100 rounded-full" />
              </td>
              <td>
                <div className="h-3.5 w-28 bg-slate-100 rounded" />
              </td>
              <td className="text-center">
                <div className="h-5 w-9 bg-slate-100 rounded-full mx-auto" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────
function EmptyState({ filtered }: { filtered: boolean }) {
  return (
    <div className="flex flex-col flex-1 bg-white rounded-xl border border-slate-200 items-center justify-center py-8 text-center">
      <Flag className="w-7 h-7 text-slate-300 mb-2" />
      <p className="text-sm font-medium text-slate-500">
        {filtered ? "No flags match your filters" : "No feature flags yet"}
      </p>
      <p className="text-xs text-slate-400 mt-0.5">
        {filtered
          ? "Try adjusting or clearing the filters above"
          : "Create your first flag using the Add Flag button"}
      </p>
    </div>
  );
}

// ── Error state ───────────────────────────────────────────────────────────────
function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col flex-1 bg-white rounded-xl border border-slate-200 items-center justify-center py-8 text-center">
      <div className="w-10 h-10 bg-red-50 rounded-full flex items-center justify-center mb-3">
        <AlertCircle className="w-5 h-5 text-red-500" />
      </div>
      <p className="text-sm font-medium text-slate-700">
        Failed to load feature flags
      </p>
      <p className="text-xs text-slate-400 mt-0.5 mb-4">
        Check that the API server is running
      </p>
      <button
        onClick={onRetry}
        className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-800 transition-colors"
      >
        <RefreshCw className="w-3 h-3" />
        Try again
      </button>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export function FeatureFlagList({ sport, site }: FeatureFlagListProps) {
  const queryClient = useQueryClient();
  const {
    data: flagsData,
    isLoading,
    error,
    refetch,
  } = useFeatureFlags({ sport, site });
  const toggleMutation = useToggleFeatureFlag();
  const [togglingId, setTogglingId] = useState<number | null>(null);
  const [confirmationDialog, setConfirmationDialog] = useState<{
    isOpen: boolean;
    flag: FeatureFlag | null;
    newEnabled: boolean;
  }>({ isOpen: false, flag: null, newEnabled: false });

  const { sendMessage } = useWebSocket({
    url: `ws://localhost:5173/ws/feature-flags`,
    onMessage: (data) => {
      if (data.type === "flag_updated") {
        queryClient.invalidateQueries({ queryKey: ["feature-flags"] });
      }
    },
  });

  const isCriticalFlag = (flag: FeatureFlag) => {
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

  const handleToggle = (flag: FeatureFlag) => {
    const newEnabled = !flag.enabled;
    if (isCriticalFlag(flag)) {
      setConfirmationDialog({ isOpen: true, flag, newEnabled });
      return;
    }
    performToggle(flag, newEnabled);
  };

  const performToggle = async (flag: FeatureFlag, newEnabled: boolean) => {
    setTogglingId(flag.id);
    const originalFlags = flagsData?.data || [];
    const updatedFlags = originalFlags.map((f: FeatureFlag) =>
      f.id === flag.id ? { ...f, enabled: newEnabled } : f,
    );
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
    } catch {
      queryClient.setQueryData(["feature-flags"], {
        ...flagsData,
        data: originalFlags,
        count: originalFlags.length,
      });
    } finally {
      setTogglingId(null);
    }
  };

  const handleConfirmToggle = () => {
    if (confirmationDialog.flag) {
      performToggle(confirmationDialog.flag, confirmationDialog.newEnabled);
    }
    setConfirmationDialog({ isOpen: false, flag: null, newEnabled: false });
  };

  if (isLoading) return <TableSkeleton />;
  if (error) return <ErrorState onRetry={() => refetch()} />;

  const flags = flagsData?.data || [];
  const isFiltered = !!(sport || site);

  if (flags.length === 0) return <EmptyState filtered={isFiltered} />;

  return (
    <>
      <div className="flex flex-col flex-1 bg-white rounded-xl border border-slate-200 overflow-hidden">
        {/* Card header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Flag className="w-3.5 h-3.5 text-slate-400" />
            <h2 className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
              Flags
            </h2>
          </div>
          <span className="text-xs text-slate-400 font-medium">
            {flags.length} {flags.length === 1 ? "flag" : "flags"}
          </span>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="min-w-full data-table">
            <thead>
              <tr>
                <th className="w-36">Sport</th>
                <th className="w-28">Site</th>
                <th className="w-24">Status</th>
                <th className="w-40">Last updated</th>
                <th className="w-16 text-center">Toggle</th>
              </tr>
            </thead>
            <tbody>
              {flags.map((flag) => (
                <tr
                  key={flag.id}
                  className={togglingId === flag.id ? "opacity-60" : ""}
                >
                  {/* Sport */}
                  <td className="font-medium text-slate-800 capitalize whitespace-nowrap">
                    {flag.sport}
                  </td>

                  {/* Site */}
                  <td className="whitespace-nowrap">
                    {flag.site ? (
                      <span className="badge badge-slate">{flag.site}</span>
                    ) : (
                      <span className="text-slate-300 text-xs italic">
                        Global
                      </span>
                    )}
                  </td>

                  {/* Status */}
                  <td className="whitespace-nowrap">
                    <span
                      className={
                        flag.enabled ? "badge badge-green" : "badge badge-red"
                      }
                    >
                      {flag.enabled ? "Enabled" : "Disabled"}
                    </span>
                  </td>

                  {/* Last updated */}
                  <td className="whitespace-nowrap text-xs text-slate-500">
                    {formatRelativeTime(flag.updated_at)}
                  </td>

                  {/* Toggle */}
                  <td className="text-center">
                    <ToggleSwitch
                      checked={flag.enabled}
                      onCheckedChange={() => handleToggle(flag)}
                      disabled={togglingId === flag.id}
                      aria-label={`Toggle ${flag.sport} ${flag.site ?? "global"} flag`}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirmation dialog for critical flags */}
      {confirmationDialog.isOpen && confirmationDialog.flag && (
        <ConfirmationDialog
          isOpen={confirmationDialog.isOpen}
          onClose={() =>
            setConfirmationDialog({
              isOpen: false,
              flag: null,
              newEnabled: false,
            })
          }
          onConfirm={handleConfirmToggle}
          title="Confirm Flag Toggle"
          message={`Are you sure you want to ${
            confirmationDialog.newEnabled ? "enable" : "disable"
          } the "${confirmationDialog.flag.sport}" feature flag? This is a critical flag that may affect system behavior.`}
          confirmText={confirmationDialog.newEnabled ? "Enable" : "Disable"}
          cancelText="Cancel"
          variant="danger"
        />
      )}
    </>
  );
}
