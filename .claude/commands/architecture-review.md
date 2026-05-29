---
description: Real architectural review of this monorepo, grounded in the actual code
argument-hint: "[structure|frontend|backend|ml|scalability|maintainability|security]"
---

Act as a senior software architect specialized in fullstack systems, FastAPI, Next.js, and MLOps. Perform a REAL architectural review of this monorepo based on the actual codebase — not generic best practices.

If `$ARGUMENTS` names a section (structure, frontend, backend, ml, scalability, maintainability, security), review ONLY that section. Otherwise, run all sections in the order below.

BEFORE YOU START:

- Read `CLAUDE.md` (repo root) and `README.md`, then explore the actual files in each area before judging it — read the key modules, don't assume.
- Treat the conventions documented in `CLAUDE.md` as ground truth. For each relevant one, assess whether the code adheres or has drifted, and call out drift explicitly.
- Do NOT recommend changes that contradict an intentional, documented convention (e.g. no ORM / raw psycopg3, centralized `Settings` via `get_settings()`, agent prompts in `prompts.yaml`, the `ErrorCode` structured error contract, OpenAPI-generated frontend types, the arq worker for the slow pipeline) unless you can show the convention itself causes a concrete problem.

RULES:

- No finding without a concrete reason and a reference to a real file/module. If you can't point to the exact file/pattern, don't claim it.
- If something is well-designed, say so — don't invent problems.
- Every criticism states: (1) the problem, (2) why it matters, (3) the real impact at scale or in maintenance, (4) the simplest reasonable fix.
- Be pragmatic. Avoid enterprise overengineering and theoretical purity. Don't recommend microservices unless clearly justified.
- Calibrate severity to the project's actual scale — assume a small team / early-stage product, not enterprise load, unless the code shows otherwise.

PROJECT STRUCTURE:

- /frontend → Next.js (App Router)
- /backend/app → FastAPI
- /backend/ml/training → ML training pipeline
- /backend/ml/evaluation → ML evaluation pipeline

---

## 1. STRUCTURE

Scope: folder boundaries, dependency flow, shared-code strategy, env/config management, Docker setup.
Red flags: hidden coupling between frontend/backend/ML, duplicated logic or schema-drift risk, missing boundaries, structure that breaks down with multiple developers.

## 2. FRONTEND — /frontend

Scope: App Router layout, server vs client component split, data fetching + caching/revalidation, state management, error/loading boundaries, form handling, typing strategy.
Red flags: business logic leaking into UI, API contracts duplicated instead of using the generated types, needless rerenders, data-fetching patterns that won't scale, inconsistent conventions.

## 3. BACKEND — /backend/app

Scope: router/dependency design, async correctness, DB access (raw psycopg3 pool), background work (arq worker), config (`Settings`), the `ErrorCode` contract, logging/observability, auth (JWT/secret handling).
Red flags: fat routers / business logic in endpoints, sync calls blocking async routes, hidden global state, weak typing, circular imports, auth or secret-handling weaknesses.

## 4. ML PIPELINE — /backend/ml

Scope: training reproducibility & determinism, dataset separation, evaluation methodology, model serialization/loading, train-vs-inference preprocessing parity, artifact/versioning, inference latency.
Red flags: train/test leakage, preprocessing mismatch between training and inference, hardcoded paths, non-deterministic training, missing model versioning, retraining that can't be automated safely.

## 5. SCALABILITY

Scope: deployment separation, statelessness/horizontal scaling, caching, queue/background needs, model-inference and DB bottlenecks, concurrency limits.
Classify each finding as: current problem, future risk, or premature optimization.

## 6. MAINTAINABILITY

Scope: consistency & readability, onboarding difficulty, documentation quality, testing strategy & coverage, type safety, lint/format, OpenAPI quality, CI/CD maturity, deployment reproducibility.
Red flags: risky CI/CD gaps, weak test pyramid, drift between code and docs.

## 7. SECURITY

Scope: CORS, auth exposure, secret/env handling, rate limiting & abuse prevention, model input sanitization, prompt injection (IN SCOPE: user-submitted text and URLs flow into the Ollama/LangGraph pipeline), unsafe deserialization, file-upload risks, dependency vulnerabilities.
Focus on REAL risks only.

---

OUTPUT FORMAT

Start with a 2–3 sentence overall assessment of the codebase's architectural health, then the sections.

For each section:

### [SECTION NAME]

✅ Good — what is genuinely well-designed and should not change.

⚠️ Could be improved — for each finding: Problem / Why it matters / Real impact / Recommended fix / Severity (Low|Medium|High).

Be concise and technical. Reference concrete files or modules. Report at most the ~5 highest-value findings per section; omit trivia and nits. Place each finding in the section where it fits best and cross-reference rather than repeating it.

# Priorities

The 3–5 highest-value improvements, ordered by impact, effort, and risk reduction. For each: expected benefit, implementation complexity, and whether it is urgent or optional.
