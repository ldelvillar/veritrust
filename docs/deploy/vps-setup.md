# VPS setup (Contabo, Ubuntu)

First-time setup of the production server, from a fresh Ubuntu image to a live stack.
Replace `VPS_IP` with the server's public IPv4 (Contabo panel → VPS). Day-to-day
operations live in [ops.md](ops.md).

## 1. SSH access from each workstation

Every workstation gets **its own key**; never copy a private key between machines.
Revoking one machine later means deleting one line from `authorized_keys`.

### Create the key (on each workstation)

PowerShell:

```powershell
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\veritrust_vps -C "veritrust-$env:COMPUTERNAME"
```

macOS/Linux:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/veritrust_vps -C "veritrust-$(hostname)"
```

### Install it on the server (while root password login still works)

Do this from **every** workstation before section 2, which turns password login off.
It asks for the root password from Contabo's login email; answer `yes` to the
fingerprint prompt the first time.

PowerShell:

```powershell
type $env:USERPROFILE\.ssh\veritrust_vps.pub | ssh root@VPS_IP "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

macOS/Linux: `ssh-copy-id -i ~/.ssh/veritrust_vps.pub root@VPS_IP`

### Add a host alias (on each workstation)

Append to `~/.ssh/config` (`C:\Users\<you>\.ssh\config` on Windows):

```text
Host veritrust
    HostName VPS_IP
    User deploy
    IdentityFile ~/.ssh/veritrust_vps

Host veritrust-root
    HostName VPS_IP
    User root
    IdentityFile ~/.ssh/veritrust_vps
```

`ssh veritrust-root` must log in **without** asking for a password. `veritrust-root`
stops working after section 2; from then on use `ssh veritrust`.

### Adding a workstation later

Create its key as above, copy the `.pub` content to a machine that already has access, and
append it there: `ssh veritrust "cat >> ~/.ssh/authorized_keys"`, paste, then Ctrl+D
(Ctrl+Z, Enter on Windows).

## 2. Harden the server (as root, once)

`ssh veritrust-root`, then:

```bash
apt update && apt full-upgrade -y
timedatectl set-timezone Europe/Madrid
```

Create the admin user on its own: `adduser` asks for the password `sudo` will use, and its
password prompt discards any lines pasted after it.

```bash
adduser deploy
```

Then give it sudo and the same keys as root:

```bash
usermod -aG sudo deploy
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh && chmod 700 /home/deploy/.ssh && chmod 600 /home/deploy/.ssh/authorized_keys
id deploy && cat /home/deploy/.ssh/authorized_keys
```

`id` must list `sudo`, and the file must hold one key per workstation. Then:

```bash
# Keys only, no root login; the 00- prefix wins over 50-cloud-init.conf (sshd keeps the first value)
printf 'PermitRootLogin no\nPasswordAuthentication no\nKbdInteractiveAuthentication no\n' > /etc/ssh/sshd_config.d/00-hardening.conf
sshd -t && sshd -T | grep -E '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication) '

# Firewall: SSH, HTTP, HTTPS only
ufw allow OpenSSH && ufw allow 80,443/tcp && ufw --force enable

# 2 GB swap: needed for image builds on a 4 GB host, a cheap safety net on 8 GB
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

`sshd -T` must print `permitrootlogin no`, `passwordauthentication no` and
`kbdinteractiveauthentication no`. Security updates open a dialog (answer Yes), so run
them on their own:

```bash
apt install -y unattended-upgrades && dpkg-reconfigure --priority=low unattended-upgrades
```

Apply the SSH settings last:

```bash
systemctl restart ssh
```

**Keep this root session open** and check from a second terminal that `ssh veritrust`
logs in and `sudo -v` accepts the password; only then close it.

## 3. Docker

As `deploy`:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh && rm get-docker.sh
sudo usermod -aG docker deploy
exit
```

Log back in (`ssh veritrust`) so the group applies, then check that `docker compose version`
is **2.24 or newer** (`docker-compose.prod.yml` uses `!override`).

Ports published by Docker bypass ufw. Only start the stack with **both** compose files:
the base file alone publishes the backend (8000) and frontend (3000) to the internet.

## 4. Code and production env files

```bash
git clone https://github.com/ldelvillar/veritrust.git ~/veritrust
```

Then create the three production env files as described in [env.md](env.md), and save
a copy of each in your password manager.

## 5. Build, cut over DNS, start

Build first; it takes a few minutes and needs the swap:

```bash
cd ~/veritrust && docker compose -f docker-compose.yml -f docker-compose.prod.yml build
```

Caddy requests TLS certificates on start, so DNS must already point at the server. In
the registrar's DNS zone (TTL lowered at least an hour beforehand), point the `API_DOMAIN`
and `APP_DOMAIN` records at `VPS_IP`, and every other hostname the site answers on (such
as `www`) too. Each of those needs a site block in the `Caddyfile`, or it gets no
certificate. Wait until a public resolver returns the new IP:

```bash
dig +short API_DOMAIN @1.1.1.1
```

To restore an old dump, start Postgres alone first and restore it as in
[backups.md](backups.md) before the next step. Then:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
curl -fsS https://API_DOMAIN/healthz
```

Every service must show `healthy`, `/healthz` must answer 200, and one real analysis
must finish in the browser.

## 6. Deploys from GitHub Actions

The Deploy workflow logs in over SSH with its own key, separate from the workstations'.
On one workstation, in Git Bash (PowerShell has no `<` redirect):

```bash
ssh-keygen -t ed25519 -f ~/.ssh/veritrust_deploy -N "" -C "github-actions-deploy"
cat ~/.ssh/veritrust_deploy.pub | ssh veritrust "cat >> ~/.ssh/authorized_keys"
gh secret set VM_HOST --body "VPS_IP"
gh secret set VM_USER --body "deploy"
gh secret set VM_SSH_KEY < ~/.ssh/veritrust_deploy
rm ~/.ssh/veritrust_deploy ~/.ssh/veritrust_deploy.pub
gh workflow run Deploy
```

The private key only needs to live in GitHub; to rotate it, repeat the steps and delete
the old `github-actions-deploy` line from `authorized_keys`. Deploys never touch the
env files.

## 7. After the first deploy

- Nightly backups: [backups.md](backups.md), then test a restore once.
- CPU steal log: [monitoring.md](monitoring.md) §5.
- Uptime alerts: an external checker (e.g. UptimeRobot) on `https://API_DOMAIN/healthz`
  and `https://APP_DOMAIN`.
