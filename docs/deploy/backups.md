# Database backups

Postgres data lives in the `postgres_data` Docker volume on the VM disk. If the disk fails or the VM is deleted, all analysis history is lost unless a dump exists. `pg_dump` writes the whole database to a SQL file you can restore from.

All commands run on the VM. Current directory does not matter — every path is absolute.

## 1. Run one backup manually first

Prove it works by hand before automating.

```bash
mkdir -p ~/backups

docker exec $(docker compose -f ~/veritrust/docker-compose.yml ps -q postgres) \
  pg_dump -U veritrust veritrust | gzip > ~/backups/test-backup.sql.gz

ls -lh ~/backups/
```

A non-empty `test-backup.sql.gz` means backups work. No password is needed because the dump runs inside the container, where local connections are trusted.

What each piece does:

| Part                                              | Meaning                                                                               |
| ------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `docker compose ... ps -q postgres`               | Prints the postgres container ID                                                      |
| `docker exec <id> pg_dump -U veritrust veritrust` | Runs `pg_dump` inside the container, as user `veritrust`, on the `veritrust` database |
| `\| gzip`                                         | Compresses the SQL stream                                                             |
| `> ~/backups/...sql.gz`                           | Writes it to a file                                                                   |

## 2. Automate with cron

`crontab -e` opens your personal schedule. Add this line:

```bash
0 3 * * * docker exec $(docker compose -f ~/veritrust/docker-compose.yml ps -q postgres) pg_dump -U veritrust veritrust | gzip > ~/backups/veritrust-$(date +\%Y\%m\%d).sql.gz 2>> ~/backups/backup.log && find ~/backups -name "*.sql.gz" -mtime +7 -delete
```

The schedule `0 3 * * *` means **every day at 03:00** (minute, hour, day-of-month, month, day-of-week).

Important details in that line:

- `$(date +\%Y\%m\%d)` names each file by date so backups don't overwrite each other. The `%` signs **must** be escaped as `\%` — cron treats a bare `%` as a newline, the #1 cause of silent backup failure.
- `2>> ~/backups/backup.log` captures errors to a log. Without it, a failing job is invisible.
- `find ~/backups ... -mtime +7 -delete` removes dumps older than 7 days. Adjust `+7` for a longer retention window.

## 3. Verify the cron job

```bash
crontab -l
```

Confirm the line is listed. To test immediately, temporarily change `0 3` to a minute from now, then check `~/backups/` for a dated file and `backup.log` for errors.

## 4. Restore from a backup

A backup you can't restore is useless — test this at least once.

```bash
gunzip -c ~/backups/veritrust-20260612.sql.gz | \
  docker exec -i $(docker compose -f ~/veritrust/docker-compose.yml ps -q postgres) \
  psql -U veritrust -d veritrust
```

`-i` keeps stdin open so the file pipes in. Use `psql` to restore, `pg_dump` to back up.

## Future: store backups off the VM

Backups currently sit on the same disk as the database, so a disk or VM loss takes them with it. The eventual fix is to push each dump to a GCS bucket (`gcloud` is already authenticated on the VM):

```bash
&& gsutil cp ~/backups/veritrust-$(date +\%Y\%m\%d).sql.gz gs://YOUR_BUCKET/veritrust-backups/
```

Append that to the cron line once a bucket exists.
