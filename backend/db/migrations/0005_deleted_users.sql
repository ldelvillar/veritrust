-- Accounts deleted in Clerk, so no Analysis or Usage is written for them after the user.deleted webhook erased their data.

CREATE TABLE public.deleted_users (
    user_id    TEXT PRIMARY KEY,
    deleted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
