# Production operations

All commands run on the VM unless noted otherwise. First-time server setup: [vps-setup.md](vps-setup.md).

## Hardening (one-time)

### SSH, firewall, updates

Key-only SSH without root login, ufw allowing only 22/80/443, and unattended security
updates: [vps-setup.md](vps-setup.md) §2.

### Log rotation

`docker-compose.yml` already caps every service's logs (json-file, 20 MB × 3
files), so no action is needed for the stack itself. The daemon-level default
below only matters for containers started outside compose. Edit
`/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
```

Then restart Docker and recreate containers:

```bash
sudo systemctl restart docker
cd ~/veritrust
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Backups

See [backups.md](backups.md).

## Updating the app

Run from the VM:

```bash
cd ~/veritrust
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build --no-deps backend worker frontend
```

`--no-deps` avoids restarting Postgres, Redis, and Ollama unnecessarily.

Deploys never restart Caddy, so a `Caddyfile` change only applies after
`docker compose -f docker-compose.yml -f docker-compose.prod.yml restart caddy`.

## MCP server

The backend serves an MCP server at `https://$API_DOMAIN/mcp` (`MCP_RESOURCE_URL` is set from `API_DOMAIN` in `docker-compose.prod.yml`). One-time Clerk Dashboard setup:

- **OAuth applications → Settings → Client onboarding → Publish DCR support**: on, so MCP clients can register themselves (this also enforces the OAuth consent screen). **Publish CIMD support** can be enabled as well; it is in beta and Clerk support must unlock it.
- **OAuth applications → Settings → Generate access tokens as JWTs**: on (the default); the backend verifies tokens locally against the JWKS.

Users connect a client with, for example, `claude mcp add --transport http veritrust https://$API_DOMAIN/mcp`, then sign in with their VeriTrust account in the browser.

## REST API keys (Institución plan)

Institución customers call the REST API from their own servers with a Clerk API key (`ak_…`). The backend verifies it against Clerk's Backend API with `CLERK_SECRET_KEY` and treats the request as the key's user: same history, same per-user rate limit as the web app. Keys are issued by hand; the API Keys tab Clerk would add to the profile modal is hidden.

One-time Clerk Dashboard setup: **API keys → Enable API keys → Enable User API keys** (not Organization API keys: the backend rejects them). Until this is on, every `ak_…` request answers 500 `AUTH_MISCONFIGURED` and the backend logs `feature_not_enabled`.

### Issuing a key

The key belongs to the customer's VeriTrust user account, so the customer signs up first. Then create the key with the Backend API (the Dashboard only enables the feature), replacing `user_…` with their user ID from **Users** in the Dashboard:

```bash
curl -X POST https://api.clerk.com/v1/api_keys \
  -H "Authorization: Bearer $CLERK_SECRET_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme CMS", "subject": "user_…"}'
```

The response's `secret` (`ak_…`) is shown **only once**; send it to the customer over a secure channel. Keep its `id` to revoke it later:

```bash
curl -X POST https://api.clerk.com/v1/api_keys/$API_KEY_ID/revoke \
  -H "Authorization: Bearer $CLERK_SECRET_KEY" \
  -H "Content-Type: application/json" \
  -d '{"revocation_reason": "contract ended"}'
```

Successful verifications are cached in-process for 60 s, so a revoked key keeps working for up to a minute. List a user's keys with `GET https://api.clerk.com/v1/api_keys?subject=user_…`.

### How the customer calls the API

Submit content, then poll the analysis until its `status` leaves `pending` (`done` or `failed`):

```bash
curl -X POST https://$API_DOMAIN/analysis \
  -H "Authorization: Bearer ak_…" \
  -H "Content-Type: application/json" \
  -d '{"text": "La vitamina C cura el resfriado común."}'
# → {"status": "pending", "analysis_id": "…"}

curl https://$API_DOMAIN/analysis/$ANALYSIS_ID -H "Authorization: Bearer ak_…"
```

Send a URL instead with `{"url": "https://…", "source_type": "url"}`. An analysis takes a few minutes, so poll every few seconds; `POST /analysis` is limited to `RATE_LIMIT_MAX_REQUESTS` per `RATE_LIMIT_WINDOW_SECONDS` per user (429 `RATE_LIMIT`). An invalid, revoked or expired key answers 401 `INVALID_TOKEN`; 503 `SERVICE_UNAVAILABLE` means Clerk could not be reached, so retry.

## Billing (Stripe)

