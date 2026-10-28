# Plan: Free and Pro plans for individuals (Stripe, EUR)

This is an implementation brief for a Claude Code session. It turns the individual plans on the landing (`frontend/src/app/(public)/_components/Pricing.tsx`) into enforced behaviour, with Pro sold through Stripe in EUR. Team and Institution plans are out of scope; leave their landing cards as "Acceso anticipado".

Read `AGENTS.md`, `backend/AGENTS.md`, `frontend/AGENTS.md`, `CONTEXT.md`, `REVIEW.md` and `docs/adr/0001-analysis-lifecycle-sole-writer.md` before starting. Every rule there still applies (one-line comments, `Settings` only, error contract, lifecycle sole writer, generated `api.d.ts`, run commands from the repo root).

## 1. Decisions already taken (do not reopen)

| Topic | Decision |
| --- | --- |
| Payment provider | Stripe Billing with Stripe Tax. Clerk Billing is ruled out (USD only, no VAT, no 3DS). |
| Prices | Pro 29€/month or 290€/year, **IVA included** (Stripe prices with `tax_behavior=inclusive`). No trials, no promo codes at launch. |
| Checkout UX | Stripe hosted Checkout to subscribe, Stripe Customer Portal to cancel, switch interval, change card and download invoices. |
| Invoices | Checkout collects the billing address (required) and an optional tax ID (`tax_id_collection`), so Spanish autónomos and companies get a factura with their NIF. |
| Plan source of truth | Our own Postgres tables, written only by Stripe webhooks and looked up by Clerk `user_id` on each gated request. Clerk metadata is not used. Works the same for web JWTs, MCP OAuth tokens and API keys. |
| Allowance period | Calendar month in `Europe/Madrid`, resets on the 1st at 00:00 Madrid time. |
| What consumes a unit | A Run that ends **done**: an Analysis consumes one unit the first time it reaches done (from its submission or from a Retry of it), each Reanalyze that ends done consumes one more, and each MCP `search_evidence` that succeeds consumes one. Failed Runs consume nothing. Retry never adds a unit of its own. |
| Old history (Free) | Analyses older than 30 days are hidden from Free users, never deleted. Upgrading brings them back. |
| History tools (Free) | Plain 30-day list, newest first, paginated. Search, filters, sort and the dashboard are Pro. The API enforces this, not only the UI. |
| CSV export | The filtered History export is Pro. The full "Exportar mis datos" export on `/app/cuenta` stays available to every plan (GDPR art. 20) and covers all the user's analyses, including hidden ones. |
| Downgrade | Public share links of a user who is no longer Pro return 404 (tokens are kept, so they work again on re-upgrade). `past_due` keeps Pro during Stripe's payment retries. Done file analyses and their original file stay viewable within the 30-day window. |
| URL text over 3,000 chars (Free) | Truncated to the plan limit by the worker, same mechanism as today's 10,000 cap. |
| Rollout | No feature flag. There are no production users yet, so limits apply as soon as the deploy lands. |
| Manual Pro grants | Not needed now (no comp plans, no Institution handling). API keys keep working and follow the plan of the user who owns the key. |

## 2. Plan matrix

This table is the spec. It lives in code in exactly one place (`app/core/plans.py`, below).

| Capability | Free | Pro | Enforced in |
| --- | --- | --- | --- |
| Analyses per month | 10 | 300 | `AnalysisIntake` via `analysis_transitions`, MCP `search_evidence` |
| Max pasted text | 3,000 chars | 10,000 chars | `AnalysisIntake.submit` |
| URL text analysed | first 3,000 chars | first 10,000 chars | worker truncation, limit fixed on the row at intake |
| File analysis (PDF/TXT/MD) | no | yes | `AnalysisIntake.submit_file` |
| History visible | last 30 days | all | `history.py`, `history_query.py` |
| History search, filters, sort | no | yes | `GET /history` |
| Dashboard | no | yes | `GET /dashboard` |
| PDF report (`window.print`) | no | yes | frontend only (see 7.4) |
| Filtered CSV export | no | yes | `GET /history/export` |
| Full account export | yes | yes | new `GET /account/export` |
| Public share links | no | yes | `POST /analysis/{id}/share`, `GET /share/{token}` |
| MCP tools | no | yes | `app/mcp/server.py` |
| Same models and sources | yes | yes | nothing to do |

