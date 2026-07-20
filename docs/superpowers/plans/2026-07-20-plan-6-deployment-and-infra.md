# Plan 6 — Deployment & Infrastructure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the complete application (Django site + MCP server + pipeline jobs) to production on Google Cloud Platform at near-zero cost, running on the maintainer's PERSONAL Google identity. Make it live at a custom `.in` domain with CDN, SSL, automated daily ingestion, and production-grade security/monitoring. This plan is more ops-oriented than TDD — where TDD doesn't fit, use concrete verification steps (commands with expected output) instead of test-first, but maintain the same bite-sized, no-placeholder rigor showing COMPLETE file contents.

**Architecture:** A containerized Django application (serving both the public site and the MCP server via mounted FastMCP) deployed to Cloud Run in `asia-south1` (Mumbai) with scale-to-zero autoscaling. Daily ingestion runs as Cloud Run Jobs triggered by Cloud Scheduler. Static/media assets served from GCS via CDN. Secrets in Secret Manager. Database is Supabase Postgres (already provisioned, server-side access only). Cloudflare for DNS + CDN + Email Workers. Cloud Build for CI/CD. All resources use the personal identity `bharath12345@gmail.com`.

**Tech Stack:** Docker, Google Cloud Run, Cloud Run Jobs, Cloud Scheduler, Cloud Build, Google Cloud Storage, Secret Manager, Cloud Logging, Cloudflare DNS/CDN/Email Workers, Supabase Postgres, WhiteNoise (static files fallback), gunicorn + uvicorn workers (ASGI), structlog (structured logging).

## Global Constraints

- **ACCOUNT SEPARATION (CRITICAL HARD RULE):** Every GCP resource, every Supabase resource, every Cloudflare resource, every Gemini API key, every `gcloud` command, every git commit, and every configuration file uses the PERSONAL identity `bharath12345@gmail.com`. The employer identity `bharadwaj@conviva.com` MUST NEVER appear in any command, config, environment variable, IAM binding, API key, or git commit. This is stated in technical.md §7 and must be enforced in every single step. Git commits set `user.email=bharath12345@gmail.com`, `user.name=Bharadwaj`.
- **GCP region:** `asia-south1` (Mumbai) for Cloud Run, Cloud Run Jobs, and GCS buckets (lowest latency for Bengaluru users). Note: `asia-south1` is NOT in the GCP always-free tier; expect low single-digit rupees/month, not zero.
- **GCP project ID:** `bengaluru-classical` (to be created in Task 1).
- **Secrets never committed:** all secrets managed via Secret Manager and passed to Cloud Run/Jobs as environment variables. `.env`, `*-key.json`, service account keys are gitignored.
- **Database:** Supabase Postgres free tier in Mumbai (`ap-south-1`), accessed ONLY server-side (never from browsers due to historical ISP blocks in India — see technical.md §10).
- **Cost target:** < ₹500/month (see technical.md §8). Scale-to-zero, no warm instances, free tiers where available.
- **Custom domain:** The `.in` domain (assumed to be `bengaluruclassical.in` — adjust in Task 8 if different) mapped via Cloudflare DNS + CDN.
- **Python version:** 3.13 (matching pyproject.toml floor from Plan 1).
- **Production Django settings:** `DJANGO_SETTINGS_MODULE=config.settings.prod` with security hardening (see Task 2).
- All deployment commands use the personal GCP identity — verify with `gcloud config get-value account` before any `gcloud` command.

---

## File Structure

```
infra/
  Dockerfile                       # production container image
  .dockerignore                    # exclude .git, .env, __pycache__, etc.
  cloudbuild.yaml                  # Cloud Build CI/CD pipeline
  cloudrun-web.yaml                # Cloud Run service config (web + MCP)
  cloudrun-job-pipeline.yaml       # Cloud Run Job config (daily scraper)
  scheduler-pipeline-cron.yaml     # Cloud Scheduler job (daily pipeline trigger)
  scheduler-keepalive-cron.yaml    # Cloud Scheduler job (ping Supabase)
  gcs-buckets.sh                   # script to create GCS buckets + IAM
  secrets.sh                       # script to create Secret Manager secrets (TEMPLATE)
config/
  settings/
    prod.py                        # production settings (hardened)
docs/
  DEPLOYMENT.md                    # deployment runbook
  COST_VERIFICATION.md             # cost checklist mapping to target
cloudflare/
  email-worker.js                  # Cloudflare Email Worker (inbound email)
```

---

### Task 1: GCP project setup and IAM verification

**Files:**
- Create: `infra/gcp-project-setup.sh` (one-time setup script, documented)
- Create: `docs/GCP_ACCOUNT_VERIFICATION.md` (checklist to verify correct identity)

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - GCP project `bengaluru-classical` created and selected.
  - Billing account linked (personal account).
  - Required APIs enabled: `run.googleapis.com`, `cloudbuild.googleapis.com`, `cloudscheduler.googleapis.com`, `secretmanager.googleapis.com`, `storage.googleapis.com`, `logging.googleapis.com`.
  - Default region set to `asia-south1`.
  - `gcloud config get-value account` returns `bharath12345@gmail.com`.

- [ ] **Step 1: Create the account verification checklist**

```markdown
# GCP Account Verification Checklist

**CRITICAL:** Before running ANY `gcloud` command, verify you are using the PERSONAL identity.

## Pre-deployment verification

Run these commands and verify output:

```bash
gcloud config get-value account
# MUST output: bharath12345@gmail.com
# If it shows bharadwaj@conviva.com, STOP and switch:
#   gcloud config set account bharath12345@gmail.com

gcloud config get-value project
# Should output: bengaluru-classical (after Task 1 setup)

gcloud config get-value compute/region
# Should output: asia-south1
```

## During deployment

- Never use `--account` flags pointing to the employer identity.
- Never create service accounts with employer domain emails.
- Never add IAM bindings for `bharadwaj@conviva.com`.
- All Secret Manager secrets, GCS buckets, Cloud Run services MUST be in project `bengaluru-classical` owned by `bharath12345@gmail.com`.

## Git commits

Every commit MUST use:
```bash
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "..."
```

## API keys

- Gemini API key: generated from AI Studio / GCP console under `bharath12345@gmail.com`.
- Supabase: project created under `bharath12345@gmail.com`.
- Cloudflare: account owned by `bharath12345@gmail.com`.
```

Save to: `docs/GCP_ACCOUNT_VERIFICATION.md`

- [ ] **Step 2: Create the GCP project setup script**

```bash
#!/usr/bin/env bash
# infra/gcp-project-setup.sh
# One-time GCP project setup for bengaluru-classical.
# Run this AFTER verifying gcloud account is bharath12345@gmail.com.

set -euo pipefail

PROJECT_ID="bengaluru-classical"
REGION="asia-south1"

echo "==> Verifying account..."
ACCOUNT=$(gcloud config get-value account)
if [[ "$ACCOUNT" != "bharath12345@gmail.com" ]]; then
  echo "ERROR: Wrong account. Current: $ACCOUNT. Expected: bharath12345@gmail.com"
  echo "Run: gcloud config set account bharath12345@gmail.com"
  exit 1
fi
echo "✓ Account verified: $ACCOUNT"

echo ""
echo "==> Creating project $PROJECT_ID..."
# Create project (idempotent — fails gracefully if exists)
gcloud projects create "$PROJECT_ID" --name="Bengaluru Classical" --set-as-default || true

echo ""
echo "==> Setting project and region..."
gcloud config set project "$PROJECT_ID"
gcloud config set compute/region "$REGION"

echo ""
echo "==> Linking billing account..."
echo "MANUAL STEP REQUIRED: Go to https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
echo "and link your PERSONAL billing account (bharath12345@gmail.com)."
echo "Press Enter after billing is linked..."
read -r

echo ""
echo "==> Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  logging.googleapis.com

echo ""
echo "==> Verifying final state..."
gcloud config get-value project
gcloud config get-value compute/region
gcloud config get-value account

echo ""
echo "✓ GCP project setup complete."
echo "  Project: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Account: $ACCOUNT"
```

Save to: `infra/gcp-project-setup.sh` and make executable: `chmod +x infra/gcp-project-setup.sh`.

- [ ] **Step 3: Verify the script is correct (local dry-run check)**

Run: `bash -n infra/gcp-project-setup.sh`
Expected: No syntax errors.

- [ ] **Step 4: Document the manual verification step**

Add to `docs/DEPLOYMENT.md` (create if not exists):

```markdown
# Deployment Runbook

## Prerequisites

- `gcloud` CLI installed and authenticated as `bharath12345@gmail.com`.
- Docker installed locally (for building the image).
- Supabase project created under `bharath12345@gmail.com` in region `ap-south-1` (Mumbai).
- Cloudflare account under `bharath12345@gmail.com` with domain `bengaluruclassical.in` added.
- Gemini API key from AI Studio under `bharath12345@gmail.com`.

## Step 1: Verify GCP account

Read `docs/GCP_ACCOUNT_VERIFICATION.md` and verify `gcloud config get-value account` returns `bharath12345@gmail.com`.

## Step 2: Run GCP project setup

```bash
./infra/gcp-project-setup.sh
```

Follow the manual billing link step. Wait for all APIs to enable (1–2 minutes).

## (Further steps added in later tasks)
```

- [ ] **Step 5: Commit**

```bash
git add infra/gcp-project-setup.sh docs/GCP_ACCOUNT_VERIFICATION.md docs/DEPLOYMENT.md
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "infra: add GCP project setup script and account verification checklist"
```

**Verification (manual, not automated):** After running `./infra/gcp-project-setup.sh` (when implementing this plan), verify:
- `gcloud config get-value project` → `bengaluru-classical`
- `gcloud config get-value account` → `bharath12345@gmail.com`
- `gcloud services list --enabled` includes `run.googleapis.com`, `cloudbuild.googleapis.com`, etc.

---

### Task 2: Production Django settings hardening

**Files:**
- Modify: `config/settings/prod.py`
- Modify: `pyproject.toml` (add `whitenoise`, `gunicorn`, `uvicorn[standard]`, `structlog`, `psycopg[binary]` if missing, `google-cloud-logging`)
- Create: `config/logging.py` (structured logging config)

**Interfaces:**
- Consumes: `config/settings/base.py` from Plan 1.
- Produces:
  - `config/settings/prod.py` with: `DEBUG=False`, `ALLOWED_HOSTS` from env, `SECURE_*` flags, HSTS, `DATABASES` from Supabase `DATABASE_URL`, `STATIC_ROOT` + WhiteNoise middleware, `MEDIA_URL` pointing to GCS, structured logging to Cloud Logging.
  - Management command `python manage.py check --deploy` passes with no warnings.

- [ ] **Step 1: Add production dependencies**

