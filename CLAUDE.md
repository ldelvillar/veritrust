# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VeriTrust is an AI-powered medical misinformation detection system. Users submit medical text or URLs; a LangGraph multi-agent pipeline (Extractor → Translator → Health Expert) powered by Llama (via Ollama) analyzes them and returns a label (`verdadera`/`falsa`), confidence score, and explanation. Results are persisted in PostgreSQL and surfaced via a Next.js dashboard.

## Commands

### Backend (run from `backend/`)

```bash
uv sync --frozen                                             # Install serving/API deps + app tests (excludes the ml stack)
uv sync --frozen --extra ml                                  # Add the ml stack (pandas, pyarrow, scikit-learn, accelerate, matplotlib, seaborn) — needed for ml/ and its tests
uv run python -m app.main                                    # Start API server (http://localhost:8000)
uv run python -m app.worker                                  # Start the analysis worker (needs Redis + Ollama)
uv run pytest tests --cov=app --cov-fail-under=80            # Run app tests (80% coverage required)
uv run pytest ml/tests --cov=ml --cov-fail-under=80          # Run ML tests (80% coverage required)
uv run pytest tests/test_foo.py -k "test_name"               # Run a single test
uv run ruff check app ml tests                               # Lint
uv run ruff format app ml tests                              # Format (also: --check in CI)
uv run mypy                                                  # Type-check app/ and ml/ (config in pyproject.toml)
```

### Frontend (run from `frontend/`)

```bash
pnpm install                    # Install dependencies (pnpm v9)
pnpm dev                        # Dev server at http://localhost:3000
pnpm build                      # Production build (also type-checks)
pnpm lint                       # ESLint
pnpm generate:api-types         # Regenerate src/types/api.d.ts from OpenAPI (backend must be running)
```

## Architecture

### Request Flow

The multi-agent pipeline is slow (3 sequential Ollama calls + BERT), so it runs
**out of the request** in an arq worker. The web process only enqueues; the
client polls the detail endpoint until the row leaves `pending`.

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
GET /analysis/{id}  (polled by frontend            ·  Extractor   (llama3)        → claims
  every 2s while status == "pending")              ·  Translator  (translategemma) → EN, batched
  → returns status + (when done) label/            ·  Health Expert (llama3.2)     → label (BioBERT) + explanation
     confidence/explanation, or error_code         → UPDATE row → 'done' (results) or 'failed' (error_code)
     when status == "failed"
