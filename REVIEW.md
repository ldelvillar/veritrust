# REVIEW.md

Rules for any agent reviewing a VeriTrust change, on top of the conventions in `AGENTS.md`, `backend/AGENTS.md`, `frontend/AGENTS.md`, `CONTEXT.md` and `docs/adr/`. A change that breaks one of those, or leaves one of their lines out of date, is a finding.

## What failure looks like here

Rank findings by these, worst first:

- **Verdict** — misinformation comes out "Verdadero". Any Verdict, Confidence or Credibility decided outside `app/core/verdict.py`, by the LLM, from Sources the report doesn't show, or against ADR-0002/0003 (a true Claim offsetting a false one, an uncertain Claim leaving an Analysis true).
- **Claims** — a Claim's Evidence or Stance lands on another Claim: lists aligned by position, or a judge failure inferred from a missing key.
- **Analysis lifecycle** — an Analysis stuck in pending, two Runs overlapping, or `status`/`stage` written outside the lifecycle module (ADR-0001).
- **Migrations** — data lost or the live schema out of step with the code: an applied file edited or deleted, a step outside a transaction, or code that needs a column before its migration ships (ADR-0004).
- **Security** — user content steering a prompt, a URL fetch reaching internal hosts, an unsafe file parse, a skipped auth or rate-limit check, or an export cell that bypasses the formula-injection guard.
- **Prompts** — a `prompts.yaml` change with no `/eval-pipeline` result showing the gold set holds.
- **API contract** — a schema change without regenerated `api.d.ts`, or an error outside the structured error contract.
- **Config, CI and deploy** — it misroutes or ships unverified: env read outside `Settings`, a deploy that can run without green CI, or a backup that can fail silently.
- **Docs** — it lies: a doc or runbook that no longer matches the code or the commands.

## Skip

- `frontend/src/types/api.d.ts`, `backend/uv.lock`, `frontend/pnpm-lock.yaml`, `skills-lock.json` — generated; CI checks them.
- `.claude/skills/**` vendored from `mattpocock/skills` (listed in `skills-lock.json`).
- `backend/data/**` — evaluation datasets.
- Anything ruff, mypy, eslint, prettier or the type check already enforce.

## Reporting

- **Evidence** — every finding cites a file and line plus a concrete failing scenario (input or state → wrong result); a guess from a name is not a finding.
- **Class** — when a finding is one instance of a pattern, name the pattern and list every instance in the diff.
- **Tags** — mark each finding **Important**, **Nit** or **Pre-existing** (a bug the change did not introduce).
- **Nits** — at most three, and only when they would change behaviour or mislead a reader.
- **Summary** — start with the count, e.g. "2 findings (1 Important, 1 Nit)"; when there is nothing to fix, say "No findings." and stop.
