# Ship.md

Run all quality checks for the VeriTrust project, fix any issues, then commit and push.

## Steps

Run these in order. Stop immediately if any step fails and cannot be auto-fixed.

### 1. Review

Run the `/review` command on the current changes.

- If there are any **must fix** issues, stop and surface them — do not proceed until resolved.
- If there are **should fix** issues, flag them to the user and ask whether to fix them before continuing.
- If there are only **worth noting** issues or none, proceed automatically.

### 2. Safety check

Run `git diff --staged && git diff HEAD` to understand what's changed.

If any `.env` file is staged, **stop immediately** and warn the user — do not proceed.

### 3. Backend checks (run from `backend/`)

```bash
uv run ruff format app ml tests                       # Auto-fixes formatting
uv run ruff check app ml tests                        # Must pass — lint
uv run mypy                                            # Must pass — type-check
uv run pytest tests --cov=app --cov-fail-under=80     # App suite — must pass (80% coverage)
uv run pytest ml/tests --cov=ml --cov-fail-under=80   # ML suite — must pass (80% coverage)
```

If tests fail:

- Diagnose the failure.
- Fix it if the cause is clear and the fix is small and safe.
- Re-run tests to confirm.
- If the fix is non-trivial or risky, stop and explain what's broken before touching anything.

If lint or type-check errors are not auto-fixable, fix them manually before proceeding.

### 4. Frontend checks (run from `frontend/`)

```bash
pnpm lint        # ESLint — fix auto-fixable issues
pnpm test        # Vitest — must pass
pnpm build       # Production build + type-check — must pass
```

If tests fail:

- Diagnose the failure.
- Fix it if the cause is clear and the fix is small and safe.
- Re-run tests to confirm.
- If the fix is non-trivial or risky, stop and explain what's broken before touching anything.

If the build fails due to type errors, fix them. If lint errors are not auto-fixable, fix them manually.

### 5. API types check

If any backend Pydantic schema under `app/schemas/` was modified, the generated frontend types must be refreshed. With the backend running at `http://localhost:8000`, run from `frontend/`:

```bash
pnpm generate:api-types
```

Then re-run `pnpm build` to confirm the new types type-check. Never edit `frontend/src/types/api.d.ts` by hand. If the backend can't be started here, stop and tell the user the types need regenerating.

### 6. Commit

Stage all changes including any fixes made during this process:

```bash
git add -A
```

Then run the `/commit` command, which handles commit message generation and env file safety checks.

### 7. Push

```bash
git push
```

If the push is rejected due to upstream changes, run `git pull --rebase` then push again. If rebase conflicts arise, stop and surface them — do not attempt to resolve conflicts silently.

## Done

Report: what was checked, what (if anything) was fixed, the commit message used, and confirmation that the push succeeded.
