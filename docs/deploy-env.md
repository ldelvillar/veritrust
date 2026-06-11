# Copy .env to the VM

Run from the repo root on your local machine. Replace `USER` and `VM_IP` with your GCP values.

## Copy

```powershell
scp -i $env:USERPROFILE\.ssh\gcp_veritrust .env USER@VM_IP:~/veritrust/.env
```

## Verify

```bash
ssh USER@VM_IP "cat ~/veritrust/.env"
```

## Notes

- Only the root `.env` is needed — `backend/.env` and `frontend/.env` are for local development outside Docker and are not used in production.
- Never commit `.env` to git.
- After updating `.env` on the VM, recreate the affected containers: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
