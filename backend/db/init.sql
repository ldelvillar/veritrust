-- Bootstrap schema for the in-compose Postgres. Runs once when the data volume is empty


CREATE TABLE IF NOT EXISTS public.analysis_history (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      TEXT NOT NULL,
    source_type  TEXT NOT NULL CHECK (source_type IN ('text', 'file', 'url', 'pdf')),
    input_text   TEXT,
    input_url    TEXT,
    -- Raw uploaded PDF (source_type = 'pdf'); served back so the report can render it.
    pdf_data     BYTEA,
    pdf_filename TEXT,
    -- Result columns are NULL while status = 'pending' (filled in by the worker).
    label        TEXT,
    confidence   DOUBLE PRECISION
                 CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
    explanation  TEXT,
    -- Per-claim BERT verdicts ([{text, label, confidence}, ...]); NULL while pending.
    claims       JSONB,
    -- Retrieved biomedical sources ([{title, url, source, year, statements}, ...]); NULL while pending.
    sources      JSONB,
    status       TEXT NOT NULL DEFAULT 'done'
                 CHECK (status IN ('pending', 'done', 'failed')),
    error_code   TEXT,
    -- Opt-in public share link; NULL = not shared. Cleared on revoke.
    share_token  TEXT UNIQUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_history_user_created
    ON public.analysis_history (user_id, created_at DESC);
