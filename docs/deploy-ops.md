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

Schedule a daily Postgres dump via crontab (`crontab -e`):

```bash
0 3 * * * docker exec $(docker compose -f ~/veritrust/docker-compose.yml ps -q postgres) \
  pg_dump -U veritrust veritrust | gzip \
  > ~/backups/veritrust-$(date +\%Y\%m\%d).sql.gz && \
  find ~/backups -name "*.sql.gz" -mtime +7 -delete
```

Create the backups directory first:

```bash
mkdir -p ~/backups
```

## Updating the app

Run from the VM:

```bash
cd ~/veritrust
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build --no-deps backend worker frontend
```

`--no-deps` avoids restarting Postgres, Redis, and Ollama unnecessarily.

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
