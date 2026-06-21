import React, { useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { FailureDashboard } from "../components/failures/FailureDashboard";
import { FailureDetailView } from "../components/failures/FailureDetailView";
import {
  useFailures,
  useFailureDetail,
  useApproveSelector,
  useRejectSelector,
  useFlagSelector,
  useUnflagSelector,
} from "../hooks/useFailures";

// ── Skeleton ──────────────────────────────────────────────────────────────────
function EscalationSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      {/* Header skeleton */}
      <div className="flex items-center justify-between">
        <div className="h-5 w-32 bg-slate-200 rounded-md" />
        <div className="h-7 w-24 bg-slate-200 rounded-lg" />
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        {[...Array(3)].map((_, i) => (
          <div
            key={i}
            className="bg-white rounded-xl border border-slate-200 px-4 py-3 flex items-center gap-3"
          >
            <div className="w-8 h-8 bg-slate-100 rounded-lg flex-shrink-0" />
            <div className="space-y-1.5">
              <div className="h-2.5 w-16 bg-slate-100 rounded" />
              <div className="h-5 w-10 bg-slate-200 rounded" />
            </div>
          </div>
        ))}
      </div>

      {/* Table skeleton */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="h-10 bg-slate-50 border-b border-slate-100 px-4 flex items-center gap-3">
          <div className="h-3 w-20 bg-slate-200 rounded" />
          <div className="h-3 w-12 bg-slate-100 rounded" />
        </div>
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="px-4 py-2.5 border-b border-slate-100 flex items-center gap-4 last:border-b-0"
          >
            <div className="h-3.5 w-8 bg-slate-100 rounded" />
            <div className="h-3.5 flex-1 bg-slate-100 rounded" />
            <div className="h-5 w-14 bg-slate-100 rounded-full" />
            <div className="h-3.5 w-20 bg-slate-100 rounded" />
            <div className="h-3.5 w-16 bg-slate-100 rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Error state ───────────────────────────────────────────────────────────────
function EscalationError({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-96 text-center">
      <div className="w-14 h-14 bg-red-50 rounded-full flex items-center justify-center mb-4">
        <AlertTriangle className="w-7 h-7 text-red-500" />
      </div>
      <h3 className="text-base font-semibold text-slate-800 mb-1">
        Failed to load failures
      </h3>
      <p className="text-sm text-slate-500 mb-6 max-w-sm">{message}</p>
      <button
        onClick={onRetry}
        className="inline-flex items-center gap-2 bg-indigo-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-indigo-700 active:bg-indigo-800 transition-colors duration-150 shadow-sm"
      >
        <RefreshCw className="w-4 h-4" />
        Try again
      </button>
    </div>
  );
}

// ── Detail loading ─────────────────────────────────────────────────────────────
function DetailSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-5 w-40 bg-slate-200 rounded-md" />
      <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-3.5 bg-slate-100 rounded w-3/4" />
        ))}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export const EscalationPage: React.FC = () => {
  const [selectedFailureId, setSelectedFailureId] = useState<number | null>(
    null,
  );

  const {
    data: failuresData,
    isLoading: failuresLoading,
    error: failuresError,
    refetch,
  } = useFailures({ page: 1, page_size: 20 });

  const { data: detailData, isLoading: detailLoading } =
    useFailureDetail(selectedFailureId);

  const approveMutation = useApproveSelector();
  const rejectMutation = useRejectSelector();
  const flagMutation = useFlagSelector();
  const unflagMutation = useUnflagSelector();

  const handleSelectFailure = (id: number) => setSelectedFailureId(id);
  const handleBackToList = () => setSelectedFailureId(null);

  const handleApprove = (selector: string, notes?: string) => {
    if (selectedFailureId)
      approveMutation.mutate({
        failureId: selectedFailureId,
        request: { selector, notes },
      });
  };

  const handleReject = (
    selector: string,
    reason: string,
    suggestedAlternative?: string,
  ) => {
    if (selectedFailureId)
      rejectMutation.mutate({
        failureId: selectedFailureId,
        request: {
          selector,
          reason,
          suggested_alternative: suggestedAlternative,
        },
      });
  };

  const handleFlag = (note: string) => {
    if (selectedFailureId)
      flagMutation.mutate({ failureId: selectedFailureId, request: { note } });
  };

  const handleUnflag = () => {
    if (selectedFailureId)
      unflagMutation.mutate({ failureId: selectedFailureId });
  };

  // Loading
  if (failuresLoading) return <EscalationSkeleton />;

  // Error
  if (failuresError)
    return (
      <EscalationError
        message={failuresError.message ?? "An unexpected error occurred."}
        onRetry={() => refetch()}
      />
    );

  // Detail loading
  if (selectedFailureId && detailLoading) return <DetailSkeleton />;

  // Detail view
  if (selectedFailureId && detailData) {
    return (
      <FailureDetailView
        failure={detailData.data}
        onBack={handleBackToList}
        onApprove={handleApprove}
        onReject={handleReject}
        onFlag={handleFlag}
        onUnflag={handleUnflag}
        loading={
          approveMutation.isPending ||
          rejectMutation.isPending ||
          flagMutation.isPending ||
          unflagMutation.isPending
        }
      />
    );
  }

  // List view
  return (
    <div className="flex flex-col flex-1 space-y-3">
      {/* Page header */}
      <h1 className="text-base font-semibold text-slate-900 tracking-tight">
        Escalation
      </h1>

      <div className="flex flex-col flex-1 min-h-0">
        <FailureDashboard
          initialFailures={failuresData?.data}
          onSelectFailure={handleSelectFailure}
          useMockData={false}
        />
      </div>
    </div>
  );
};

export default EscalationPage;
