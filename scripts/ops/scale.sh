#!/usr/bin/env bash
# PaaS routine: change Cloud Run min/max instances, for example min 1 during practicum
# hours to avoid cold starts, and back to min 0 afterwards.
#
# Usage: scripts/ops/scale.sh <min> <max>
#
# Terraform also manages these values (main.tf), so the next `terraform apply` resets them.
# Keep max x 7 DB connections below the Cloud SQL limit (25 on db-f1-micro).
set -euo pipefail
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"

MIN="${1:?Usage: scale.sh <min> <max>}"
MAX="${2:?Usage: scale.sh <min> <max>}"
CONN_PER_INSTANCE=7 # pool_size 5 + max_overflow 2 in app/database.py
CONN_LIMIT=25

if [ "$MIN" -gt "$MAX" ]; then
  echo "min ($MIN) must not exceed max ($MAX)" >&2
  exit 1
fi
NEEDED=$((MAX * CONN_PER_INSTANCE))
if [ "$NEEDED" -ge "$CONN_LIMIT" ]; then
  echo "WARNING: $MAX instances x $CONN_PER_INSTANCE connections = $NEEDED, at or above the db-f1-micro limit of $CONN_LIMIT" >&2
fi
if [ "$MIN" -gt 0 ]; then
  echo "NOTE: min $MIN keeps instances warm and is billed while idle"
fi

step "Scaling $SERVICE to min=$MIN max=$MAX"
run gcloud run services update "$SERVICE" --project="$PROJECT_ID" --region="$REGION" \
  --min-instances="$MIN" --max-instances="$MAX" --quiet

step "Result"
run gcloud run services describe "$SERVICE" --project="$PROJECT_ID" --region="$REGION" \
  --format='yaml(spec.template.metadata.annotations)'
