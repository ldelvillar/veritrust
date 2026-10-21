# Production .env

The stack reads three env files on the server, all in `~/veritrust`: the root `.env`
(compose interpolation), `backend/.env` (backend, worker, migrate) and `frontend/.env`
(frontend). The source of truth is your password manager; the server holds the only
other copy, and deploys never touch it. Production values differ from local development
ones, so never sync one from the other, and never commit an `.env` file.

## What goes in each file

Generate the two passwords on the server with `openssl rand -hex 32`; hex only, because
they end up inside connection URLs.

Root `.env`:

```dotenv
POSTGRES_USER=veritrust
POSTGRES_PASSWORD=<hex>
POSTGRES_DB=veritrust
REDIS_PASSWORD=<hex>
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_…
APP_DOMAIN=veritrust.es
API_DOMAIN=api.veritrust.es
ACME_EMAIL=<address for Let's Encrypt notices>
```

`backend/.env`, starting from an empty file rather than `backend/.env.example` (which
sets `LLM_PROVIDER=ollama`). The compose files already set the database and Redis URLs,
CORS, `APP_BASE_URL`, `MCP_RESOURCE_URL` and `LOG_FORMAT`; every other setting keeps its
default:

```dotenv
LLM_PROVIDER=mistral
MISTRAL_API_KEY=…
CLERK_JWKS_URL=https://<Clerk Frontend API host>/.well-known/jwks.json
CLERK_ISSUER=https://<Clerk Frontend API host>
CLERK_AUDIENCE=<the aud claim of the Production instance's session tokens>
CLERK_SECRET_KEY=sk_live_…
RESEND_API_KEY=…
RESEND_FROM_EMAIL=…
CONTACT_TO_EMAIL=<inbox for the demo form>
```

`frontend/.env`:

```dotenv
NEXT_PUBLIC_API_URL=https://api.veritrust.es
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_…
CLERK_SECRET_KEY=sk_live_…
```

The Clerk values come from the **Production** instance (Dashboard → API keys); its
Frontend API URL is the issuer. Then restrict the files to their owner:

```bash
chmod 600 ~/veritrust/.env ~/veritrust/backend/.env ~/veritrust/frontend/.env
```

## Changing a value

Edit the entry in the password manager first, then the server copy:

```bash
ssh veritrust
cd ~/veritrust && nano backend/.env
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

`up -d` recreates the containers whose env changed. `--build` matters for the root
`.env`: `NEXT_PUBLIC_*` values and `API_DOMAIN` are baked into the frontend at build time.

## Restoring the files

On a new server, recreate them from the password manager with `nano`, or upload them
from files kept **outside the repo**:

```bash
scp prod.env veritrust:~/veritrust/.env
scp backend.prod.env veritrust:~/veritrust/backend/.env
scp frontend.prod.env veritrust:~/veritrust/frontend/.env
ssh veritrust "chmod 600 ~/veritrust/.env ~/veritrust/backend/.env ~/veritrust/frontend/.env"
```
