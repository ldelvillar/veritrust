# Monitoring & alerting

Two layers:

1. **In-stack self-healing** (already wired in `docker-compose.yml`): every service
   has a healthcheck, `restart: unless-stopped` restarts crashed containers, and the
   `autoheal` sidecar restarts containers whose healthcheck fails while the process
   stays up (e.g. a hung Ollama). The worker's cron reaper fails orphaned `pending`
   rows so users never stare at an eternal spinner.
2. **External checks** (this doc): an uptime service emails you when the site or the
   API stops answering, and the logs show failed analyses.

## 1. Uptime checks (frontend + API readiness)

Any external checker works; UptimeRobot's free plan checks every 5 minutes and alerts
by email. Create two HTTPS monitors:

- `https://API_DOMAIN/healthz`: it returns 503 unless Postgres and Redis answer, so this
  one check covers the API process and its dependencies.
- `https://APP_DOMAIN`: the frontend behind Caddy.

The checker runs outside the server, so it also catches a dead VM, an expired
certificate or a DNS mistake.

## 2. Failed analyses

`/healthz` stays green when the pipeline itself breaks (a bad Mistral key, an evidence
source down), so look at the errors too. The backend and worker log one JSON line per
record in production (`LOG_FORMAT=json`); count the last day's errors:

```bash
cd ~/veritrust
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --since 24h backend worker | grep -c '"severity": "ERROR"'
```

An isolated failed analysis logs one ERROR; a broken pipeline logs a stream. Drop the
`-c` to read them. Nothing alerts on these automatically yet.

## 3. Disk space

Images, build cache, logs and backups all share the VM's disk:

```bash
df -h / && docker system df
```

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
which rebuilds images **on the VM** and competes with running analyses for CPU. Either avoid
pushing, or disable the workflow for the day:

```bash
gh workflow disable Deploy   # re-enable afterwards: gh workflow enable Deploy
```

## 5. CPU steal log (shared-vCPU hosts)

On a host that oversells vCPUs (e.g. Contabo), **steal** (`st`) is the share of time the
VM wanted a CPU but the hypervisor gave it to another tenant. Log it once a minute so you
can tell whether the provider is slowing analyses down. `crontab -e` and add:

```cron
* * * * * vmstat 55 2 | awk -v t="$(date -Is)" 'NR==2{for(i=1;i<=NF;i++)c[$i]=i} END{print t, "us=" $c["us"], "sy=" $c["sy"], "id=" $c["id"], "wa=" $c["wa"], "st=" $c["st"]}' >> ~/monitoring/cpu-steal.log 2>&1
```

Create the directory first with `mkdir -p ~/monitoring`. Each line is the average over the
55 s window that starts at its timestamp (`vmstat`'s second report; the first is since
boot), for example `2026-10-26T10:15:00+00:00 us=4 sy=1 id=95 wa=0 st=0`. Columns are
found by header name, so newer `vmstat` versions with extra columns still work. The log
grows ~30 MB a year, so it needs no rotation.

Daily summary (average and maximum steal, and how many minutes it was at 10% or more):

```bash
awk '{d=substr($1,1,10); split($6,s,"="); n[d]++; sum[d]+=s[2]; if(s[2]+0>mx[d]+0)mx[d]=s[2]; if(s[2]>=10)hi[d]++} END{for(d in n) print d, "minutes=" n[d], "avg_st=" sum[d]/n[d], "max_st=" mx[d]+0, "minutes_st_ge_10=" hi[d]+0}' ~/monitoring/cpu-steal.log | sort
```

Read `st` together with `us`/`sy`: steal only costs you time when the VM is busy (an
analysis or a build running). Sustained `st` above 10–20% under load means a noisy host;
open a ticket or move providers (see `ops.md` for the measured footprint to size the next VM).
