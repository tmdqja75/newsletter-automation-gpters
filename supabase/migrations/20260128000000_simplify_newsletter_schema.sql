-- Migration: Simplify newsletter schema to single body column
-- Created: 2026-01-28
-- Description: Drops complex JSONB structure, adds markdown body column
-- Strategy: Fresh start - deletes all existing newsletters

BEGIN;

-- Step 1: Drop dependent views that reference published_at column
DROP VIEW IF EXISTS active_topics_with_latest_newsletter CASCADE;
DROP VIEW IF EXISTS newsletter_engagement_metrics CASCADE;

-- Step 2: Delete all existing newsletters (fresh start strategy)
DELETE FROM newsletters;

-- Step 3: Drop old columns
ALTER TABLE newsletters
DROP COLUMN IF EXISTS tldr,
DROP COLUMN IF EXISTS core_issues,
DROP COLUMN IF EXISTS deep_dive,
DROP COLUMN IF EXISTS next_questions,
DROP COLUMN IF EXISTS sources,
DROP COLUMN IF EXISTS published_at;

-- Step 4: Add new body column (NOT NULL since we deleted all data)
ALTER TABLE newsletters
ADD COLUMN body TEXT NOT NULL;

-- Step 5: Recreate views using created_at instead of published_at
CREATE VIEW active_topics_with_latest_newsletter AS
SELECT
    ut.id AS topic_id,
    ut.user_id,
    ut.topic_text,
    ut.topic_description,
    ut.created_at AS topic_created_at,
    n.id AS latest_newsletter_id,
    n.title AS latest_newsletter_title,
    n.created_at AS latest_newsletter_created_at,
    n.email_sent_at AS latest_newsletter_sent_at
FROM user_topics ut
LEFT JOIN LATERAL (
    SELECT id, title, created_at, email_sent_at
    FROM newsletters
    WHERE topic_id = ut.id AND is_published = true
    ORDER BY created_at DESC
    LIMIT 1
) n ON true
WHERE ut.is_active = true;

COMMENT ON VIEW active_topics_with_latest_newsletter IS 'Active topics with their most recent published newsletter';

CREATE VIEW newsletter_engagement_metrics AS
SELECT
    n.id AS newsletter_id,
    n.user_id,
    n.topic_id,
    n.title,
    n.created_at,
    n.email_sent_at,
    COUNT(DISTINCT CASE WHEN ee.event_type = 'opened' THEN ee.id END) AS open_count,
    COUNT(DISTINCT CASE WHEN ee.event_type = 'clicked' THEN ee.id END) AS click_count,
    COUNT(DISTINCT CASE WHEN ee.event_type = 'bounced' THEN ee.id END) AS bounce_count,
    nf.feedback_type,
    nf.comment AS feedback_comment
FROM newsletters n
LEFT JOIN email_events ee ON n.id = ee.newsletter_id
LEFT JOIN newsletter_feedback nf ON n.id = nf.newsletter_id
GROUP BY n.id, n.user_id, n.topic_id, n.title, n.created_at, n.email_sent_at, nf.feedback_type, nf.comment;

COMMENT ON VIEW newsletter_engagement_metrics IS 'Newsletter engagement metrics (opens, clicks, bounces, feedback)';

-- Step 6: Update table and column comments
COMMENT ON TABLE newsletters IS 'Generated newsletter content with markdown body';
COMMENT ON COLUMN newsletters.body IS 'Complete newsletter content in markdown format';
COMMENT ON COLUMN newsletters.title IS 'Newsletter title';
COMMENT ON COLUMN newsletters.is_published IS 'Publication status (kept for tracking)';

COMMIT;
