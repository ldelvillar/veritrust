# Copy BERT model to the VM

Run from the repo root on your local machine. Replace `USER` and `VM_IP` with your GCP values.

## 1. Ensure the target directory exists on the VM

```bash
ssh USER@VM_IP "mkdir -p ~/veritrust/backend/models"
```

## 2. Copy the model

```powershell
gcloud compute scp --recurse backend/models/bert_classifier/<MODEL_FOLDER> USER@veritrust:/home/USER/veritrust/backend/models/bert_classifier/ --zone us-central1-c
```

## 3. Verify

```bash
ssh USER@VM_IP "ls ~/veritrust/backend/models/bert_classifier/"
```

Expected output:

```text
config.json  model.safetensors  tokenizer.json  tokenizer_config.json
```

## 4. Restart the worker

After updating the model, restart the worker so it loads the new weights:

```bash
ssh USER@VM_IP "cd ~/veritrust && docker compose restart worker"
```
