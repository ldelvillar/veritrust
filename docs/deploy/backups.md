# Database backups

Postgres data lives in the `postgres_data` Docker volume on the VM disk. If the disk fails or the VM is deleted, all analysis history is lost unless a dump exists. `pg_dump` writes the whole database to a file you can restore from.

All commands run on the VM. Current directory does not matter — every path is absolute.

## 1. Run one backup manually first

Prove it works by hand before automating.

```bash
mkdir -p ~/backups

docker exec $(docker compose -f ~/veritrust/docker-compose.yml ps -q postgres) \
  pg_dump -Fc -U veritrust veritrust > ~/backups/test-backup.dump

ls -lh ~/backups/
```

A `test-backup.dump` of at least several KB means backups work. No password is needed because the dump runs inside the container, where local connections are trusted.

What each piece does:

| Part                                              | Meaning                                                                               |
| ------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `docker compose ... ps -q postgres`               | Prints the postgres container ID                                                      |
| `docker exec <id> pg_dump -U veritrust veritrust` | Runs `pg_dump` inside the container, as user `veritrust`, on the `veritrust` database |
| `-Fc`                                             | Custom format: compressed, restored with `pg_restore`                                 |
| `> ~/backups/test-backup.dump`                    | Writes it to a file                                                                   |

## 2. Automate with cron

`crontab -e` opens your personal schedule (as `deploy`, not with `sudo`). Add this line:

```cron
0 3 * * * docker exec $(docker compose -f ~/veritrust/docker-compose.yml ps -q postgres) pg_dump -Fc -U veritrust veritrust > ~/backups/veritrust-$(date +\%Y\%m\%d).dump 2>> ~/backups/backup.log && find ~/backups -name "veritrust-*.dump" -mtime +7 -delete
```

The schedule `0 3 * * *` means **every day at 03:00** server time (minute, hour, day-of-month, month, day-of-week).

Important details in that line:

- `$(date +\%Y\%m\%d)` names each file by date so backups don't overwrite each other. The `%` signs **must** be escaped as `\%` — cron treats a bare `%` as a newline, the #1 cause of silent backup failure.
- `2>> ~/backups/backup.log` captures `pg_dump`'s errors. There is no pipe, so a failed dump is logged and `&&` skips the cleanup; a `| gzip` here would hide both.
- `find ~/backups ... -mtime +7 -delete` removes dumps older than 7 days. Adjust `+7` for a longer retention window. The deploy workflow's `pre-deploy-*.dump` files have their own retention.

## 3. Verify the cron job

Make cron run it once, a couple of minutes from now:

1. `date` shows the server time; say it is 10:42.
2. `crontab -e` and change `0 3` to `44 10`.
3. After 10:44, `ls -lh ~/backups/` must show a `veritrust-YYYYMMDD.dump` of several KB or more, and `cat ~/backups/backup.log` must print nothing.
4. `crontab -e` again and put back `0 3`; `crontab -l` confirms it.

## 4. Restore from a backup

A backup you can't restore is useless. Test one at least once, into a throwaway database so production is untouched:

```bash
cid=$(docker compose -f ~/veritrust/docker-compose.yml ps -q postgres)
f=$(ls -t ~/backups/veritrust-*.dump | head -1); echo "$f"
docker exec $cid createdb -U veritrust restore_test
docker exec -i $cid pg_restore -U veritrust -d restore_test --no-owner < "$f"
for db in restore_test veritrust; do
  docker exec $cid psql -U veritrust -d $db -tAc "SELECT '$db', (SELECT count(*) FROM schema_migrations), (SELECT count(*) FROM analysis_history), (SELECT count(*) FROM analysis_feedback)"
done
docker exec $cid dropdb -U veritrust restore_test
```

It restores the newest nightly dump. `pg_restore` must finish without errors, and the two lines (migrations, analyses, feedback) must match, or production's be slightly higher if analyses finished after the dump. `-i` keeps stdin open so the file pipes in.

To actually restore production from a nightly dump, follow the steps in section 5 with that dump instead of a `pre-deploy-*` one: stop the writers, `pg_restore --clean --if-exists --create`, then start them again with `docker compose -f ~/veritrust/docker-compose.yml start backend worker`. Everything written since the dump is lost.

## 5. Undo a bad migration

Every deploy dumps the database to `~/backups/pre-deploy-<timestamp>.dump` before the `migrate` service runs (see `.github/workflows/deploy.yml`).

If a migration **fails**, its transaction rolls back and the deploy goes red. Compose has already replaced the API and worker containers but won't start them, so they stay down until a fixed or reverted commit deploys. There is nothing to restore.

If a migration **succeeds but damages data or schema**, restore the dump taken just before the deploy that ran it (later dumps already contain the damage). Everything written since that deploy is lost.

1. Stop the writers, so nothing writes during the restore and the new code never runs against the old schema:

   ```bash
   docker compose -f ~/veritrust/docker-compose.yml stop backend worker
   ```

2. Restore the dump. `--create` drops and recreates the whole database, so tables the migration created (which aren't in the dump) go too; it connects to `postgres` because `veritrust` is the database being dropped:

   ```bash
   docker exec -i $(docker compose -f ~/veritrust/docker-compose.yml ps -q postgres) \
     pg_restore -U veritrust -d postgres --clean --if-exists --create < ~/backups/pre-deploy-20261025-120000.dump
   ```

3. On your machine, `git revert` the commit that added the migration and push to `main`. The restored `schema_migrations` no longer lists that migration, so the runner accepts the file being gone, and the deploy starts the API and worker again.

The dump is in `pg_dump`'s custom format (compressed, includes `schema_migrations`), so restore it with `pg_restore`, not `psql`.

## Future: store backups off the VM

Backups currently sit on the same disk as the database, so a disk or VM loss takes them with it. The fix is to copy each dump to storage at a different provider (the destination is not chosen yet) by appending the upload command to the cron line.
