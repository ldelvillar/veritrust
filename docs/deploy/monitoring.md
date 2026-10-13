# Monitoring & alerting

Two layers:

1. **In-stack self-healing** (already wired in `docker-compose.yml`): every service
   has a healthcheck, `restart: unless-stopped` restarts crashed containers, and the
   `autoheal` sidecar restarts containers whose healthcheck fails while the process
   stays up (e.g. a hung Ollama). The worker's cron reaper fails orphaned `pending`
   rows so users never stare at an eternal spinner.
2. **GCP Cloud Monitoring** (this doc): uptime checks + email alerts so a dead site
   or a failing worker pages you instead of relying on someone watching logs.

Run these once from your local machine with `gcloud` pointed at the project.
Replace `PROJECT_ID`, `APP_DOMAIN`, `API_DOMAIN`, and `you@example.com`.

## 1. Notification channel (email)

```bash
gcloud beta monitoring channels create \
  --display-name="VeriTrust alerts" \
  --type=email \
  --channel-labels=email_address=you@example.com
```

Note the channel name it prints (`projects/PROJECT_ID/notificationChannels/NNN`).

## 2. Uptime checks (frontend + API readiness)

`/healthz` returns 503 unless Postgres and Redis answer, so this single check covers
the API process and its dependencies:

```bash
gcloud monitoring uptime create veritrust-api \
  --resource-type=uptime-url \
  --resource-labels=host=API_DOMAIN,project_id=PROJECT_ID \
  --protocol=https --port=443 --path=/healthz \
  --period=1 --timeout=10

gcloud monitoring uptime create veritrust-app \
  --resource-type=uptime-url \
  --resource-labels=host=APP_DOMAIN,project_id=PROJECT_ID \
  --protocol=https --port=443 --path=/ \
  --period=1 --timeout=10
```

Then in Console → Monitoring → Uptime checks, open each check and add an alert
policy bound to the email channel (one click; doing it via CLI requires a JSON
policy file and offers nothing extra here).

## 3. Worker failure alerts (Ops Agent + log-based metric)

On the VM, install the Ops Agent and ship container logs:

```bash
curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
sudo bash add-google-cloud-ops-agent-repo.sh --also-install
```

Configure it to tail Docker's JSON log files (`/etc/google-cloud-ops-agent/config.yaml`):

```yaml
logging:
  receivers:
    veritrust_containers:
      type: files
      include_paths:
        - /var/lib/docker/containers/*/*-json.log
  processors:
    parse_docker:
      type: parse_json
  service:
    pipelines:
      containers:
        receivers: [veritrust_containers]
        processors: [parse_docker]
```

```bash
sudo systemctl restart google-cloud-ops-agent
```

The backend and worker emit one JSON line per log record in production
(`LOG_FORMAT=json`, set in `docker-compose.prod.yml`), so a substring filter on the
docker envelope is stable. Create a metric counting worker/API errors:

```bash
gcloud logging metrics create veritrust_app_errors \
  --description="Lineas de log ERROR/CRITICAL de backend y worker" \
  --log-filter='resource.type="gce_instance" AND jsonPayload.log:"\"severity\": \"ERROR\""'
```

In Console → Monitoring → Alerting, create a policy on
`logging/user/veritrust_app_errors` (threshold: above 3 in 5 minutes is a sane
start — an isolated failed analysis logs one ERROR; a broken pipeline logs a
stream) and bind it to the email channel.

## 4. Demo-day quick checks

```bash
# Everything Up and (healthy)?
docker compose ps

# Queue backlog — latency degrades by backlog long before anything fails
docker compose exec redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning ZCARD arq:queue

# Who is eating CPU/RAM right now
docker stats --no-stream
```

Freeze deploys while presenting: a push to `main` triggers the Deploy workflow,
which rebuilds images **on the VM** and competes with Ollama for CPU. Either avoid
pushing, or disable the workflow for the day:

```bash
gh workflow disable Deploy   # re-enable afterwards: gh workflow enable Deploy
```
