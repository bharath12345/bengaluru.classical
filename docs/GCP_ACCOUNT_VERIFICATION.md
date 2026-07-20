# GCP Account Verification Checklist

**CRITICAL:** Before running ANY `gcloud` command, verify you are using the PERSONAL identity.

## Pre-deployment verification

```bash
gcloud config get-value account
# MUST output: bharath12345@gmail.com
# If it shows bharadwaj@conviva.com, STOP and switch:
#   gcloud config set account bharath12345@gmail.com

gcloud config get-value project
# Should output: bengaluru-classical

gcloud config get-value compute/region
# Should output: asia-south1
```

## Rules

- Never use employer identity `bharadwaj@conviva.com` for runtime, billing, or IAM.
- All secrets live in Secret Manager in project `bengaluru-classical`.
- Git commits: `user.name=Bharadwaj`, `user.email=bharath12345@gmail.com`.
