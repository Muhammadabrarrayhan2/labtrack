# shellcheck shell=bash
# Shared helpers for scripts/ops. Sourced, not executed.
#
# Every script reads its target from the environment:
#   PROJECT_ID  GCP project (required)
#   REGION      GCP region (default asia-southeast2)
#   SERVICE     Cloud Run service (default labtrack-api)
#   ZONE        Zone of the ops VM (default <REGION>-a)
#   VM_NAME     Ops VM name (default labtrack-ops)

: "${PROJECT_ID:?Set PROJECT_ID, for example: export PROJECT_ID=labtrack-123456}"
REGION="${REGION:-asia-southeast2}"
SERVICE="${SERVICE:-labtrack-api}"
ZONE="${ZONE:-$REGION-a}"
VM_NAME="${VM_NAME:-labtrack-ops}"
export PROJECT_ID REGION SERVICE ZONE VM_NAME

# Print a step header
step() {
  printf '\n==> %s\n' "$*"
}

# Print a command, then run it, so the terminal output doubles as an operations log
run() {
  printf '+ %s\n' "$*"
  "$@"
}

# Name of the Cloud SQL instance created by Terraform (labtrack-db-<suffix>)
sql_instance() {
  local name
  name=$(gcloud sql instances list --project="$PROJECT_ID" \
    --filter='name ~ ^labtrack-db-' --format='value(name)' --limit=1)
  if [ -z "$name" ]; then
    echo "No Cloud SQL instance named labtrack-db-* in project $PROJECT_ID" >&2
    return 1
  fi
  printf '%s\n' "$name"
}

# UTC timestamp for names and log lines
stamp() {
  date -u +%Y%m%dT%H%M%SZ
}