```

### Backend (`backend/`)

- **`app/main.py`** — Web-process lifespan: opens the DB pool and the arq Redis pool (for enqueuing). The graph lives in the worker, not here.
- **`app/worker.py`** — arq worker (`python -m app.worker`): builds the graph at startup and runs `run_analysis`, translating pipeline errors into a `failed` row + stable `error_code`.
- **`app/api/routes/`** — `analysis.py` (POST enqueues a pending row; GET returns status/results), `dashboard.py`, `history.py` (each declares `responses=` for OpenAPI error contract)
- **`app/api/dependencies/`** — Clerk JWT validation (`get_current_user.py`), rate limiting (`check_rate_limit.py`)
- **`app/agents/`** — LangGraph orchestration in `main.py`; individual agents in `extractor.py`, `translator.py`, `health_expert.py`; typed pipeline errors and `ainvoke_graph` helper in `errors.py`
- **`app/prompts/prompts.yaml`** — All LLM system prompts (loaded via `app/prompts/agents.py`)
- **`app/db/`** — Raw psycopg3 async queries; no ORM. Split by concern: `pool.py` (shared `AsyncConnectionPool` + `DatabaseError`), `history.py` (analysis CRUD + pagination), `dashboard.py` (aggregated metrics)
- **`app/core/config.py`** — Centralised `Settings` (pydantic-settings) for all service config (DB, Clerk, CORS); cached `get_settings()` accessor and `validate_runtime()` startup check
- **`app/schemas/errors.py`** — `ErrorCode` enum + `ErrorDetail`/`ErrorResponse` Pydantic models (the wire contract; exported to frontend via OpenAPI)
- **`app/core/errors.py`** — Spanish messages keyed by `ErrorCode` + `make_error_detail()` factory used by every route's `HTTPException`
- **`ml/`** — Standalone BioBERT training and evaluation; separate test suite

### Frontend (`frontend/src/`)

- **`app/`** — Next.js App Router pages: `/`, `/analisis`, `/dashboard`, `/historial`, and static legal pages
- **`lib/apiClient.ts`** — Authenticated fetch wrapper that attaches Clerk JWT; throws `ApiError` carrying `{code, message, status}` on non-2xx responses
- **`hooks/useApiQuery.ts`** — Generic data-fetching hook wrapping `apiClient`; used by dashboard/history pages
- **`types/api.d.ts`** — Generated from OpenAPI schema; do not edit by hand

## Key Conventions

- **Centralised config** — all env-derived service config (DB, Clerk, CORS) flows through the `Settings` model in `app/core/config.py`, accessed via the cached `get_settings()`. Don't read env vars (`os.getenv`/`load_dotenv`) ad hoc in feature code; add a field to `Settings` instead. Required vars are validated once at startup via `get_settings().validate_runtime()` in the lifespan (a missing/invalid value is a startup failure surfaced via `/healthz` 503, not a per-request 500). `Settings` construction is side-effect-free, so importing modules never requires a populated environment.
- **Comments & docstrings** — keep them short. Comments explain *what*, in one line; don't embed architectural decisions, business-logic rationale, or trade-off discussion in code (those belong here or in the PR). Class and method docstrings are a single plain sentence describing what it does — no multi-paragraph explanations.
- **Agent prompts** live in `backend/app/prompts/prompts.yaml`, not in Python code.
- **TypeScript API types** are generated from the backend's OpenAPI spec — run `pnpm generate:api-types` after changing schemas.
- **No ORM** — database access uses raw psycopg3 async SQL under `app/db/` (`history.py`, `dashboard.py`), served by a module-level `AsyncConnectionPool` in `app/db/pool.py`, opened in lifespan startup and closed on shutdown.
- **Async end-to-end** — all routes, dependencies, and DB functions are `async def`. The LangGraph pipeline is invoked via `await graph.ainvoke(...)` (helper `ainvoke_graph` in `app/agents/errors.py`); individual agent nodes stay sync `def` since LangGraph dispatches them to its own threadpool. URL extraction (`extract_text_from_url`) stays sync and is called from the route via `await asyncio.to_thread(...)`.
- **80% test coverage** is enforced in CI for both `app` and `ml` modules.
- **pnpm** (not npm/yarn) for frontend; **uv** (not pip) for backend.
- **Structured error contract** — every route raises `HTTPException(detail=make_error_detail(ErrorCode.X))` and declares its possible 4xx/5xx codes via `responses=`. To add a new error: extend `ErrorCode` in `app/schemas/errors.py`, add its Spanish message in `app/core/errors.py`, declare it in the route's `responses=` dict, then regenerate frontend types.
- **Typed exception dispatch** — `analyze_news` translates transport-level failures to typed errors (`OllamaConnectionError`) via `invoke_graph` in `app/agents/errors.py`; the route branches on type, never on `str(exc)`.
- **Lint/format/type-check** — Ruff (lint + Black-compatible formatter) and mypy are configured in `backend/pyproject.toml` and enforced by CI on both `backend_app` and `backend_ml` jobs. Tests are excluded from mypy. Three files (`app/agents/main.py`, `app/agents/health_expert.py`, `ml/evaluation/evaluate_factcheck.py`) carry a per-file `E402` ignore for the intentional `sys.path` manipulation that lets them run as scripts.

## Before Making Changes

- Run the relevant test suite before and after changes
- Run `uv run ruff check app ml tests`, `uv run ruff format --check app ml tests`, and `uv run mypy` before pushing — CI enforces all three
- Never edit `frontend/src/types/api.d.ts` by hand (generated file)
- Run `pnpm generate:api-types` after any schema change

## Security

- Never hardcode credentials, keys, or URLs — always read from environment variables
- Test fixtures must use dummy/mock values, never real keys

## Environment Variables

See `.env.example` in each package for required variables.

- **Backend** — read env only through the `Settings` model in `app/core/config.py` (cached via `get_settings()`). Required vars are checked once at startup by `validate_runtime()` in the lifespan; missing values surface as `/healthz` 503.
- **Frontend** — read env only through `clientEnv` (`src/env/client.ts`, `NEXT_PUBLIC_*`) or `serverEnv` (`src/env/server.ts`, `'server-only'`). Both throw at module load when required vars are missing in production; the root layout imports both so the check runs during `next build`.
