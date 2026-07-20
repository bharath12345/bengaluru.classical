#!/usr/bin/env bash
# One-time GCP project setup for bengaluru-classical.
# Run AFTER verifying gcloud account is bharath12345@gmail.com.
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

echo "==> Creating project $PROJECT_ID (idempotent)..."
gcloud projects create "$PROJECT_ID" --name="Bengaluru Classical" --set-as-default || true

gcloud config set project "$PROJECT_ID"
gcloud config set compute/region "$REGION"

echo "MANUAL: Link PERSONAL billing at"
echo "https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
read -r -p "Press Enter after billing is linked..."

echo "==> Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  logging.googleapis.com \
  artifactregistry.googleapis.com

echo "✓ Project setup complete."
