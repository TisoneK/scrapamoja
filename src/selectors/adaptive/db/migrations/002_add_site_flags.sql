-- Migration: Add site-specific feature flags seed data
-- Story: 8.2 - Site-Based Feature Flags
-- Date: 2026-03-06
-- Purpose: Add seed data for common sites with default disabled state

-- First, ensure base sport data exists (in case table was created without seed data)
INSERT OR IGNORE INTO feature_flags (sport, enabled, created_at, updated_at) VALUES 
    ('basketball', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('tennis', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('football', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('soccer', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('baseball', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('hockey', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('volleyball', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('rugby', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cricket', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('golf', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Insert site-specific feature flags for common betting/scraping sites
-- All flags are disabled by default as per security requirements
INSERT OR IGNORE INTO feature_flags (sport, site, enabled, created_at, updated_at) VALUES 
    -- Basketball sites
    ('basketball', 'flashscore', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('basketball', 'bet365', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('basketball', 'williamhill', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    
    -- Tennis sites
    ('tennis', 'flashscore', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('tennis', 'bet365', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('tennis', 'williamhill', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    
    -- Football sites
    ('football', 'flashscore', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('football', 'bet365', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('football', 'williamhill', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    
    -- Soccer sites
    ('soccer', 'flashscore', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('soccer', 'bet365', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('soccer', 'williamhill', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    
    -- Baseball sites
    ('baseball', 'flashscore', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('baseball', 'bet365', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('baseball', 'williamhill', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    
    -- Hockey sites
    ('hockey', 'flashscore', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('hockey', 'bet365', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('hockey', 'williamhill', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    
    -- Volleyball sites
    ('volleyball', 'flashscore', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('volleyball', 'bet365', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('volleyball', 'williamhill', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    
    -- Rugby sites
    ('rugby', 'flashscore', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('rugby', 'bet365', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('rugby', 'williamhill', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    
    -- Cricket sites
    ('cricket', 'flashscore', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cricket', 'bet365', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('cricket', 'williamhill', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    
    -- Golf sites
    ('golf', 'flashscore', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('golf', 'bet365', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('golf', 'williamhill', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Add verification query to ensure data was inserted correctly
-- This query should return 40 rows (10 global + 30 site-specific)
SELECT 
    sport,
    site,
    enabled,
    COUNT(*) as flag_count
FROM feature_flags 
GROUP BY sport, site, enabled
ORDER BY sport, site;
