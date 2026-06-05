# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VeriTrust is an AI-powered medical misinformation detection system. Users submit medical text or URLs; a LangGraph multi-agent pipeline (Extractor → Translator → Investigator → Health Expert) powered by Llama (via Ollama) and a fine-tuned BioBERT classifier analyzes them and returns a label (`verdadera`/`falsa`), confidence score, per-claim verdicts, supporting sources, and explanation. The Investigator retrieves biomedical literature from Europe PMC, and the verdict's confidence is attenuated when that evidence is missing. Results are persisted in PostgreSQL and surfaced via a Next.js dashboard.

`backend/` is Python (FastAPI + arq worker), `frontend/` is Next.js. The two communicate over a typed contract: the frontend's `types/api.d.ts` is generated from the backend's OpenAPI spec.

## Always verify before declaring done

Run the checks below and fix failures (root cause, not suppression) before treating any change as complete. CI enforces all of them.

- **Backend** — `uv run --directory backend ruff check app ml tests`, `uv run --directory backend ruff format --check app ml tests`, `uv run --directory backend mypy`, and the relevant test suite at ≥80% coverage.
- **Frontend** — `pnpm --dir frontend lint` and `pnpm --dir frontend build` (build also type-checks).
- After any backend schema change, run `pnpm --dir frontend generate:api-types` (backend must be running) — the frontend won't type-check against a stale contract.

## Shell command conventions

Run every command from the **repo root**. Never `cd` into a subdirectory, and never use `Push-Location` or `pnpm --dir backend`.

- Backend Python tools: `uv run --directory backend <tool> <args>`
- Frontend scripts: `pnpm --dir frontend <script>`
- Both at once: chain with `&&` in a single command, still from root

## Commands

### Backend

```bash
uv sync --directory backend --frozen                                         # Serving/API deps + app tests (excludes ml stack)
uv sync --directory backend --frozen --extra ml                              # Add ml stack (pandas, pyarrow, scikit-learn, accelerate, matplotlib, seaborn) for ml/ and its tests
uv run --directory backend python -m app.main                                # API server (http://localhost:8000)
uv run --directory backend python -m app.worker                              # Analysis worker (needs Redis + Ollama)
uv run --directory backend pytest tests --cov=app --cov-fail-under=80        # App tests (80% coverage required)
uv run --directory backend pytest ml/tests --cov=ml --cov-fail-under=80      # ML tests (80% coverage required)
uv run --directory backend pytest tests/test_foo.py -k "test_name"           # Single test (prefer this over the full suite while iterating)
uv run --directory backend ruff check app ml tests                           # Lint
uv run --directory backend ruff format app ml tests                          # Format (CI runs --check)
uv run --directory backend mypy                                              # Type-check app/ and ml/ (tests excluded; config in pyproject.toml)
```

### Frontend

```bash
pnpm --dir frontend install                  # Install deps (pnpm v9)
pnpm --dir frontend dev                      # Dev server (http://localhost:3000)
pnpm --dir frontend build                    # Production build (also type-checks)
pnpm --dir frontend lint                     # ESLint
pnpm --dir frontend generate:api-types       # Regenerate src/types/api.d.ts from OpenAPI (backend must be running)
```

Use **uv** (not pip) for backend and **pnpm v9** (not npm/yarn) for frontend.

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

