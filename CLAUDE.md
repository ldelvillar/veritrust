# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VeriTrust is an AI-powered medical misinformation detection system. Users submit medical text or URLs; a LangGraph multi-agent pipeline (Extractor → Translator → Health Expert) powered by Llama (via Ollama) analyzes them and returns a label (`verdadera`/`falsa`), confidence score, and explanation. Results are persisted in PostgreSQL and surfaced via a Next.js dashboard.

## Commands

### Backend (run from `backend/`)

```bash
uv sync --frozen                                             # Install dependencies
uv run python -m app.main                                    # Start API server (http://localhost:8000)
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

```text
User (browser)
  → Clerk JWT auth
  → POST /analysis (FastAPI)
  → URL text extraction if needed (BeautifulSoup)
  → LangGraph pipeline:
      Extractor agent  (llama3 via Ollama)        → extracts medical claims (single structured-output call)
      Translator agent (translategemma via Ollama) → translates ALL claims in a single batched call
      Health Expert    (llama3.2 via Ollama)       → labels (via BioBERT tool) + explains
  → Save to PostgreSQL (Supabase)
  → Return {analysis_id, label, confidence, explanation}
```

### Backend (`backend/`)

- **`app/main.py`** — FastAPI lifespan management (starts Ollama, initialises DB)
- **`app/api/routes/`** — `analysis.py`, `dashboard.py`, `history.py` (each declares `responses=` for OpenAPI error contract)
- **`app/api/dependencies/`** — Clerk JWT validation (`get_current_user.py`), rate limiting (`check_rate_limit.py`)
- **`app/agents/`** — LangGraph orchestration in `main.py`; individual agents in `extractor.py`, `translator.py`, `health_expert.py`; typed pipeline errors and `invoke_graph` helper in `errors.py`
- **`app/prompts/prompts.yaml`** — All LLM system prompts (loaded via `app/prompts/agents.py`)
- **`app/db/main.py`** — Raw psycopg2 queries; no ORM
- **`app/schemas/errors.py`** — `ErrorCode` enum + `ErrorDetail`/`ErrorResponse` Pydantic models (the wire contract; exported to frontend via OpenAPI)
- **`app/core/errors.py`** — Spanish messages keyed by `ErrorCode` + `make_error_detail()` factory used by every route's `HTTPException`
- **`ml/`** — Standalone BioBERT training and evaluation; separate test suite

### Frontend (`frontend/src/`)

- **`app/`** — Next.js App Router pages: `/`, `/analisis`, `/dashboard`, `/historial`, and static legal pages
- **`lib/apiClient.ts`** — Authenticated fetch wrapper that attaches Clerk JWT; throws `ApiError` carrying `{code, message, status}` on non-2xx responses
- **`hooks/useApiQuery.ts`** — Generic data-fetching hook wrapping `apiClient`; used by dashboard/history pages
- **`types/api.d.ts`** — Generated from OpenAPI schema; do not edit by hand

## Key Conventions

- **Agent prompts** live in `backend/app/prompts/prompts.yaml`, not in Python code.
- **TypeScript API types** are generated from the backend's OpenAPI spec — run `pnpm generate:api-types` after changing schemas.
- **No ORM** — database access uses raw psycopg3 async SQL in `app/db/main.py`, served by a module-level `AsyncConnectionPool` opened in lifespan startup and closed on shutdown.
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
