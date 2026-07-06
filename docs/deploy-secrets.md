# Secrets in GCP Secret Manager

The production `.env` lives in Secret Manager as a single secret (`veritrust-env`).
Each deploy renders it onto the VM before `docker compose up`, so the VM copy is a
disposable cache, not the source of truth. Until the secret exists, deploys keep
whatever `.env` is already on the VM (see the guarded step in
`.github/workflows/deploy.yml`).

Run the one-time setup from your local machine with `gcloud` authenticated against
the project that owns the VM.

## 1. One-time setup

### Create the secret from the VM's .env

The VM's `.env` is the live production config; the repo-root `.env` on your laptop
holds **development** values (e.g. Clerk test keys) and must never become the
secret. Copy the VM file to a temp path *outside the repo* (so it can't be
committed), create the secret from it, and delete the copy:

```bash
scp -i ~/.ssh/gcp_veritrust USER@VM_IP:~/veritrust/.env /tmp/veritrust-env.prod
gcloud services enable secretmanager.googleapis.com
gcloud secrets create veritrust-env --replication-policy=automatic --data-file=/tmp/veritrust-env.prod
rm /tmp/veritrust-env.prod
```

### Grant the VM's service account read access

Find the service account attached to the VM:

```bash
gcloud compute instances describe VM_NAME --zone=ZONE --format="value(serviceAccounts[0].email)"
```

Grant it accessor on this secret only (not project-wide):

```bash
gcloud secrets add-iam-policy-binding veritrust-env \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
```

### Check the VM's access scopes

Default GCE scopes do **not** include Secret Manager. The VM needs the
`cloud-platform` scope (IAM above still limits what it can actually read):

```bash
gcloud compute instances describe VM_NAME --zone=ZONE --format="value(serviceAccounts[0].scopes)"
```

If `https://www.googleapis.com/auth/cloud-platform` is missing, stop the VM, update
the scopes, and start it again:

```bash
gcloud compute instances stop VM_NAME --zone=ZONE
gcloud compute instances set-service-account VM_NAME --zone=ZONE --scopes=cloud-platform
gcloud compute instances start VM_NAME --zone=ZONE
```

### Verify from the VM

```bash
ssh USER@VM_IP "gcloud secrets versions access latest --secret=veritrust-env | head -1"
```

## 2. Rotating or changing a value

Never edit `~/veritrust/.env` on the VM by hand (the next deploy overwrites it),
and never push the repo-root `.env` (development values). Pull the current
production secret, edit that copy, push it back as a new version, redeploy:

```bash
gcloud secrets versions access latest --secret=veritrust-env > /tmp/veritrust-env.prod
# edit /tmp/veritrust-env.prod
gcloud secrets versions add veritrust-env --data-file=/tmp/veritrust-env.prod
rm /tmp/veritrust-env.prod
gh workflow run Deploy
```

## 3. Notes

- The secret holds the whole `.env` consumed by `docker-compose.yml` (see
  `.env.example` at the repo root for the expected variables).
- After migration there are exactly two configs: the repo-root `.env` (local
  development, Clerk test keys) and the `veritrust-env` secret (production).
  They are *supposed* to differ — never sync one from the other.
- `backend/.env` and `frontend/.env` remain local-development files; they are not
  used in production and must never be uploaded.
- Old secret versions stay readable by default; disable them after rotating a
  compromised value: `gcloud secrets versions disable N --secret=veritrust-env`.
