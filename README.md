# VeriTrust

AI-powered medical misinformation detector. Users submit text or a URL; a LangGraph multi-agent pipeline (Extractor → Translator → Investigator → Health Expert) backed by Llama (via Ollama) and a fine-tuned BioBERT classifier returns a verdict (`verdadera`/`falsa`), confidence score, supporting biomedical sources, and medical explanation. The Investigator cross-checks each claim against Europe PMC literature, and the verdict's confidence is attenuated when no supporting evidence is found. Results are persisted in PostgreSQL and shown in a Next.js dashboard.

## Stack

- **Backend** — FastAPI (web) + arq worker, LangGraph, Ollama, Transformers (BioBERT), Europe PMC evidence retrieval, psycopg3
- **Frontend** — Next.js 16 (App Router), React 19, Clerk, SWR, Tailwind v4
- **Data** — PostgreSQL, Redis (arq job queue)
- **ML** — BioBERT fine-tuned on PUBHEALTH

Analysis is asynchronous: `POST /analysis` returns immediately with a `pending`
id, an arq worker runs the pipeline, and the frontend polls `GET /analysis/{id}`
until the verdict is ready.

## Repository layout

```
backend/
  app/        FastAPI service (routes, agents, db, schemas)
  ml/         BioBERT training and evaluation
  tests/      App test suite
frontend/
  src/        Next.js App Router
```

## Prerequisites

- Python 3.11+ and [`uv`](https://docs.astral.sh/uv/)
- Node.js 22+ and `pnpm` 9+
- [Ollama](https://ollama.com/) running locally on `:11434` with the models `llama3`, `llama3.2`, and `translategemma` pulled
- A PostgreSQL database (the Docker Compose stack provides one)
- A Redis instance on `:6379` (job queue for the analysis worker)
- A [Clerk](https://clerk.com/) application for auth

## Onboarding

### Quick start — Docker (recommended)

```bash
cp .env.example .env             # fill in Clerk values
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
docker compose exec ollama ollama pull llama3
docker compose exec ollama ollama pull llama3.2
docker compose exec ollama ollama pull translategemma
```

Frontend at `http://localhost:3000`, backend at `http://localhost:8000`. The BioBERT weights under `backend/models/bert_classifier/` are mounted into the backend container read-only.

### Local development (without Docker)

#### 1. Configure environment

Copy the example env files and fill in real values:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Backend needs at minimum: `DATABASE_URL`, `REDIS_URL`, `CLERK_JWKS_URL`, `CLERK_AUDIENCE`, `CORS_ALLOWED_ORIGINS`, `OLLAMA_BASE_URL`.
Frontend needs: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`.

#### 2. Backend

```bash
cd backend
uv sync --frozen                      # install serving + api deps
uv sync --frozen --extra ml           # add the ML stack (only if training/evaluating)
uv run python -m app.main             # web API at http://localhost:8000
uv run python -m app.worker           # analysis worker (separate terminal; needs Redis + Ollama)
```

#### 3. Frontend

```bash
cd frontend
pnpm install
pnpm dev                        # http://localhost:3000
```

#### 4. Pull the Ollama models

```bash
ollama pull llama3
ollama pull llama3.2
ollama pull translategemma
```

#### 5. BioBERT model

The detector loads weights from `backend/models/bert_classifier/`. Either copy a pre-trained checkpoint there or run the training pipeline:

```bash
cd backend
uv run python -m ml.training.train
```

## Common commands

### Backend (from `backend/`)

```bash
uv run pytest tests --cov=app --cov-fail-under=80     # app tests
uv run pytest ml/tests --cov=ml --cov-fail-under=80   # ML tests
uv run ruff check app ml tests                        # lint
uv run ruff format app ml tests                       # format
uv run mypy                                           # type-check
```

### Frontend (from `frontend/`)

```bash
pnpm lint
pnpm test
pnpm build
pnpm generate:api-types         # regenerate src/types/api.d.ts (backend must be running)
```

## Notes

- After changing a backend Pydantic schema, regenerate the frontend types with `pnpm generate:api-types`. Never edit `frontend/src/types/api.d.ts` by hand.
- The database schema lives in `backend/db/init.sql`, applied once to a fresh database (mounted into the Postgres container's `docker-entrypoint-initdb.d`). There is no migration framework yet — pre-launch, recreate the volume (`docker compose down -v && docker compose up`) to pick up schema changes.

## License

MIT — see [LICENSE](LICENSE).
