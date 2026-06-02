---
description: Propose-first improvement pass for VeriTrust — UI/UX polish, new features, and product strategy, grounded in the actual code
argument-hint: "[polish|features|strategy] (optional — defaults to all)"
---

You are working on VeriTrust, an AI medical-misinformation detector (Next.js App
Router frontend + FastAPI/LangGraph backend, Clerk auth, async analysis worker).
Read `CLAUDE.md` first and treat its conventions as binding.

Your job this session: make VeriTrust feel like a more professional, complete
product — through UI/UX polish, new user-facing features, and product strategy.
Work in two phases. Do NOT write or edit any code until I approve a plan.

If `$ARGUMENTS` names a focus (`polish`, `features`, or `strategy`), bias the
audit and plan toward it. Otherwise cover all three.

## PHASE 1 — Audit & propose (do this first, no code changes)

1. Explore the real app, don't assume:
   - Frontend: walk the pages under `frontend/src/app` (`/`, `/analisis`,
     `/dashboard`, `/historial`, legal pages), the shared components, `apiClient`,
     `useApiQuery`, and how loading / empty / error / pending-polling states are
     actually handled.
   - Backend: the analysis flow (POST `/analysis` → pending row → worker → poll
     detail), the error contract (`ErrorCode` / `make_error_detail`), dashboard
     and history endpoints. Note what data already exists but isn't surfaced.

2. Evaluate it as a product, from a first-time user's eyes:
   - Where does it look unfinished, inconsistent, or untrustworthy? (Trust matters
     a lot for a misinformation tool — call out anything that undermines
     credibility.)
   - What obvious capability is missing that users would expect?
   - What's confusing in the analysis → result → history journey?

3. Produce a prioritized improvement plan as a table:
   | # | Improvement | Type (Polish/Feature/Strategy) | User impact | Effort (S/M/L) | Files touched | Risk |
   Order by impact-to-effort. Include a mix of quick wins and 1–2 bigger bets.
   For each item give 1–2 sentences of concrete detail (what it looks like / does),
   not vague labels like "improve UX".

4. Flag anything that needs my decision (design direction, scope, new deps) and
   ask before assuming. Surface tradeoffs instead of picking silently.

Then STOP and let me choose which items to build.

## PHASE 2 — Build (only what I approve)

For each approved item:
- Make surgical changes that trace directly to that item — no drive-by refactors,
  no speculative abstractions, match the surrounding code's style.
- Frontend: respect the existing component patterns, `apiClient`/`ApiError`
  handling, and Clerk auth. Keep loading/empty/error/pending states first-class.
  Ensure it's responsive and accessible (labels, focus, contrast).
- Backend: if a feature needs a new endpoint or error, follow the conventions —
  extend `ErrorCode` + Spanish message + `responses=`, read config via `Settings`,
  raw psycopg3 under `app/db/`, async end-to-end. After any schema change, run
  `pnpm generate:api-types` (never hand-edit `api.d.ts`).
- Verify before claiming done: run the relevant tests, `pnpm build`/`pnpm lint`
  for frontend, and `uv run ruff check`/`uv run mypy`/`pytest` for backend. Report
  actual results — if something fails or you skipped a check, say so.
- Keep coverage ≥80% where you touch backend code; add tests for new logic.

Work one item at a time, show me the diff intent, and pause between items so I can
steer. Prefer a few well-finished improvements over many half-done ones.
