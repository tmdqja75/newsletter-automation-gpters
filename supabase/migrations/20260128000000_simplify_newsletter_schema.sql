-- Migration: Simplify newsletter schema to single body column
-- Created: 2026-01-28
-- Description: Drops complex JSONB structure, adds markdown body column
-- Strategy: Fresh start - deletes all existing newsletters

BEGIN;

-- Step 1: Delete all existing newsletters (fresh start strategy)
DELETE FROM newsletters;

-- Step 2: Drop old columns
ALTER TABLE newsletters
DROP COLUMN IF EXISTS tldr,
DROP COLUMN IF EXISTS core_issues,
DROP COLUMN IF EXISTS deep_dive,
DROP COLUMN IF EXISTS next_questions,
DROP COLUMN IF EXISTS sources,
DROP COLUMN IF EXISTS published_at;

-- Step 3: Add new body column (NOT NULL since we deleted all data)
ALTER TABLE newsletters
ADD COLUMN body TEXT NOT NULL;

-- Step 4: Update table and column comments
COMMENT ON TABLE newsletters IS 'Generated newsletter content with markdown body';
COMMENT ON COLUMN newsletters.body IS 'Complete newsletter content in markdown format';
COMMENT ON COLUMN newsletters.title IS 'Newsletter title';
COMMENT ON COLUMN newsletters.is_published IS 'Publication status (kept for tracking)';

COMMIT;
