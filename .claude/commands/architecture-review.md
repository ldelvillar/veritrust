---
description: Real architectural review of this monorepo, grounded in the actual code
argument-hint: "[structure|frontend|backend|pipeline|scalability|maintainability|security]"
---

Act as a senior software architect specialized in fullstack systems, FastAPI, Next.js, and LLM pipelines. Review the architecture of this monorepo as the code actually is, not against generic best practices.

If `$ARGUMENTS` names a section (structure, frontend, backend, pipeline, scalability, maintainability, security), review ONLY that section. Otherwise, run all sections in the order below.

BEFORE YOU START:

- Read `backend/AGENTS.md`, `frontend/AGENTS.md`, `CONTEXT.md` and every ADR in `docs/adr/` — the conventions and decisions live there, not in the root `AGENTS.md`. Then read the key modules of each area before judging it.
- Treat those conventions and accepted ADRs as ground truth. For each relevant one, assess whether the code adheres or has drifted, and call out drift explicitly.
- Challenge a convention or ADR only with a concrete problem it causes in this code: name it, and check the ADR's Considered Options so you never re-propose a rejected option.
- Name things with the `CONTEXT.md` vocabulary (Analysis, Run, Retry vs Reanalyze, Verdict, Evidence coverage, …).

RULES:

- No finding without a concrete reason and a reference to a real file/module. If you can't point to the exact file/pattern, don't claim it.
- If something is well-designed, say so — don't invent problems.
- Every criticism states: (1) the problem, (2) why it matters, (3) the real impact at scale or in maintenance, (4) the simplest reasonable fix.
- Be pragmatic. Avoid enterprise overengineering and theoretical purity. Don't recommend microservices unless clearly justified.
- Calibrate severity to the project's actual scale — assume a small team / early-stage product on a single VM, not enterprise load, unless the code shows otherwise.

---

## 1. STRUCTURE

Scope: package boundaries (`frontend/`, `backend/app`, `backend/ml`) and dependency direction, the generated API contract, env/config management across both packages, Docker Compose (local stack and `docker-compose.prod.yml` overlay).
Red flags: hidden coupling between frontend/backend/ml, duplicated logic or schema-drift risk, missing boundaries, structure that breaks down with multiple developers.

## 2. FRONTEND — `frontend/`

Scope: App Router layout (public pages vs the Clerk-protected `/app` tree in `src/proxy.ts`), server vs client component split and server preloads (`src/lib/serverApi.ts`), data fetching with SWR (`useApiQuery`/`useApiMutation`) and pending-analysis polling, error/loading boundaries, form handling, typing against the generated `api.d.ts`.
Red flags: business logic leaking into UI (e.g. re-deriving a Verdict the backend already sends), API contracts duplicated instead of using the generated types, needless rerenders or polling, data-fetching patterns that won't scale, drift from `frontend/AGENTS.md`.

## 3. BACKEND — `backend/app` (API, worker, MCP)

Scope: router/dependency design, async correctness, DB access (raw psycopg3 pool) and schema evolution (`backend/db/init.sql`, no migration framework), the Analysis lifecycle across routes, arq worker and orphan reaper, the MCP server (`app/mcp/`) as a second entry point, config (`Settings`), the `ErrorCode` contract, logging/observability, auth (Clerk JWT for the web API, Clerk OAuth for MCP).
Red flags: fat routers / business logic in endpoints, sync calls blocking async routes, hidden global state, weak typing, circular imports, the MCP path diverging from the web API (auth, rate limits, intake), writes or decisions that bypass the modules `backend/AGENTS.md` names as sole owners.

## 4. AI PIPELINE — `backend/app/agents`, `backend/ml`

Scope: the LangGraph graph and agent boundaries (Extractor → Translator → Investigator → Health Expert), the LLM provider layer (`app/utils/llm.py`) and per-agent models, structured-output robustness, the evidence clients (Europe PMC, PubMed, openFDA, CIMA under `app/utils/`) and Evidence outage handling, what the deterministic `app/core/verdict.py` decides vs what the LLM writes, prompt management (`prompts.yaml`), and the evaluation harness in `backend/ml` (datasets and splits, gold set, metrics, evidence replay and checkpoints, run metadata; `docs/ml-experiments.md` is its lab notebook).
Red flags: LLM output trusted without validation, Verdict logic leaking into prompts or agents, the harness drifting from the production graph or config, thresholds tuned on the test split, eval runs that can't be reproduced (live evidence APIs, unpinned models), behaviour that holds on a development-only hosted provider but not on production Ollama.

## 5. SCALABILITY

Scope: the single-VM deployment, statelessness/horizontal scaling of web and worker, worker concurrency and Ollama throughput, external evidence API rate limits, polling load, caching, DB pool and query bottlenecks.
Classify each finding as: current problem, future risk, or premature optimization.

## 6. MAINTAINABILITY

Scope: consistency & readability, onboarding difficulty, documentation quality (the AGENTS.md files, `CONTEXT.md`, ADRs, runbooks in `docs/`), testing strategy & coverage (backend and frontend), type safety, lint/format, OpenAPI quality, CI/CD (`.github/workflows/`), deployment reproducibility.
Red flags: risky CI/CD gaps, weak test pyramid, drift between code and docs.

## 7. SECURITY

Scope: CORS, auth exposure (Clerk JWT and JWKS handling, MCP OAuth, the unauthenticated share-link and `/config` routes), secret/env handling (production `.env` from GCP Secret Manager), rate limiting & abuse prevention (including the contact form), SSRF on URL fetching, prompt injection (IN SCOPE: user-submitted text, URLs, files and MCP tool inputs flow into the LangGraph pipeline), rendering of LLM output in the frontend, file-upload risks, stored health content and its deletion, unsafe deserialization, dependency vulnerabilities.
Report risks that apply to this code and deployment, not theoretical ones.

---

OUTPUT FORMAT

Start with a 2–3 sentence overall assessment of the codebase's architectural health, then the sections.

For each section:

### [SECTION NAME]

✅ Good — what is genuinely well-designed and should not change.

⚠️ Could be improved — for each finding: Problem / Why it matters / Real impact / Recommended fix / Severity (Low|Medium|High).

Be concise and technical. Reference concrete files or modules. Report only the highest-value findings per section; omit trivia and nits. Place each finding in the section where it fits best and cross-reference rather than repeating it.

# Priorities

The highest-value improvements, ordered by impact, effort, and risk reduction. For each: expected benefit, implementation complexity, and whether it is urgent or optional.
