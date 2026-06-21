/**
 * FailureDashboard Component
 * 
 * Displays a list of selector failures with filtering and navigation.
 * This is the main entry point for the escalation UI.
 * 
 * Story: 4.1 - View Proposed Selectors with Visual Preview
 * 
 * @component
 * 
 * Features:
 * - Lists failures with pagination
 * - Supports filtering by sport, site, error type, severity
 * - Shows summary info for each failure
 * - Navigation to detail view
 */

import React, { useState } from 'react';
import { AlertTriangle, Filter, ChevronRight, Clock } from 'lucide-react';

// Types
interface FailureListItem {
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

interface FailureDashboardProps {
  /** Initial failures data */
  initialFailures?: FailureListItem[];
  /** Callback when user clicks on a failure */
  onSelectFailure?: (failureId: number) => void;
  /** API base URL */
  apiBaseUrl?: string;
  /** Whether to use mock data */
  useMockData?: boolean;
}

// Mock data for development
const mockFailures: FailureListItem[] = [
  {
    failure_id: 1,
    selector_id: 'match-title',
    failed_selector: '.match-title',
    sport: 'basketball',
    site: 'flashscore',
    timestamp: new Date().toISOString(),
    error_type: 'empty_result',
    severity: 'minor',
    has_alternatives: true,
    alternative_count: 3,
  },
  {
    failure_id: 2,
    selector_id: 'odds-container',
    failed_selector: '#odds-container',
    sport: 'football',
    site: 'flashscore',
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    error_type: 'exception',
    severity: 'moderate',
    has_alternatives: true,
    alternative_count: 2,
    flagged: true,
    flag_note: 'Complex DOM structure needs developer review',
    flagged_at: new Date(Date.now() - 1800000).toISOString(),
  },
  {
    failure_id: 3,
    selector_id: 'team-scores',
    failed_selector: '.team-scores',
    sport: 'tennis',
    site: 'flashscore',
    timestamp: new Date(Date.now() - 7200000).toISOString(),
    error_type: 'timeout',
    severity: 'high',
    has_alternatives: true,
    alternative_count: 1,
    flagged: true,
    flag_note: 'Selector too specific, may not work across all match types',
    flagged_at: new Date(Date.now() - 3600000).toISOString(),
  },
];

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

/**
 * Get error type badge styles
 */
const getErrorTypeStyles = (errorType: string): string => {
  switch (errorType) {
    case 'exception': return 'bg-red-50 text-red-700';
    case 'timeout': return 'bg-yellow-50 text-yellow-700';
    case 'empty_result': return 'bg-blue-50 text-blue-700';
    default: return 'bg-gray-50 text-gray-700';
  }
};

/**
 * Format timestamp to relative time
 */
const formatRelativeTime = (timestamp: string): string => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
};

