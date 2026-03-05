-- Migration: Add selector_id and context_snapshot to audit_log table
-- Story: 6.1 - Record Human Decisions & 6.2 - Maintain Complete Audit Trail
-- Date: 2026-03-06

-- Add selector_id column for unique selector identification
ALTER TABLE audit_log 
ADD COLUMN selector_id VARCHAR(100);

-- Add context_snapshot column for full context at decision time
ALTER TABLE audit_log 
ADD COLUMN context_snapshot JSON;

-- Make failure_id nullable to support audit events without failures
ALTER TABLE audit_log 
ALTER COLUMN failure_id DROP NOT NULL;

-- Create indexes for audit trail performance (Story 6.2 requirements)
CREATE INDEX idx_audit_log_selector_id ON audit_log(selector_id);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_action_type ON audit_log(action_type);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- Composite index for connected decision queries
CREATE INDEX idx_audit_log_selector_timestamp ON audit_log(selector_id, timestamp);

-- Create index for context_snapshot queries (JSON indexing if supported)
-- Note: SQLite doesn't support JSON indexes, but PostgreSQL does
-- CREATE INDEX idx_audit_log_context_snapshot ON audit_log USING GIN(context_snapshot);

-- Update existing records to have default selector_id if possible
UPDATE audit_log 
SET selector_id = 'legacy_' || id 
WHERE selector_id IS NULL;
