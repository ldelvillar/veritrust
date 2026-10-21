# Reviewer evals

Known past bugs, reintroduced on purpose, that the review setup must catch, plus clean changes it must leave alone. Run them after changing anything the reviewers read or run, and keep the change only if no case regresses.

## When to run

- After changing `REVIEW.md`, `.claude/commands/pr-security-review.md`, `.github/workflows/claude-code-review.yml`, or any `CLAUDE.md`/`AGENTS.md`.
- When the review plugin (`code-review@claude-code-plugins`) or the action's default model may have changed; neither is pinned.
- Otherwise every few weeks, to catch drift.

## Cases

Each bug case undoes one `fix:` commit in production code only; the tests stay as on `main`, so CI fails and the PR can't merge. Titles and descriptions are fixed and neutral: the reviewer weighs the PR's stated intent, so changing them changes the result.

| Case | Undo | Run as | Branch | Pass when |
|---|---|---|---|---|
| A | `67b43d3` in `backend/app/core/verdict.py` | PR | `refactor/true-verdict` | Claude bug review posts an Important finding citing ADR-0003 |
| B | `86079f7` in `backend/app/api/dependencies/check_rate_limit.py` | local | `refactor/client-ip` | `/code-review` reports the client-chosen rate-limit key or the undone `86079f7` |
| C | `2b22065`, by hand (see below) | local | `refactor/jwks-client` | `/code-review` and `/pr-security-review` both report the unthrottled JWKS refetch |
| D | `e29a1ed` in `backend/app/api/routes/analysis.py` | PR | `feat/feedback-rate-limit` | exactly one thread flags the undone `e29a1ed` (from either the bug review or the undone-fix check) |
| Clean | rewrite of `86079f7`'s lines, same behaviour (see below) | PR | `refactor/last-forwarded-hop` | no Important finding from any job, and CI green |

PR titles and descriptions, one per case:

- **A** — `refactor(agents): decide a true Verdict from the true Claims alone` / "Trims `_overall` so an Analysis with true Claims is true unless one is false."
- **B** — commit `refactor(auth): read the client IP from the first X-Forwarded-For hop`.
- **C** — commit `refactor(auth): use PyJWT's JWKS client directly`.
- **D** — `feat(api): rate-limit verdict feedback like analysis submissions` / "Puts `POST /analysis/{id}/feedback` behind `check_rate_limit` and documents its 429."
- **Clean** — `refactor(auth): find the last X-Forwarded-For hop without building a list` / "Walks the X-Forwarded-For hops from the end and returns the first non-blank one, instead of building the full list first. Same result: the last hop the proxy wrote, or the direct peer."

Building the cases from `main`:

- **A, B, D** — `git diff <fix> <fix>^ -- <file> | git apply`, then commit with the case's title.
- **C** — the code moved after `2b22065`: in `backend/app/core/jwks.py`, delete `JWKS_REFRESH_COOLDOWN_SECONDS` and `_CooldownJWKClient` with their now-unused imports, and have `_get_jwks_client` return `PyJWKClient(jwks_url, cache_keys=True, lifespan=600)`. `ruff check` must pass.
- **Clean** — in `_client_ip`, replace the `hops` list and its `if hops: return hops[-1]` with `forwarded = request.headers.get("x-forwarded-for") or ""`, then `for hop in reversed(forwarded.split(",")):` returning the first non-blank `hop.strip()`. The contact and rate-limit tests must pass.

## Running a PR case

1. Build the branch from `main` under the case's branch name, push it, and open the PR with the exact title and description.
2. Wait for `Claude bug review`, `Claude security review` and `Claude undone-fix check`, then collect `gh api repos/ldelvillar/veritrust/pulls/<n>/comments` and the PR's conversation comments.
3. Score it against the case's pass condition.
4. Close it with `gh pr close <n> --delete-branch --comment "Reviewer eval; not for merge."`.

## Running a local case

B and C reintroduce security bugs, so they are built as local-only branches and never pushed.

1. Build the branch from `main` and commit it; check it has no upstream.
2. Start a **fresh** agent (not a fork: it must not know which bug is planted) in its own worktree, and hand it only this brief: switch to the branch; run the `code-review` skill with `main...HEAD`, then the `pr-security-review` skill; return both outputs verbatim; never push, edit, commit or comment.
3. Score both outputs against the case's pass condition.
4. Remove the worktree and delete the branch.

The run is done when every case has a pass or fail recorded below, and every eval branch, PR and worktree is gone.

## Growing the set

- Every bug that reaches `main` becomes a case once fixed, above all one the reviewers missed: its fix commit is the case.
- Every reviewer finding rejected as wrong becomes a clean case, so no later change brings it back.

## Results

Each run adds a row; a change to the review setup is kept only if no case goes from pass to fail.

| Date | Setup | A | B | C | D | Clean |
|---|---|---|---|---|---|---|
| 2026-10-21 | #37–#39 (plugin bug review, Anthropic security command) | pass | pass, `/pr-security-review` silent | pass, `/pr-security-review` silent | fail | — |
| 2026-10-21 | #42 (security exception, REVIEW.md undone-fix rule) | — | pass, `/pr-security-review` silent | pass | fail | pass |
| 2026-10-21 | #45 (undone-fix check job) | — | — | — | fail: caught twice, two threads (ordering fixed in #48) | pass |

`/pr-security-review` stays silent on B even with the exception: Caddy 2.5+ without `trusted_proxies` probably replaces a client-sent `X-Forwarded-For`, so the bypass may not be reachable in production, which keeps it under the 8/10 confidence bar. `/code-review` still catches it.
