-- Bootstrap schema for the in-compose Postgres. Runs once when the data
-- volume is empty (the official postgres image executes everything under
-- /docker-entrypoint-initdb.d only on initial database creation).


CREATE TABLE IF NOT EXISTS public.analysis_history (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      TEXT NOT NULL,
    source_type  TEXT NOT NULL CHECK (source_type IN ('text', 'file', 'url')),
    input_text   TEXT,
    input_url    TEXT,
    label        TEXT NOT NULL,
    confidence   DOUBLE PRECISION NOT NULL
                 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    explanation  TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_history_user_created
    ON public.analysis_history (user_id, created_at DESC);
