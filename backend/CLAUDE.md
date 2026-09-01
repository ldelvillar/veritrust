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

- **`app/agents/`** — LangGraph orchestration (`main.py`) + agent nodes; evidence retrieval in `app/utils/` (`europepmc.py`, `pubmed.py`, `openfda.py`, `cima.py`; CIMA only for drug claims) filtered by an LLM relevance judge (`agents/relevance.py`); evidence-attenuated confidence in `app/core/credibility.py`; typed pipeline errors and `ainvoke_graph` in `errors.py`.
- **`app/prompts/prompts.yaml`** — All LLM system prompts (loaded via `app/prompts/agents.py`). Prompts live here, never inline in Python.
- **`ml/`** — Standalone pipeline evaluation harness; separate test suite. Imports `app/`, never the reverse.

## Conventions

- **Structured error contract** — every route raises `HTTPException(detail=make_error_detail(ErrorCode.X))` and declares its 4xx/5xx codes via `responses=`. To add an error: extend `ErrorCode` in `app/schemas/errors.py`, add the Spanish message in `app/core/errors.py`, declare it in the route's `responses=`, then regenerate API types.
- **Typed exception dispatch** — transport failures are translated to typed errors (e.g. `OllamaConnectionError`) via `invoke_graph` in `app/agents/errors.py`. Branch on exception type, never on `str(exc)`.
- **Async end-to-end** — routes, dependencies, and DB functions are `async def`; invoke the graph via `ainvoke_graph`. Agent nodes stay sync `def` (LangGraph threadpool). `extract_text_from_url` stays sync, called via `await asyncio.to_thread(...)`.
- **No ORM** — raw psycopg3 async SQL under `app/db/`, served by the module-level pool opened/closed in the lifespan.
- **Per-file `E402` ignore** — `app/agents/main.py` and `app/agents/health_expert.py` ignore `E402` for intentional `sys.path` manipulation. Preserve it.
