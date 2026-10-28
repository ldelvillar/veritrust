-- Billing: Stripe customers and subscriptions, processed webhook events, the Usage ledger and each analysis's text limit.

CREATE TABLE public.billing_customers (
    user_id            TEXT PRIMARY KEY,
    stripe_customer_id TEXT NOT NULL UNIQUE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.subscriptions (
    stripe_subscription_id TEXT PRIMARY KEY,
    user_id                TEXT NOT NULL,
    status                 TEXT NOT NULL CHECK (status IN (
        'incomplete', 'incomplete_expired', 'trialing', 'active',
        'past_due', 'canceled', 'unpaid', 'paused')),
    price_id               TEXT NOT NULL,
    billing_interval       TEXT NOT NULL CHECK (billing_interval IN ('month', 'year')),
    current_period_end     TIMESTAMPTZ NOT NULL,
    cancel_at              TIMESTAMPTZ,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_subscriptions_user ON public.subscriptions (user_id);

CREATE TABLE public.stripe_events (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ON DELETE SET NULL: deleting an analysis never gives its units back.
CREATE TABLE public.usage_events (
    id          BIGSERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('analysis', 'reanalysis', 'evidence_search')),
    analysis_id UUID REFERENCES public.analysis_history (id) ON DELETE SET NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_usage_events_user_time ON public.usage_events (user_id, occurred_at);

-- The Plan's text limit fixed when the analysis opens; NULL (rows from before billing) means the schema maximum.
ALTER TABLE public.analysis_history ADD COLUMN max_input_chars INTEGER;
