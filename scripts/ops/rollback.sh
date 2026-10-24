#!/usr/bin/env bash
# PaaS routine: roll Cloud Run back to the previous revision by shifting 100% of traffic.
#
# Usage:
#   scripts/ops/rollback.sh               # previous revision (the one before the serving one)
#   scripts/ops/rollback.sh <revision>    # a specific revision
#   scripts/ops/rollback.sh --to-latest   # undo: send traffic back to the newest revision
#
# Note: after a rollback, traffic is pinned to that revision and new deploys receive no
# traffic until you run --to-latest.
set -euo pipefail
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"

GC=(--project="$PROJECT_ID" --region="$REGION")

if [ "${1:-}" = "--to-latest" ]; then
  step "Sending 100% of traffic to the latest revision of $SERVICE"
  run gcloud run services update-traffic "$SERVICE" "${GC[@]}" --to-latest
  exit 0
fi

step "Current traffic split"
run gcloud run services describe "$SERVICE" "${GC[@]}" \
  --format='table(status.traffic.revisionName,status.traffic.percent)'

if [ -n "${1:-}" ]; then
  TARGET="$1"
else
  CURRENT=$(gcloud run services describe "$SERVICE" "${GC[@]}" \
    --format='value(status.traffic[0].revisionName)')
  # Revisions newest first; take the first one after the serving revision
  TARGET=$(gcloud run revisions list --service="$SERVICE" "${GC[@]}" \
    --sort-by='~metadata.creationTimestamp' --format='value(metadata.name)' |
    awk -v cur="$CURRENT" 'found { print; exit } $0 == cur { found = 1 }')
  if [ -z "$TARGET" ]; then
    echo "No revision older than $CURRENT, nothing to roll back to" >&2
    exit 1
  fi
  echo "Serving revision: $CURRENT"
fi

step "Shifting 100% of traffic to $TARGET"
run gcloud run services update-traffic "$SERVICE" "${GC[@]}" --to-revisions="$TARGET=100"

step "Smoke test"
URL=$(gcloud run services describe "$SERVICE" "${GC[@]}" --format='value(status.url)')
run curl -fsS "$URL/health"
echo
echo "Rolled back to $TARGET. Run 'scripts/ops/rollback.sh --to-latest' after the fix is deployed."
