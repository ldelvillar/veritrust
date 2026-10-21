-- Databases created before 'mixed' kept their old verdict checks, since the baseline skips existing tables.

ALTER TABLE public.analysis_history
    DROP CONSTRAINT analysis_history_verdict_check,
    ADD CONSTRAINT analysis_history_verdict_check
        CHECK (verdict IS NULL OR verdict IN ('real', 'fake', 'mixed', 'uncertain'));

ALTER TABLE public.analysis_feedback
    DROP CONSTRAINT analysis_feedback_suggested_verdict_check,
    ADD CONSTRAINT analysis_feedback_suggested_verdict_check
        CHECK (suggested_verdict IS NULL OR suggested_verdict IN ('real', 'fake', 'mixed', 'uncertain')),
    DROP CONSTRAINT analysis_feedback_verdict_snapshot_check,
    ADD CONSTRAINT analysis_feedback_verdict_snapshot_check
        CHECK (verdict_snapshot IN ('real', 'fake', 'mixed', 'uncertain'));
