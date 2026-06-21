/**
 * ApprovalPanel Component
 * 
 * Panel for approving, rejecting, or flagging proposed selectors.
 * 
 * Story: 4.3 - Flag Selectors for Developer Review
 * 
 * @component
 */

import React, { useState } from 'react';
import { Check, X, MessageSquare, Flag } from 'lucide-react';

interface ApprovalPanelProps {
  /** Currently selected selector */
  selectedSelector?: string;
  /** Callback when user approves */
  onApprove?: (selector: string, notes?: string) => void;
  /** Callback when user rejects */
  onReject?: (selector: string, reason: string) => void;
  /** Callback when user flags for developer review */
  onFlag?: (note: string) => void;
  /** Whether the failure is already flagged */
  isFlagged?: boolean;
  /** Callback when user removes flag */
  onUnflag?: () => void;
  /** Whether actions are disabled */
  disabled?: boolean;
  /** Loading state */
  loading?: boolean;
}

export const ApprovalPanel: React.FC<ApprovalPanelProps> = ({
  selectedSelector,
  onApprove,
  onReject,
  onFlag,
  isFlagged = false,
  onUnflag,
  disabled = false,
  loading = false,
}) => {
  const [notes, setNotes] = useState('');
  const [reason, setReason] = useState('');
  const [flagNote, setFlagNote] = useState('');
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [showFlagForm, setShowFlagForm] = useState(false);

  const handleApprove = () => {
    if (selectedSelector) {
      onApprove?.(selectedSelector, notes || undefined);
      setNotes('');
    }
  };

  const handleReject = () => {
    if (selectedSelector && reason) {
      onReject?.(selectedSelector, reason);
      setReason('');
      setShowRejectForm(false);
    }
  };

  const handleFlag = () => {
    if (flagNote) {
      onFlag?.(flagNote);
      setFlagNote('');
      setShowFlagForm(false);
    }
  };

  const handleUnflag = () => {
    onUnflag?.();
  };

  return (
    <div className="approval-panel bg-gray-50 rounded-lg p-4">
      <h4 className="text-sm font-medium text-gray-700 mb-4">
        Actions
      </h4>

      {/* Approve Section */}
      <div className="mb-4">
        <button
          onClick={handleApprove}
          disabled={disabled || !selectedSelector || loading}
          className="w-full flex items-center justify-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Check className="w-4 h-4 mr-2" />
          Approve Selector
        </button>
        
        {/* Optional Notes */}
        <div className="mt-2">
          <label className="block text-xs text-gray-500 mb-1">
            <MessageSquare className="w-3 h-3 inline mr-1" />
            Optional Notes
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add notes about this approval..."
            className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
            rows={2}
            disabled={disabled}
          />
        </div>
      </div>

      {/* Reject Section */}
      <div className="border-t border-gray-200 pt-4">
        {!showRejectForm ? (
          <button
            onClick={() => setShowRejectForm(true)}
            disabled={disabled || !selectedSelector || loading}
            className="w-full flex items-center justify-center px-4 py-2 border border-red-300 text-red-700 rounded-lg hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <X className="w-4 h-4 mr-2" />
            Reject Selector
          </button>
        ) : (
          <div className="space-y-2">
            <label className="block text-sm text-red-700 font-medium">
              Reason for rejection (required)
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Explain why this selector is being rejected..."
              className="w-full border border-red-300 rounded px-2 py-1 text-sm"
              rows={3}
              required
              disabled={disabled}
            />
            <div className="flex space-x-2">
              <button
                onClick={() => {
                  setShowRejectForm(false);
                  setReason('');
                }}
                disabled={disabled || loading}
                className="flex-1 px-3 py-1 border border-gray-300 rounded text-sm hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={disabled || !reason || loading}
                className="flex-1 px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700 disabled:opacity-50"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Flag Section */}
      <div className="border-t border-gray-200 pt-4 mt-4">
        {isFlagged ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="flex items-center text-amber-700 text-sm font-medium">
                <Flag className="w-4 h-4 mr-1" />
                Flagged for Review
              </span>
              <button
                onClick={handleUnflag}
                disabled={disabled || loading}
                className="text-xs text-gray-500 hover:text-gray-700 underline"
              >
                Remove Flag
              </button>
            </div>
          </div>
        ) : !showFlagForm ? (
          <button
            onClick={() => setShowFlagForm(true)}
            disabled={disabled || loading}
            className="w-full flex items-center justify-center px-4 py-2 border border-amber-300 text-amber-700 rounded-lg hover:bg-amber-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Flag className="w-4 h-4 mr-2" />
            Flag for Developer Review
          </button>
        ) : (
          <div className="space-y-2">
            <label className="block text-sm text-amber-700 font-medium">
              Reason for flagging (required)
            </label>
            <textarea
              value={flagNote}
              onChange={(e) => setFlagNote(e.target.value)}
              placeholder="Explain why this needs developer review..."
              className="w-full border border-amber-300 rounded px-2 py-1 text-sm"
              rows={3}
              required
              disabled={disabled}
            />
            <div className="flex space-x-2">
              <button
                onClick={() => {
                  setShowFlagForm(false);
                  setFlagNote('');
                }}
                disabled={disabled || loading}
                className="flex-1 px-3 py-1 border border-gray-300 rounded text-sm hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleFlag}
                disabled={disabled || !flagNote || loading}
                className="flex-1 px-3 py-1 bg-amber-600 text-white rounded text-sm hover:bg-amber-700 disabled:opacity-50"
              >
                Confirm Flag
              </button>
            </div>
          </div>
        )}
      </div>

      {/* No selector selected message */}
      {!selectedSelector && (
        <p className="text-xs text-gray-500 text-center mt-4">
          Select an alternative to approve, reject, or flag
        </p>
      )}
    </div>
  );
};

export default ApprovalPanel;
