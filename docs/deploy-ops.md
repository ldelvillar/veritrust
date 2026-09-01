# Production operations

All commands run on the VM unless noted otherwise.

## Hardening (one-time)

### Restrict SSH access

In GCP Console → VPC network → Firewall, edit the SSH rule (port 22) and set source IP to your own IP instead of `0.0.0.0/0`.

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

### Automatic security updates

```bash
sudo apt-get install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

## Backups

See [deploy-backups.md](deploy-backups.md).

## Updating the app

Run from the VM:

```bash
cd ~/veritrust
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build --no-deps backend worker frontend
```

`--no-deps` avoids restarting Postgres, Redis, and Ollama unnecessarily.

## Capacity & scaling

The throughput ceiling is the single shared Ollama, **not** the worker count. Each analysis runs three Ollama models sequentially (`llama3`, `translategemma`, `llama3.2`), and the worker takes one job at a time (`WORKER_MAX_JOBS=1`) because the pipeline saturates CPU/Ollama — concurrency >1 only inflates per-job latency. A run is capped at `ANALYSIS_JOB_TIMEOUT_SECONDS` (600s). Rows `pending` for more than `ANALYSIS_STALE_AFTER_SECONDS` (300s) **whose arq job no longer exists** are reaped to `failed`; rows whose job is still queued or running are left alone, so a deep queue under concurrent traffic does not fail anyone's analysis prematurely.

**Memory budget (e2-standard-4, 16 GB).** `docker-compose.prod.yml` caps each
service with `mem_limit` (ollama 9g, worker 3g, postgres/backend 1g each,
frontend 768m, redis 512m, caddy 256m); a runaway container is OOM-killed and
restarted by its restart policy instead of triggering a VM-level OOM where the
kernel picks the victim. Ollama runs with `OLLAMA_MAX_LOADED_MODELS=1` — the
pipeline uses one model at a time, so peak RAM tracks the largest model (~6 GB
for `llama3` at 8k ctx) at the cost of a model swap between stages. If you
change the machine type or the models, revisit both.

What this means for scaling:

- **Adding worker replicas alone does not raise throughput** — they contend on the same Ollama container (CPU-only in this stack), and three models per run thrash a CPU instance. Scale **Ollama** first (a GPU host, or a separate Ollama per worker), *then* add workers behind it.
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
