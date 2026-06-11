# Commit.md

Analyze the staged changes and write a conventional commit message for the VeriTrust project.

## Instructions

1. Run `git diff --staged` to review what's staged.
2. If nothing is staged, run `git diff HEAD` to check unstaged changes, then tell the user to stage what they want committed and stop.
3. Identify the **primary intent** of the changes — don't describe every file touched, describe what the change accomplishes.
4. Write a commit message following the format below.
5. Run `git commit -m "<message>"` — do not ask for confirmation unless the changes are ambiguous or span multiple unrelated concerns (in which case, flag this and suggest splitting).

## Commit Message Format

For a simple, short, or single-concern change, write a **title only** — no body, no bullets:

```text
<type>(<scope>): <short description>
```

Only add a body when the title genuinely can't carry the substance (multiple
non-obvious changes, or context the diff won't reveal):

```text
<type>(<scope>): <short description>

- <bullet 1>
- <bullet 2>
- <bullet 3>
```

When you do add a body, use **short bullet points** (≤3, each a single line).
Do **not** write prose paragraphs explaining motivation at length; the title
names the intent, the bullets name what changed. When in doubt, prefer a
title-only commit.

**Types** (full Conventional Commits / Angular set):

- `feat` — new feature or behaviour
- `fix` — bug fix
- `perf` — performance improvement with no behaviour change
- `refactor` — restructuring with no behaviour change
- `test` — adding or updating tests
- `build` — build system or external dependencies (Dockerfiles, `uv.lock`, `pnpm-lock.yaml`)
- `ci` — CI configuration and workflows (`.github/workflows/`)
- `chore` — tooling or maintenance that doesn't fit another type
- `style` — formatting only (Ruff format, Prettier)
- `docs` — documentation only
- `revert` — reverts a previous commit

**Scopes for this project:**

- `auth` — Clerk JWT validation (`get_current_user.py`), rate limiting (`check_rate_limit.py`)
- `agents` — LangGraph pipeline and the Extractor / Translator / Investigator / Health Expert nodes
- `prompts` — agent system prompts in `app/prompts/prompts.yaml`
- `ml` — BioBERT training/evaluation under `backend/ml/`, the detector tool
- `db` — raw psycopg3 SQL and the async pool in `app/db/main.py`
- `api` — FastAPI routes, dependencies, `app/main.py`, the structured error contract
- `frontend` — Next.js pages, components, hooks, `apiClient.ts`
- `config` — `pyproject.toml`, lint/type config, env examples, Docker/compose

## Rules

- Keep the title under 72 characters.
- Use the imperative mood: "add rate limiting" not "added rate limiting".
- Do not mention file names in the title unless the file name _is_ the feature (e.g. `add .env.example`).
- Do not include the scope if the change is truly cross-cutting.
- If a backend Pydantic schema changed (under `app/schemas/`), the frontend types in `frontend/src/types/api.d.ts` must be regenerated via `pnpm generate:api-types` — if the diff shows a schema change without a matching `api.d.ts` change, warn the user before committing.
- Never edit `frontend/src/types/api.d.ts` by hand — it is generated.
- Never commit anything in `.env` files — if staged, warn the user immediately and do not proceed.
