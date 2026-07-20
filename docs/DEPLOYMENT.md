# Deployment Runbook

## Prerequisites

1. Follow [`GCP_ACCOUNT_VERIFICATION.md`](./GCP_ACCOUNT_VERIFICATION.md).
2. Personal GCP account: `bharath12345@gmail.com`.
3. Domain (e.g. `bengaluruclassical.in`) on Cloudflare.

## One-time setup

```bash
# 1. Verify identity
gcloud config get-value account  # must be bharath12345@gmail.com

# 2. Create project + enable APIs
bash infra/gcp-project-setup.sh

# 3. Buckets
bash infra/gcs-buckets.sh

# 4. Secrets (interactive — never commit values)
bash infra/secrets.sh

# 5. Artifact Registry
gcloud artifacts repositories create bengaluru-classical \
  --repository-format=docker --location=asia-south1
```

## Build & deploy

```bash
# Local image smoke test
docker build -f infra/Dockerfile -t bengaluru-classical:local .
docker run --rm -p 8080:8080 \
  -e DJANGO_SETTINGS_MODULE=config.settings.dev \
  -e DJANGO_SECRET_KEY=local-test \
  -e DATABASE_URL=postgres://blr:blr@host.docker.internal:5432/blr_classical \
  bengaluru-classical:local

# Cloud Build (CI/CD)
gcloud builds submit --config=infra/cloudbuild.yaml
```

## Pipeline jobs

```bash
# Create Cloud Run Job from infra/cloudrun-job-pipeline.yaml
# Schedule via Cloud Scheduler (see infra/scheduler-*.yaml comments)
```

## Cloudflare

- DNS + CDN for `bengaluruclassical.in` → Cloud Run
- Email Worker: see `infra/cloudflare/README.md`

## Post-deploy checks

- `GET /health/` → `{"status":"ok"}`
- `GET /` → upcoming list
- `GET /mcp` → MCP streamable HTTP
- `GET /.well-known/mcp.json` → discovery doc
- Admin review queue at `/admin/`
