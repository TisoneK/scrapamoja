/**
 * FailuresPage - Main page for the Escalation UI
 * 
 * This is the entry point for viewing and managing selector failures.
 * Combines the FailureDashboard with FailureDetailView for a complete experience.
 * 
 * Story: 4.1 - View Proposed Selectors with Visual Preview
 * 
 * @component
 */

import React, { useState } from 'react';
import { FailureDashboard } from '../components/failures/FailureDashboard';
import { FailureDetailView } from '../components/failures/FailureDetailView';
import { useFailures, useFailureDetail, useApproveSelector, useRejectSelector, useFlagSelector, useUnflagSelector } from '../hooks/useFailures';
import type { FailureListItem } from '../hooks/useFailures';

export const FailuresPage: React.FC = () => {
  const [selectedFailureId, setSelectedFailureId] = useState<number | null>(null);
  
  // Fetch failures list with React Query
  const { 
    data: failuresData, 
    isLoading: failuresLoading, 
    error: failuresError 
  } = useFailures({
    page: 1,
    page_size: 20,
  });
  
  // Fetch selected failure detail with React Query
  const { 
    data: detailData, 
    isLoading: detailLoading, 
    error: detailError 
  } = useFailureDetail(selectedFailureId);
  
  // Mutations for approve/reject/flag
  const approveMutation = useApproveSelector();
  const rejectMutation = useRejectSelector();
  const flagMutation = useFlagSelector();
  const unflagMutation = useUnflagSelector();
  
  const handleSelectFailure = (failureId: number) => {
    setSelectedFailureId(failureId);
  };
  
  const handleBackToList = () => {
    setSelectedFailureId(null);
  };
  
  const handleApprove = (selector: string, notes?: string) => {
    if (selectedFailureId) {
      approveMutation.mutate({
        failureId: selectedFailureId,
        request: { selector, notes },
      });
    }
  };
  
  const handleReject = (selector: string, reason: string, suggestedAlternative?: string) => {
    if (selectedFailureId) {
      rejectMutation.mutate({
        failureId: selectedFailureId,
        request: { selector, reason, suggested_alternative: suggestedAlternative },
      });
    }
  };
  
  const handleFlag = (note: string) => {
    if (selectedFailureId) {
      flagMutation.mutate({
        failureId: selectedFailureId,
        request: { note },
      });
    }
  };
  
  const handleUnflag = () => {
    if (selectedFailureId) {
      unflagMutation.mutate({
        failureId: selectedFailureId,
      });
    }
  };
  
  // Loading state
  if (failuresLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading failures...</p>
        </div>
      </div>
    );
  }
  
  // Error state
  if (failuresError) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center text-red-600">
          <p className="text-lg font-medium">Error loading failures</p>
          <p className="text-sm">{failuresError.message}</p>
        </div>
      </div>
    );
  }
  
  // Detail view
  if (selectedFailureId && detailData) {
    return (
      <div className="container mx-auto px-4 py-6">
        <FailureDetailView
          failure={detailData.data}
          onBack={handleBackToList}
          onApprove={handleApprove}
          onReject={handleReject}
          onFlag={handleFlag}
          onUnflag={handleUnflag}
          loading={approveMutation.isPending || rejectMutation.isPending || flagMutation.isPending || unflagMutation.isPending}
        />
      </div>
    );
  }
  
  // Loading detail
  if (selectedFailureId && detailLoading) {
    return (
      <div className="container mx-auto px-4 py-6">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading failure details...</p>
          </div>
        </div>
      </div>
    );
  }
  
  // List view
  return (
    <div className="container mx-auto px-4 py-6">
      <FailureDashboard
        initialFailures={failuresData?.data}
        onSelectFailure={handleSelectFailure}
        useMockData={false}
      />
    </div>
  );
};

export default FailuresPage;