## 3. Domain and decision records (do first)

Use the `domain-modeling` skill.

- Add a `## Plans` section to `CONTEXT.md` with these terms, each with an `_Avoid_` line, matching the existing style:
  - **Plan**: what a user is entitled to, Free or Pro. _Avoid_: tier, level, package.
  - **Subscription**: the paid Stripe agreement that makes a user Pro while it is active or past due. _Avoid_: membership, license.
  - **Allowance**: how many done Runs a Plan allows per calendar month (Madrid time). _Avoid_: quota, credits.
  - **Usage**: the done Runs (and successful evidence searches) counted against the Allowance this month. _Avoid_: consumption, spend.
  - **History window**: how far back a Plan sees its History; 30 days for Free, unlimited for Pro. _Avoid_: retention (nothing is deleted).
- Write `docs/adr/0005-billing-with-stripe-and-postgres-entitlements.md`: Stripe over Clerk Billing (currency, VAT, 3DS), Postgres as the entitlement source of truth (all auth paths, instant effect), Usage as an append-only ledger written in the same transaction as `complete()` so deleting analyses never refunds units, and the advisory-lock allowance check living inside `analysis_transitions` to keep ADR-0001 intact.

## 4. Stripe setup (manual, document in `docs/deploy/stripe.md`)

The coding session can't click through Stripe, so write these steps as a runbook. Consider the `wizard` skill for an interactive script.

