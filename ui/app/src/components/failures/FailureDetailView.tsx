/**
 * FailureDetailView Component
 * 
 * Displays detailed information about a specific selector failure,
 * including the failed selector, proposed alternatives, and visual preview.
 * 
 * Story: 4.1 - View Proposed Selectors with Visual Preview
 * 
 * @component
 * 
 * Features:
 * - Shows failed selector with error details
 * - Displays visual preview with highlighting
 * - Lists proposed alternatives with confidence scores
 * - Provides approve/reject actions
 */

import React, { useState, useEffect } from 'react';
import { ArrowLeft, Check, X, AlertTriangle, Clock, Globe, Flag, Wand2 } from 'lucide-react';
import { VisualPreview } from './VisualPreview';
import { ApprovalPanel } from './ApprovalPanel';
import { CustomSelectorForm } from './CustomSelectorForm';

// Types
interface BlastRadiusInfo {
  affected_count: number;
  affected_sports: string[];
  severity: 'low' | 'medium' | 'high' | 'critical';
  container_path: string;
}

interface AlternativeSelector {
  selector: string;
  strategy: 'css' | 'xpath' | 'text' | 'attribute';
  confidence_score: number;
  blast_radius?: BlastRadiusInfo;
  highlight_css?: string;
  // Custom selector fields (Story 4.4)
  is_custom?: boolean;
  custom_notes?: string;
}

