-- Billing enforcement: every analysis carries its Plan's text limit, and deleting one no longer scans the Usage ledger.

-- Rows from before billing get the schema maximum, which was the only limit then.
UPDATE public.analysis_history SET max_input_chars = 10000 WHERE max_input_chars IS NULL;
ALTER TABLE public.analysis_history ALTER COLUMN max_input_chars SET NOT NULL;

-- ON DELETE SET NULL looks up the analysis's Usage rows on every delete; without this index each one scans the ledger.
CREATE INDEX idx_usage_events_analysis ON public.usage_events (analysis_id);