1. Stripe account in Spain, EUR as default currency. Test mode first.
2. Stripe Tax: add the Spain registration, set the origin address, and set the product tax code to the SaaS code that matches the audience (check Stripe's list; the personal-use SaaS code is the likely default). Add OSS later, once cross-border EU B2C sales get close to 10,000€/year.
3. Product "VeriTrust Pro" with two prices: 29.00 EUR monthly and 290.00 EUR yearly, both `tax_behavior=inclusive`. Copy the price IDs into `STRIPE_PRICE_PRO_MONTHLY` and `STRIPE_PRICE_PRO_YEARLY`.
4. Customer Portal: allow cancel (at period end), switch between the two Pro prices, update payment method, show invoice history. Disallow quantity changes.
5. Billing settings: Smart Retries on, and "cancel the subscription" when all retries fail (that ends `past_due`). Turn on Stripe's customer emails for receipts, failed payments and upcoming renewals, in Spanish.
6. Webhook endpoint `https://api.veritrust.es/billing/webhook` with the events listed in 5.4. Copy its signing secret into `STRIPE_WEBHOOK_SECRET`.
7. Local development: `stripe listen --forward-to localhost:8000/billing/webhook` gives a local `whsec_…`.
8. Repeat 3 to 6 in live mode for production. Test-mode and live-mode keys are never mixed.

## 5. Backend

### 5.1 Settings and dependencies

- Add the `stripe` Python SDK with `uv add --directory backend stripe` (commits the lockfile). Pin the API version on the client (`stripe_version=`) so webhook payloads don't change shape under you.
- New `Settings` fields in `backend/app/core/config.py` (one-line comments, same style as the rest):
  - `stripe_secret_key: str = ""`
  - `stripe_webhook_secret: str = ""`
  - `stripe_price_pro_monthly: str = ""`
  - `stripe_price_pro_yearly: str = ""`
  - `stripe_api_base_url: str | None = None` (only so tests can point the SDK at a stub)
- `validate_runtime()`: add all four non-optional ones to `missing` (billing is live from launch, so a missing key is a `/healthz` 503, not a checkout 500).
- Add them to `backend/.env.example`, `docs/deploy/env.md` (the `backend/.env` block) and the compose files only if those pass env explicitly. Tests use dummy values such as `sk_test_dummy` and `whsec_test_dummy`, never real keys.
- Stripe SDK calls are blocking HTTP unless you use its async methods. Use the `StripeClient` async variants (`…_async`) if the pinned version has them; otherwise wrap calls in `asyncio.to_thread`. Never call the sync SDK inside `async def` (backend AGENTS.md).

### 5.2 Migration `backend/db/migrations/0003_billing.sql`

High-risk (migration): `/code-review max` and the user reads the diff. Never edit `0001`/`0002`.

```sql
CREATE TABLE public.billing_customers (
    user_id            TEXT PRIMARY KEY,
    stripe_customer_id TEXT NOT NULL UNIQUE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.subscriptions (
    stripe_subscription_id TEXT PRIMARY KEY,
    user_id                TEXT NOT NULL,
    status                 TEXT NOT NULL CHECK (status IN (
        'incomplete','incomplete_expired','trialing','active',
        'past_due','canceled','unpaid','paused')),
    price_id               TEXT NOT NULL,
    billing_interval       TEXT NOT NULL CHECK (billing_interval IN ('month','year')),
    current_period_end     TIMESTAMPTZ NOT NULL,
    cancel_at              TIMESTAMPTZ,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_subscriptions_user ON public.subscriptions (user_id);

CREATE TABLE public.stripe_events (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.usage_events (
    id          BIGSERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('analysis','reanalysis','evidence_search')),
    analysis_id UUID REFERENCES public.analysis_history (id) ON DELETE SET NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_usage_events_user_time ON public.usage_events (user_id, occurred_at);

ALTER TABLE public.analysis_history ADD COLUMN max_input_chars INTEGER;
```

`ON DELETE SET NULL` is deliberate: deleting an analysis (or "delete all") must never give units back. `max_input_chars` is the plan's text limit fixed when the analysis opens, so the worker truncates URL text to it and a later Reanalyze after a downgrade keeps the original limit. `NULL` means the schema default (10,000) for rows from before the migration.

### 5.3 `app/core/plans.py`: the only place plan rules live

- `PlanName = Literal["free", "pro"]`.
- `@dataclass(frozen=True) class PlanLimits`: `name`, `analyses_per_month`, `max_input_chars`, `history_days: int | None`, and booleans `files`, `history_tools`, `dashboard`, `csv_export`, `share`, `mcp`, `pdf`.
- `FREE` and `PRO` constants holding the matrix in section 2. `PRO.max_input_chars` is `MAX_INPUT_TEXT_LENGTH` from `app/schemas/analysis.py`, not a second literal.
- `PRO_STATUSES = {"active", "trialing", "past_due"}`; anything else is Free.
- `limits_for(subscription: SubscriptionRow | None) -> PlanLimits`: Pro when the row's status is in `PRO_STATUSES` and its `price_id` is one of the two configured Pro prices.
- `month_window(now) -> tuple[datetime, datetime]`: start of this Madrid month and start of the next (the next one is `resets_at`). Use `zoneinfo.ZoneInfo("Europe/Madrid")`.
- `history_floor(limits, now) -> datetime | None`.
- Table of cases in `backend/tests/unit/test_plans.py`: every Stripe status, unknown price, `None`, month window across the DST changes (last Sunday of March and of October) and across 31 Dec / 1 Jan.

### 5.4 `app/db/billing.py` (SQL) and `app/core/billing.py` (Stripe)

`app/db/billing.py`, raw psycopg3 like the other modules:

- `get_customer_id(user_id)`, `insert_customer(user_id, stripe_customer_id)` (on conflict, return the existing one).
- `user_id_for_customer(stripe_customer_id)`.
- `upsert_subscription(row)`: full replace of the row's fields.
- `get_user_subscription(user_id) -> SubscriptionRow | None`: the "best" one (Pro status first, then latest `current_period_end`), in case a user ever ends up with two.
- `record_event(event_id, type) -> bool`: `INSERT … ON CONFLICT DO NOTHING`; False means already processed.
- `usage_this_month(user_id, start, end) -> int` and `insert_usage(user_id, kind, analysis_id=None)` for evidence searches.
- Tests against real Postgres in `backend/tests/db/test_billing_sql.py`.

`app/core/billing.py`, the Stripe adapter (the only module importing `stripe`):

- `create_checkout_session(user_id, email, interval) -> str` (URL):
  - get or create the Stripe customer (metadata `clerk_user_id`, email from the JWT `email` claim when present), store it in `billing_customers` before creating the session;
  - `mode="subscription"`, the price for `interval`, `client_reference_id=user_id`, `subscription_data.metadata.clerk_user_id=user_id`;
  - `automatic_tax={"enabled": True}`, `billing_address_collection="required"`, `customer_update={"address": "auto", "name": "auto"}`, `tax_id_collection={"enabled": True}`;
  - `locale="es"`, `allow_promotion_codes=False`;
  - `consent_collection={"terms_of_service": "required"}` and `custom_text.terms_of_service_acceptance` linking `/terminos-y-condiciones`, where the user agrees that the service starts at once and that they lose the withdrawal right for the period already used (have a lawyer confirm the wording, see 8);
  - `success_url=f"{APP_BASE_URL}/app/cuenta?checkout=success"`, `cancel_url=f"{APP_BASE_URL}/app/cuenta?checkout=cancelled"`.
- `create_portal_session(user_id) -> str` with `return_url=f"{APP_BASE_URL}/app/cuenta"`.
- `parse_webhook(payload: bytes, signature: str)`: `stripe.Webhook.construct_event`; a bad signature raises a typed `InvalidWebhook`.
- `sync_subscription(subscription_id)`: **re-fetch the Subscription from Stripe** and upsert it. Never trust the event's embedded object or the event order; Stripe delivers out of order and retries.
- Translate Stripe transport/API errors to a typed `BillingUnavailable` (branch on type, never on `str(exc)`).

Events handled by the webhook:

| Event | Action |
| --- | --- |
| `checkout.session.completed` | link `client_reference_id` to the customer if missing, then `sync_subscription(session.subscription)` |
| `customer.subscription.created` / `updated` / `deleted` | `sync_subscription(sub.id)`; the user comes from `billing_customers` (fall back to `metadata.clerk_user_id`) |
| `invoice.paid` / `invoice.payment_failed` | `sync_subscription(invoice.subscription)` (status moves to `active` / `past_due`) |
| anything else | 200 and ignore |

Processing: verify the signature on the **raw** body (`await request.body()`, never the parsed JSON), `record_event` (already seen → 200 at once), handle, return 200. If handling fails, delete the event row (or record it only after success) and return 500 so Stripe retries. Log the event id and type, never the payload.

### 5.5 Routes: `app/api/routes/billing.py` and `app/api/routes/account.py`

Register them in `app/api/router.py`. Every route raises `HTTPException(detail=make_error_detail(ErrorCode.X))` and declares its codes in `responses=`.

- `GET /billing/plan` (auth) → `PlanResponse`: `plan`, `status | None`, `interval | None`, `current_period_end | None`, `cancel_at | None` (the date a scheduled cancellation takes effect), `limits` (the `PlanLimits` fields), `usage` (`used`, `pending`, `remaining`, `resets_at`). The frontend's only source of plan state.
- `POST /billing/checkout` (auth) body `{interval: "month" | "year"}` → `{url}`. 409 `ALREADY_SUBSCRIBED` if the user is already Pro.
- `POST /billing/portal` (auth) → `{url}`. 404 `BILLING_ACCOUNT_NOT_FOUND` if the user never had a customer.
- `POST /billing/webhook` (no auth, signature only). 400 `INVALID_WEBHOOK`. Exclude it from the per-user rate limit and from CORS concerns (Stripe calls it server to server). Check that Caddy's `request_body max_size` and any body-parsing middleware leave the raw body intact.
- `GET /account/export` (auth, every plan): the same CSV serialisation as `history_export.py`, over all the user's done analyses with no history window and no History query. Reuse `export_history` with an "all" query and no floor, rather than a second SQL path.

New `ErrorCode`s (extend `app/schemas/errors.py`, Spanish messages in `app/core/errors.py`):

| Code | HTTP | Spanish message (suggested) |
| --- | --- | --- |
| `PLAN_REQUIRED` | 403 | "Esta función está disponible en el plan Pro." |
| `ALLOWANCE_EXHAUSTED` | 402 | "Has usado todos los análisis de este mes. Se renuevan el día 1 o puedes pasarte a Pro." |
| `TEXT_TOO_LONG_FOR_PLAN` | 413 | "El texto supera el máximo de tu plan." |
| `ALREADY_SUBSCRIBED` | 409 | "Ya tienes el plan Pro." |
| `BILLING_ACCOUNT_NOT_FOUND` | 404 | "Todavía no tienes una suscripción." |
| `BILLING_UNAVAILABLE` | 503 | "No se pudo conectar con el sistema de pagos. Inténtalo de nuevo." |
| `INVALID_WEBHOOK` | 400 | (not user facing) |

`PLAN_REQUIRED`, `ALLOWANCE_EXHAUSTED` and `TEXT_TOO_LONG_FOR_PLAN` are raised by the intake, so add them to `REFUSAL_CODES` (`app/core/analysis_lifecycle.py`) and `REFUSAL_HTTP_STATUS` (`app/api/dependencies/analysis_intake.py`); the existing test keeps the two in step.

### 5.6 Plan dependency

`app/api/dependencies/plan.py`:

- `current_plan(user = Depends(get_current_user)) -> PlanLimits`: one indexed query per request, no cache (a webhook takes effect on the next request).
- `require(feature: str)`: a dependency factory that raises 403 `PLAN_REQUIRED` when `getattr(limits, feature)` is False.
- `web_submitter` gains the plan: `Submitter(user_id, origin, notify_email, limits)`. Add `limits: PlanLimits` to the `Submitter` dataclass; MCP builds it the same way.

### 5.7 Enforcement in the analysis lifecycle

High-risk area (lifecycle, ADR-0001). The allowance check must be atomic with the row it opens, so it goes in `app/db/analysis_transitions.py`, the only module allowed to write `status`.

- `insert_pending`, `insert_pending_file` and `reopen` take `allowance: int` (the plan's `analyses_per_month`), `month_start`, `month_end` and `max_input_chars` (insert only). In one transaction:
  1. `SELECT pg_advisory_xact_lock(hashtext('allowance:' || user_id))`;
  2. `used = count(usage_events in [month_start, month_end))`, `in_flight = count(analysis_history WHERE user_id = … AND status = 'pending')`;
  3. if `used + in_flight >= allowance`, return a sentinel (no row written); the intake raises `AnalysisRefused(ALLOWANCE_EXHAUSTED)`;
  4. otherwise insert or reopen as today, storing `max_input_chars` on insert.
- `complete()` inserts the usage row **in the same transaction** as the `done` update: kind `analysis` if no `usage_events` row exists yet for that `analysis_id`, else `reanalysis`. This gives the "first done counts once, Retry adds nothing, each Reanalyze counts" rule without tracking what opened the Run. A Run that completes after midnight on the 1st counts in the new month; document that in the ADR.
- `AnalysisIntake.submit`: refuse `TEXT_TOO_LONG_FOR_PLAN` when the pasted text is longer than `limits.max_input_chars` (the Pydantic schema still caps at 10,000 for everyone).
- `AnalysisIntake.submit_file`: refuse `PLAN_REQUIRED` when `not limits.files`, before reading the body.
- `retry` and `reanalyze` go through the same allowance check in `reopen`. A Retry needs a free unit because its success will consume the analysis's first unit.
- `load_pending_content` also returns `max_input_chars`; `AnalysisRun`/`UrlContent` carry it, and `extract_text_from_url(url, max_chars)` / `extract_text_from_file(data, filename, max_chars)` / `extract_text_from_pdf` take the limit instead of importing `MAX_INPUT_TEXT_LENGTH` (default to it when `NULL`).
- Update `tests/unit/test_analysis_lifecycle_sole_writer.py` only if it needs to know about the new table; `usage_events` writes stay inside `analysis_transitions.py` too.
- Tests in `tests/db/test_analysis_lifecycle.py` and `tests/support/lifecycle.py`: allowance reached refuses; failed Run consumes nothing; Retry to done consumes one; Reanalyze to done consumes one more; deleting an analysis keeps its usage; two concurrent submissions with one unit left, exactly one wins (use two pool connections with `asyncio.gather`); month boundary.

### 5.8 Enforcement elsewhere

- **History** (`app/api/routes/history.py`, `app/db/history_query.py`): `search_history` and `export_history` take `visible_since: datetime | None` from the plan (not a `HistoryQuery` field: it's an entitlement, not a query) and add it as one predicate in `_where`. For Free, `GET /history` refuses `PLAN_REQUIRED` when any `HistoryQuery` field differs from its default (search, content type, verdict, status, dates, sort); pagination stays free. `GET /history/export` requires `csv_export`. Facets are computed within the window. Add cases to `tests/db/test_history_query.py`.
- **Pending summary** (`GET /history/pending`): unchanged.
- **Detail, status, file, feedback** (`app/db/history.py` readers used by `app/api/routes/analysis.py`): for Free, an analysis older than the window answers 403 `PLAN_REQUIRED` (the frontend shows an upsell, not a 404). Pass the floor into the SQL rather than filtering in Python.
- **Delete one / delete all**: no plan check, and they act on hidden analyses too (erasure right).
- **Dashboard** (`app/api/routes/dashboard.py`): `require("dashboard")`.
- **Share**: `POST /analysis/{id}/share` requires `share`; `DELETE …/share` stays open. `get_shared_analysis_by_token` joins the owner's subscription and returns nothing unless it is in `PRO_STATUSES` with a Pro price; the route answers its usual 404. The OG image route in `frontend/src/app/(public)/r/[token]/` uses the same endpoint, so it follows automatically.
- **MCP** (`app/mcp/server.py`): every tool resolves the caller's plan after `_current_user_id()` and raises `_tool_error(ErrorCode.PLAN_REQUIRED)` when `not limits.mcp`. `verify_claim` passes `limits` in its `Submitter`, so the allowance applies through the intake. `search_evidence` checks `usage_this_month < analyses_per_month` before enqueueing (no in-flight count; the rate limit bounds the overshoot) and passes `user_id` to `run_evidence_search`, which calls `insert_usage(user_id, "evidence_search")` on success. Extend `tests/integration/test_mcp_server.py`.
- **API keys** (`_user_from_api_key`): nothing to change; the plan is looked up by `sub` like any other caller.
- **`GET /config`**: unchanged (it stays the public schema maximum). Per-user limits come from `GET /billing/plan`.

### 5.9 Account deletion while subscribed

Users delete their account through Clerk's `UserButton`. Without handling, a deleted user keeps being charged. Add:

- `POST /webhooks/clerk` verifying the Svix signature (`svix` package, new `CLERK_WEBHOOK_SECRET` in `Settings`, `.env.example`, `docs/deploy/env.md` and `validate_runtime`).
- On `user.deleted`: cancel any active Stripe subscription immediately (`prorate` per your T&C, see 8), and delete that user's `billing_customers`/`subscriptions` rows. Keep `usage_events` only if you need them for disputes; otherwise delete them too, and say which in the privacy policy.
- Document the Clerk dashboard webhook setup in `docs/deploy/stripe.md`.
- Cancelling needs **Subscriptions: Write** on the fine-grained Stripe key; update the permission table in `docs/deploy/stripe.md` and both keys (test and live).

### 5.10 Regenerate the contract

After the schema changes: start the backend and run `pnpm --dir frontend generate:api-types`. Never edit `frontend/src/types/api.d.ts` by hand.

## 6. Frontend

### 6.1 Plan state

- `src/hooks/usePlan.ts`: fetches `GET /billing/plan` through `apiClient`, using the existing `useApiQuery` pattern. Expose `plan`, `limits`, `usage`, `refresh()`.
- Preload it server side in `src/app/app/layout.tsx` via `serverApi.ts`, so gated UI never flashes the wrong state.
- Every gate also handles the API's `PLAN_REQUIRED`, `ALLOWANCE_EXHAUSTED` and `TEXT_TOO_LONG_FOR_PLAN` errors, since the plan can change between render and click (for example a portal cancel that just ended).

### 6.2 Shared upsell pieces

- `src/components/UpgradePrompt.tsx`: inline card or tooltip variant with "Hazte Pro" linking to `/app/cuenta#plan`. Colours from tokens only (`primary`, `primary-soft`, `warning` for "quedan pocos"), scale utilities only, icons from `src/assets/`.
- `src/components/layout/Sidebar.tsx`: a plan badge ("Gratis" / "Pro") and a usage meter ("4 de 10 análisis este mes", resets date on hover), plus a "Hazte Pro" link for Free.

### 6.3 `/app/cuenta`

New `_components/PlanCard.tsx` above the existing cards (`id="plan"`):

- Free: what Pro adds (reuse the landing's item list, imported from a shared module rather than copied), a monthly/annual toggle, "Hazte Pro" → `POST /billing/checkout` → `window.location.assign(url)`.
- Pro: interval, next renewal date, "Se cancelará el …" with `cancel_at` when it is set, a warning band when `past_due` ("No hemos podido cobrar tu suscripción, actualiza tu método de pago"), and "Gestionar suscripción" → `POST /billing/portal`.
- `?checkout=success`: show "Activando tu plan Pro…" and poll `GET /billing/plan` (for example every 2s, up to 30s) until it says Pro, because the webhook can land after the redirect. Then show a success message (`success` tokens). `?checkout=cancelled`: a neutral note.
- `CuentaClient.tsx`: point "Exportar mis datos" at the new `GET /account/export` instead of `/history/export`.

### 6.4 Gates on existing screens

- **Analysis form** (`src/app/app/analisis/_components/AnalysisForm.tsx`): the character limit comes from `limits.max_input_chars` instead of `/config`. Free: the file tab is disabled with `UpgradePrompt`, and the URL tab shows "Con el plan Gratis se analizan los primeros 3.000 caracteres de la página". When `usage.remaining === 0`, disable submit and show the reset date plus the upsell. Update `AnalysisForm.test.tsx`.
- **History** (`src/app/app/historial/`): Free shows a "Mostrando los últimos 30 días" note; the search box, filters and sort are disabled with the upsell; the CSV export button is locked. Keep building every URL through `src/lib/historyQuery.ts`; Free sends only the default query.
- **Dashboard** (`src/app/app/dashboard/page.tsx`): for Free, render an upsell page server side instead of calling the API (no 403 error boundary).
- **Analysis detail** (`src/components/AnalysisResult.tsx`, `ShareDialog.tsx`, `src/hooks/useAnalysisReanalysis.ts`): lock "Exportar PDF" and "Compartir" for Free; the Reanalyze confirm dialog says it uses one of the remaining analyses; a 403 `PLAN_REQUIRED` on load (analysis older than 30 days) renders an upsell state in `src/app/app/analisis/[id]/AnalisisClient.tsx`.
- **Help** (`src/app/app/ayuda/helpContent.ts`): add a plans and billing section (allowance, reset day, how to cancel, invoices).

### 6.5 Public pages

- `src/app/(public)/_components/Pricing.tsx`: the Pro card offers monthly and annual. Its CTA goes to `/registro?redirect_url=/app/cuenta%23plan` when signed out and `/app/cuenta#plan` when signed in (check how `src/config/auth.ts` handles redirect URLs). Update the subtitle, since the Pro plan is no longer early access but Equipo still is. Update `Pricing.test.tsx`.
- `src/app/(public)/demo/_components/DemoForm.tsx`: remove the `pro` entry from `PLAN_INTEREST`, keep `equipo`.
- Grep for "anticipado", "precio", "Pro" and "gratis" in `Faq.tsx`, `Cta.tsx`, `Hero.tsx`, `Header.tsx`, `Footer.tsx` and `not-found.tsx`, and update copy that no longer holds.

### 6.6 E2E

- Extend `frontend/e2e/mock-api.mts` with `GET /billing/plan` (seedable Free or Pro, with usage), `POST /billing/checkout` and `/billing/portal` (return a local URL), `GET /account/export`, and the new error codes on gated routes. An unmocked route answers 501, so cover every new call.
- New `frontend/e2e/billing.spec.ts`: Free sees the meter and the locked file tab; an exhausted allowance blocks submit; the checkout button redirects to the mocked URL; `?checkout=success` polls until Pro; Pro sees the manage button and an unlocked dashboard; a Free 30-day notice on History.
- Update `account.spec.ts`, `history.spec.ts` and `share.spec.ts` for the gates.

## 7. Known limits to state in the PR

1. Monthly allowance overshoot: `search_evidence` checks without counting in-flight jobs, so a Free or Pro user can exceed it by a few concurrent searches (bounded by the per-user rate limit).
2. A Run that finishes after midnight on the 1st counts in the new month.
3. URL truncation is silent in the report today (also at 10,000); a "texto recortado" notice on the report is a possible follow-up.
4. The PDF lock is cosmetic: export is `window.print()`, so a Free user can still print the page from the browser. Accept this, or make the print stylesheet render an upsell for Free.

## 8. Legal and business (not code, but blocks launch)

- `src/app/(public)/terminos-y-condiciones`: subscription, automatic renewal, price with IVA, how to cancel (portal, effective at period end), what happens on non-payment, the immediate start of the service and the withdrawal right (TRLGDCU art. 103), refunds policy.
- `src/app/(public)/politica-de-privacidad`: Stripe as a processor (payment data, billing address, tax ID), international transfers, retention of invoices (tax law: 4 to 6 years), usage records.
- `src/app/(public)/aviso-legal`: check the business identity data needed on invoices.
- Have a lawyer or gestor review the terms and the withdrawal-right wording before going live, and confirm the tax setup (alta in IAE, Modelo 303, OSS later).

## 9. Delivery: PRs and checks

Every change goes through a squash-merged PR from a branch. Put the checks below in each PR description.

| PR | Scope | Required review |
| --- | --- | --- |
| 1. Billing foundations | `CONTEXT.md`, ADR-0005, migration `0003`, `Settings`, `plans.py`, `db/billing.py`, `core/billing.py`, billing routes, webhook, `GET /billing/plan`, Stripe runbook in `docs/deploy/stripe.md`, env docs | `/code-review max` (migration, Settings), `/security-review` (webhook, payment input), `/simplify` |
| 2. Backend enforcement | Allowance in `analysis_transitions`, usage ledger in `complete()`, intake gates, worker truncation, history window and tool gates, dashboard, exports split, share gating, MCP gating, Clerk `user.deleted` webhook, regenerated `api.d.ts` | `/code-review max` (lifecycle, auth), `/security-review` (Clerk webhook), `/simplify` |
| 3. Frontend | Plan hook, account plan card, checkout and portal flows, gates on every screen, landing and demo copy, help, e2e | `/code-review`, `/simplify` |
| 4. Legal pages | Terms, privacy, legal notice | the user reads the diff |

PR 3 depends on PR 2's regenerated `api.d.ts`. Run `/eval-pipeline` only if a change ends up touching the agents or verdict code (none should).

Before declaring each PR done:

```bash
uv run --directory backend ruff check app evaluation tests
uv run --directory backend ruff format --check app evaluation tests
uv run --directory backend mypy
uv run --directory backend pytest tests --cov=app --cov-fail-under=80
pnpm --dir frontend lint && pnpm --dir frontend typecheck && pnpm --dir frontend format:check && pnpm --dir frontend test && pnpm --dir frontend build && pnpm --dir frontend e2e
```

Manual end-to-end check in Stripe test mode (after PR 3): sign up, use the 10 Free analyses, see the block, subscribe monthly with card `4242 4242 4242 4242` and with the 3DS card `4000 0027 6000 3184`, check the tax line and the invoice with a test NIF, switch to annual in the portal, cancel at period end, use `stripe trigger invoice.payment_failed` for `past_due`, delete the account and see the subscription cancelled in Stripe.
