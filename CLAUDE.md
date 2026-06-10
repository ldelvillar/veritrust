# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VeriTrust is an AI-powered medical misinformation detection system: users submit medical text or URLs, a LangGraph multi-agent pipeline analyzes them, and results (label, confidence, per-claim verdicts, sources, explanation) are persisted in PostgreSQL and surfaced via a Next.js dashboard. `backend/` is Python (FastAPI + arq worker), `frontend/` is Next.js; they communicate over a typed contract — `frontend/src/types/api.d.ts` is generated from the backend's OpenAPI spec.

## Always verify before declaring done

CI enforces all of these; fix failures at the root cause, never by suppression.

- **Backend** — ruff check, ruff format `--check`, mypy, and the relevant test suite at ≥80% coverage (exact invocations below).
- **Frontend** — lint and build (build also type-checks).

## Shell command conventions

Run every command from the **repo root** — never `cd` into a subdirectory. Backend tools: `uv run --directory backend <tool>` (uv, not pip). Frontend scripts: `pnpm --dir frontend <script>` (pnpm v11, not npm/yarn). Chain with `&&` when running both.

## Commands

### Backend

```bash
uv sync --directory backend --frozen                                         # Serving/API deps + app tests (excludes ml stack)
uv sync --directory backend --frozen --extra ml                              # Add ml stack for ml/ and its tests
uv run --directory backend python -m app.main                                # API server (http://localhost:8000)
uv run --directory backend python -m app.worker                              # Analysis worker (needs Redis + Ollama)
uv run --directory backend pytest tests --cov=app --cov-fail-under=80        # App tests
uv run --directory backend pytest ml/tests --cov=ml --cov-fail-under=80      # ML tests
uv run --directory backend pytest tests/test_foo.py -k "test_name"           # Single test (prefer while iterating)
uv run --directory backend ruff check app ml tests                           # Lint
uv run --directory backend ruff format app ml tests                          # Format (CI runs --check)
uv run --directory backend mypy                                              # Type-check app/ and ml/ (tests excluded)
```

### Frontend

```bash
pnpm --dir frontend install                  # Install deps
pnpm --dir frontend dev                      # Dev server (http://localhost:3000)
pnpm --dir frontend build                    # Production build (also type-checks)
pnpm --dir frontend lint                     # ESLint
pnpm --dir frontend generate:api-types       # Regenerate src/types/api.d.ts from OpenAPI (backend must be running)
```

## Architecture

### Request flow

The pipeline is slow (3 sequential Ollama calls, Europe PMC lookups, BERT), so it runs **out of the request** in an arq worker. The web process only enqueues; the client polls the detail endpoint until the row leaves `pending`.

```text
Web process (FastAPI)                          Worker process (arq, app/worker.py)
─────────────────────                          ───────────────────────────────────
User (browser)
  → Clerk JWT auth
  → POST /analysis
  → INSERT 'pending' row (returns analysis_id)
  → enqueue run_analysis on Redis ─────────────→ run_analysis(analysis_id, …)
  → Return {status: "pending", analysis_id}        → URL text extraction if needed (BeautifulSoup)
                                                   → LangGraph pipeline:
GET /analysis/{id}  (polled by frontend            ·  Extractor     (llama3)         → claims
  every 2s while status == "pending")              ·  Translator    (translategemma) → EN, batched
  → returns status + (when done) label/            ·  Investigator  (Europe PMC)     → sources + evidence_coverage
     confidence/explanation/claims/                ·  Health Expert (llama3.2)       → label (BioBERT) + explanation;
     sources, or error_code when                   → Confidence attenuated by evidence_coverage
     status == "failed"                            → UPDATE row → 'done' (results) or 'failed' (error_code)
```

### Backend (`backend/`)

