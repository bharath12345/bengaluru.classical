#!/usr/bin/env bash
# Create GCS buckets for raw ingests and posters.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-bengaluru-classical}"
REGION="${REGION:-asia-south1}"
RAW_BUCKET="${RAW_BUCKET:-bengaluru-classical-raw}"
POSTERS_BUCKET="${POSTERS_BUCKET:-bengaluru-classical-posters}"

ACCOUNT=$(gcloud config get-value account)
if [[ "$ACCOUNT" != "bharath12345@gmail.com" ]]; then
  echo "ERROR: Wrong account: $ACCOUNT"
  exit 1
fi

gcloud storage buckets create "gs://${RAW_BUCKET}" \
  --project="$PROJECT_ID" --location="$REGION" --uniform-bucket-level-access || true

gcloud storage buckets create "gs://${POSTERS_BUCKET}" \
  --project="$PROJECT_ID" --location="$REGION" --uniform-bucket-level-access || true

# Public read for posters
gcloud storage buckets add-iam-policy-binding "gs://${POSTERS_BUCKET}" \
  --member=allUsers --role=roles/storage.objectViewer || true

echo "✓ Buckets ready: gs://${RAW_BUCKET}, gs://${POSTERS_BUCKET}"
