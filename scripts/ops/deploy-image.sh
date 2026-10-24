#!/usr/bin/env bash
# PaaS routine: deploy a container image to Cloud Run as a new revision.
# The usual path is GitHub Actions; this script is the manual fallback.
#
# Usage:
#   scripts/ops/deploy-image.sh <tag|full-image-uri>
#   scripts/ops/deploy-image.sh --build <tag>   # build from the repo with Cloud Build first
set -euo pipefail
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"

BUILD=false
if [ "${1:-}" = "--build" ]; then
  BUILD=true
  shift
fi
TARGET="${1:?Usage: deploy-image.sh [--build] <tag|image-uri>}"

if [[ "$TARGET" == *"/"* ]]; then
  IMAGE="$TARGET"
else
  IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/labtrack/api:$TARGET"
fi

if [ "$BUILD" = true ]; then
  step "Building $IMAGE with Cloud Build"
  run gcloud builds submit --project="$PROJECT_ID" --tag "$IMAGE" "$(dirname "$0")/../.."
fi

step "Deploying $IMAGE to Cloud Run service $SERVICE"
run gcloud run deploy "$SERVICE" --project="$PROJECT_ID" --region="$REGION" --image="$IMAGE" --quiet

step "Smoke test"
URL=$(gcloud run services describe "$SERVICE" --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)')
run curl -fsS "$URL/health"
echo
echo "Deployed. Revisions:"
run gcloud run revisions list --service="$SERVICE" --project="$PROJECT_ID" --region="$REGION" --limit=3
