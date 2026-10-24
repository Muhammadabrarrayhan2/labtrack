#!/usr/bin/env bash
# PaaS routine: rotate the JWT signing secret and roll out a new Cloud Run revision.
#
# Usage: scripts/ops/rotate-secret.sh
#
# Effect: every token signed with the old secret becomes invalid, so all users must log in
# again. Do this outside practicum hours. Cloud Run reads secret version "latest" when an
# instance starts, which is why a new revision is forced.
set -euo pipefail
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"

SECRET=labtrack-jwt-secret

step "Current versions of $SECRET"
run gcloud secrets versions list "$SECRET" --project="$PROJECT_ID" --limit=3

step "Adding a new random version (48 characters, value not printed)"
NEW_VALUE=$(openssl rand -base64 64 | tr -dc 'A-Za-z0-9' | head -c 48)
printf '%s' "$NEW_VALUE" |
  run gcloud secrets versions add "$SECRET" --project="$PROJECT_ID" --data-file=-
unset NEW_VALUE

step "Forcing a new revision so every instance loads the new secret"
run gcloud run services update "$SERVICE" --project="$PROJECT_ID" --region="$REGION" \
  --update-labels="jwt-rotated-at=$(date -u +%Y%m%d-%H%M%S)" --quiet

step "Smoke test"
URL=$(gcloud run services describe "$SERVICE" --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)')
run curl -fsS "$URL/health"
echo
echo "Rotated. Old versions stay enabled but unused; disable one with:"
echo "  gcloud secrets versions disable <version> --secret=$SECRET --project=$PROJECT_ID"
