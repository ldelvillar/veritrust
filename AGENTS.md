# AGENTS.md

Package-specific guidance lives in `backend/AGENTS.md` and `frontend/AGENTS.md`; each loads when you work with files under that directory.

## Project Overview

VeriTrust is an AI-powered medical misinformation detection system: users submit medical text, URLs, or files (PDF/TXT/MD), a LangGraph multi-agent pipeline analyzes them, and results (label, confidence, per-claim verdicts, sources, explanation) are persisted in PostgreSQL and surfaced via a Next.js dashboard. `backend/` is Python (FastAPI + arq worker), `frontend/` is Next.js; they communicate over a typed contract — `frontend/src/types/api.d.ts` is generated from the backend's OpenAPI spec. Domain terms (Analysis, Run, Retry vs Reanalyze, Orphaned analysis, …) are defined in `CONTEXT.md`; architectural decisions live in `docs/adr/`.

## Always verify before declaring done

CI enforces all of these; fix failures at the root cause, never by suppression.

- **Backend** — ruff check, ruff format `--check`, mypy, and the relevant test suite at ≥80% coverage (exact invocations in `backend/AGENTS.md`).
- **Frontend** — lint, typecheck (covers tests, which build skips), prettier `--check`, build, and e2e.

## Review before opening a PR

Every change reaches `main` through a PR (squash-merged; the PR title becomes the commit title), so start work on a branch. When the change implements a GitHub issue, put `Closes #N` in the PR description, so reviewers check it against the issue rather than only the PR's own summary. Before the first push of a **risky** change, run `/code-review` (with no upstream yet, it reviews the branch against `main` plus uncommitted changes). A change is risky when it touches any of:

- pipeline agents, prompts, graph wiring, or verdict/confidence logic — also run `/eval-pipeline`
- DB models or migrations
- API schemas (anything that regenerates `api.d.ts`)
- the worker, queue, or analysis lifecycle (state transitions, Retry vs Reanalyze, orphaned analyses)
- auth, file/URL ingestion, or user input reaching an LLM — also run `/security-review`
- `Settings`, env vars, CI/deploy, backups, or infra runbooks
- both `backend/` and `frontend/`
- roughly 200+ changed lines, or a new module or abstraction — also run `/simplify`

A **high-risk** change (migrations, verdict logic or prompts, auth or ingestion, CI/deploy/backups) gets `/code-review max`, and the user reads its diff before merging.

When reviewing a change, read `REVIEW.md` first. Hand the reviewer only the target, never your own reasoning. Triage every finding with the user: fix it, or reject it with a stated reason.

After changing the review setup (`REVIEW.md`, the review commands or workflow, any `CLAUDE.md`/`AGENTS.md`), run the reviewer evals in `docs/review-evals.md` and keep the change only if no case regresses.

Keep review rounds converging:

- After the first round, re-review only what changed since: `/code-review <last-reviewed-sha>..HEAD`.
- Fix the whole class of bug a finding names, every instance, not only the flagged line.
- If a third round still raises Important findings, stop and reconsider the approach with the user.

## Shell command conventions

Run every command from the **repo root** — never `cd` into a subdirectory. Backend tools: `uv run --directory backend <tool>` (uv, not pip). Frontend scripts: `pnpm --dir frontend <script>` (pnpm v11, not npm/yarn). Chain with `&&` when running both.

## Architecture

### Request flow

The pipeline is slow (several sequential LLM calls, plus medical-source lookups for every claim), so it runs **out of the request** in an arq worker. The web process only enqueues; the client polls the detail endpoint until the row leaves `pending`. The provider and per-agent models are configurable (`LLM_PROVIDER` plus that provider's own fields in `Settings`); `backend/.env.example` is the source of truth for the accepted values. Production runs the Mistral API (`mistral`) until a dedicated GPU server is bought, then returns to self-hosted `ollama`; the other hosted API providers are development-only.

## Conventions

- **Centralised config** — read env only through `Settings` via `get_settings()`; never `os.getenv`/`load_dotenv` in feature code — add a field to `Settings` instead. Required vars are validated once at startup (`validate_runtime()`); missing values surface as `/healthz` 503, not per-request 500s. `Settings` construction is side-effect-free. Frontend reads env only through `clientEnv` (`src/env/client.ts`) or `serverEnv` (`src/env/server.ts`); both throw at module load when production vars are missing. See `.env.example` in each package.
- **Generated API types** — after any backend schema change, run `pnpm --dir frontend generate:api-types` (backend running); the frontend won't type-check against a stale contract. `frontend/src/types/api.d.ts` is generated; never edit it by hand.
- **Comments & docstrings** — every code comment is **exactly one line**; never multi-line, multi-sentence, or stacked `#`/`//` blocks. Class/method docstrings are a single plain sentence. Architectural rationale belongs here or in the PR, not in code.

## Security

- Never hardcode credentials, keys, or URLs — read them from environment via the config layer.
- Test fixtures must use dummy/mock values, never real keys.

## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues on `ldelvillar/veritrust`, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default triage labels, each named after its role (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one root `CONTEXT.md` plus `docs/adr/`. See `docs/agents/domain.md`.