Pro is sold through Stripe Billing in EUR, IVA included (ADR-0005). The backend only creates Checkout and Customer Portal sessions; everything below is set up by hand in the Stripe Dashboard. Do it all in **test mode** first, then repeat steps 3 to 7 in **live mode** for production. Test-mode and live-mode keys are never mixed: test keys (`sk_test_…`) go in local `.env` files, live keys (`sk_live_…`) only in the server's `backend/.env` (see `env.md`).

1. **Account**: a Stripe account in Spain with EUR as the default currency. Under **Settings → Business → Public details**, set the terms of service URL to `https://$APP_DOMAIN/terminos-y-condiciones`; Checkout asks the customer to accept the terms and refuses to open without that URL.
2. **Stripe Tax** (**Tax → Settings**): add the Spain registration, set the origin address, and set the product tax code to the SaaS code that matches the audience (check Stripe's list; the personal-use SaaS code is the likely default). Add OSS later, once cross-border EU B2C sales get close to 10,000€/year.
3. **Product**: "VeriTrust Pro" with two prices, 29.00 EUR monthly and 290.00 EUR yearly, both with tax behaviour **inclusive**. Copy the price IDs (`price_…`) into `STRIPE_PRICE_PRO_MONTHLY` and `STRIPE_PRICE_PRO_YEARLY`. A Subscription on any other price never makes a user Pro, so never replace a price ID while Subscriptions still use it: move them to the new price first, or existing subscribers drop to Free.
4. **Customer Portal** (**Settings → Billing → Customer portal**): allow cancelling (at the end of the period), switching between the two Pro prices, updating the payment method and seeing invoice history. Disallow quantity changes.
5. **One subscription per customer** (**Settings → Checkout and Payment Links → Subscriptions**): turn on **Limit customers to one subscription**, so a customer who already pays is sent to the portal instead of a second Checkout. The backend also expires a customer's other open Checkout sessions when it opens a new one.
6. **Billing settings** (**Settings → Billing → Subscriptions and emails**): Smart Retries on, and **cancel the subscription** when all retries fail (that ends `past_due`, which keeps Pro while retries run). Turn on Stripe's customer emails for receipts, failed payments and upcoming renewals, in Spanish.
7. **Webhook** (**Developers → Webhooks → Add endpoint**): URL `https://$API_DOMAIN/billing/webhook`, API version `2026-09-30.endive` (the version pinned as `STRIPE_API_VERSION` in `backend/app/core/billing.py`), and these events:
   - `checkout.session.completed`
   - `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`
   - `invoice.paid`, `invoice.payment_failed`

   Copy the endpoint's signing secret (`whsec_…`) into `STRIPE_WEBHOOK_SECRET`. The secret key from **Developers → API keys** goes into `STRIPE_SECRET_KEY`.
8. **Local development**: `stripe listen --forward-to localhost:8000/billing/webhook` forwards test-mode events and prints a local `whsec_…` for `backend/.env`. `stripe trigger invoice.payment_failed` exercises `past_due`.

The four `STRIPE_*` variables are required: without them the backend refuses to start and `/healthz` answers 503. The webhook answers 400 to a request with a bad signature, and 5xx when handling fails, so Stripe retries it (**Developers → Webhooks → the endpoint** lists failed deliveries and can resend them). The backend logs each event's id and type, never its payload.

To check a user's Plan by hand:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec postgres \
  psql -U veritrust -d veritrust -c \
  "SELECT status, price_id, current_period_end FROM subscriptions WHERE user_id = 'user_…'"
```

## Capacity & scaling

The throughput ceiling is the single shared Ollama, **not** the worker count. Each analysis runs three Ollama models sequentially (`llama3`, `translategemma`, `llama3.2`), and the worker takes one job at a time (`WORKER_MAX_JOBS=1`) because the pipeline saturates CPU/Ollama — concurrency >1 only inflates per-job latency. A run is capped at `ANALYSIS_JOB_TIMEOUT_SECONDS` (600s). Rows `pending` for more than `ANALYSIS_STALE_AFTER_SECONDS` (300s) **whose arq job no longer exists** are reaped to `failed`; rows whose job is still queued or running are left alone, so a deep queue under concurrent traffic does not fail anyone's analysis prematurely.

**Memory budget (4 GB host, hosted LLM).** `docker-compose.prod.yml` caps each
service with `mem_limit` (worker 1g, postgres/backend 512m each, frontend/redis
384m each, caddy 128m, autoheal 32m; ~2.9 GB in total, 3–6× the measured peaks
below); a runaway container is OOM-killed and
restarted by its restart policy instead of triggering a VM-level OOM where the
kernel picks the victim. Redis's cap must stay above its 256 MB `maxmemory`. The
`ollama` profile adds a 9g cap that only fits a 16 GB host (the old e2-standard-4).
Ollama runs with `OLLAMA_MAX_LOADED_MODELS=1` — the
pipeline uses one model at a time, so peak RAM tracks the largest model (~6 GB
for `llama3` at 8k ctx) at the cost of a model swap between stages. If you
change the machine type or the models, revisit both.

**Measured footprint with a hosted LLM (19 Oct 2026).** With `LLM_PROVIDER=mistral` and no
`ollama` container, the stack needs well under 1 GB at runtime; the one-off peak is the image
build. Measured on Docker Desktop (8 GB VM, 16 CPUs) with the base compose file (no Caddy, no
`mem_limit`s), `WORKER_MAX_JOBS=1`, one analysis of each kind run back to back, and 320 page
loads over 8 concurrent connections. Peaks are each container's cgroup `memory.peak` since start:

| Service | Idle | Peak | Peak CPU |
| --- | --- | --- | --- |
| worker | ~135 MiB | 250 MiB | ~200% (PDF parsing) |
| backend | ~145 MiB | 204 MiB¹ | ~100% |
| frontend | ~45 MiB | 105 MiB | ~75% |
| postgres | ~40 MiB | 85 MiB | ~30% |
| redis | ~11 MiB | 18 MiB | — |
| autoheal | ~8 MiB | 14 MiB | — |
| **Total** | **~385 MiB** | **~675 MiB** | |

¹ Includes the ~50 MiB test driver that ran inside the backend container to enqueue the jobs.

| Run | Input | Wall time |
| --- | --- | --- |
| Text | 3 claims, 260 characters | 21 s |
| URL | `es.wikipedia.org/wiki/Vacuna`, cut to 10,000 characters | 34 s |
| PDF | CIMA ficha técnica, 13 pages, 200 KB | 29 s |
| PDF | EMA Comirnaty product information, 381 pages, 2.4 MB | 50 s |

- **Build:** `docker compose build --no-cache backend frontend` with the stack running raised
  the VM's used memory from 1.2 GB to 2.85 GB (+1.6 GB) for ~2.5 minutes. Images: backend
  333 MB, frontend 222 MB; the build cache grows with every rebuild, so prune it on small disks.
- **Sizing:** OS and Docker (~0.4 GB) + stack (~0.7 GB) + build (~1.6 GB) ≈ 2.7 GB, so a
  4 GB host fits with the caps above and 2 GB of swap as headroom for builds; 8 GB has room
  to raise `WORKER_MAX_JOBS`.
- **Not covered:** a 10 MB PDF (the upload limit), Caddy (~30–50 MiB, not measured), concurrent
  jobs, and Postgres growth as data accrues (shared buffers default to 128 MB).

The judge, `ministral-3:14b` (the `Settings` default; see `docs/experiments/2026-10.md`,
2026-10-01), needs ~11 GB loaded at 8k ctx: more than Ollama's 9g cap above, and on
CPU about a minute per claim. A production VM for it needs a 16 GB GPU and a higher
Ollama cap; the budget above is the e2-standard-4's and must be redone for it. Setting
`OLLAMA_JUDGE_MODEL=llama3.2` fits the old budget, but that judge calls most false
claims with a firm verdict `verdadera`.

What this means for scaling:

- **Adding worker replicas alone does not raise throughput** — they contend on the same Ollama container (CPU-only in this stack), and three models per run thrash a CPU instance. Scale **Ollama** first (a GPU host, or a separate Ollama per worker), _then_ add workers behind it.
- The per-user rate limit (`RATE_LIMIT_MAX_REQUESTS`/`RATE_LIMIT_WINDOW_SECONDS`, default 5/60s) is abuse control, not global throughput — it is per-user, so a few users can still fill the single queue for everyone.

Watch the queue backlog as the leading indicator — latency degrades by backlog long before any request fails. arq keeps queued jobs in the `arq:queue` sorted set in Redis:

```bash
# Number of jobs waiting in the queue
docker compose exec redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning ZCARD arq:queue
```

## Useful commands

```bash
# View logs
docker compose logs -f worker     # pipeline logs
docker compose logs -f backend    # API logs
docker compose logs -f caddy      # TLS / proxy logs

# Resource usage
docker stats

# Restart a single service
docker compose restart worker

# Full restart
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```