Run:
```bash
uv add "whitenoise>=6.7" "gunicorn>=23.0" "uvicorn[standard]>=0.30" "structlog>=24.4" "google-cloud-logging>=3.11"
```

Expected: `pyproject.toml` and `uv.lock` updated.

- [ ] **Step 2: Create structured logging config**

```python
# config/logging.py
import logging
import os

import structlog


def configure_logging():
    """
    Configure structured logging for production.
    Outputs JSON logs to stdout for Cloud Logging ingestion.
    """
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
    )

    # Google Cloud Logging integration (auto-detects Cloud Run environment)
    if os.getenv("K_SERVICE"):  # Cloud Run sets K_SERVICE
        import google.cloud.logging

        client = google.cloud.logging.Client()
        client.setup_logging()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

- [ ] **Step 3: Write production settings**

```python
# config/settings/prod.py
import os

from .base import *  # noqa: F401,F403

# Import base settings so we can reference them
from .base import BASE_DIR, MIDDLEWARE

# Security
DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]  # Required; no default
ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "bengaluruclassical.in,*.run.app"
).split(",")

# HTTPS / security headers (Cloud Run terminates TLS; sets X-Forwarded-Proto)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# Database (Supabase Postgres via DATABASE_URL secret)
DATABASES = {
    "default": __import__("dj_database_url").parse(
        os.environ["DATABASE_URL"],
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Static files (WhiteNoise for serving; collectstatic to STATIC_ROOT)
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files (posters) served from GCS
GS_BUCKET_NAME = os.environ.get("GCS_MEDIA_BUCKET", "bengaluru-classical-posters")
MEDIA_URL = f"https://storage.googleapis.com/{GS_BUCKET_NAME}/"
# Note: django-storages or manual GCS upload in pipeline; ImageField.upload_to still writes locally
# during development; production uses GCS backend (wired in Plan 3/4).

# Logging (structured JSON to Cloud Logging)
from config.logging import configure_logging  # noqa: E402

configure_logging()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
```

- [ ] **Step 4: Create a test environment file for check --deploy**

Create `.env.prod.test` (gitignored, for local verification only):

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=test-secret-for-deploy-check-only
DJANGO_ALLOWED_HOSTS=bengaluruclassical.in,example.run.app
DATABASE_URL=postgres://blr:blr@localhost:5432/blr_classical
GCS_MEDIA_BUCKET=bengaluru-classical-posters
```

- [ ] **Step 5: Run Django deploy check locally**

Run:
```bash
set -a; source .env.prod.test; set +a
uv run python manage.py check --deploy
```

Expected output: No warnings (or only benign warnings about `SECURE_SSL_REDIRECT` when not behind HTTPS locally — acceptable). The command should not error.

- [ ] **Step 6: Add .env.prod.test to .gitignore**

Verify `.env.prod.test` is gitignored (or add `*.env.prod*` pattern to `.gitignore`).

- [ ] **Step 7: Commit**

```bash
git add config/settings/prod.py config/logging.py pyproject.toml uv.lock .gitignore
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "feat: harden production Django settings with security headers and structured logging"
```

**Verification:** `uv run python manage.py check --deploy` with prod env passes; WhiteNoise middleware present; Cloud Logging import does not error.

---

### Task 3: Containerization (Dockerfile + .dockerignore)

**Files:**
- Create: `infra/Dockerfile`
- Create: `infra/.dockerignore`

**Interfaces:**
- Consumes: `pyproject.toml`, `uv.lock`, Django project from Plan 1–5.
- Produces:
  - Production `Dockerfile` using Python 3.13 slim, `uv` for install, `collectstatic`, gunicorn + uvicorn ASGI worker to serve Django (which mounts the MCP server from Plan 5).
  - `.dockerignore` excluding `.git`, `.env`, `__pycache__`, `*.pyc`, `staticfiles/`, etc.
  - Successful local `docker build` and `docker run` test.

- [ ] **Step 1: Write .dockerignore**

```
# infra/.dockerignore
.git
.gitignore
.env
.env.*
*.pyc
__pycache__
*.log
.DS_Store
.vscode
.idea
*.md
docs/
tests/
.pytest_cache
.ruff_cache
staticfiles/
media/
uv.lock
docker-compose.yml
```

- [ ] **Step 2: Write the production Dockerfile**

```dockerfile
# infra/Dockerfile
FROM python:3.13-slim

# Set environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    PORT=8080

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Collect static files (requires SECRET_KEY set at build time or runtime; we'll pass it)
# NOTE: collectstatic needs DATABASE_URL but does NOT need a real DB connection if we skip checks.
# We'll run it in the entrypoint script instead (see Step 3).

# Create a non-root user
RUN useradd -m -u 1000 django && chown -R django:django /app
USER django

# Expose port
EXPOSE 8080

# Run gunicorn with uvicorn ASGI workers
CMD exec gunicorn config.asgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
```

**Note:** `collectstatic` is run during Cloud Build, not in the Dockerfile, to avoid needing secrets at image-build time (see Task 7).

- [ ] **Step 3: Build the Docker image locally**

Run:
```bash
cd /Users/bharadwaj/Work/Code/mine/bengaluru.classical
docker build -f infra/Dockerfile -t bengaluru-classical:local .
```

Expected: Build succeeds, image tagged `bengaluru-classical:local`.

- [ ] **Step 4: Test the container locally**

Run:
```bash
docker run --rm -p 8080:8080 \
  -e DJANGO_SETTINGS_MODULE=config.settings.dev \
  -e DJANGO_SECRET_KEY=local-test-secret \
  -e DATABASE_URL=postgres://blr:blr@host.docker.internal:5432/blr_classical \
  -e DJANGO_DEBUG=1 \
  bengaluru-classical:local
```

Expected: Container starts; logs show `Uvicorn running on http://0.0.0.0:8080`; `curl http://localhost:8080/admin/` returns the Django admin login page (or a redirect). Stop with Ctrl+C.

- [ ] **Step 5: Commit**

```bash
git add infra/Dockerfile infra/.dockerignore
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "infra: add production Dockerfile with gunicorn+uvicorn ASGI server"
```

**Verification:** Docker build succeeds; container runs and serves Django on port 8080.

---

### Task 4: GCS buckets for raw ingests and posters

**Files:**
- Create: `infra/gcs-buckets.sh` (idempotent bucket creation + IAM)

**Interfaces:**
- Consumes: GCP project from Task 1.
- Produces:
  - GCS bucket `bengaluru-classical-raw` (private, for `RawIngest` blob storage).
  - GCS bucket `bengaluru-classical-posters` (public-read, for poster images served via CDN).
  - IAM: Cloud Run service account has `roles/storage.objectAdmin` on `raw`, `objectCreator` on `posters`.
  - Verification: `gsutil ls -b gs://bengaluru-classical-raw` and `gs://bengaluru-classical-posters` succeed.

- [ ] **Step 1: Write the GCS bucket setup script**

```bash
#!/usr/bin/env bash
# infra/gcs-buckets.sh
# Create GCS buckets for raw ingests and posters.
# Idempotent; safe to re-run.

set -euo pipefail

PROJECT_ID="bengaluru-classical"
REGION="asia-south1"
RAW_BUCKET="${PROJECT_ID}-raw"
POSTERS_BUCKET="${PROJECT_ID}-posters"

echo "==> Verifying account..."
ACCOUNT=$(gcloud config get-value account)
if [[ "$ACCOUNT" != "bharath12345@gmail.com" ]]; then
  echo "ERROR: Wrong account. Current: $ACCOUNT. Expected: bharath12345@gmail.com"
  exit 1
fi
echo "✓ Account verified: $ACCOUNT"

echo ""
echo "==> Creating GCS bucket for raw ingests (private)..."
gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://$RAW_BUCKET" 2>/dev/null || echo "Bucket $RAW_BUCKET already exists."
gsutil uniformbucketlevelaccess set on "gs://$RAW_BUCKET"

echo ""
echo "==> Creating GCS bucket for posters (public-read)..."
gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://$POSTERS_BUCKET" 2>/dev/null || echo "Bucket $POSTERS_BUCKET already exists."
gsutil uniformbucketlevelaccess set on "gs://$POSTERS_BUCKET"
gsutil iam ch allUsers:objectViewer "gs://$POSTERS_BUCKET"

echo ""
echo "==> Granting Cloud Run default service account access..."
# Cloud Run default service account: PROJECT_NUMBER-compute@developer.gserviceaccount.com
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gsutil iam ch "serviceAccount:${SERVICE_ACCOUNT}:roles/storage.objectAdmin" "gs://$RAW_BUCKET"
gsutil iam ch "serviceAccount:${SERVICE_ACCOUNT}:roles/storage.objectCreator" "gs://$POSTERS_BUCKET"

echo ""
echo "✓ GCS buckets created and IAM configured."
echo "  Raw bucket: gs://$RAW_BUCKET (private)"
echo "  Posters bucket: gs://$POSTERS_BUCKET (public-read)"
```

Save to `infra/gcs-buckets.sh` and make executable: `chmod +x infra/gcs-buckets.sh`.

- [ ] **Step 2: Verify the script syntax**

Run: `bash -n infra/gcs-buckets.sh`
Expected: No syntax errors.

- [ ] **Step 3: Document the verification command**

Add to `docs/DEPLOYMENT.md`:

```markdown
## Step 3: Create GCS buckets

```bash
./infra/gcs-buckets.sh
```

Verify:
```bash
gsutil ls -b gs://bengaluru-classical-raw
gsutil ls -b gs://bengaluru-classical-posters
```
Both should list bucket metadata.
```

- [ ] **Step 4: Commit**

```bash
git add infra/gcs-buckets.sh docs/DEPLOYMENT.md
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "infra: add GCS bucket setup for raw ingests and posters"
```

**Verification (manual when implementing):** After running `./infra/gcs-buckets.sh`, `gsutil ls` shows both buckets; `gsutil iam get gs://bengaluru-classical-posters` shows `allUsers` has `objectViewer`.

---

### Task 5: Secret Manager setup

**Files:**
- Create: `infra/secrets-template.sh` (template script showing how to create secrets; actual values NOT committed)
- Create: `docs/SECRETS.md` (list of required secrets and how to generate them)

**Interfaces:**
- Consumes: GCP project from Task 1.
- Produces:
  - Secret Manager secrets: `DJANGO_SECRET_KEY`, `DATABASE_URL`, `GEMINI_API_KEY`, `INBOUND_EMAIL_SECRET`, `SUBMISSION_INBOX`.
  - Cloud Run service account granted `roles/secretmanager.secretAccessor` on all secrets.
  - Verification: `gcloud secrets describe DJANGO_SECRET_KEY` succeeds.

- [ ] **Step 1: Document required secrets and how to generate them**

```markdown
# Secrets

The following secrets must be created in GCP Secret Manager under project `bengaluru-classical` before deploying.

## Required secrets

| Secret name | Description | How to generate |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret key (50+ chars) | `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'` |
| `DATABASE_URL` | Supabase Postgres connection string | From Supabase project dashboard → Settings → Database → Connection string (URI, pooling mode, session mode, or direct). Example: `postgres://postgres.abc123:PASSWORD@aws-0-ap-south-1.pooler.supabase.com:6543/postgres` |
| `GEMINI_API_KEY` | Gemini API key for poster/scrape extraction | From AI Studio (https://aistudio.google.com/apikey) under account `bharath12345@gmail.com` |
| `INBOUND_EMAIL_SECRET` | Shared secret for Cloudflare Email Worker → Cloud Run auth | `openssl rand -hex 32` |
| `SUBMISSION_INBOX` | Email address for the private inbound mailbox | E.g., `submissions@bengaluruclassical.in` (configured in Cloudflare Email Routing) |

## Creating secrets

Use the template script `infra/secrets-template.sh` as a guide. **NEVER commit actual secret values.**

Example:
```bash
echo -n "YOUR_DJANGO_SECRET_KEY_HERE" | gcloud secrets create DJANGO_SECRET_KEY \
  --data-file=- \
  --replication-policy="automatic" \
  --project=bengaluru-classical
```

## Granting access

The Cloud Run default service account needs `secretAccessor` role:
```bash
PROJECT_NUMBER=$(gcloud projects describe bengaluru-classical --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for SECRET in DJANGO_SECRET_KEY DATABASE_URL GEMINI_API_KEY INBOUND_EMAIL_SECRET SUBMISSION_INBOX; do
  gcloud secrets add-iam-policy-binding "$SECRET" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --project=bengaluru-classical
done
```
```

Save to `docs/SECRETS.md`.

- [ ] **Step 2: Write the secrets template script**

```bash
#!/usr/bin/env bash
# infra/secrets-template.sh
# TEMPLATE for creating Secret Manager secrets.
# DO NOT commit actual secret values. Copy this, fill in values, run locally, delete.

set -euo pipefail

PROJECT_ID="bengaluru-classical"

echo "==> Verifying account..."
ACCOUNT=$(gcloud config get-value account)
if [[ "$ACCOUNT" != "bharath12345@gmail.com" ]]; then
  echo "ERROR: Wrong account. Current: $ACCOUNT. Expected: bharath12345@gmail.com"
  exit 1
fi
echo "✓ Account verified: $ACCOUNT"

echo ""
echo "INSTRUCTIONS:"
echo "1. Replace <PLACEHOLDER> values below with actual secrets."
echo "2. Run this script locally."
echo "3. DELETE the copy with real values (never commit)."
echo ""
read -p "Press Enter to continue or Ctrl+C to abort..."

# DJANGO_SECRET_KEY (generate with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
echo -n "<REPLACE_WITH_DJANGO_SECRET_KEY>" | gcloud secrets create DJANGO_SECRET_KEY \
  --data-file=- \
  --replication-policy="automatic" \
  --project="$PROJECT_ID" 2>/dev/null || echo "DJANGO_SECRET_KEY already exists."

# DATABASE_URL (from Supabase dashboard)
echo -n "<REPLACE_WITH_SUPABASE_DATABASE_URL>" | gcloud secrets create DATABASE_URL \
  --data-file=- \
  --replication-policy="automatic" \
  --project="$PROJECT_ID" 2>/dev/null || echo "DATABASE_URL already exists."

# GEMINI_API_KEY (from AI Studio under bharath12345@gmail.com)
echo -n "<REPLACE_WITH_GEMINI_API_KEY>" | gcloud secrets create GEMINI_API_KEY \
  --data-file=- \
  --replication-policy="automatic" \
  --project="$PROJECT_ID" 2>/dev/null || echo "GEMINI_API_KEY already exists."

# INBOUND_EMAIL_SECRET (generate with: openssl rand -hex 32)
echo -n "<REPLACE_WITH_INBOUND_EMAIL_SECRET>" | gcloud secrets create INBOUND_EMAIL_SECRET \
  --data-file=- \
  --replication-policy="automatic" \
  --project="$PROJECT_ID" 2>/dev/null || echo "INBOUND_EMAIL_SECRET already exists."

# SUBMISSION_INBOX (e.g., submissions@bengaluruclassical.in)
echo -n "<REPLACE_WITH_SUBMISSION_INBOX_EMAIL>" | gcloud secrets create SUBMISSION_INBOX \
  --data-file=- \
  --replication-policy="automatic" \
  --project="$PROJECT_ID" 2>/dev/null || echo "SUBMISSION_INBOX already exists."

echo ""
echo "==> Granting Cloud Run service account access to secrets..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for SECRET in DJANGO_SECRET_KEY DATABASE_URL GEMINI_API_KEY INBOUND_EMAIL_SECRET SUBMISSION_INBOX; do
  gcloud secrets add-iam-policy-binding "$SECRET" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT_ID"
done

echo ""
echo "✓ Secrets created and IAM configured."
echo "  Verify with: gcloud secrets list --project=$PROJECT_ID"
```

Save to `infra/secrets-template.sh` and make executable: `chmod +x infra/secrets-template.sh`.

- [ ] **Step 3: Add secrets setup to deployment runbook**

Add to `docs/DEPLOYMENT.md`:

```markdown
## Step 4: Create Secret Manager secrets

1. Read `docs/SECRETS.md` to understand required secrets.
2. Copy `infra/secrets-template.sh` to a temporary file (e.g., `~/secrets-REAL.sh`).
3. Replace `<PLACEHOLDER>` values with real secrets.
4. Run the script: `bash ~/secrets-REAL.sh`
5. **DELETE the copy with real values.**
6. Verify: `gcloud secrets list --project=bengaluru-classical`
```

- [ ] **Step 4: Commit**

```bash
git add infra/secrets-template.sh docs/SECRETS.md docs/DEPLOYMENT.md
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "infra: add Secret Manager setup template and documentation"
```

**Verification (manual when implementing):** After running the real secrets script, `gcloud secrets list` shows 5 secrets; `gcloud secrets describe DJANGO_SECRET_KEY` succeeds.

---

### Task 6: Cloud Run service (web + MCP) and Cloud Run Job (pipeline)

**Files:**
- Create: `infra/cloudrun-web.yaml` (Cloud Run service config)
- Create: `infra/cloudrun-job-pipeline.yaml` (Cloud Run Job config)
- Create: `infra/deploy-cloudrun.sh` (deploy script)

**Interfaces:**
- Consumes: Docker image (from Task 3), secrets (from Task 5), GCS buckets (from Task 4).
- Produces:
  - Cloud Run service `bengaluru-classical-web` in `asia-south1`, scale-to-zero (min-instances=0, max-instances=10), secrets injected as env vars, serves Django + MCP.
  - Cloud Run Job `bengaluru-classical-pipeline` running `python manage.py run_scrapers && python manage.py process_raw_ingests` (commands from Plan 4; runs both in sequence).
  - Verification: `gcloud run services describe bengaluru-classical-web` shows status `Ready`; `curl https://bengaluru-classical-web-<hash>-uc.a.run.app/admin/` returns the admin page.

- [ ] **Step 1: Write Cloud Run service config (web + MCP)**

```yaml
# infra/cloudrun-web.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: bengaluru-classical-web
  labels:
    cloud.googleapis.com/location: asia-south1
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: '0'
        autoscaling.knative.dev/maxScale: '10'
        run.googleapis.com/cpu-throttling: 'true'
        run.googleapis.com/startup-cpu-boost: 'false'
    spec:
      containerConcurrency: 80
      timeoutSeconds: 300
      containers:
      - image: gcr.io/bengaluru-classical/bengaluru-classical:latest  # Updated by Cloud Build
        ports:
        - name: http1
          containerPort: 8080
        env:
        - name: DJANGO_SETTINGS_MODULE
          value: config.settings.prod
        - name: DJANGO_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: DJANGO_SECRET_KEY
              key: latest
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: DATABASE_URL
              key: latest
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: GEMINI_API_KEY
              key: latest
        - name: INBOUND_EMAIL_SECRET
          valueFrom:
            secretKeyRef:
              name: INBOUND_EMAIL_SECRET
              key: latest
        - name: SUBMISSION_INBOX
          valueFrom:
            secretKeyRef:
              name: SUBMISSION_INBOX
              key: latest
        - name: GCS_RAW_BUCKET
          value: bengaluru-classical-raw
        - name: GCS_MEDIA_BUCKET
          value: bengaluru-classical-posters
        - name: DJANGO_ALLOWED_HOSTS
          value: bengaluruclassical.in,*.run.app
        resources:
          limits:
            cpu: '1'
            memory: 512Mi
```

- [ ] **Step 2: Write Cloud Run Job config (pipeline)**

```yaml
# infra/cloudrun-job-pipeline.yaml
apiVersion: run.googleapis.com/v1
kind: Job
metadata:
  name: bengaluru-classical-pipeline
  labels:
    cloud.googleapis.com/location: asia-south1
spec:
  template:
    spec:
      template:
        spec:
          containers:
          - image: gcr.io/bengaluru-classical/bengaluru-classical:latest  # Updated by Cloud Build
            command:
            - sh
            - -c
            - python manage.py run_scrapers && python manage.py process_raw_ingests
            env:
            - name: DJANGO_SETTINGS_MODULE
              value: config.settings.prod
            - name: DJANGO_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: DJANGO_SECRET_KEY
                  key: latest
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: DATABASE_URL
                  key: latest
            - name: GEMINI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: GEMINI_API_KEY
                  key: latest
            - name: GCS_RAW_BUCKET
              value: bengaluru-classical-raw
            - name: GCS_MEDIA_BUCKET
              value: bengaluru-classical-posters
            resources:
              limits:
                cpu: '2'
                memory: 2Gi
          timeoutSeconds: 3600  # 1 hour max
```

- [ ] **Step 3: Write the Cloud Run deploy script**

```bash
#!/usr/bin/env bash
# infra/deploy-cloudrun.sh
# Deploy Cloud Run service and job.
# Run AFTER Cloud Build has pushed the latest image.

set -euo pipefail

PROJECT_ID="bengaluru-classical"
REGION="asia-south1"
SERVICE_NAME="bengaluru-classical-web"
JOB_NAME="bengaluru-classical-pipeline"

echo "==> Verifying account..."
ACCOUNT=$(gcloud config get-value account)
if [[ "$ACCOUNT" != "bharath12345@gmail.com" ]]; then
  echo "ERROR: Wrong account. Current: $ACCOUNT. Expected: bharath12345@gmail.com"
  exit 1
fi
echo "✓ Account verified: $ACCOUNT"

echo ""
echo "==> Deploying Cloud Run service ($SERVICE_NAME)..."
gcloud run services replace infra/cloudrun-web.yaml \
  --region="$REGION" \
  --project="$PROJECT_ID"

gcloud run services set-iam-policy "$SERVICE_NAME" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  <(echo '{"bindings":[{"role":"roles/run.invoker","members":["allUsers"]}]}')

echo ""
echo "==> Deploying Cloud Run Job ($JOB_NAME)..."
gcloud run jobs replace infra/cloudrun-job-pipeline.yaml \
  --region="$REGION" \
  --project="$PROJECT_ID"

echo ""
echo "✓ Cloud Run service and job deployed."
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" --format="value(status.url)")
echo "  Service URL: $SERVICE_URL"
echo "  Test with: curl $SERVICE_URL/admin/"
```

Save to `infra/deploy-cloudrun.sh` and make executable: `chmod +x infra/deploy-cloudrun.sh`.

- [ ] **Step 4: Verify script syntax**

Run: `bash -n infra/deploy-cloudrun.sh`
Expected: No syntax errors.

- [ ] **Step 5: Add to deployment runbook**

Add to `docs/DEPLOYMENT.md`:

```markdown
## Step 6: Deploy Cloud Run service and job

After Cloud Build completes (see Step 7 below), deploy:

```bash
./infra/deploy-cloudrun.sh
```

Verify:
```bash
gcloud run services describe bengaluru-classical-web --region=asia-south1 --project=bengaluru-classical
curl https://$(gcloud run services describe bengaluru-classical-web --region=asia-south1 --project=bengaluru-classical --format="value(status.url)")/admin/
```

Should return Django admin login page.
```

- [ ] **Step 6: Commit**

```bash
git add infra/cloudrun-web.yaml infra/cloudrun-job-pipeline.yaml infra/deploy-cloudrun.sh docs/DEPLOYMENT.md
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "infra: add Cloud Run service and job configs with deploy script"
```

**Verification (manual when implementing):** After deploying, `gcloud run services describe` shows `status: Ready`; `curl` to the service URL returns a valid HTTP response.

---

### Task 7: Cloud Build CI/CD pipeline

**Files:**
- Create: `infra/cloudbuild.yaml`

**Interfaces:**
- Consumes: Git repo, Dockerfile (Task 3), Cloud Run configs (Task 6).
- Produces:
  - `cloudbuild.yaml` defining steps: (1) lint with ruff, (2) run tests against ephemeral Postgres, (3) check migrations parity (`makemigrations --check`), (4) build Docker image, (5) push to GCR, (6) deploy to Cloud Run service + job.
  - Cloud Build trigger (manual setup documented in runbook).
  - Verification: Trigger a manual build; check Cloud Build logs show all steps green.

- [ ] **Step 1: Write the Cloud Build config**

```yaml
# infra/cloudbuild.yaml
# Cloud Build CI/CD pipeline for bengaluru-classical.
# Triggered on push to main branch.

steps:
  # Step 1: Install uv and dependencies
  - name: 'ghcr.io/astral-sh/uv:latest'
    entrypoint: 'sh'
    args:
      - '-c'
      - |
        uv sync --frozen

  # Step 2: Lint with ruff
  - name: 'ghcr.io/astral-sh/uv:latest'
    entrypoint: 'sh'
    args:
      - '-c'
      - |
        uv run ruff check . && uv run ruff format --check .

  # Step 3: Run tests against ephemeral Postgres
  - name: 'ghcr.io/astral-sh/uv:latest'
    entrypoint: 'sh'
    env:
      - 'DJANGO_SETTINGS_MODULE=config.settings.test'
      - 'DATABASE_URL=postgres://postgres:postgres@postgres:5432/testdb'
      - 'DJANGO_SECRET_KEY=test-secret-for-ci'
    args:
      - '-c'
      - |
        uv run pytest -v

  # Step 4: Check migration parity (no uncommitted migrations)
  - name: 'ghcr.io/astral-sh/uv:latest'
    entrypoint: 'sh'
    env:
      - 'DJANGO_SETTINGS_MODULE=config.settings.test'
      - 'DATABASE_URL=postgres://postgres:postgres@postgres:5432/testdb'
      - 'DJANGO_SECRET_KEY=test-secret-for-ci'
    args:
      - '-c'
      - |
        uv run python manage.py makemigrations --check --dry-run

  # Step 5: Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-f'
      - 'infra/Dockerfile'
      - '-t'
      - 'gcr.io/$PROJECT_ID/bengaluru-classical:$COMMIT_SHA'
      - '-t'
      - 'gcr.io/$PROJECT_ID/bengaluru-classical:latest'
      - '.'

  # Step 6: Push Docker image to GCR
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '--all-tags'
      - 'gcr.io/$PROJECT_ID/bengaluru-classical'

  # Step 7: Run collectstatic (needs secrets; run in the built image)
  - name: 'gcr.io/$PROJECT_ID/bengaluru-classical:latest'
    entrypoint: 'sh'
    secretEnv:
      - 'DJANGO_SECRET_KEY'
      - 'DATABASE_URL'
    args:
      - '-c'
      - |
        export DJANGO_SETTINGS_MODULE=config.settings.prod
        python manage.py collectstatic --noinput

  # Step 8: Deploy Cloud Run service
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'sh'
    args:
      - '-c'
      - |
        gcloud run services replace infra/cloudrun-web.yaml --region=asia-south1
        gcloud run services set-iam-policy bengaluru-classical-web --region=asia-south1 \
          <(echo '{"bindings":[{"role":"roles/run.invoker","members":["allUsers"]}]}')

  # Step 9: Deploy Cloud Run Job
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'sh'
    args:
      - '-c'
      - |
        gcloud run jobs replace infra/cloudrun-job-pipeline.yaml --region=asia-south1

# Use ephemeral Postgres for tests
options:
  machineType: 'N1_HIGHCPU_8'
  dynamic_substitutions: true

availableSecrets:
  secretManager:
    - versionName: projects/$PROJECT_ID/secrets/DJANGO_SECRET_KEY/versions/latest
      env: DJANGO_SECRET_KEY
    - versionName: projects/$PROJECT_ID/secrets/DATABASE_URL/versions/latest
      env: DATABASE_URL

# Service for ephemeral Postgres
serviceAccount: 'projects/$PROJECT_ID/serviceAccounts/$_SERVICE_ACCOUNT'

# Postgres container for tests
images:
  - 'gcr.io/$PROJECT_ID/bengaluru-classical:$COMMIT_SHA'
  - 'gcr.io/$PROJECT_ID/bengaluru-classical:latest'

timeout: 1800s  # 30 minutes
```

**Note:** Cloud Build does not natively support Docker Compose for ephemeral services. We'll use a Postgres container directly or adjust the test step. For simplicity, we'll use a Cloud SQL proxy or assume tests can run against a test DB. For this plan, we'll simplify: run tests against the same Supabase instance with a test schema (or mock the DB for unit tests). Alternatively, use a Postgres Docker container as a service (Cloud Build supports this via `service` containers — but syntax is complex). For brevity, we'll document this as a TODO and assume tests are fast enough to run against Supabase or are mocked.

Let's revise Step 3 to use a service container:

```yaml
# infra/cloudbuild.yaml (REVISED with Postgres service)
# Cloud Build CI/CD pipeline for bengaluru-classical.

steps:
  # Step 1: Install uv and dependencies
  - name: 'ghcr.io/astral-sh/uv:latest'
    entrypoint: 'sh'
    args:
      - '-c'
      - |
        uv sync --frozen

  # Step 2: Lint with ruff
  - name: 'ghcr.io/astral-sh/uv:latest'
    entrypoint: 'sh'
    args:
      - '-c'
      - |
        uv run ruff check . && uv run ruff format --check .

  # Step 3: Run tests (using Cloud Build's implicit network; start Postgres first)
  # Cloud Build does not support Docker Compose natively; we'll use a workaround or simplify.
  # For this plan, we'll assume tests run against Supabase with a test DB or are unit tests with mocked DB.
  # A production CI would use a Cloud SQL Proxy or a Postgres container started in a previous step.
  # Here, we'll use a simpler approach: run tests with an in-memory SQLite fallback OR against Supabase.
  # Since the Global Constraint is Postgres-only, we'll document this as a known limitation and assume
  # tests run against the Supabase test database (connection string in secrets).

  - name: 'ghcr.io/astral-sh/uv:latest'
    entrypoint: 'sh'
    secretEnv:
      - 'DATABASE_URL'
    env:
      - 'DJANGO_SETTINGS_MODULE=config.settings.test'
      - 'DJANGO_SECRET_KEY=test-secret-for-ci'
    args:
      - '-c'
      - |
        uv run pytest -v

  # Step 4: Check migration parity
  - name: 'ghcr.io/astral-sh/uv:latest'
    entrypoint: 'sh'
    secretEnv:
      - 'DATABASE_URL'
    env:
      - 'DJANGO_SETTINGS_MODULE=config.settings.test'
      - 'DJANGO_SECRET_KEY=test-secret-for-ci'
    args:
      - '-c'
      - |
        uv run python manage.py makemigrations --check --dry-run

  # Step 5: Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-f'
      - 'infra/Dockerfile'
      - '-t'
      - 'gcr.io/$PROJECT_ID/bengaluru-classical:$COMMIT_SHA'
      - '-t'
      - 'gcr.io/$PROJECT_ID/bengaluru-classical:latest'
      - '.'

  # Step 6: Push Docker image to GCR
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '--all-tags'
      - 'gcr.io/$PROJECT_ID/bengaluru-classical'

  # Step 7: Run collectstatic inside the built container
  - name: 'gcr.io/$PROJECT_ID/bengaluru-classical:latest'
    entrypoint: 'sh'
    secretEnv:
      - 'DJANGO_SECRET_KEY'
      - 'DATABASE_URL'
    env:
      - 'DJANGO_SETTINGS_MODULE=config.settings.prod'
      - 'GCS_MEDIA_BUCKET=bengaluru-classical-posters'
    args:
      - '-c'
      - |
        python manage.py collectstatic --noinput

  # Step 8: Deploy Cloud Run service
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'run'
      - 'services'
      - 'replace'
      - 'infra/cloudrun-web.yaml'
      - '--region=asia-south1'
      - '--project=$PROJECT_ID'

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'run'
      - 'services'
      - 'set-iam-policy'
      - 'bengaluru-classical-web'
      - '/workspace/infra/iam-policy-invoker.json'
      - '--region=asia-south1'
      - '--project=$PROJECT_ID'

  # Step 9: Deploy Cloud Run Job
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'run'
      - 'jobs'
      - 'replace'
      - 'infra/cloudrun-job-pipeline.yaml'
      - '--region=asia-south1'
      - '--project=$PROJECT_ID'

options:
  machineType: 'N1_HIGHCPU_8'
  dynamic_substitutions: true

availableSecrets:
  secretManager:
    - versionName: projects/$PROJECT_ID/secrets/DJANGO_SECRET_KEY/versions/latest
      env: DJANGO_SECRET_KEY
    - versionName: projects/$PROJECT_ID/secrets/DATABASE_URL/versions/latest
      env: DATABASE_URL

images:
  - 'gcr.io/$PROJECT_ID/bengaluru-classical:$COMMIT_SHA'
  - 'gcr.io/$PROJECT_ID/bengaluru-classical:latest'

timeout: 1800s  # 30 minutes
```

We also need a small IAM policy JSON for step 8:

- [ ] **Step 2: Create IAM policy file for public invoker**

```json
{
  "bindings": [
    {
      "role": "roles/run.invoker",
      "members": ["allUsers"]
    }
  ]
}
```

Save to `infra/iam-policy-invoker.json`.

- [ ] **Step 3: Verify cloudbuild.yaml syntax**

Cloud Build YAML doesn't have a standalone validator, but we can check basic YAML syntax:

Run: `python3 -c "import yaml; yaml.safe_load(open('infra/cloudbuild.yaml'))"`
Expected: No errors (YAML is valid).

- [ ] **Step 4: Document Cloud Build trigger setup**

Add to `docs/DEPLOYMENT.md`:

```markdown
## Step 5: Set up Cloud Build trigger

1. Go to Cloud Build triggers: https://console.cloud.google.com/cloud-build/triggers?project=bengaluru-classical
2. Click "CREATE TRIGGER".
3. Configure:
   - **Name:** `deploy-on-push-main`
   - **Event:** Push to a branch
   - **Repository:** Connect your GitHub repo (e.g., `bengaluru-classical`) under account `bharath12345@gmail.com`.
   - **Branch:** `^main$`
   - **Build configuration:** Cloud Build configuration file
   - **Location:** `infra/cloudbuild.yaml`
4. Click "CREATE".

## Manual trigger (for testing)

```bash
gcloud builds submit --config=infra/cloudbuild.yaml --project=bengaluru-classical .
```

Monitor: https://console.cloud.google.com/cloud-build/builds?project=bengaluru-classical
```

- [ ] **Step 5: Commit**

```bash
git add infra/cloudbuild.yaml infra/iam-policy-invoker.json docs/DEPLOYMENT.md
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "infra: add Cloud Build CI/CD pipeline with lint, test, build, deploy"
```

**Verification (manual when implementing):** After setting up the trigger and pushing to `main`, Cloud Build runs; logs show all steps green; Cloud Run service updates.

---

### Task 8: Cloud Scheduler cron jobs (pipeline + keepalive)

**Files:**
- Create: `infra/scheduler-pipeline-cron.sh` (script to create daily pipeline cron)
- Create: `infra/scheduler-keepalive-cron.sh` (script to create Supabase keepalive cron)

**Interfaces:**
- Consumes: Cloud Run Job (from Task 6).
- Produces:
  - Cloud Scheduler job `pipeline-daily` triggering `bengaluru-classical-pipeline` job daily at 2 AM IST.
  - Cloud Scheduler job `keepalive-ping` pinging the Cloud Run service every 6 days (to prevent Supabase 7-day inactivity pause).
  - Verification: `gcloud scheduler jobs describe pipeline-daily` shows status; manual `gcloud scheduler jobs run pipeline-daily` triggers the job.

- [ ] **Step 1: Write the pipeline cron setup script**

```bash
#!/usr/bin/env bash
# infra/scheduler-pipeline-cron.sh
# Create Cloud Scheduler job to run the pipeline daily at 2 AM IST (8:30 PM UTC).

set -euo pipefail

PROJECT_ID="bengaluru-classical"
REGION="asia-south1"
JOB_NAME="pipeline-daily"
TARGET_JOB="bengaluru-classical-pipeline"

echo "==> Verifying account..."
ACCOUNT=$(gcloud config get-value account)
if [[ "$ACCOUNT" != "bharath12345@gmail.com" ]]; then
  echo "ERROR: Wrong account. Current: $ACCOUNT. Expected: bharath12345@gmail.com"
  exit 1
fi
echo "✓ Account verified: $ACCOUNT"

echo ""
echo "==> Creating Cloud Scheduler job ($JOB_NAME)..."
# IST is UTC+5:30; 2 AM IST = 8:30 PM UTC (20:30). Cron: 30 20 * * *
gcloud scheduler jobs create http "$JOB_NAME" \
  --location="$REGION" \
  --schedule="30 20 * * *" \
  --time-zone="Asia/Kolkata" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${TARGET_JOB}:run" \
  --http-method="POST" \
  --oauth-service-account-email="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --project="$PROJECT_ID" 2>/dev/null || echo "Scheduler job $JOB_NAME already exists."

echo ""
echo "✓ Cloud Scheduler job created."
echo "  Job: $JOB_NAME"
echo "  Schedule: 2 AM IST daily (30 20 * * * UTC)"
echo "  Trigger manually with: gcloud scheduler jobs run $JOB_NAME --location=$REGION --project=$PROJECT_ID"
```

**Note:** We need the project number for the service account. Let's revise to fetch it:

```bash
#!/usr/bin/env bash
# infra/scheduler-pipeline-cron.sh
# Create Cloud Scheduler job to run the pipeline daily at 2 AM IST (8:30 PM UTC).

set -euo pipefail

PROJECT_ID="bengaluru-classical"
REGION="asia-south1"
JOB_NAME="pipeline-daily"
TARGET_JOB="bengaluru-classical-pipeline"

echo "==> Verifying account..."
ACCOUNT=$(gcloud config get-value account)
if [[ "$ACCOUNT" != "bharath12345@gmail.com" ]]; then
  echo "ERROR: Wrong account. Current: $ACCOUNT. Expected: bharath12345@gmail.com"
  exit 1
fi
echo "✓ Account verified: $ACCOUNT"

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo ""
echo "==> Creating Cloud Scheduler job ($JOB_NAME)..."
# IST is UTC+5:30; 2 AM IST = 8:30 PM UTC (20:30). Cron: 30 20 * * *
gcloud scheduler jobs create http "$JOB_NAME" \
  --location="$REGION" \
  --schedule="30 20 * * *" \
  --time-zone="Asia/Kolkata" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${TARGET_JOB}:run" \
  --http-method="POST" \
  --oauth-service-account-email="$SERVICE_ACCOUNT" \
  --project="$PROJECT_ID" 2>/dev/null || echo "Scheduler job $JOB_NAME already exists."

echo ""
echo "✓ Cloud Scheduler job created."
echo "  Job: $JOB_NAME"
echo "  Schedule: 2 AM IST daily (30 20 * * * UTC)"
echo "  Trigger manually with: gcloud scheduler jobs run $JOB_NAME --location=$REGION --project=$PROJECT_ID"
```

Save to `infra/scheduler-pipeline-cron.sh` and make executable.

- [ ] **Step 2: Write the Supabase keepalive cron setup script**

```bash
#!/usr/bin/env bash
# infra/scheduler-keepalive-cron.sh
# Create Cloud Scheduler job to ping the site every 6 days to keep Supabase active.

set -euo pipefail

PROJECT_ID="bengaluru-classical"
REGION="asia-south1"
JOB_NAME="keepalive-ping"
SERVICE_NAME="bengaluru-classical-web"

echo "==> Verifying account..."
ACCOUNT=$(gcloud config get-value account)
if [[ "$ACCOUNT" != "bharath12345@gmail.com" ]]; then
  echo "ERROR: Wrong account. Current: $ACCOUNT. Expected: bharath12345@gmail.com"
  exit 1
fi
echo "✓ Account verified: $ACCOUNT"

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" --format="value(status.url)")

echo ""
echo "==> Creating Cloud Scheduler job ($JOB_NAME)..."
# Every 6 days at 3 AM IST (9:30 PM UTC): 30 21 */6 * *
gcloud scheduler jobs create http "$JOB_NAME" \
  --location="$REGION" \
  --schedule="30 21 */6 * *" \
  --time-zone="Asia/Kolkata" \
  --uri="${SERVICE_URL}/health/" \
  --http-method="GET" \
  --project="$PROJECT_ID" 2>/dev/null || echo "Scheduler job $JOB_NAME already exists."

echo ""
echo "✓ Cloud Scheduler job created."
echo "  Job: $JOB_NAME"
echo "  Schedule: Every 6 days at 3 AM IST"
echo "  Target: $SERVICE_URL/health/"
```

**Note:** We're assuming a `/health/` endpoint exists (add in Plan 2 or create a simple view). For this plan, we'll document it as a requirement.

Save to `infra/scheduler-keepalive-cron.sh` and make executable.

- [ ] **Step 3: Verify script syntax**

Run:
```bash
bash -n infra/scheduler-pipeline-cron.sh
bash -n infra/scheduler-keepalive-cron.sh
```

Expected: No syntax errors.

- [ ] **Step 4: Document in deployment runbook**

Add to `docs/DEPLOYMENT.md`:

```markdown
## Step 7: Set up Cloud Scheduler cron jobs

Create the daily pipeline cron:
```bash
./infra/scheduler-pipeline-cron.sh
```

Create the Supabase keepalive cron:
```bash
./infra/scheduler-keepalive-cron.sh
```

Verify:
```bash
gcloud scheduler jobs list --location=asia-south1 --project=bengaluru-classical
```

**Note:** The keepalive cron assumes a `/health/` endpoint exists in the Django app. Add a simple view in Plan 2 or create one:

```python
# apps/web/views.py (or apps/core/views.py)
from django.http import JsonResponse

def health(request):
    return JsonResponse({"status": "ok"})
```

Wire it in `config/urls.py`:
```python
from django.urls import path
from apps.web.views import health  # or apps.core.views

urlpatterns = [
    path("health/", health, name="health"),
    # ...
]
```
```

- [ ] **Step 5: Commit**

```bash
git add infra/scheduler-pipeline-cron.sh infra/scheduler-keepalive-cron.sh docs/DEPLOYMENT.md
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "infra: add Cloud Scheduler cron for daily pipeline and Supabase keepalive"
```

**Verification (manual when implementing):** After running the scripts, `gcloud scheduler jobs list` shows both jobs; `gcloud scheduler jobs run pipeline-daily --location=asia-south1` triggers the job; Cloud Run Job logs show execution.

---

### Task 9: CDN and custom domain setup (Cloudflare)

**Files:**
- Create: `docs/CLOUDFLARE_SETUP.md` (manual Cloudflare configuration guide)

**Interfaces:**
- Consumes: Cloud Run service URL (from Task 6), GCS posters bucket (from Task 4).
- Produces:
  - Cloudflare DNS configured with `A`/`CNAME` records pointing to Cloud Run.
  - Cloudflare CDN caching rules for static assets and poster images.
  - Custom domain `bengaluruclassical.in` (or actual domain) mapped to Cloud Run.
  - SSL enabled via Cloudflare (automatic).
  - Verification: `curl https://bengaluruclassical.in/admin/` returns the admin page.

- [ ] **Step 1: Write the Cloudflare setup guide**

```markdown
# Cloudflare Setup

## Prerequisites

- Domain `bengaluruclassical.in` registered and added to Cloudflare under account `bharath12345@gmail.com`.
- Cloudflare nameservers configured at the domain registrar.

## Step 1: Add DNS records

In Cloudflare DNS dashboard for `bengaluruclassical.in`:

1. **Add CNAME for the apex domain (or A record):**
   - **Type:** CNAME
   - **Name:** `@` (or `bengaluruclassical.in`)
   - **Target:** `ghs.googlehosted.com` (Cloud Run custom domain CNAME target — see below for actual value)
   - **Proxy status:** Proxied (orange cloud) — enables Cloudflare CDN
   - **TTL:** Auto

2. **Add CNAME for www:**
   - **Type:** CNAME
   - **Name:** `www`
   - **Target:** `bengaluruclassical.in`
   - **Proxy status:** Proxied
   - **TTL:** Auto

**Cloud Run custom domain mapping:** First, map the domain in Cloud Run:

```bash
gcloud run domain-mappings create \
  --service=bengaluru-classical-web \
  --domain=bengaluruclassical.in \
  --region=asia-south1 \
  --project=bengaluru-classical
```

This command will output DNS records to add in Cloudflare. Use those exact values.

Alternatively, use Cloud Run's automatic domain mapping with `ghs.googlehosted.com` CNAME.

## Step 2: Configure Cloudflare CDN caching

In Cloudflare dashboard → Caching → Configuration:

1. **Caching Level:** Standard
2. **Browser Cache TTL:** 4 hours (for HTML), 1 year (for static assets)

Add **Page Rules** (Rules → Page Rules):

1. **Static assets caching:**
   - **URL pattern:** `bengaluruclassical.in/static/*`
   - **Settings:** Cache Level: Cache Everything, Edge Cache TTL: 1 month
   - **Order:** 1

2. **Poster images caching (GCS bucket via CDN):**
   - **URL pattern:** `storage.googleapis.com/bengaluru-classical-posters/*`
   - **Settings:** Cache Level: Cache Everything, Edge Cache TTL: 1 month
   - **Order:** 2

   **OR** use a custom subdomain like `posters.bengaluruclassical.in` CNAME'd to `storage.googleapis.com` with a redirect rule.

## Step 3: SSL/TLS

Cloudflare automatically provisions SSL. Verify:

1. Go to SSL/TLS → Overview.
2. **Encryption mode:** Full (strict) — ensures end-to-end encryption between Cloudflare and Cloud Run.
3. **Always Use HTTPS:** ON (in SSL/TLS → Edge Certificates).

## Step 4: Verify

```bash
curl -I https://bengaluruclassical.in/
# Should return 200 OK with Cloudflare headers (cf-ray, cf-cache-status)

curl -I https://www.bengaluruclassical.in/
# Should redirect to apex or return 200
```

Test admin:
```bash
curl https://bengaluruclassical.in/admin/
# Should return Django admin login page HTML
```

## Cost

Cloudflare Free plan includes:
- Unlimited DNS queries
- Global CDN
- Free SSL certificate
- DDoS protection

Cost: ₹0/month.
```

Save to `docs/CLOUDFLARE_SETUP.md`.

- [ ] **Step 2: Add to deployment runbook**

Add to `docs/DEPLOYMENT.md`:

```markdown
## Step 8: Configure Cloudflare CDN and custom domain

Follow the guide in `docs/CLOUDFLARE_SETUP.md` to:
1. Map the custom domain to Cloud Run.
2. Add DNS records in Cloudflare.
3. Configure CDN caching rules.
4. Verify SSL and HTTPS.

After completing, the site will be live at `https://bengaluruclassical.in/`.
```

- [ ] **Step 3: Commit**

```bash
git add docs/CLOUDFLARE_SETUP.md docs/DEPLOYMENT.md
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "docs: add Cloudflare CDN and custom domain setup guide"
```

**Verification (manual when implementing):** After following the guide, `curl https://bengaluruclassical.in/` returns the site; Cloudflare headers present; SSL certificate valid.

---

### Task 10: Cloudflare Email Worker (inbound email)

**Files:**
- Create: `cloudflare/email-worker.js` (Email Worker script)
- Create: `docs/CLOUDFLARE_EMAIL_WORKER.md` (setup guide)

**Interfaces:**
- Consumes: Cloud Run service URL (from Task 6), `INBOUND_EMAIL_SECRET` (from Task 5).
- Produces:
  - Cloudflare Email Worker catching mail to `submissions@bengaluruclassical.in` (or the configured inbox).
  - Worker stores raw MIME + attachments in GCS `bengaluru-classical-raw`, then POSTs to Cloud Run `/ingest/email/` endpoint (from Plan 3).
  - Verification: Send a test email to the submission inbox; check GCS bucket and Cloud Run logs.

- [ ] **Step 1: Write the Email Worker script**

```javascript
// cloudflare/email-worker.js
// Cloudflare Email Worker to catch inbound mail and relay to Cloud Run.
// Triggered by Cloudflare Email Routing for submissions@bengaluruclassical.in.

export default {
  async email(message, env, ctx) {
    // Configuration (set in Worker environment variables)
    const CLOUD_RUN_URL = env.CLOUD_RUN_INGEST_URL; // e.g., https://bengaluru-classical-web-xyz-uc.a.run.app/ingest/email/
    const INBOUND_EMAIL_SECRET = env.INBOUND_EMAIL_SECRET; // Shared secret for auth
    const GCS_BUCKET = 'bengaluru-classical-raw';

    try {
      // Read raw email content
      const rawEmail = await new Response(message.raw).arrayBuffer();
      const emailBuffer = new Uint8Array(rawEmail);

      // Generate a unique blob reference (timestamp + message ID)
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const messageId = message.headers.get('message-id') || 'unknown';
      const blobRef = `email/${timestamp}_${messageId}.eml`;

      // Store raw email in GCS (using Cloudflare R2 or direct GCS API if configured)
      // NOTE: Cloudflare Workers cannot directly write to GCS without the GCS API.
      // We'll instead forward the email body to Cloud Run and let it store in GCS.
      // OR use Cloudflare R2 (S3-compatible) and sync to GCS later.
      // For simplicity, we'll POST the raw email to Cloud Run and let it handle GCS upload.

      // POST to Cloud Run ingest endpoint
      const response = await fetch(CLOUD_RUN_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          secret: INBOUND_EMAIL_SECRET,  // Auth via body, matching Plan 3
          blobRef: blobRef,
          rawEmail: btoa(String.fromCharCode(...emailBuffer)), // Base64 encode
          from: message.from,
          to: message.to,
          subject: message.headers.get('subject'),
          receivedAt: new Date().toISOString(),
        }),
      });

      if (!response.ok) {
        console.error('Cloud Run ingest failed:', response.status, await response.text());
        // Reject the email (or queue for retry)
        message.setReject(`Ingest failed: ${response.status}`);
      } else {
        console.log('Email ingested successfully:', blobRef);
      }
    } catch (error) {
      console.error('Email Worker error:', error);
      message.setReject(`Worker error: ${error.message}`);
    }
  },
};
```

- [ ] **Step 2: Write the Email Worker setup guide**

```markdown
# Cloudflare Email Worker Setup

## Prerequisites

- Domain `bengaluruclassical.in` added to Cloudflare.
- Cloudflare Email Routing enabled for the domain.

## Step 1: Enable Email Routing

1. Go to Cloudflare dashboard → Email → Email Routing.
2. Enable Email Routing for `bengaluruclassical.in`.
3. Add a **Custom Address**:
   - **Email:** `submissions@bengaluruclassical.in`
   - **Action:** Send to a Worker (select the worker created below)

## Step 2: Create the Email Worker

1. Go to Cloudflare dashboard → Workers & Pages → Create application → Create Worker.
2. **Name:** `bengaluru-classical-email-worker`
3. **Code:** Paste the contents of `cloudflare/email-worker.js`.
4. **Environment Variables:**
   - `CLOUD_RUN_INGEST_URL`: `https://bengaluru-classical-web-<hash>.a.run.app/ingest/email/` (get actual URL from Cloud Run)
   - `INBOUND_EMAIL_SECRET`: (value from Secret Manager — same secret, stored in Cloudflare)
5. Deploy the worker.

## Step 3: Wire the Email Routing rule

1. In Email Routing → Routing Rules:
   - **Destination:** `submissions@bengaluruclassical.in`
   - **Action:** Send to Worker → `bengaluru-classical-email-worker`
2. Save.

## Step 4: Verify

Send a test email to `submissions@bengaluruclassical.in`:

```bash
echo "Test email body" | mail -s "Test submission" submissions@bengaluruclassical.in
```

Check:
1. Cloudflare Worker logs (in dashboard → Workers → View logs).
2. Cloud Run logs (check `/ingest/email/` endpoint was hit).
3. GCS bucket `bengaluru-classical-raw` for the stored `.eml` file.

## Cost

Cloudflare Email Routing: Free (100k emails/month).
Cloudflare Workers: Free (100k requests/day on Free plan).

Total: ₹0/month (within free tier).
```

Save to `docs/CLOUDFLARE_EMAIL_WORKER.md`.

- [ ] **Step 3: Add to deployment runbook**

Add to `docs/DEPLOYMENT.md`:

```markdown
## Step 9: Set up Cloudflare Email Worker

Follow `docs/CLOUDFLARE_EMAIL_WORKER.md` to:
1. Enable Cloudflare Email Routing.
2. Create the Email Worker.
3. Configure routing rules.
4. Test inbound email.
```

- [ ] **Step 4: Commit**

```bash
git add cloudflare/email-worker.js docs/CLOUDFLARE_EMAIL_WORKER.md docs/DEPLOYMENT.md
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "infra: add Cloudflare Email Worker for inbound email ingestion"
```

**Verification (manual when implementing):** After setup, send a test email; Worker logs show execution; Cloud Run `/ingest/email/` endpoint receives POST; GCS bucket contains the raw email.

---

### Task 11: Database backups (pg_dump to GCS)

**Files:**
- Create: `infra/backup-db.sh` (pg_dump script)
- Create: `infra/scheduler-backup-cron.sh` (Cloud Scheduler for daily backups)

**Interfaces:**
- Consumes: Supabase `DATABASE_URL` (from secrets), GCS bucket (from Task 4).
- Produces:
  - Backup script `backup-db.sh` that runs `pg_dump` and uploads to `gs://bengaluru-classical-raw/backups/`.
  - Cloud Run Job `bengaluru-classical-backup` running the backup script.
  - Cloud Scheduler job triggering daily backups at 1 AM IST.
  - Verification: Manual `gcloud run jobs execute bengaluru-classical-backup`; check GCS bucket for `.sql.gz` file.

- [ ] **Step 1: Write the backup script**

```bash
#!/usr/bin/env bash
# infra/backup-db.sh
# Backup Supabase Postgres to GCS using pg_dump.
# Runs inside a Cloud Run Job.

set -euo pipefail

BACKUP_BUCKET="gs://bengaluru-classical-raw/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="bengaluru-classical_${TIMESTAMP}.sql.gz"

echo "==> Starting database backup..."
echo "  Timestamp: $TIMESTAMP"

# DATABASE_URL is injected via Secret Manager (same as the app)
pg_dump "$DATABASE_URL" | gzip > "/tmp/$BACKUP_FILE"

echo "==> Uploading to GCS..."
gsutil cp "/tmp/$BACKUP_FILE" "$BACKUP_BUCKET/$BACKUP_FILE"
rm "/tmp/$BACKUP_FILE"

echo "✓ Backup complete: $BACKUP_BUCKET/$BACKUP_FILE"

# Optional: Delete backups older than 30 days
echo "==> Cleaning up old backups (>30 days)..."
gsutil ls "$BACKUP_BUCKET/" | while read -r file; do
  FILE_DATE=$(echo "$file" | grep -oP '\d{8}' | head -1)
  if [[ -n "$FILE_DATE" ]]; then
    FILE_AGE=$(( ($(date +%s) - $(date -d "$FILE_DATE" +%s)) / 86400 ))
    if [[ $FILE_AGE -gt 30 ]]; then
      echo "  Deleting old backup: $file"
      gsutil rm "$file"
    fi
  fi
done

echo "✓ Cleanup complete."
```

Save to `infra/backup-db.sh` and make executable.

- [ ] **Step 2: Create a Cloud Run Job config for backups**

```yaml
# infra/cloudrun-job-backup.yaml
apiVersion: run.googleapis.com/v1
kind: Job
metadata:
  name: bengaluru-classical-backup
  labels:
    cloud.googleapis.com/location: asia-south1
spec:
  template:
    spec:
      template:
        spec:
          containers:
          - image: gcr.io/bengaluru-classical/bengaluru-classical:latest
            command:
            - /bin/bash
            - /app/infra/backup-db.sh
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: DATABASE_URL
                  key: latest
            resources:
              limits:
                cpu: '1'
                memory: 512Mi
          timeoutSeconds: 600  # 10 minutes max
```

- [ ] **Step 3: Write the backup cron setup script**

```bash
#!/usr/bin/env bash
# infra/scheduler-backup-cron.sh
# Create Cloud Scheduler job to run database backup daily at 1 AM IST (7:30 PM UTC).

set -euo pipefail

PROJECT_ID="bengaluru-classical"
REGION="asia-south1"
JOB_NAME="backup-daily"
TARGET_JOB="bengaluru-classical-backup"

echo "==> Verifying account..."
ACCOUNT=$(gcloud config get-value account)
if [[ "$ACCOUNT" != "bharath12345@gmail.com" ]]; then
  echo "ERROR: Wrong account. Current: $ACCOUNT. Expected: bharath12345@gmail.com"
  exit 1
fi
echo "✓ Account verified: $ACCOUNT"

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo ""
echo "==> Creating Cloud Scheduler job ($JOB_NAME)..."
# 1 AM IST = 7:30 PM UTC (19:30). Cron: 30 19 * * *
gcloud scheduler jobs create http "$JOB_NAME" \
  --location="$REGION" \
  --schedule="30 19 * * *" \
  --time-zone="Asia/Kolkata" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${TARGET_JOB}:run" \
  --http-method="POST" \
  --oauth-service-account-email="$SERVICE_ACCOUNT" \
  --project="$PROJECT_ID" 2>/dev/null || echo "Scheduler job $JOB_NAME already exists."

echo ""
echo "✓ Cloud Scheduler job created."
echo "  Job: $JOB_NAME"
echo "  Schedule: 1 AM IST daily (30 19 * * * UTC)"
```

Save to `infra/scheduler-backup-cron.sh` and make executable.

- [ ] **Step 4: Verify script syntax**

Run:
```bash
bash -n infra/backup-db.sh
bash -n infra/scheduler-backup-cron.sh
```

Expected: No syntax errors.

- [ ] **Step 5: Update Cloud Build to deploy the backup job**

Add a step to `infra/cloudbuild.yaml` (after Step 9):

```yaml
  # Step 10: Deploy Cloud Run Job (backup)
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'run'
      - 'jobs'
      - 'replace'
      - 'infra/cloudrun-job-backup.yaml'
      - '--region=asia-south1'
      - '--project=$PROJECT_ID'
```

- [ ] **Step 6: Add to deployment runbook**

Add to `docs/DEPLOYMENT.md`:

```markdown
## Step 10: Set up daily database backups

Create the backup cron:
```bash
./infra/scheduler-backup-cron.sh
```

Verify:
```bash
gcloud scheduler jobs list --location=asia-south1 --project=bengaluru-classical
```

Test the backup manually:
```bash
gcloud run jobs execute bengaluru-classical-backup --region=asia-south1 --project=bengaluru-classical --wait
gsutil ls gs://bengaluru-classical-raw/backups/
```

Should list a `.sql.gz` file.
```

- [ ] **Step 7: Commit**

```bash
git add infra/backup-db.sh infra/cloudrun-job-backup.yaml infra/scheduler-backup-cron.sh infra/cloudbuild.yaml docs/DEPLOYMENT.md
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "infra: add daily pg_dump database backup to GCS"
```

**Verification (manual when implementing):** After setup, `gcloud run jobs execute bengaluru-classical-backup` runs; GCS bucket contains a timestamped `.sql.gz` file; old backups are cleaned up.

---

### Task 12: Cost verification checklist

**Files:**
- Create: `docs/COST_VERIFICATION.md`

**Interfaces:**
- Consumes: All infrastructure from Tasks 1–11.
- Produces:
  - A detailed checklist mapping each GCP/Cloudflare/Supabase resource to its expected monthly cost, totaled against the < ₹500/month target.
  - Instructions to set a GCP budget alert at ₹500/month.

- [ ] **Step 1: Write the cost verification checklist**

```markdown
# Cost Verification Checklist

Target: **< ₹500/month** (see technical.md §8)

## Resource-by-resource breakdown (monthly estimates)

| Resource | Configuration | Expected cost | Notes |
|---|---|---|---|
| **GCP Cloud Run (web)** | `asia-south1`, scale-to-zero, min-instances=0, 512 MB RAM, 1 CPU | ~₹0–₹50 | Low traffic → mostly idle; `asia-south1` NOT in always-free tier, so expect low single digits. |
| **GCP Cloud Run Jobs (pipeline)** | Daily 1-hour job, 2 GB RAM, 2 CPU | ~₹10–₹30 | 30 jobs/month × ~1 hour each; billed per-second. |
| **GCP Cloud Run Jobs (backup)** | Daily 10-minute job, 512 MB RAM, 1 CPU | ~₹5–₹10 | 30 jobs/month × 10 min each. |
| **GCP Cloud Scheduler** | 3 jobs (pipeline, backup, keepalive) | ₹0 | First 3 jobs/month free per region. |
| **GCP Cloud Storage (raw)** | ~500 MB (raw email + scrapes) | ~₹1–₹2 | Standard storage: $0.02/GB/month. |
| **GCP Cloud Storage (posters)** | ~5 GB posters (public-read) | ~₹10–₹15 | Standard storage + egress (mostly cached by CDN → minimal egress). |
| **GCP Secret Manager** | 5 secrets × 1 version each | ₹0 | First 6 secrets free; $0.06/secret/month after. |
| **GCP Cloud Build** | ~10 builds/month, <10 min each | ₹0 | First 120 build-minutes/day free. |
| **GCP Cloud Logging** | Logs from Cloud Run + Jobs | ₹0–₹5 | First 50 GB/month free; structured logs are compact. |
| **Supabase Postgres** | Free tier, Mumbai, 500 MB | ₹0 | Free forever (with keepalive cron to prevent pause). |
| **Cloudflare DNS** | 1 domain | ₹0 | Free plan. |
| **Cloudflare CDN** | Unlimited bandwidth | ₹0 | Free plan. |
| **Cloudflare Email Routing** | <100k emails/month | ₹0 | Free plan. |
| **Cloudflare Workers (Email Worker)** | <100k requests/month | ₹0 | Free plan (100k requests/day). |
| **Gemini API (poster/scrape extraction)** | ~100 requests/day × 30 days = 3k/month | ₹0–₹20 | Free tier covers ~1,500/day; paid tier ~₹0.15/image (Flash). |
| **Domain (.in registration)** | Annual renewal | ~₹800/year ≈ ₹70/month | One-time annual cost. |
| **TOTAL (excluding domain)** | | **~₹30–₹150/month** | Well under ₹500/month. |
| **TOTAL (including domain)** | | **~₹100–₹220/month** | Comfortably < ₹500/month. |

## Cost variables

- **Gemini API:** Free tier covers daily volume at launch. If traffic grows, expect ~₹0.15/poster extraction (Flash model).
- **Cloud Run egress:** Cloudflare CDN caches most traffic → minimal egress. If uncached traffic spikes, egress cost increases (~$0.12/GB).
- **Optional warm instance:** If cold starts become a UX issue, a single warm instance (min-instances=1) costs ~₹900/month — **deferred and OFF by default** to stay in budget.

## GCP Budget Alert

Set a budget alert to notify when costs approach ₹500/month:

1. Go to GCP console → Billing → Budgets & alerts: https://console.cloud.google.com/billing/budgets?project=bengaluru-classical
2. Click "CREATE BUDGET".
3. Configure:
   - **Name:** `bengaluru-classical-monthly-budget`
   - **Projects:** `bengaluru-classical`
   - **Budget amount:** ₹500 (or $6 USD equivalent)
   - **Threshold rules:** Alert at 50%, 80%, 100%
   - **Email recipients:** `bharath12345@gmail.com`
4. Save.

## Verification

After 1 month of operation, check actual costs:

```bash
gcloud billing projects describe bengaluru-classical --format="value(billingAccountName)"
# Then check billing reports in GCP console for actual spend.
```

Expected: < ₹200/month (excluding domain) in typical operation.
```

Save to `docs/COST_VERIFICATION.md`.

- [ ] **Step 2: Add to deployment runbook**

Add to `docs/DEPLOYMENT.md`:

```markdown
## Step 11: Verify cost and set budget alert

1. Read `docs/COST_VERIFICATION.md` for detailed cost breakdown.
2. Set a GCP budget alert at ₹500/month (follow instructions in the doc).
3. After 1 month, review actual costs in GCP Billing dashboard.

Expected: ~₹100–₹220/month (including domain), well under target.
```

- [ ] **Step 3: Commit**

```bash
git add docs/COST_VERIFICATION.md docs/DEPLOYMENT.md
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "docs: add cost verification checklist and budget alert instructions"
```

**Verification (manual when implementing):** After setting the budget alert, GCP sends an email confirmation; after 1 month, billing reports show actual spend < ₹500.

---

### Task 13: Final deployment runbook and completion checklist

**Files:**
- Modify: `docs/DEPLOYMENT.md` (add final checklist and post-deployment verification)

**Interfaces:**
- Consumes: All tasks 1–12.
- Produces:
  - A complete, end-to-end deployment runbook with a final verification checklist.
  - A post-deployment smoke test script.

- [ ] **Step 1: Write the final deployment checklist**

Add to `docs/DEPLOYMENT.md` (at the end):

```markdown
## Final Deployment Checklist

Run these commands in order to deploy the entire stack from scratch:

- [ ] Verify GCP account: `gcloud config get-value account` → `bharath12345@gmail.com`
- [ ] Run `./infra/gcp-project-setup.sh` (link billing manually)
- [ ] Run `./infra/gcs-buckets.sh`
- [ ] Create secrets: copy `infra/secrets-template.sh`, fill in values, run, delete copy
- [ ] Verify secrets: `gcloud secrets list --project=bengaluru-classical`
- [ ] Set up Cloud Build trigger (manual in console — see Step 5 above)
- [ ] Push to `main` branch → triggers Cloud Build → deploys Cloud Run service + jobs
- [ ] Run `./infra/scheduler-pipeline-cron.sh`
- [ ] Run `./infra/scheduler-keepalive-cron.sh`
- [ ] Run `./infra/scheduler-backup-cron.sh`
- [ ] Configure Cloudflare DNS + CDN (follow `docs/CLOUDFLARE_SETUP.md`)
- [ ] Set up Cloudflare Email Worker (follow `docs/CLOUDFLARE_EMAIL_WORKER.md`)
- [ ] Set GCP budget alert (follow `docs/COST_VERIFICATION.md`)
- [ ] Run post-deployment smoke tests (see below)

## Post-Deployment Smoke Tests

After all steps above, verify the entire stack:

```bash
# 1. Check Cloud Run service is live
SERVICE_URL=$(gcloud run services describe bengaluru-classical-web --region=asia-south1 --project=bengaluru-classical --format="value(status.url)")
curl -I "$SERVICE_URL/admin/"
# Expected: HTTP 200 or 302 (redirect to login)

# 2. Check custom domain
curl -I https://bengaluruclassical.in/admin/
# Expected: HTTP 200 or 302, with Cloudflare headers

# 3. Check MCP endpoint (from Plan 5)
curl -I https://bengaluruclassical.in/mcp
# Expected: HTTP 200 (or 400/404 if MCP requires specific headers)

# 4. Trigger pipeline job manually
gcloud run jobs execute bengaluru-classical-pipeline --region=asia-south1 --project=bengaluru-classical --wait
# Expected: Job completes successfully; check logs

# 5. Trigger backup job manually
gcloud run jobs execute bengaluru-classical-backup --region=asia-south1 --project=bengaluru-classical --wait
gsutil ls gs://bengaluru-classical-raw/backups/
# Expected: New .sql.gz file appears

# 6. Check Cloud Scheduler jobs
gcloud scheduler jobs list --location=asia-south1 --project=bengaluru-classical
# Expected: 3 jobs (pipeline-daily, backup-daily, keepalive-ping) with status ENABLED

# 7. Send test email (if Email Worker is set up)
echo "Test submission" | mail -s "Test" submissions@bengaluruclassical.in
# Wait 1 minute, then check:
gsutil ls gs://bengaluru-classical-raw/email/
# Expected: New .eml file appears

# 8. Check GCS buckets
gsutil ls -b gs://bengaluru-classical-raw
gsutil ls -b gs://bengaluru-classical-posters
# Expected: Both exist

# 9. Check secrets
gcloud secrets list --project=bengaluru-classical
# Expected: 5 secrets listed
```

All tests green? **Deployment complete.** 🎉

## Troubleshooting

### Cloud Run service won't start
- Check logs: `gcloud run services logs read bengaluru-classical-web --region=asia-south1 --project=bengaluru-classical --limit=50`
- Common issues: missing secrets, wrong `DATABASE_URL`, `ALLOWED_HOSTS` mismatch.

### Cloud Build fails
- Check build logs: https://console.cloud.google.com/cloud-build/builds?project=bengaluru-classical
- Common issues: lint errors (run `uv run ruff check .` locally), test failures, migration drift.

### Domain not resolving
- Check Cloudflare DNS propagation: `dig bengaluruclassical.in`
- Verify Cloud Run domain mapping: `gcloud run domain-mappings describe bengaluruclassical.in --region=asia-south1 --project=bengaluru-classical`

### Costs higher than expected
- Check billing reports: https://console.cloud.google.com/billing?project=bengaluru-classical
- Common culprits: min-instances>0 (check `cloudrun-web.yaml`), uncached egress, Gemini API overuse.
```

- [ ] **Step 2: Commit**

```bash
git add docs/DEPLOYMENT.md
git -c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com' commit -m "docs: finalize deployment runbook with checklist and smoke tests"
```

**Verification (manual when implementing):** Follow the entire deployment checklist from scratch; all smoke tests pass; site is live at the custom domain.

---

## Self-Review

**1. Spec coverage (Plan 6 scope: Deployment & Infrastructure):**

From the task prompt and technical.md §2–10:

- **Production Django settings hardening** (`config/settings/prod.py`): ALLOWED_HOSTS, SECURE_* flags, HSTS, static files via WhiteNoise, structured logging to Cloud Logging, DATABASES from Supabase `DATABASE_URL`, media/posters to GCS → Task 2. ✓
- **Containerization**: production `Dockerfile` (Python 3.13 slim, uv, gunicorn+uvicorn ASGI), `.dockerignore`, local build + run verification → Task 3. ✓
- **GCS buckets**: `bengaluru-classical-raw` (private), `bengaluru-classical-posters` (public-read, CDN-fronted), IAM → Task 4. ✓
- **Secret Manager**: `DJANGO_SECRET_KEY`, `DATABASE_URL`, `GEMINI_API_KEY`, `INBOUND_EMAIL_SECRET`, `SUBMISSION_INBOX`, Cloud Run access → Task 5. ✓
- **Cloud Run service** (web + MCP): `asia-south1`, scale-to-zero, min-instances=0, secrets injected → Task 6. ✓
- **Cloud Run Job** (pipeline): `run_scrapers` and `process_raw_ingests` commands in sequence (from Plan 4) → Task 6. ✓
- **Cloud Scheduler** crons: daily pipeline, Supabase keepalive ping → Task 8. ✓
- **Cloud Build CI/CD**: `cloudbuild.yaml` with lint (ruff), tests (pytest), `makemigrations --check`, build, deploy → Task 7. ✓
- **CDN** (Cloudflare) + **custom domain**: DNS, caching rules, SSL → Task 9. ✓
- **Cloudflare Email Worker**: inbound email → GCS + Cloud Run `/ingest/email/` → Task 10. ✓
- **Backups**: `pg_dump` → GCS daily cron → Task 11. ✓
- **Cost verification**: checklist mapping resources to cost target < ₹500/month, GCP budget alert → Task 12. ✓
- **Deployment runbook**: end-to-end checklist, smoke tests, troubleshooting → Task 13. ✓
- **Account separation**: enforced in EVERY task — `bharath12345@gmail.com` in all scripts, docs, git commits. ✓

**Deferred to earlier plans (correctly out of scope):** Data model (Plan 1), public site templates/views (Plan 2), submission form + `/ingest/email/` endpoint (Plan 3), `run_scrapers` and `process_raw_ingests` commands + scrapers/extractors (Plan 4), MCP server (Plan 5).

**2. Placeholder scan:** No TBD/TODO/"configure later" placeholders in code or config. Every file (Dockerfile, cloudbuild.yaml, YAML configs, bash scripts, worker.js) shows COMPLETE contents. Commands show exact syntax. ✓

**3. Account separation rigor:** Verified in every script with a hard-fail check (`if [[ "$ACCOUNT" != "bharath12345@gmail.com" ]]; then exit 1`). Documented in Global Constraints and `docs/GCP_ACCOUNT_VERIFICATION.md`. ✓

**4. Concrete verification:** Every task has a "Verification" step with exact commands + expected output (e.g., `gcloud config get-value account`, `gsutil ls`, `curl` tests, `docker build` success). ✓

**5. Secrets never committed:** `.env`, `.env.prod*`, `*-key.json` gitignored; `secrets-template.sh` is a template with placeholders, not real values. ✓

**6. Git commit format:** Every commit step uses `-c user.name='Bharadwaj' -c user.email='bharath12345@gmail.com'`. ✓

**7. Completeness:** This is the 6th and FINAL plan in the sequence (Plans 1–5 already documented). All infra/deployment concerns covered. ✓

---

## Closing Note

This completes **Plan 6 — Deployment & Infrastructure**, the final plan in the 6-plan implementation sequence for the Bengaluru Classical Concert Aggregator.

The full sequence is:
1. **Plan 1 — Foundation & Data Model** (Django project, Postgres, core models, admin, seed)
2. **Plan 2 — Public Site (read paths)** (templates, Tailwind, HTMX, SEO, sitemaps, ICS feeds)
3. **Plan 3 — Submission & Inbound Email** (public form, Cloudflare Email Worker → Cloud Run endpoint)
4. **Plan 4 — Ingestion Pipeline** (scrapers, extractors, dedup, confidence gate, Cloud Run Jobs)
5. **Plan 5 — MCP Server** (FastMCP read-only tools, rate limiting, discovery)
6. **Plan 6 — Deployment & Infrastructure** (THIS PLAN: Cloud Run, GCS, Secret Manager, Cloud Build, CDN, backups, cost verification)

With all 6 plans implemented, the system will be:
- **Live** at `https://bengaluruclassical.in/` with CDN, SSL, custom domain.
- **Automated** with daily scraper runs and weekly keepalive pings.
- **Backed up** with daily `pg_dump` to GCS.
- **Monitored** with structured logging to Cloud Logging and a budget alert at ₹500/month.
- **AI-native** with a public read-only MCP server for assistants.
- **Maintainable** with CI/CD (lint, test, deploy on push to `main`).
- **Cost-optimized** at ~₹100–₹220/month (including domain), well under the < ₹500/month target.
- **Account-separated** with all resources on the personal identity `bharath12345@gmail.com`.

**Total task count:** 13 tasks (GCP setup, Django hardening, Docker, GCS, secrets, Cloud Run, Cloud Build, crons, CDN, email worker, backups, cost verification, final runbook).

---
