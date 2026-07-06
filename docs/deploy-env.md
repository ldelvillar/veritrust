# Production .env

The source of truth for the production `.env` is GCP Secret Manager — see
[deploy-secrets.md](deploy-secrets.md). Every deploy renders the secret onto the VM,
so manual edits to `~/veritrust/.env` are overwritten by the next deploy.

## Fallback: copy .env over SSH

Only needed before the Secret Manager setup exists (the deploy keeps the VM's
current `.env` while the secret is missing). Run from the repo root on your local
machine, replacing `USER` and `VM_IP`:

```powershell
scp -i $env:USERPROFILE\.ssh\gcp_veritrust .env USER@VM_IP:~/veritrust/.env
```

Verify:

```bash
ssh USER@VM_IP "cat ~/veritrust/.env"
```

## Notes

- Only the root `.env` is needed — `backend/.env` and `frontend/.env` are for local
  development outside Docker and are not used in production.
- Never commit `.env` to git.
- After updating `.env` on the VM, recreate the affected containers:
  `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
