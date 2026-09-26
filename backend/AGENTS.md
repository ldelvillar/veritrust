# Backend

Python (FastAPI + arq worker). Run every command from the **repo root** — never `cd` into this directory.

## Commands

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

## Layout notes

- **`app/core/`** — Cross-cutting logic the routes call: history CSV serialisation including the formula-injection guard (`history_export.py`). Routes fetch and respond; formatting lives here.
- **Analysis lifecycle** (`app/core/analysis_lifecycle.py`) — the only writer of an analysis's `status` and `stage` (ADR-0001, enforced by `tests/unit/test_analysis_lifecycle_sole_writer.py`). `AnalysisIntake` opens analyses for the routes and MCP (submit, file submit, Retry, Reanalyze); `AnalysisRunner` runs, closes and reaps them for the worker, whose own job is `analyse()`: content in, `Completion` out, or `AnalysisFailure(code)`. Its SQL is `app/db/analysis_transitions.py` (import it nowhere else) and its arq adapter is `ArqAnalysisQueue` in `analysis_jobs.py`, the only place that knows the job name and payload — never call `enqueue_job("run_analysis", …)` or write `status`/`stage` elsewhere. Tests run against real Postgres in `tests/db/test_analysis_lifecycle.py`, with the doubles in `tests/support/lifecycle.py`.
- **Verdict** (`app/core/verdict.py`) — the only place a Verdict is decided or derived. `decide(claims, sources, EvidenceSearch)` turns the Investigator's stances and search counts into a typed `Verdict` (kind, attenuated confidence, raw falsehood, Evidence coverage — `None` on an Evidence outage — and one verdict per claim); the Health Expert calls it and the LLM only explains the result. Stored rows are read back through `kind_of`, `credibility_of`, `confidence_level_of` and `CREDIBILITY_SQL`, which `tests/db/test_credibility_sql.py` keeps in step with `credibility_of`. Never re-derive a verdict, band or credibility anywhere else — the frontend shows the `verdict` it receives. Tables of cases live in `tests/unit/test_verdict.py`.
- **History query** (`app/db/history_query.py`) — the only place a History query becomes SQL. `HistoryQuery` (`app/schemas/history.py`: search, content type, verdict, status, date range, sort) is validated once, where `/history` and `/history/export` take it via `Depends()`, and trusted downstream — never re-clamp its values. `search_history` returns the page, its total and the verdict Facet (the query without its own filter, so the total is one of its cells); `export_history` returns the same query's done analyses. A new filter is one field on `HistoryQuery` plus one predicate in `_where`. Tests run against real Postgres in `tests/db/test_history_query.py`.
- **`app/prompts/prompts.yaml`** — All LLM prompt text: system prompts plus the health expert's user-message templates, interpolated with `str.format` (loaded via `app/prompts/agents.py`). Prompts live here, never inline in Python.
- **`ml/`** — Standalone pipeline evaluation harness; separate test suite. Imports `app/`, never the reverse.

## Conventions

- **Structured error contract** — every route raises `HTTPException(detail=make_error_detail(ErrorCode.X))` and declares its 4xx/5xx codes via `responses=`. To add an error: extend `ErrorCode` in `app/schemas/errors.py`, add the Spanish message in `app/core/errors.py`, declare it in the route's `responses=`, then regenerate API types. Request validation (422) is the exception: the handler in `app/main.py` returns it as `VALIDATION` and `app/api/router.py` documents it once per router, so never declare 422 per route. Lifecycle refusals are the other exception: the intake raises `AnalysisRefused(code)` and one handler in `app/main.py` answers with the status from `REFUSAL_HTTP_STATUS` (`app/api/dependencies/analysis_intake.py`), which a test keeps in step with `REFUSAL_CODES`.
- **Typed exception dispatch** — transport failures are translated to typed errors (e.g. `OllamaConnectionError`) via `invoke_graph` in `app/agents/errors.py`. Branch on exception type, never on `str(exc)`.
- **Async end-to-end, blocking I/O off the loop** — routes, dependencies, and DB functions are `async def`; invoke the graph via `ainvoke_graph`. Code that does blocking I/O stays sync and runs off the event loop instead — as a sync `def` dependency in FastAPI's threadpool (`get_current_user`: the JWKS fetch is blocking HTTP), via `await asyncio.to_thread(...)` (`extract_text_from_url`, the MCP token verifier), or as a sync agent node in LangGraph's threadpool. Never wrap blocking code in `async def`.
- **No ORM** — raw psycopg3 async SQL under `app/db/`, served by the module-level pool opened/closed in the lifespan.

## MCP server

The web process also serves a remote MCP server (`backend/app/mcp/`, official `mcp` SDK, Streamable HTTP) at `/mcp`, so AI clients can use VeriTrust on a signed-in user's behalf:

- **`verify_claim`** (text or URL) — opens an `origin='mcp'` analysis through the same `AnalysisIntake` as `POST /analysis`, then polls the row until it leaves `pending` or `MCP_TOOL_WAIT_SECONDS` runs out; **`get_verification`** resumes a long-running one.
- **`search_evidence`** — enqueues `run_evidence_search`, which runs Extractor → Translator → evidence search + relevance judge (`create_evidence_graph`) with no verdict. It goes through the worker, never the web process, so Ollama load stays serialized. The arq result is kept for an hour and bound to the caller in Redis, so **`get_evidence`** resumes a search that outlasted the wait.

Auth is Clerk OAuth: clients discover Clerk from `/.well-known/oauth-protected-resource/mcp`, and `ClerkOAuthTokenVerifier` checks the JWT access token (same JWKS, issuer, `client_id` present). The server is built in the lifespan after `validate_runtime()` and reached through two exact routes, not a catch-all mount. Tool calls share the per-user rate limit with the web API.
