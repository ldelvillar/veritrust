-- Migration: async analysis pipeline.
--
-- POST /analysis now inserts a 'pending' row and returns immediately; an arq
-- worker fills in the result and flips the row to 'done' (or 'failed' with an
-- error_code). Apply this once to an existing database (e.g. Supabase) that was
-- created before the status column existed. Fresh databases get the final shape
-- from db/init.sql and do not need this file.

ALTER TABLE public.analysis_history
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'done'
        CHECK (status IN ('pending', 'done', 'failed')),
    ADD COLUMN IF NOT EXISTS error_code TEXT;

-- Result columns are unknown while a row is pending, so they must allow NULL.
ALTER TABLE public.analysis_history
    ALTER COLUMN label DROP NOT NULL,
    ALTER COLUMN confidence DROP NOT NULL,
    ALTER COLUMN explanation DROP NOT NULL;

-- Relax the confidence range check so it tolerates the NULL of a pending row.
ALTER TABLE public.analysis_history
    DROP CONSTRAINT IF EXISTS analysis_history_confidence_check;
ALTER TABLE public.analysis_history
    ADD CONSTRAINT analysis_history_confidence_check
        CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0));