interface FailureDetail {
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

interface FailureDetailViewProps {
  /** The failure detail data */
  failure?: FailureDetail;
  /** Callback when user navigates back */
  onBack?: () => void;
  /** Callback when user approves a selector */
  onApprove?: (selector: string, notes?: string) => void;
  /** Callback when user rejects a selector */
  onReject?: (selector: string, reason: string) => void;
  /** Callback when user flags for developer review */
  onFlag?: (note: string) => void;
  /** Callback when user removes flag */
  onUnflag?: () => void;
  /** Callback when user creates a custom selector (Story 4.4) */
  onCreateCustomSelector?: (selector: string, strategy: string, notes: string) => void;
  /** Loading state */
  loading?: boolean;
  /** Error message if fetch failed */
  error?: string;
}

/**
 * Get confidence color
 */
const getConfidenceColor = (score: number): string => {
  if (score >= 0.7) return 'text-green-600';
  if (score >= 0.4) return 'text-yellow-600';
  return 'text-red-600';
};

/**
 * Get severity badge styles
 */
const getSeverityStyles = (severity: string): string => {
  switch (severity) {
    case 'critical': return 'bg-red-100 text-red-800';
    case 'high': return 'bg-orange-100 text-orange-800';
    case 'moderate': return 'bg-yellow-100 text-yellow-800';
    default: return 'bg-gray-100 text-gray-800';
  }
};

export const FailureDetailView: React.FC<FailureDetailViewProps> = ({
  failure,
  onBack,
  onApprove,
  onReject,
  onFlag,
  onUnflag,
  onCreateCustomSelector,
  loading = false,
  error,
}) => {
  const [selectedAlternative, setSelectedAlternative] = useState<string | null>(null);
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [showRejectionModal, setShowRejectionModal] = useState(false);
  const [showCustomSelectorModal, setShowCustomSelectorModal] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');

  // Auto-select first alternative if none selected
  useEffect(() => {
    if (failure?.alternatives.length && !selectedAlternative) {
      setSelectedAlternative(failure.alternatives[0].selector);
    }
  }, [failure, selectedAlternative]);

  const handleApprove = () => {
    if (selectedAlternative) {
      onApprove?.(selectedAlternative, approvalNotes);
      setShowApprovalModal(false);
      setApprovalNotes('');
    }
  };

  const handleReject = () => {
    if (selectedAlternative && rejectionReason) {
      onReject?.(selectedAlternative, rejectionReason);
      setShowRejectionModal(false);
      setRejectionReason('');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading failure details...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500">Error: {error}</div>
      </div>
    );
  }

  if (!failure) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">No failure data available</div>
      </div>
    );
  }

  return (
    <div className="failure-detail-view">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={onBack}
          className="flex items-center text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Dashboard
        </button>
        <div className="flex items-center space-x-2">
          <span className={`px-3 py-1 rounded text-sm ${getSeverityStyles(failure.severity)}`}>
            {failure.severity}
          </span>
        </div>
      </div>

      {/* Failure Info */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Failed Selector</h2>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Selector:</span>
            <code className="bg-gray-100 px-3 py-1 rounded text-sm">
              {failure.failed_selector}
            </code>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Error Type:</span>
            <span className="text-red-600 font-medium">{failure.error_type}</span>
          </div>
          {failure.failure_reason && (
            <div className="flex items-start">
              <span className="text-gray-600 mr-4">Reason:</span>
              <span className="text-gray-800">{failure.failure_reason}</span>
            </div>
          )}
          <div className="flex items-center space-x-4 pt-2">
            {failure.sport && (
              <span className="flex items-center text-sm text-gray-600">
                <Globe className="w-4 h-4 mr-1" />
                {failure.sport}
              </span>
            )}
            {failure.site && (
              <span className="text-sm text-gray-600">{failure.site}</span>
            )}
            <span className="flex items-center text-sm text-gray-600">
              <Clock className="w-4 h-4 mr-1" />
              {new Date(failure.timestamp).toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      {/* Flag Note - Show prominently if flagged */}
      {failure.flagged && failure.flag_note && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
          <div className="flex items-start">
            <AlertTriangle className="w-5 h-5 text-amber-600 mr-2 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-amber-800">Flagged for Developer Review</h3>
              <p className="text-sm text-amber-700 mt-1">{failure.flag_note}</p>
              {failure.flagged_at && (
                <p className="text-xs text-amber-600 mt-2">
                  Flagged on {new Date(failure.flagged_at).toLocaleString()}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Visual Preview */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-4">Visual Preview</h3>
        <VisualPreview
          alternatives={failure.alternatives}
          selectedAlternativeId={selectedAlternative || undefined}
          onSelectAlternative={setSelectedAlternative}
        />
      </div>

      {/* Action Panel with Approve/Reject/Flag */}
      <div className="mb-6">
        <ApprovalPanel
          selectedSelector={selectedAlternative || undefined}
          onApprove={(selector, notes) => {
            onApprove?.(selector, notes);
            setShowApprovalModal(false);
            setApprovalNotes('');
          }}
          onReject={(selector, reason) => {
            onReject?.(selector, reason);
            setShowRejectionModal(false);
            setRejectionReason('');
          }}
          onFlag={onFlag}
          isFlagged={failure?.flagged}
          onUnflag={onUnflag}
          disabled={!selectedAlternative}
          loading={loading}
        />
        
        {/* Create Custom Selector Button (Story 4.4) */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <button
            onClick={() => setShowCustomSelectorModal(true)}
            disabled={loading}
            className="w-full flex items-center justify-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Wand2 className="w-4 h-4 mr-2" />
            Create Custom Selector
          </button>
          <p className="text-xs text-gray-500 text-center mt-2">
            Manually create an alternative selector for edge cases
          </p>
        </div>
      </div>

      {/* Approval Modal */}
      {showApprovalModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold mb-4">Approve Selector</h3>
            <p className="text-sm text-gray-600 mb-4">
              Are you sure you want to approve this selector?
            </p>
            <code className="block bg-gray-100 p-2 rounded text-sm mb-4">
              {selectedAlternative}
            </code>
            <textarea
              value={approvalNotes}
              onChange={(e) => setApprovalNotes(e.target.value)}
              placeholder="Optional notes..."
              className="w-full border rounded p-2 text-sm mb-4"
              rows={3}
            />
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setShowApprovalModal(false)}
                className="px-4 py-2 border rounded"
              >
                Cancel
              </button>
              <button
                onClick={handleApprove}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                Approve
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rejection Modal */}
      {showRejectionModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold mb-4">Reject Selector</h3>
            <p className="text-sm text-gray-600 mb-4">
              Please provide a reason for rejecting this selector.
            </p>
            <code className="block bg-gray-100 p-2 rounded text-sm mb-4">
              {selectedAlternative}
            </code>
            <textarea
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="Reason for rejection (required)..."
              className="w-full border rounded p-2 text-sm mb-4"
              rows={3}
              required
            />
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setShowRejectionModal(false)}
                className="px-4 py-2 border rounded"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={!rejectionReason}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
              >
                Reject
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Custom Selector Modal (Story 4.4) */}
      {showCustomSelectorModal && failure && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-lg w-full">
            <CustomSelectorForm
              failureId={failure.failure_id}
              onSubmit={(selector, strategy, notes) => {
                onCreateCustomSelector?.(selector, strategy, notes);
                setShowCustomSelectorModal(false);
              }}
              onCancel={() => setShowCustomSelectorModal(false)}
              isSubmitting={loading}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default FailureDetailView;
