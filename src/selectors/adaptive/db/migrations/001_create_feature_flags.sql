-- Migration: Create feature_flags table
-- Story: 8.1 - Sport-Based Feature Flags
-- Date: 2026-03-06

-- Create feature_flags table
CREATE TABLE feature_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sport VARCHAR(100) NOT NULL,
    site VARCHAR(255) NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_feature_flags_sport ON feature_flags(sport);
CREATE INDEX idx_feature_flags_site ON feature_flags(site);
CREATE INDEX idx_feature_flags_enabled ON feature_flags(enabled);
CREATE INDEX idx_feature_flags_created_at ON feature_flags(created_at);
CREATE INDEX idx_feature_flags_updated_at ON feature_flags(updated_at);

-- Create unique constraint on sport + site combination
CREATE UNIQUE INDEX uq_feature_flag_sport_site ON feature_flags(sport, site);

-- Create trigger to automatically update updated_at timestamp
CREATE TRIGGER update_feature_flags_updated_at 
    AFTER UPDATE ON feature_flags
    FOR EACH ROW
BEGIN
    UPDATE feature_flags 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

-- Insert initial seed data for common sports (disabled by default)
INSERT INTO feature_flags (sport, enabled) VALUES 
    ('basketball', FALSE),
    ('tennis', FALSE),
    ('football', FALSE),
    ('soccer', FALSE),
    ('baseball', FALSE),
    ('hockey', FALSE),
    ('volleyball', FALSE),
    ('rugby', FALSE),
    ('cricket', FALSE),
    ('golf', FALSE);
