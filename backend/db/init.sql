-- Bootstrap schema for the in-compose Postgres. Runs once when the data volume is empty


CREATE TABLE IF NOT EXISTS public.analysis_history (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      TEXT NOT NULL,
    source_type  TEXT NOT NULL CHECK (source_type IN ('text', 'file', 'url')),
    input_text   TEXT,
    input_url    TEXT,
    -- Raw uploaded file (source_type = 'file': pdf/txt/md); served back so the report can render it.
    file_data    BYTEA,
    file_filename TEXT,
    -- Result columns are NULL while status = 'pending' (filled in by the worker).
    label        TEXT,
    confidence   DOUBLE PRECISION
                 CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
    -- Fracción [0, 1] de afirmaciones con literatura relacionada; NULL si no se pudo medir (outage).
    evidence_coverage DOUBLE PRECISION
                 CHECK (evidence_coverage IS NULL OR (evidence_coverage >= 0.0 AND evidence_coverage <= 1.0)),
    explanation  TEXT,
    -- Verdict bucket (real/fake/uncertain) derived from label at completion; NULL while pending/failed.
    verdict      TEXT CHECK (verdict IS NULL OR verdict IN ('real', 'fake', 'uncertain')),
    -- Per-claim verdicts ([{text, label, confidence}, ...]); NULL while pending.
    claims       JSONB,
    -- Retrieved biomedical sources ([{title, url, source, year, statements}, ...]); NULL while pending.
    sources      JSONB,
    status       TEXT NOT NULL DEFAULT 'done'
                 CHECK (status IN ('pending', 'done', 'failed')),
    -- Agente activo mientras status = 'pending' (preparing/extractor/translator/investigator/health_expert); NULL en reposo.
    stage        TEXT,
    error_code   TEXT,
    -- Opt-in public share link; NULL = not shared. Cleared on revoke.
    share_token  TEXT UNIQUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Instante en que la fila dejó de estar 'pending' (done o failed); NULL mientras se analiza.
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_analysis_history_user_created
    ON public.analysis_history (user_id, created_at DESC);

-- Feeds the verdict filter and dashboard/history verdict aggregations.
CREATE INDEX IF NOT EXISTS idx_analysis_history_user_verdict
    ON public.analysis_history (user_id, verdict);

-- Valoraciones de veredicto de los usuarios; datos etiquetados para afinar el pipeline.
CREATE TABLE IF NOT EXISTS public.analysis_feedback (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id       UUID NOT NULL REFERENCES public.analysis_history(id) ON DELETE CASCADE,
    user_id           TEXT NOT NULL,
    is_correct        BOOLEAN NOT NULL,
    -- Veredicto que el usuario considera correcto; solo cuando is_correct = false.
    suggested_verdict TEXT CHECK (suggested_verdict IS NULL OR suggested_verdict IN ('real', 'fake', 'uncertain')),
    comment           TEXT,
    -- Snapshot de lo valorado; sobrevive a un re-análisis que sobrescribe la fila.
    verdict_snapshot  TEXT NOT NULL CHECK (verdict_snapshot IN ('real', 'fake', 'uncertain')),
    label_snapshot    TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_feedback_analysis_created
    ON public.analysis_feedback (analysis_id, created_at DESC);
