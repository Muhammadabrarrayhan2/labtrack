#!/usr/bin/env bash
# PaaS routine: start or stop the Cloud SQL instance without deleting data.
# Stopping saves the instance-hour cost (storage is still billed). While stopped,
# /health returns 503, which is also how the incident simulation in
# docs/06-sop-dukungan-teknis.md is triggered.
#
# Usage: scripts/ops/sql-start-stop.sh start|stop|status
set -euo pipefail
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"

ACTION="${1:?Usage: sql-start-stop.sh start|stop|status}"
INSTANCE=$(sql_instance)

case "$ACTION" in
  start) POLICY=ALWAYS ;;
  stop) POLICY=NEVER ;;
  status) POLICY="" ;;
  *)
    echo "Unknown action: $ACTION (use start, stop or status)" >&2
    exit 1
    ;;
esac

if [ -n "$POLICY" ]; then
  step "$(date -u +%FT%TZ) setting activation policy of $INSTANCE to $POLICY"
  run gcloud sql instances patch "$INSTANCE" --project="$PROJECT_ID" --activation-policy="$POLICY" --quiet
fi

step "Status of $INSTANCE"
run gcloud sql instances describe "$INSTANCE" --project="$PROJECT_ID" \
  --format='table(name,state,settings.activationPolicy,settings.tier)'
