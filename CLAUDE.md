# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Package-specific guidance lives in `backend/CLAUDE.md` and `frontend/CLAUDE.md`; each loads when you work with files under that directory.

## Project Overview

VeriTrust is an AI-powered medical misinformation detection system: users submit medical text, URLs, or files (PDF/TXT/MD), a LangGraph multi-agent pipeline analyzes them, and results (label, confidence, per-claim verdicts, sources, explanation) are persisted in PostgreSQL and surfaced via a Next.js dashboard. `backend/` is Python (FastAPI + arq worker), `frontend/` is Next.js; they communicate over a typed contract — `frontend/src/types/api.d.ts` is generated from the backend's OpenAPI spec.

## Always verify before declaring done

CI enforces all of these; fix failures at the root cause, never by suppression.

- **Backend** — ruff check, ruff format `--check`, mypy, and the relevant test suite at ≥80% coverage (exact invocations in `backend/CLAUDE.md`).
- **Frontend** — lint, prettier `--check`, and build (build also type-checks).

## Shell command conventions

Run every command from the **repo root** — never `cd` into a subdirectory. Backend tools: `uv run --directory backend <tool>` (uv, not pip). Frontend scripts: `pnpm --dir frontend <script>` (pnpm v11, not npm/yarn). Chain with `&&` when running both.

## Architecture

### Request flow

The pipeline is slow (multiple sequential Ollama calls, medical sources lookups, BERT), so it runs **out of the request** in an arq worker. The web process only enqueues; the client polls the detail endpoint until the row leaves `pending`.

```text
Web process (FastAPI)                          Worker process (arq, app/worker.py)
─────────────────────                          ───────────────────────────────────
User (browser)
  → Clerk JWT auth
  → POST /analysis
  → INSERT 'pending' row (returns analysis_id)
  → enqueue run_analysis on Redis ─────────────→ run_analysis(analysis_id, …)
  → Return {status: "pending", analysis_id}        → URL/file text extraction if needed
                                                   → LangGraph pipeline:
GET /analysis/{id}  (polled by frontend            ·  Extractor     (llama3)              → claims
  every 2s while status == "pending")              ·  Translator    (translategemma)      → EN, batched
  → returns status + (when done) label/            ·  Investigator  (4 sources + judge)   → sources + evidence_coverage
     confidence/explanation/claims/                ·  Health Expert (llama3.2)            → label (BioBERT) + explanation;
     sources, or error_code when                   → Confidence attenuated by coverage; softened if evidence contradicts
     status == "failed"                            → UPDATE row → 'done' (results) or 'failed' (error_code)
```

## Conventions

- **Centralised config** — read env only through `Settings` via `get_settings()`; never `os.getenv`/`load_dotenv` in feature code — add a field to `Settings` instead. Required vars are validated once at startup (`validate_runtime()`); missing values surface as `/healthz` 503, not per-request 500s. `Settings` construction is side-effect-free. Frontend reads env only through `clientEnv` (`src/env/client.ts`) or `serverEnv` (`src/env/server.ts`); both throw at module load when production vars are missing. See `.env.example` in each package.
- **Generated API types** — after any backend schema change, run `pnpm --dir frontend generate:api-types` (backend running); the frontend won't type-check against a stale contract. `frontend/src/types/api.d.ts` is generated; never edit it by hand.
- **Comments & docstrings** — every code comment is **exactly one line**; never multi-line, multi-sentence, or stacked `#`/`//` blocks. Class/method docstrings are a single plain sentence. Architectural rationale belongs here or in the PR, not in code.

## Security

- Never hardcode credentials, keys, or URLs — read them from environment via the config layer.
- Test fixtures must use dummy/mock values, never real keys.
