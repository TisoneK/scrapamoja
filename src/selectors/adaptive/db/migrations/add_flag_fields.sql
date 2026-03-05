-- Migration: Add flag fields to failures table
-- Story: 4.3 - Flag Selectors for Developer Review
-- Date: 2026-03-05

-- Add flag-related columns to failures table
ALTER TABLE failures 
ADD COLUMN flagged BOOLEAN DEFAULT FALSE,
ADD COLUMN flag_note TEXT,
ADD COLUMN flagged_at TIMESTAMP;

-- Create index for flagged failures for better query performance
CREATE INDEX idx_failures_flagged ON failures(flagged);

-- Create index for flagged_at for time-based queries
CREATE INDEX idx_failures_flagged_at ON failures(flagged_at) WHERE flagged = TRUE;
