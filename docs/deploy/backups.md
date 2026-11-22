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

A `test-backup.dump` of at least several KB means backups work. No password is needed because the dump runs inside the container, where local connections are trusted. Then delete it with `rm ~/backups/test-backup.dump`: no cleanup rule matches its name, so it would keep a full plaintext copy of the database forever.

What each piece does:

| Part                                              | Meaning                                                                               |
| ------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `docker compose ... ps -q postgres`               | Prints the postgres container ID                                                      |
| `docker exec <id> pg_dump -U veritrust veritrust` | Runs `pg_dump` inside the container, as user `veritrust`, on the `veritrust` database |
| `-Fc`                                             | Custom format: compressed, restored with `pg_restore`                                 |
| `> ~/backups/test-backup.dump`                    | Writes it to a file                                                                   |

## 2. Automate with cron

Each dump is also encrypted with [age](https://github.com/FiloSottile/age) to a public key, so the copies that leave the VM are unreadable without the private key, which never touches the server. Create the key pair once on your workstation:

```powershell
age-keygen | age -p -a -o $env:USERPROFILE\.age\veritrust-backup.key.age
```

It prints the public key (`age1…`) and asks for a passphrase; the unprotected private key is never written to disk. Keep the passphrase and the contents of `veritrust-backup.key.age` in your password manager: losing either makes every encrypted backup unreadable. Then on the VM:

```bash
sudo apt install -y age
mkdir -p ~/.config/age && echo 'age1…' > ~/.config/age/backup-recipients.txt
```

`crontab -e` opens your personal schedule (as `deploy`, not with `sudo`). Add this line:

```cron
0 3 * * * f=$HOME/backups/veritrust-$(date +\%Y\%m\%d).dump; docker exec $(docker compose -f ~/veritrust/docker-compose.yml ps -q postgres) pg_dump -Fc -U veritrust veritrust > $f 2>> ~/backups/backup.log && age -R ~/.config/age/backup-recipients.txt -o $f.age $f 2>> ~/backups/backup.log && find ~/backups -name "veritrust-*.dump*" -mtime +7 -delete; find ~/backups -name "pre-deploy-*.dump" -mtime +27 -delete
```

The schedule `0 3 * * *` means **every day at 03:00** server time (minute, hour, day-of-month, month, day-of-week).

Important details in that line:

- `$(date +\%Y\%m\%d)` names each file by date so backups don't overwrite each other. The `%` signs **must** be escaped as `\%` — cron treats a bare `%` as a newline, the #1 cause of silent backup failure.
- `2>> ~/backups/backup.log` captures `pg_dump`'s and `age`'s errors. There is no pipe, so a failed dump is logged and `&&` skips the encryption and cleanup; a `| gzip` here would hide both. Skipping the cleanup is deliberate: a dump that keeps failing must not also delete the last good backups.
- `age -R ... -o $f.age $f` writes an encrypted `veritrust-YYYYMMDD.dump.age` next to the plain dump. The plain one stays on the VM for the restores in sections 4 and 5; only the `.age` copy leaves it.
- `find ~/backups ... -mtime +7 -delete` removes dumps older than 7 days, plain and encrypted. Adjust `+7` for a longer retention window, up to `+27` (see the next point).
- `find ~/backups -name "pre-deploy-*.dump" -mtime +27 -delete` removes the deploy workflow's dumps once they are 28 full days old. The workflow only keeps the newest 10, so without this rule a rarely deployed server would keep them for months. It runs even when the backup fails (`;`, not `&&`). The privacy policy says backups rotate on a cycle of about a month, so keep both limits at `+27` or below.

## 3. Verify the cron job

Make cron run it once, a couple of minutes from now:

1. `date` shows the server time; say it is 10:42.
2. `crontab -e` and change `0 3` to `44 10`.
3. After 10:44, `ls -lh ~/backups/` must show a `veritrust-YYYYMMDD.dump` of several KB or more and a slightly larger `veritrust-YYYYMMDD.dump.age`, and `cat ~/backups/backup.log` must print nothing.
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

To actually restore production from a nightly dump, follow the steps in section 5 with that dump instead of a `pre-deploy-*` one: stop the writers, save the record of deleted accounts (section 5, step 2), `pg_restore --clean --if-exists --create`, re-apply the erasures (section 5, step 4), then start them again with `docker compose -f ~/veritrust/docker-compose.yml start backend worker`. Everything written since the dump is lost.

## 5. Undo a bad migration

Every deploy dumps the database to `~/backups/pre-deploy-<timestamp>.dump` before the `migrate` service runs (see `.github/workflows/deploy.yml`), and so does the manual update in [ops.md](ops.md#updating-the-app).

If a migration **fails**, its transaction rolls back and the deploy goes red. Compose has already replaced the API and worker containers but won't start them, so they stay down until a fixed or reverted commit deploys. There is nothing to restore.

If a migration **succeeds but damages data or schema**, restore the dump taken just before the deploy that ran it (later dumps already contain the damage). Never restore a `pre-deploy-*.partial.dump`; it is an interrupted dump. Everything written since that deploy is lost.

1. Stop the writers, so nothing writes during the restore and the new code never runs against the old schema:

   ```bash
   docker compose -f ~/veritrust/docker-compose.yml stop backend worker
   ```

2. Save the record of deleted accounts. The `user.deleted` webhook writes every deleted account to `deleted_users`, and the worker keeps each one for 35 days, longer than any dump is kept. The restore replaces that table with the dump's older copy, so copy it out of the live database first:

   ```bash
   docker exec $(docker compose -f ~/veritrust/docker-compose.yml ps -q postgres) \
     pg_dump -U veritrust -d veritrust --data-only -t public.deleted_users --inserts --on-conflict-do-nothing > ~/backups/deleted-users.sql
   ```

   If the live database can't be read (the disk or the VM is gone), skip this step and use the fallback in step 4.

3. Restore the dump. `--create` drops and recreates the whole database, so tables the migration created (which aren't in the dump) go too; it connects to `postgres` because `veritrust` is the database being dropped:

   ```bash
   docker exec -i $(docker compose -f ~/veritrust/docker-compose.yml ps -q postgres) \
     pg_restore -U veritrust -d postgres --clean --if-exists --create < ~/backups/pre-deploy-20261025-120000.dump
   ```

4. Re-apply the erasures. The dump can hold users who deleted their account after it was taken, and the privacy policy promises that a restore applies their erasures again. Load the saved record into the restored database, delete the rows of every account in it from the same tables the webhook clears, then delete the saved file, which no cleanup rule matches:

   ```bash
   vt() { docker exec -i $(docker compose -f ~/veritrust/docker-compose.yml ps -q postgres) psql -U veritrust -d veritrust -v ON_ERROR_STOP=1 "$@"; }
   vt < ~/backups/deleted-users.sql
   for t in analysis_history billing_customers subscriptions usage_events; do vt -c "DELETE FROM $t WHERE user_id IN (SELECT user_id FROM deleted_users)"; done
   rm ~/backups/deleted-users.sql
   ```

   Their Stripe subscriptions were already cancelled when they deleted their account. **Fallback**, when step 2 was skipped, the dump is older than 35 days (a failing backup cron skips its cleanup), or the restored database has no `deleted_users` table (a dump from before migration `0005`): list the restored user IDs with `vt -c "SELECT user_id FROM analysis_history UNION SELECT user_id FROM billing_customers"`, check each in the Clerk Dashboard (**Users**; a deleted user is gone), and run the same `DELETE`s with `WHERE user_id = ANY('{user_a,user_b}')`, listing the IDs Clerk no longer has.

5. On your machine, `git revert` the commit that added the migration and push to `main`. The restored `schema_migrations` no longer lists that migration, so the runner accepts the file being gone, and the deploy starts the API and worker again.

The dump is in `pg_dump`'s custom format (compressed, includes `schema_migrations`), so restore it with `pg_restore`, not `psql`.

## Off-site copies

A disk or VM loss takes the local dumps with it, so the encrypted `.age` copies also live off the VM. For now a scheduled job on a workstation (set up as in [Setting up the pull](#setting-up-the-pull-on-a-workstation)) pulls them daily at 9:00 local time with `scp -p` into a staging folder and moves them into place only once the pull succeeded (`-p` keeps each file's original date, which the cleanup below relies on); it needs the SSH key loaded in the agent (`ssh-add`), since a passphrase prompt fails under `BatchMode`. Before pilot data accrues, replace it with an upload of the same files to an EU bucket at another provider, appended to the cron line.

Off-site copies are kept for **28 days**, in line with the privacy policy's backup cycle of about a month, so the same scheduled task (and later the bucket's lifecycle rule) must delete `.age` files older than that; the Windows job runs this after each successful pull (the Linux job runs the `find` equivalent, in the setup below):

```powershell
Get-ChildItem <folder> -Filter 'veritrust-*.dump.age' | Where-Object LastWriteTime -lt (Get-Date).AddDays(-28) | Remove-Item
```

To restore from an off-site copy, decrypt it on the workstation (it asks for the passphrase), then copy it to the VM and restore it as in section 4:

```powershell
age -d -i $env:USERPROFILE\.age\veritrust-backup.key.age -o veritrust.dump veritrust-YYYYMMDD.dump.age
scp veritrust.dump veritrust:/tmp/veritrust.dump
```

On Linux, the first line is `(umask 077; age -d -i ~/.age/veritrust-backup.key.age -o veritrust.dump veritrust-YYYYMMDD.dump.age)`, with the key copied from your password manager to `~/.age/`; the subshell's `umask 077` keeps the decrypted dump readable by you alone without changing your shell's umask.

Once the restore is done, delete both decrypted copies (`Remove-Item veritrust.dump`, or `rm veritrust.dump` on Linux, then `ssh veritrust rm /tmp/veritrust.dump`): no cleanup rule matches them.

### Setting up the pull on a workstation

The workstation doesn't need to be always on: the job catches up at the next login after a missed 9:00. It must still run at least once every **7 days**, because the VM deletes older dumps; a longer gap loses those days off-site. The pulled files stay encrypted, so the workstation needs neither `age` nor the backup key unless you also restore from it.

1. Give it SSH access as in [vps-setup.md section 1](vps-setup.md#adding-a-workstation-later): its own key, authorized from a machine that already has access, and the `veritrust` alias.
2. Load the key into the agent, then connect once by hand to accept the host key (`BatchMode` can't answer the fingerprint prompt): `ssh-add`, then `ssh veritrust true`.
3. If you're moving the job from another workstation, create the folder the job uses, `%USERPROFILE%\veritrust-backups` on Windows (`New-Item -ItemType Directory -Force "$env:USERPROFILE\veritrust-backups"`) or `~/veritrust-backups` on Linux (`mkdir -p ~/veritrust-backups`), and copy the existing `.age` files from the previous workstation's folder into it, to keep the 28-day history, with a copy that keeps their modified dates, which the cleanup reads: Explorer or `Copy-Item` on Windows, `cp -p`, `scp -p` or `rsync -t` on Linux (plain `cp` or `scp` resets them to now, so old copies outlive the 28 days). Check the dates in the new folder afterwards.
4. Create the job (below), run it once, and check that the newest `.age` file arrived with the VM's early-morning date, not the time of the pull.
5. On the previous workstation, disable or delete its job.

**Windows.** The agent service ships disabled, so first enable it in an admin PowerShell: `Set-Service ssh-agent -StartupType Automatic; Start-Service ssh-agent`. It keeps added keys across reboots, so `ssh-add` is needed once. Then, as your user:

```powershell
$script = "$env:USERPROFILE\veritrust-backup-pull.ps1"
Set-Content $script @'
$dir = "$env:USERPROFILE\veritrust-backups"
$stage = "$dir\.incoming"
New-Item -ItemType Directory -Force $dir | Out-Null
foreach ($try in 1..8) {
    Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue
    New-Item -ItemType Directory $stage | Out-Null
    scp -p -o BatchMode=yes -o ConnectTimeout=30 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 'veritrust:backups/veritrust-*.dump.age' "$stage"
    if ($LASTEXITCODE -eq 0) {
        Move-Item "$stage\*" $dir -Force
        Remove-Item $stage
        Get-ChildItem $dir -Filter 'veritrust-*.dump.age' | Where-Object LastWriteTime -lt (Get-Date).AddDays(-28) | Remove-Item
        exit 0
    }
    if ($try -lt 8) { Start-Sleep -Seconds 900 }
}
Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue
exit 1
'@
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Daily -At 9:00
$trigger.StartBoundary = (Get-Date '09:00').ToString('s')
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 3)
Register-ScheduledTask -TaskName 'VeriTrust backup pull' -Action $action -Trigger $trigger -Settings $settings -Force
Start-ScheduledTask -TaskName 'VeriTrust backup pull'
```

- The script pulls into `.incoming` and moves the files into place only after scp succeeds, so a run cut off mid-file (sleep, timeout, time limit) never truncates a good copy; the next attempt starts from an empty `.incoming`.
- It retries a failed pull every 15 minutes for up to 2 hours (the network may not be up yet at a catch-up run), and deletes old copies only after a successful pull, so a broken pull never empties the folder; the SSH timeouts end an attempt stuck on a dead connection (a laptop that slept mid-transfer) within about 90 seconds, and `-ExecutionTimeLimit` stops the whole run after 3 hours, so it can't block the next day's start.
- The `StartBoundary` line stores 9:00 without a UTC offset, so the task follows local time through daylight saving; without it, the trigger is a fixed UTC time.
- `-StartWhenAvailable` runs a missed 9:00 as soon as the machine is on; the battery switches stop a laptop on battery from skipping the day; `-Force` replaces an existing task of the same name.
- The task runs only while you're logged in, since it needs your loaded key.
- Check it with `Get-ScheduledTaskInfo -TaskName 'VeriTrust backup pull'`: `LastTaskResult` is `0` on success and `1` when every attempt failed; `267009` only means it's still running, which lasts up to 2 hours while it retries; any other code means the run was stopped, for example by the 3-hour limit, so treat it as a failed pull.

**Linux.** Use a systemd user timer (systemd 244 or later, for `Restart=` on a one-shot service): cron skips a run the machine was off for, while `Persistent=true` runs it at the next login. Create the pull script:

```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/veritrust-backup-pull <<'EOF'
#!/bin/sh
set -eu
dir="$HOME/veritrust-backups"
stage="$dir/.incoming"
mkdir -p "$dir"
rm -rf "$stage"
mkdir "$stage"
scp -p -o BatchMode=yes -o ConnectTimeout=30 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 'veritrust:backups/veritrust-*.dump.age' "$stage/"
mv -f "$stage"/*.dump.age "$dir/"
rmdir "$stage"
find "$dir" -maxdepth 1 -name 'veritrust-*.dump.age' -mtime +27 -delete
EOF
chmod +x ~/.local/bin/veritrust-backup-pull
```

Then `~/.config/systemd/user/veritrust-backup-pull.service`:

```ini
[Unit]
Description=Pull the VeriTrust off-site backups

[Service]
Type=oneshot
ExecStart=%h/.local/bin/veritrust-backup-pull
TimeoutStartSec=30min
Restart=on-failure
RestartSec=15min
```

and `~/.config/systemd/user/veritrust-backup-pull.timer`:

```ini
[Unit]
Description=Daily VeriTrust off-site backup pull

[Timer]
OnCalendar=*-*-* 09:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now veritrust-backup-pull.timer
systemctl --user start veritrust-backup-pull.service
journalctl --user -u veritrust-backup-pull.service -n 20
```

- As on Windows, the script pulls into `.incoming` and moves the files into place only after scp succeeds (`set -e` stops at the first failure), so an interrupted run never truncates a good copy and a failed one never runs the cleanup.
- `find -mtime +27` matches files at least 28 days old, the same cutoff as the Windows cleanup; `-maxdepth 1` keeps it out of `.incoming`.
- The service reaches your key through the agent your desktop session exports: `systemctl --user show-environment | grep SSH_AUTH_SOCK` must print a socket. If it prints nothing, add `systemctl --user import-environment SSH_AUTH_SOCK` to `~/.profile`.
- Unlike Windows, a plain `ssh-agent` forgets keys at logout, so run `ssh-add` after each login unless your desktop keyring loads it; until then a failed pull retries every 15 minutes.
