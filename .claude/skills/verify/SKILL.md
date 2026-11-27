---
name: verify
description: Run the change in the real stack and watch it work end to end. Use before committing a change to backend/ or frontend/, and when asked to verify, smoke-test or check that a change works.
---

# Verify

Checks and unit tests prove the parts; this proves the product: the real API, worker, Postgres, Redis, LLM provider and frontend, driven through a browser the way a user drives them. Done means you have watched the change work in the running app and can name the evidence for each behaviour it touches.

## 1. Start the stack

1. `docker info` must answer. When it doesn't, ask the user to start Docker Desktop.
2. `docker compose up -d --build --wait` builds the working tree, applies migrations and waits for every healthcheck. It binds ports 3000 and 8000, so a native `pnpm dev` or `uvicorn` on them must stop first.

Done when `docker compose ps` shows `backend`, `worker` and `frontend` healthy. The worker calls the real `LLM_PROVIDER` from `backend/.env`, so every Run spends provider calls: verify once per finished change, not once per edit.

## 2. Run the smoke

1. `docker compose exec -T postgres psql -U veritrust -d veritrust -c "TRUNCATE public.usage_events"` clears the Usage in compose's own Postgres, so the dev user's Free Allowance (10 analyses a month) never runs out across verify rounds. Run it before every `e2e:live`.
2. `pnpm --dir frontend e2e:live` signs in the Clerk dev user, submits a claim, and waits for its report for up to the 15-minute pipeline budget.

Done when it is green.

## 3. Exercise the change

The smoke proves the main flow survives. Now watch the change itself happen:

- **Frontend** — drive the changed screen at `http://localhost:3000` with a temporary `frontend/e2e/<name>.live.ts` (signed in like the smoke), run it with `pnpm --dir frontend e2e:live <name>`, `Read` the screenshots it takes, then delete it.
- **Backend, pipeline or worker** — follow the Run in `docker compose logs worker backend --since 15m` and in its row: `docker compose exec -T postgres psql -U veritrust -d veritrust -c "SELECT id, status, stage, verdict, error_code FROM public.analysis_history ORDER BY created_at DESC LIMIT 5"`.

Done when every behaviour the change adds or alters has been seen in the running app, each with its evidence: a screenshot, a log line or a row.

## When a step fails

1. Read the failure where Playwright leaves it, `frontend/test-results/<test>/error-context.md` (the page snapshot) and `test-failed-1.png`, then the worker and backend logs.
2. Fix the root cause, rebuild with `docker compose up -d --build --wait` (the images still hold the old code), and rerun from step 2.

A failure that passes on a rerun is a bug in the app or the smoke: report it, with its evidence, as a finding.

## Report

State what ran, the Analysis id and Verdict the smoke reached, and each behaviour you watched with its evidence. Leave the stack running for the next round; `docker compose down` stops it.
