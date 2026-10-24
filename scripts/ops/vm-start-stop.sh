#!/usr/bin/env bash
# IaaS routine: start or stop the labtrack-ops VM. A stopped VM is not billed for vCPU or
# memory; its disk and snapshots still are. The nightly backup timer has Persistent=true,
# so a missed run is executed shortly after the next start.
#
# Usage: scripts/ops/vm-start-stop.sh start|stop|status
set -euo pipefail
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"

ACTION="${1:?Usage: vm-start-stop.sh start|stop|status}"
GC=(--project="$PROJECT_ID" --zone="$ZONE")

case "$ACTION" in
  start | stop)
    step "$(date -u +%FT%TZ) running '$ACTION' on $VM_NAME in $ZONE"
    run gcloud compute instances "$ACTION" "$VM_NAME" "${GC[@]}"
    ;;
  status) ;;
  *)
    echo "Unknown action: $ACTION (use start, stop or status)" >&2
    exit 1
    ;;
esac

step "Status of $VM_NAME"
run gcloud compute instances describe "$VM_NAME" "${GC[@]}" \
  --format='table(name,status,machineType.basename(),networkInterfaces[0].networkIP)'
