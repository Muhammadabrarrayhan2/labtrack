#!/usr/bin/env bash
# PaaS routine: take an on-demand Cloud SQL backup, for example before a schema change,
# a risky deploy or an assessment. On-demand backups are kept until deleted.
#
# Usage: scripts/ops/sql-backup-now.sh ["description"]
set -euo pipefail
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"

INSTANCE=$(sql_instance)
DESCRIPTION="${1:-On-demand backup $(stamp)}"

step "Creating backup of $INSTANCE: $DESCRIPTION"
run gcloud sql backups create --instance="$INSTANCE" --project="$PROJECT_ID" --description="$DESCRIPTION"

step "Latest backups"
run gcloud sql backups list --instance="$INSTANCE" --project="$PROJECT_ID" --limit=5 \
  --format='table(id,windowStartTime,type,status,description)'