export const FailureDashboard: React.FC<FailureDashboardProps> = ({
  initialFailures,
  onSelectFailure,
  apiBaseUrl = 'http://localhost:8000',
  useMockData = true,
}) => {
  const [failures, setFailures] = useState<FailureListItem[]>(initialFailures || (useMockData ? mockFailures : []));
  const [filters, setFilters] = useState({
    sport: '',
    site: '',
    errorType: '',
    severity: '',
    flagged: false,
  });
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 20,
    total: 0,
  });
  const [loading, setLoading] = useState(false);

  const handleFilterChange = (key: string, value: string | boolean) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    // In production, would trigger API refetch
  };

  const handlePageChange = (newPage: number) => {
    setPagination(prev => ({ ...prev, page: newPage }));
    // In production, would trigger API refetch
  };

  const filteredFailures = failures.filter(f => {
    if (filters.sport && f.sport !== filters.sport) return false;
    if (filters.site && f.site !== filters.site) return false;
    if (filters.errorType && f.error_type !== filters.errorType) return false;
    if (filters.severity && f.severity !== filters.severity) return false;
    if (filters.flagged && !f.flagged) return false;
    return true;
  });

  return (
    <div className="failure-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Selector Failures</h1>
          <p className="text-sm text-gray-600 mt-1">
            Review and approve proposed selector alternatives
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-500">
            {filteredFailures.length} failure(s)
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg border border-gray-200 mb-6">
        <div className="flex items-center space-x-2 mb-4">
          <Filter className="w-4 h-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700">Filters</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Sport</label>
            <select
              value={filters.sport}
              onChange={(e) => handleFilterChange('sport', e.target.value)}
              className="w-full text-sm border border-gray-300 rounded-md px-3 py-2"
            >
              <option value="">All Sports</option>
              <option value="football">Football</option>
              <option value="basketball">Basketball</option>
              <option value="tennis">Tennis</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Site</label>
            <select
              value={filters.site}
              onChange={(e) => handleFilterChange('site', e.target.value)}
              className="w-full text-sm border border-gray-300 rounded-md px-3 py-2"
            >
              <option value="">All Sites</option>
              <option value="flashscore">Flashscore</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Error Type</label>
            <select
              value={filters.errorType}
              onChange={(e) => handleFilterChange('errorType', e.target.value)}
              className="w-full text-sm border border-gray-300 rounded-md px-3 py-2"
            >
              <option value="">All Types</option>
              <option value="exception">Exception</option>
              <option value="timeout">Timeout</option>
              <option value="empty_result">Empty Result</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Severity</label>
            <select
              value={filters.severity}
              onChange={(e) => handleFilterChange('severity', e.target.value)}
              className="w-full text-sm border border-gray-300 rounded-md px-3 py-2"
            >
              <option value="">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="moderate">Moderate</option>
              <option value="minor">Minor</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Status</label>
            <label className="flex items-center space-x-2 mt-2">
              <input
                type="checkbox"
                checked={filters.flagged}
                onChange={(e) => handleFilterChange('flagged', e.target.checked)}
                className="rounded border-gray-300 text-amber-600 focus:ring-amber-500"
              />
              <span className="text-sm text-gray-700">Flagged Only</span>
            </label>
          </div>
        </div>
      </div>

      {/* Failure List */}
      <div className="space-y-3">
        {loading ? (
          <div className="text-center py-8 text-gray-500">Loading...</div>
        ) : filteredFailures.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No failures found matching your filters
          </div>
        ) : (
          filteredFailures.map((failure) => (
            <button
              key={failure.failure_id}
              onClick={() => onSelectFailure?.(failure.failure_id)}
              className="w-full text-left bg-white p-4 rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-sm transition-all group"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                      {failure.failed_selector}
                    </code>
                    <span className={`text-xs px-2 py-0.5 rounded ${getSeverityStyles(failure.severity)}`}>
                      {failure.severity}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded ${getErrorTypeStyles(failure.error_type)}`}>
                      {failure.error_type}
                    </span>
                    {failure.flagged && (
                      <span className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-800">
                        Flagged
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-4 text-xs text-gray-500">
                    {failure.sport && (
                      <span className="capitalize">{failure.sport}</span>
                    )}
                    {failure.site && (
                      <span className="capitalize">{failure.site}</span>
                    )}
                    <span className="flex items-center">
                      <Clock className="w-3 h-3 mr-1" />
                      {formatRelativeTime(failure.timestamp)}
                    </span>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  {failure.has_alternatives && (
                    <span className="flex items-center space-x-1 text-sm text-blue-600">
                      <span className="bg-blue-100 px-2 py-1 rounded">
                        {failure.alternative_count} alternative(s)
                      </span>
                    </span>
                  )}
                  <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-blue-500" />
                </div>
              </div>
            </button>
          ))
        )}
      </div>

      {/* Pagination */}
      {pagination.total > pagination.pageSize && (
        <div className="flex items-center justify-center space-x-2 mt-6">
          <button
            onClick={() => handlePageChange(pagination.page - 1)}
            disabled={pagination.page === 1}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600">
            Page {pagination.page} of {Math.ceil(pagination.total / pagination.pageSize)}
          </span>
          <button
            onClick={() => handlePageChange(pagination.page + 1)}
            disabled={pagination.page * pagination.pageSize >= pagination.total}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default FailureDashboard;
