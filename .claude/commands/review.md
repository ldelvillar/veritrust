# Review.md

Review the current changes in the VeriTrust project and flag any real issues before shipping.

## What to review

Run `git diff HEAD` to get the full picture of what's changed. If nothing is changed, say so and stop.

Focus only on things that matter. Do not flag style preferences, formatting, or anything already enforced by Ruff / mypy / ESLint / TypeScript.

### Logic & correctness

- Off-by-one errors, wrong conditions, unreachable branches
- LangGraph pipeline ordering must stay Extractor → Translator → Investigator → Health Expert; translations must preserve order and cardinality with the extracted statements, and the Investigator runs before the Health Expert so evidence coverage can attenuate the verdict confidence
- Global verdict math in `app/agents/health_expert.py` (fake-probability average, label threshold) — make sure label/confidence stay coherent
- `sync def` agent nodes vs `async def` routes/DB — no blocking I/O introduced inside an `async def`, and no `await` dropped on async DB/graph calls
- Race conditions or state inconsistencies in the SWR data hooks (`useApiQuery`) or React state

### Security

- Any credential, secret, key, or `DATABASE_URL` hardcoded or logged — everything must come from environment variables
- Clerk JWT validation weakened — `verify_aud` / `verify_iss` must stay on, RS256 only, no `verify=False`
- A protected route missing its auth dependency (`Depends(get_current_user)` or `Depends(check_rate_limit)`)
- SSRF protections in `app/utils/extract_text_from_url.py` removed or bypassed (scheme check, private-IP block, per-redirect revalidation)
- Prompt-injection delimiters (`<<USER_INPUT>> … <<END>>`) dropped from the extractor prompt
- Raw LLM output rendered as HTML on the frontend (`react-markdown` must stay without `rehype-raw`)

### Data layer

- Raw SQL in `app/db/main.py` that interpolates untrusted input instead of using `%s` parameters — the only dynamic SQL fragments allowed are the whitelisted ones (`safe_score_sort`, the parameter-built `where_sql`)
- A backend Pydantic schema (`app/schemas/`) changed but `frontend/src/types/api.d.ts` not regenerated via `pnpm generate:api-types`

### Tests

- New behaviour added without a corresponding test under `backend/tests/` (app) or `backend/ml/tests/` (ml)
- Test structure doesn't mirror the module/route structure
- Tests hitting a real DB, real Ollama, or downloading model weights instead of mocking them

### Conventions

- Agent prompts hardcoded in Python instead of `app/prompts/prompts.yaml`
- A new error path raising a bare `HTTPException` instead of `make_error_detail(ErrorCode.X)` + a matching entry in the route's `responses=` dict
- Frontend API calls made outside `frontend/src/lib/apiClient.ts` / `useApiQuery`
- `frontend/src/types/api.d.ts` edited by hand instead of regenerated

## Output format

Be direct and concise. Group findings by severity:

**Must fix** — blocks shipping, correctness or security issue
**Should fix** — not blocking but will cause problems soon
**Worth noting** — minor, can be addressed later

If there are no issues, say "Looks good — nothing blocking." and stop. Don't invent problems.
