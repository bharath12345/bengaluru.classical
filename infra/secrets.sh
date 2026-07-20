#!/usr/bin/env bash
# TEMPLATE: create Secret Manager secrets (values entered interactively).
# Do NOT commit secret values.
set -euo pipefail

ACCOUNT=$(gcloud config get-value account)
if [[ "$ACCOUNT" != "bharath12345@gmail.com" ]]; then
  echo "ERROR: Wrong account: $ACCOUNT"
  exit 1
fi

SECRETS=(
  DJANGO_SECRET_KEY
  DATABASE_URL
  GEMINI_API_KEY
  INBOUND_EMAIL_SECRET
  EMAIL_HOST_PASSWORD
)

for name in "${SECRETS[@]}"; do
  echo "Creating/updating secret: $name"
  read -r -s -p "Value for $name: " value
  echo
  printf '%s' "$value" | gcloud secrets create "$name" --data-file=- 2>/dev/null \
    || printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=-
done

echo "✓ Secrets created."
