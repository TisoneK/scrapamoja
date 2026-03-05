/**
 * VisualPreview Component
 * 
 * Renders a DOM snapshot with highlighting for matched selectors.
 * This component displays the captured HTML snapshot and overlays
 * visual indicators showing what each proposed selector would capture.
 * 
 * Story: 4.1 - View Proposed Selectors with Visual Preview
 * 
 * @component
 * 
 * Features:
 * - Renders captured DOM snapshot (HTML) in a sanitized container
 * - Applies CSS highlighting to elements matching proposed selectors
 * - Shows confidence scores as badges next to each alternative
 * - Displays blast radius information for impact awareness
 * 
 * Usage:
 * ```tsx
 * <VisualPreview 
 *   snapshotHtml={failure.snapshot?.html}
 *   alternatives={failure.alternatives}
 *   selectedAlternativeId={selectedId}
 *   onSelectAlternative={handleSelect}
 * />
 * ```
 */

import React, { useState, useCallback, useMemo } from 'react';
import { AlertCircle, CheckCircle, XCircle, Info } from 'lucide-react';

// Types (should match API schemas)
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

interface VisualPreviewProps {
  /** HTML content of the captured DOM snapshot */
  snapshotHtml?: string;
  /** List of proposed alternative selectors */
  alternatives: AlternativeSelector[];
  /** Currently selected alternative ID for highlighting */
  selectedAlternativeId?: string;
  /** Callback when user selects an alternative */
  onSelectAlternative?: (selector: string) => void;
  /** Whether the preview is in read-only mode */
  readOnly?: boolean;
}

/**
 * Get confidence tier color based on score
 */
const getConfidenceColor = (score: number): string => {
  if (score >= 0.7) return 'bg-green-500';
  if (score >= 0.4) return 'bg-yellow-500';
  return 'bg-red-500';
};

/**
 * Get severity badge color
 */
const getSeverityColor = (severity: string): string => {
  switch (severity) {
    case 'low': return 'bg-green-100 text-green-800';
    case 'medium': return 'bg-yellow-100 text-yellow-800';
    case 'high': return 'bg-orange-100 text-orange-800';
    case 'critical': return 'bg-red-100 text-red-800';
    default: return 'bg-gray-100 text-gray-800';
  }
};

/**
 * Sanitize HTML to prevent XSS attacks
 * Removes script tags, event handlers, and dangerous attributes
 */
const sanitizeHtml = (html: string): string => {
  if (!html) return '';
  
  // Create a temporary container for sanitization
  const temp = document.createElement('div');
  temp.textContent = html; // This escapes HTML entities
  
  // Get back the escaped version
  let sanitized = temp.innerHTML;
  
  // Additional security: remove potentially dangerous patterns
  const dangerousPatterns = [
    /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
    /on\w+="[^"]*"/gi,
    /on\w+='[^']*'/gi,
    /javascript:/gi,
    /data:/gi,
  ];
  
  dangerousPatterns.forEach(pattern => {
    sanitized = sanitized.replace(pattern, '');
  });
  
  return sanitized;
};

/**
 * VisualPreview Component
 */
