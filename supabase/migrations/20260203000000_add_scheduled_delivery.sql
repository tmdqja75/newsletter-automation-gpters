-- Migration: Add scheduled delivery question types
-- Created: 2026-02-03
-- Description: Adds 'delivery_day' and 'generate_now' to allowed question_type values
--              to support the scheduled newsletter delivery feature (Issue #32)

BEGIN;

-- Drop existing constraint
ALTER TABLE personalization_questions
DROP CONSTRAINT personalization_questions_type_check;

-- Re-create with new allowed types
ALTER TABLE personalization_questions
ADD CONSTRAINT personalization_questions_type_check CHECK (
    question_type IN ('goal', 'difficulty', 'scope', 'time', 'source', 'subtopic', 'custom', 'delivery_day', 'generate_now')
);

COMMIT;