- **`app/main.py`** — Web-process lifespan: DB pool + arq Redis pool (enqueue only; the graph lives in the worker).
- **`app/worker.py`** — arq worker: builds the graph at startup, runs `run_analysis`, maps pipeline errors to a `failed` row + stable `error_code`.
- **`app/api/routes/`** — `analysis.py`, `dashboard.py`, `history.py`; each declares `responses=` for the OpenAPI error contract.
- **`app/api/dependencies/`** — Clerk JWT validation, rate limiting.
- **`app/agents/`** — LangGraph orchestration (`main.py`) + agent nodes; Europe PMC retrieval in `app/utils/europepmc.py`; evidence-attenuated confidence in `app/core/credibility.py`; typed pipeline errors and `ainvoke_graph` in `errors.py`.
- **`app/prompts/prompts.yaml`** — All LLM system prompts (loaded via `app/prompts/agents.py`). Prompts live here, never inline in Python.
- **`app/db/`** — Raw psycopg3 async SQL: `pool.py` (shared `AsyncConnectionPool` + `DatabaseError`), `history.py` (CRUD + pagination; claims/sources as JSONB), `dashboard.py` (metrics).
- **`app/core/config.py`** — Centralised `Settings` (pydantic-settings), cached `get_settings()`, `validate_runtime()` startup check.
- **`app/schemas/errors.py`** — `ErrorCode` enum + wire-contract models. **`app/core/errors.py`** — Spanish messages + `make_error_detail()`.
- **`ml/`** — Standalone BioBERT training and evaluation; separate test suite.

### Frontend (`frontend/src/`)

- **`app/`** — App Router pages: `/`, `/analisis`, `/dashboard`, `/historial`, static legal pages.
- **`lib/apiClient.ts`** — Authenticated fetch wrapper (Clerk JWT); throws `ApiError` with `{code, message, status}` on non-2xx.
- **`hooks/useApiQuery.ts`** — Generic data-fetching hook over `apiClient`.
- **`types/api.d.ts`** — Generated from OpenAPI; never edit by hand.

## Conventions

- **Centralised config** — read env only through `Settings` via `get_settings()`; never `os.getenv`/`load_dotenv` in feature code — add a field to `Settings` instead. Required vars are validated once at startup (`validate_runtime()`); missing values surface as `/healthz` 503, not per-request 500s. `Settings` construction is side-effect-free. Frontend reads env only through `clientEnv` (`src/env/client.ts`) or `serverEnv` (`src/env/server.ts`); both throw at module load when production vars are missing. See `.env.example` in each package.
- **Structured error contract** — every route raises `HTTPException(detail=make_error_detail(ErrorCode.X))` and declares its 4xx/5xx codes via `responses=`. To add an error: extend `ErrorCode` in `app/schemas/errors.py`, add the Spanish message in `app/core/errors.py`, declare it in the route's `responses=`, then regenerate API types.
- **Typed exception dispatch** — transport failures are translated to typed errors (e.g. `OllamaConnectionError`) via `invoke_graph` in `app/agents/errors.py`. Branch on exception type, never on `str(exc)`.
- **Async end-to-end** — routes, dependencies, and DB functions are `async def`; invoke the graph via `ainvoke_graph`. Agent nodes stay sync `def` (LangGraph threadpool). `extract_text_from_url` stays sync, called via `await asyncio.to_thread(...)`.
- **No ORM** — raw psycopg3 async SQL under `app/db/`, served by the module-level pool opened/closed in the lifespan.
- **Generated API types** — after any backend schema change, run `pnpm --dir frontend generate:api-types` (backend running); the frontend won't type-check against a stale contract.
- **SVG icons** — icon components live in `frontend/src/assets/` as default exports (`SVGProps<SVGSVGElement>` spread, `stroke="currentColor"`); import and size them via `className`. Don't define inline icon functions in feature files; add or reuse an asset instead.
- **Comments & docstrings** — every code comment is **exactly one line**; never multi-line, multi-sentence, or stacked `#`/`//` blocks. Class/method docstrings are a single plain sentence. Architectural rationale belongs here or in the PR, not in code.
- **Per-file `E402` ignore** — `app/agents/main.py`, `app/agents/health_expert.py`, and `ml/evaluation/evaluate_factcheck.py` ignore `E402` for intentional `sys.path` manipulation. Preserve it.

## Security

- Never hardcode credentials, keys, or URLs — read them from environment via the config layer.
- Test fixtures must use dummy/mock values, never real keys.