export const VisualPreview: React.FC<VisualPreviewProps> = ({
  snapshotHtml,
  alternatives,
  selectedAlternativeId,
  onSelectAlternative,
  readOnly = false,
}) => {
  const [zoom, setZoom] = useState(100);
  const [showOverlay, setShowOverlay] = useState(true);

  // Sanitize HTML before rendering
  const sanitizedHtml = useMemo(() => 
    snapshotHtml ? sanitizeHtml(snapshotHtml) : '', 
    [snapshotHtml, sanitizeHtml]
  );

  // If no snapshot available, show placeholder
  if (!sanitizedHtml) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg">
        <div className="text-center text-gray-500">
          <Info className="w-12 h-12 mx-auto mb-4" />
          <p className="text-lg font-medium">No snapshot available</p>
          <p className="text-sm">DOM snapshot was not captured for this failure</p>
        </div>
      </div>
    );
  }

  return (
    <div className="visual-preview-container">
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-4 p-2 bg-gray-50 rounded-lg">
        <div className="flex items-center space-x-4">
          <label className="flex items-center space-x-2">
            <span className="text-sm text-gray-600">Zoom:</span>
            <input
              type="range"
              min="50"
              max="200"
              value={zoom}
              onChange={(e) => setZoom(Number(e.target.value))}
              className="w-24"
            />
            <span className="text-sm text-gray-600">{zoom}%</span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={showOverlay}
              onChange={(e) => setShowOverlay(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm text-gray-600">Show overlay</span>
          </label>
        </div>
        <div className="text-sm text-gray-500">
          {alternatives.length} alternative(s) available
        </div>
      </div>

      {/* Preview Area */}
      <div 
        className="relative border rounded-lg overflow-auto bg-white"
        style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top left' }}
      >
        {/* Render HTML content */}
        <div 
          className="p-4"
          dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
        />
        
        {/* Highlight Overlay */}
        {showOverlay && selectedAlternativeId && (
          <div className="absolute inset-0 pointer-events-none">
            {/* CSS highlighting applied via style injection */}
            <style>{`
              ${alternatives
                .filter(alt => alt.selector === selectedAlternativeId)
                .map(alt => alt.highlight_css || '')
                .join('\n')}
            `}</style>
          </div>
        )}
      </div>

      {/* Alternatives Panel */}
      <div className="mt-4 space-y-2">
        <h4 className="text-sm font-medium text-gray-700">Proposed Alternatives</h4>
        {alternatives.map((alt, index) => (
          <button
            key={index}
            onClick={() => onSelectAlternative?.(alt.selector)}
            disabled={readOnly}
            className={`w-full text-left p-3 rounded-lg border transition-colors ${
              selectedAlternativeId === alt.selector
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <code className="text-sm bg-gray-100 px-2 py-1 rounded block">
                    {alt.selector}
                  </code>
                  {/* Custom Selector Badge (Story 4.4) */}
                  {alt.is_custom && (
                    <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs rounded-full font-medium">
                      Custom
                    </span>
                  )}
                </div>
                <span className="text-xs text-gray-500 mt-1 block">
                  Strategy: {alt.strategy}
                </span>
                {/* Custom notes preview (Story 4.4) */}
                {alt.is_custom && alt.custom_notes && (
                  <span className="text-xs text-gray-400 mt-1 block italic">
                    Note: {alt.custom_notes.substring(0, 50)}{alt.custom_notes.length > 50 ? '...' : ''}
                  </span>
                )}
              </div>
              <div className="flex items-center space-x-3">
                {/* Confidence Score Badge */}
                <span className={`px-2 py-1 rounded text-white text-xs ${getConfidenceColor(alt.confidence_score)}`}>
                  {Math.round(alt.confidence_score * 100)}%
                </span>
                
                {/* Blast Radius Severity */}
                {alt.blast_radius && (
                  <span className={`px-2 py-1 rounded text-xs ${getSeverityColor(alt.blast_radius.severity)}`}>
                    {alt.blast_radius.severity}
                  </span>
                )}
              </div>
            </div>
            
            {/* Blast Radius Details */}
            {alt.blast_radius && alt.blast_radius.affected_count > 0 && (
              <div className="mt-2 text-xs text-gray-600">
                <span className="font-medium">Impact:</span> {alt.blast_radius.affected_count} selector(s) affected
                {alt.blast_radius.affected_sports.length > 0 && (
                  <span className="ml-2">• Sports: {alt.blast_radius.affected_sports.join(', ')}</span>
                )}
              </div>
            )}
          </button>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-4 flex items-center space-x-4 text-xs text-gray-600">
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-green-500 rounded"></div>
          <span>High Confidence (≥70%)</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-yellow-500 rounded"></div>
          <span>Medium Confidence (40-69%)</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-red-500 rounded"></div>
          <span>Low Confidence (<40%)</span>
        </div>
      </div>
    </div>
  );
};

export default VisualPreview;