- **`app/main.py`** — Web-process lifespan: opens the DB pool and the arq Redis pool (for enqueuing). The graph lives in the worker, not here.
- **`app/worker.py`** — arq worker (`python -m app.worker`): builds the graph at startup, runs `run_analysis`, translates pipeline errors into a `failed` row + stable `error_code`.
- **`app/api/routes/`** — `analysis.py` (POST enqueues a pending row; GET returns status/results), `dashboard.py`, `history.py`. Each declares `responses=` for the OpenAPI error contract.
- **`app/api/dependencies/`** — Clerk JWT validation (`get_current_user.py`), rate limiting (`check_rate_limit.py`).
- **`app/agents/`** — LangGraph orchestration in `main.py`; agents in `extractor.py`, `translator.py`, `investigator.py` (Europe PMC retrieval via `app/utils/europepmc.py`), `health_expert.py` (BioBERT per-claim verdict + evidence-attenuated confidence via `app/core/credibility.py`). Typed pipeline errors and the `ainvoke_graph` helper live in `errors.py`.
- **`app/prompts/prompts.yaml`** — All LLM system prompts (loaded via `app/prompts/agents.py`). Prompts live here, never inline in Python.
- **`app/db/`** — Raw psycopg3 async SQL; no ORM. `pool.py` (shared `AsyncConnectionPool` + `DatabaseError`), `history.py` (analysis CRUD + pagination; per-claim verdicts and sources persisted as JSONB `claims`/`sources` columns), `dashboard.py` (aggregated metrics).
- **`app/core/config.py`** — Centralised `Settings` (pydantic-settings) for all service config; cached `get_settings()` accessor and `validate_runtime()` startup check.
- **`app/schemas/errors.py`** — `ErrorCode` enum + `ErrorDetail`/`ErrorResponse` Pydantic models (the wire contract; exported to frontend via OpenAPI).
- **`app/core/errors.py`** — Spanish messages keyed by `ErrorCode` + `make_error_detail()` factory used by every route's `HTTPException`.
- **`ml/`** — Standalone BioBERT training and evaluation; separate test suite.

### Frontend (`frontend/src/`)

- **`app/`** — Next.js App Router pages: `/`, `/analisis`, `/dashboard`, `/historial`, and static legal pages.
- **`lib/apiClient.ts`** — Authenticated fetch wrapper that attaches the Clerk JWT; throws `ApiError` carrying `{code, message, status}` on non-2xx.
- **`hooks/useApiQuery.ts`** — Generic data-fetching hook wrapping `apiClient`; used by dashboard/history pages.
- **`types/api.d.ts`** — Generated from the OpenAPI schema; never edit by hand.

## Conventions

- **Centralised config** — read env only through the `Settings` model in `app/core/config.py` via the cached `get_settings()`. Don't use `os.getenv`/`load_dotenv` ad hoc in feature code; add a field to `Settings` instead. Required vars are validated once at startup by `validate_runtime()` in the lifespan; a missing/invalid value surfaces as `/healthz` 503, not a per-request 500. `Settings` construction is side-effect-free, so importing modules never requires a populated environment. Frontend reads env only through `clientEnv` (`src/env/client.ts`, `NEXT_PUBLIC_*`) or `serverEnv` (`src/env/server.ts`, `'server-only'`); both throw at module load when production vars are missing. See `.env.example` in each package for required vars.
- **Structured error contract** — every route raises `HTTPException(detail=make_error_detail(ErrorCode.X))` and declares its 4xx/5xx codes via `responses=`. To add an error: extend `ErrorCode` in `app/schemas/errors.py`, add the Spanish message in `app/core/errors.py`, declare it in the route's `responses=`, then run `generate:api-types`.
- **Typed exception dispatch** — `analyze_news` translates transport-level failures to typed errors (e.g. `OllamaConnectionError`) via `invoke_graph` in `app/agents/errors.py`. Branch on exception type, never on `str(exc)`.
- **Async end-to-end** — all routes, dependencies, and DB functions are `async def`. Invoke the graph via `await graph.ainvoke(...)` (helper `ainvoke_graph` in `app/agents/errors.py`). Individual agent nodes stay sync `def` (LangGraph dispatches them to its own threadpool). `extract_text_from_url` stays sync and is called via `await asyncio.to_thread(...)`.
- **No ORM** — database access is raw psycopg3 async SQL under `app/db/`, served by the module-level `AsyncConnectionPool` in `app/db/pool.py` (opened/closed in the lifespan).
- **TypeScript API types** are generated from the backend's OpenAPI spec — run `generate:api-types` after changing schemas, never hand-edit `frontend/src/types/api.d.ts`.
- **Comments & docstrings** — keep them short. Comments explain _what_ in one line. Class/method docstrings are a single plain sentence. Don't put architectural rationale or trade-off discussion in code; it belongs here or in the PR.
- **Per-file `E402` ignore** — `app/agents/main.py`, `app/agents/health_expert.py`, and `ml/evaluation/evaluate_factcheck.py` carry an `E402` ignore for the intentional `sys.path` manipulation that lets them run as scripts. Preserve it.

## Security

- Never hardcode credentials, keys, or URLs — read them from environment via the config layer above.
- Test fixtures must use dummy/mock values, never real keys.
