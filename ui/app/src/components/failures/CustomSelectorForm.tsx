/**
 * CustomSelectorForm Component
 * 
 * Form for creating custom selectors for a failure.
 * Allows users to manually create alternative selectors when the
 * auto-proposal system cannot handle specific edge cases.
 * 
 * Story: 4.4 - Create Custom Selector Strategies
 * 
 * @component
 */

import React, { useState } from 'react';
import { X, Wand2, AlertCircle } from 'lucide-react';

// Strategy types available for custom selectors
const STRATEGY_TYPES = [
  { value: 'css', label: 'CSS Selector', description: 'Standard CSS selector (id, class, attribute)' },
  { value: 'xpath', label: 'XPath', description: 'XML Path language selector' },
  { value: 'text_anchor', label: 'Text Anchor', description: 'Select element by text content' },
  { value: 'attribute_match', label: 'Attribute Match', description: 'Match by specific attribute value' },
];

interface CustomSelectorFormProps {
  /** Failure ID for which to create custom selector */
  failureId: number;
  /** Callback when form is submitted */
  onSubmit: (selector: string, strategy: string, notes: string) => void;
  /** Callback when form is cancelled */
  onCancel: () => void;
  /** Whether the form is currently submitting */
  isSubmitting?: boolean;
  /** Error message if submission failed */
  error?: string;
}

export const CustomSelectorForm: React.FC<CustomSelectorFormProps> = ({
  failureId,
  onSubmit,
  onCancel,
  isSubmitting = false,
  error,
}) => {
  const [selectorString, setSelectorString] = useState('');
  const [strategyType, setStrategyType] = useState('css');
  const [notes, setNotes] = useState('');
  const [validationError, setValidationError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate selector string
    if (!selectorString.trim()) {
      setValidationError('Selector string is required');
      return;
    }
    
    // Validate based on strategy type
    if (strategyType === 'xpath') {
      // XPath should start with / or (//
      if (!selectorString.startsWith('/')) {
        setValidationError('XPath selectors should start with /');
        return;
      }
      // Basic XPath validation - no quotes issues
      if ((selectorString.match(/'/g) || []).length % 2 !== 0) {
        setValidationError('XPath has unmatched quotes');
        return;
      }
    } else if (strategyType === 'css') {
      // Basic CSS validation - check for common issues
      const trimmed = selectorString.trim();
      // Check for unclosed brackets
      const openBrackets = (trimmed.match(/\[/g) || []).length;
      const closeBrackets = (trimmed.match(/\]/g) || []).length;
      if (openBrackets !== closeBrackets) {
        setValidationError('CSS selector has unclosed brackets');
        return;
      }
      // Check for empty class/id
      if (trimmed.match(/\.[.]|#[#]/)) {
        setValidationError('CSS selector has empty class or ID');
        return;
      }
    }
    
    setValidationError('');
    onSubmit(selectorString.trim(), strategyType, notes.trim());
  };

  return (
    <div className="custom-selector-form">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <Wand2 className="w-5 h-5 text-indigo-600 mr-2" />
          <h3 className="text-lg font-semibold text-gray-900">
            Create Custom Selector
          </h3>
        </div>
        <button
          onClick={onCancel}
          className="text-gray-400 hover:text-gray-600"
          disabled={isSubmitting}
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Description */}
      <p className="text-sm text-gray-600 mb-4">
        Enter a custom selector to handle edge cases that the auto-proposal system cannot resolve.
        Your custom selector will be treated as a proposed alternative and can be approved or rejected.
      </p>

      {/* Error display */}
      {(error || validationError) && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start">
          <AlertCircle className="w-5 h-5 text-red-500 mr-2 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-800">
              {validationError || error}
            </p>
          </div>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit}>
        {/* Selector String */}
        <div className="mb-4">
          <label htmlFor="selectorString" className="block text-sm font-medium text-gray-700 mb-1">
            Selector String <span className="text-red-500">*</span>
          </label>
          <textarea
            id="selectorString"
            value={selectorString}
            onChange={(e) => setSelectorString(e.target.value)}
            placeholder="e.g., #nav-menu li:first-child or //div[@class='container']"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono"
            rows={3}
            disabled={isSubmitting}
            required
          />
          <p className="mt-1 text-xs text-gray-500">
            Enter the CSS or XPath selector that should replace the failed selector
          </p>
        </div>

        {/* Strategy Type */}
        <div className="mb-4">
          <label htmlFor="strategyType" className="block text-sm font-medium text-gray-700 mb-1">
            Strategy Type <span className="text-red-500">*</span>
          </label>
          <select
            id="strategyType"
            value={strategyType}
            onChange={(e) => setStrategyType(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            disabled={isSubmitting}
            required
          >
            {STRATEGY_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-gray-500">
            {STRATEGY_TYPES.find((t) => t.value === strategyType)?.description}
          </p>
        </div>

        {/* Notes */}
        <div className="mb-4">
          <label htmlFor="notes" className="block text-sm font-medium text-gray-700 mb-1">
            Notes <span className="text-gray-400">(optional)</span>
          </label>
          <textarea
            id="notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Explain your approach or why this selector should work..."
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            rows={3}
            disabled={isSubmitting}
          />
          <p className="mt-1 text-xs text-gray-500">
            Provide context about your custom selector for future reference and learning
          </p>
        </div>

        {/* Actions */}
        <div className="flex justify-end space-x-3 pt-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center"
            disabled={isSubmitting || !selectorString.trim()}
          >
            {isSubmitting ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Creating...
              </>
            ) : (
              <>
                <Wand2 className="w-4 h-4 mr-2" />
                Create Selector
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default CustomSelectorForm;
