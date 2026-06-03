-- Migration: per-claim verdicts.
--
-- The Health Expert agent already classifies each extracted statement with BERT
-- ({text, label, confidence}); this column persists that breakdown so the result
-- page can show a claim-by-claim verdict. Apply this once to an existing database.
-- Fresh databases get the final shape from db/init.sql and do not need this file.

ALTER TABLE public.analysis_history
    ADD COLUMN IF NOT EXISTS claims JSONB;
