# AGENTS.md

Package-specific guidance lives in `backend/AGENTS.md` and `frontend/AGENTS.md`; each loads when you work with files under that directory.

## Project Overview

VeriTrust is an AI-powered medical misinformation detection system: users submit medical text, URLs, or files (PDF/TXT/MD), a LangGraph multi-agent pipeline analyzes them, and results (label, confidence, per-claim verdicts, sources, explanation) are persisted in PostgreSQL and surfaced via a Next.js dashboard. `backend/` is Python (FastAPI + arq worker), `frontend/` is Next.js; they communicate over a typed contract — `frontend/src/types/api.d.ts` is generated from the backend's OpenAPI spec. Domain terms (Analysis, Run, Retry vs Reanalyze, Orphaned analysis, …) are defined in `CONTEXT.md`; architectural decisions live in `docs/adr/`.

## Always verify before declaring done

CI enforces all of these; fix failures at the root cause, never by suppression.

- **Backend** — ruff check, ruff format `--check`, mypy, and the relevant test suite at ≥80% coverage (exact invocations in `backend/AGENTS.md`).
- **Frontend** — lint, typecheck (covers tests, which build skips), prettier `--check`, and build.

## Shell command conventions

Run every command from the **repo root** — never `cd` into a subdirectory. Backend tools: `uv run --directory backend <tool>` (uv, not pip). Frontend scripts: `pnpm --dir frontend <script>` (pnpm v11, not npm/yarn). Chain with `&&` when running both.

## Architecture

### Request flow

The pipeline is slow (several sequential LLM calls, plus medical-source lookups for every claim), so it runs **out of the request** in an arq worker. The web process only enqueues; the client polls the detail endpoint until the row leaves `pending`. The provider and per-agent models are configurable (`LLM_PROVIDER` plus that provider's own fields in `Settings`); `backend/.env.example` is the source of truth for the accepted values. Production runs `ollama` self-hosted; the hosted API providers are development-only.

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
