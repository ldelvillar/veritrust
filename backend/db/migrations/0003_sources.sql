-- Migration: retrieved biomedical sources.
--
-- The Investigator agent queries Europe PMC for each translated statement and
-- attaches the supporting literature ({title, url, source, year, statement}); this
-- column persists that evidence so the result page can show a "Fuentes" section.
-- Apply this once to an existing database. Fresh databases get the final shape
-- from db/init.sql and do not need this file.

ALTER TABLE public.analysis_history
    ADD COLUMN IF NOT EXISTS sources JSONB;
