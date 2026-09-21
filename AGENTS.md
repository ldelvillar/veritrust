# AGENTS.md

Package-specific guidance lives in `backend/AGENTS.md` and `frontend/AGENTS.md`; each loads when you work with files under that directory.

## Project Overview

VeriTrust is an AI-powered medical misinformation detection system: users submit medical text, URLs, or files (PDF/TXT/MD), a LangGraph multi-agent pipeline analyzes them, and results (label, confidence, per-claim verdicts, sources, explanation) are persisted in PostgreSQL and surfaced via a Next.js dashboard. `backend/` is Python (FastAPI + arq worker), `frontend/` is Next.js; they communicate over a typed contract — `frontend/src/types/api.d.ts` is generated from the backend's OpenAPI spec.

## Always verify before declaring done

CI enforces all of these; fix failures at the root cause, never by suppression.

- **Backend** — ruff check, ruff format `--check`, mypy, and the relevant test suite at ≥80% coverage (exact invocations in `backend/AGENTS.md`).
- **Frontend** — lint, prettier `--check`, and build (build also type-checks).

## Shell command conventions

Run every command from the **repo root** — never `cd` into a subdirectory. Backend tools: `uv run --directory backend <tool>` (uv, not pip). Frontend scripts: `pnpm --dir frontend <script>` (pnpm v11, not npm/yarn). Chain with `&&` when running both.

## Architecture

### Request flow

The pipeline is slow (several sequential LLM calls, plus medical-source lookups for every claim), so it runs **out of the request** in an arq worker. The web process only enqueues; the client polls the detail endpoint until the row leaves `pending`. The provider and per-agent models are configurable (`LLM_PROVIDER` plus that provider's own fields in `Settings`); `backend/.env.example` is the source of truth for the accepted values. Production runs `ollama` self-hosted; the hosted API providers are development-only.

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
GET /analysis/{id}  (polled by frontend            ·  Extractor     → claims
  every 2s while status == "pending")              ·  Translator    → claims in EN, batched
  → returns status + (when done) label/            ·  Investigator  → sources + evidence_coverage (several medical APIs, LLM relevance judge)
     confidence/explanation/claims/                ·  Health Expert → explanation only; the LLM never decides the label
     sources, or error_code when                   → Verdict: Laplace-smoothed stance counts per claim, averaged over the
     status == "failed"                               claims the literature speaks to, then a three-way band (falsa/incierta/verdadera)
                                                   → Confidence attenuated by evidence_coverage
                                                   → UPDATE row → 'done' (results) or 'failed' (error_code)
```

### MCP server

The web process also serves a remote MCP server (`backend/app/mcp/`, official `mcp` SDK, Streamable HTTP) at `/mcp`, so AI clients can use VeriTrust on a signed-in user's behalf:

- **`verify_claim`** (text or URL) — inserts an `origin='mcp'` row and enqueues the same `run_analysis` job as `POST /analysis`, then polls the row until it leaves `pending` or `MCP_TOOL_WAIT_SECONDS` runs out; **`get_verification`** resumes a long-running one.
- **`search_evidence`** — enqueues `run_evidence_search`, which runs Extractor → Translator → evidence search + relevance judge (`create_evidence_graph`) with no verdict. It goes through the worker, never the web process, so Ollama load stays serialized. The arq result is kept for an hour and bound to the caller in Redis, so **`get_evidence`** resumes a search that outlasted the wait.

Auth is Clerk OAuth: clients discover Clerk from `/.well-known/oauth-protected-resource/mcp`, and `ClerkOAuthTokenVerifier` checks the JWT access token (same JWKS, issuer, `client_id` present). The server is built in the lifespan after `validate_runtime()` and reached through two exact routes, not a catch-all mount. Tool calls share the per-user rate limit with the web API.

## Conventions

- **Centralised config** — read env only through `Settings` via `get_settings()`; never `os.getenv`/`load_dotenv` in feature code — add a field to `Settings` instead. Required vars are validated once at startup (`validate_runtime()`); missing values surface as `/healthz` 503, not per-request 500s. `Settings` construction is side-effect-free. Frontend reads env only through `clientEnv` (`src/env/client.ts`) or `serverEnv` (`src/env/server.ts`); both throw at module load when production vars are missing. See `.env.example` in each package.
- **Generated API types** — after any backend schema change, run `pnpm --dir frontend generate:api-types` (backend running); the frontend won't type-check against a stale contract. `frontend/src/types/api.d.ts` is generated; never edit it by hand.
- **Comments & docstrings** — every code comment is **exactly one line**; never multi-line, multi-sentence, or stacked `#`/`//` blocks. Class/method docstrings are a single plain sentence. Architectural rationale belongs here or in the PR, not in code.

## Security

- Never hardcode credentials, keys, or URLs — read them from environment via the config layer.
- Test fixtures must use dummy/mock values, never real keys.
