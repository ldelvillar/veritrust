# Production operations

All commands run on the VM unless noted otherwise.

## Hardening (one-time)

### Restrict SSH access

In GCP Console → VPC network → Firewall, edit the SSH rule (port 22) and set source IP to your own IP instead of `0.0.0.0/0`.

### Log rotation

Prevent Docker logs from growing unbounded. Edit `/etc/docker/daemon.json`:

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

The throughput ceiling is the single shared Ollama, **not** the worker count. Each analysis runs three Ollama models sequentially (`llama3`, `translategemma`, `llama3.2`) plus BioBERT, and the worker takes one job at a time (`WORKER_MAX_JOBS=1`) because the pipeline saturates CPU/Ollama — concurrency >1 only inflates per-job latency. A run is capped at `ANALYSIS_JOB_TIMEOUT_SECONDS` (600s); rows still `pending` after `ANALYSIS_STALE_AFTER_SECONDS` (900s) are reaped to `failed`.

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
