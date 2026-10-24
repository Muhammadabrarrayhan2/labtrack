#!/usr/bin/env bash
# IaaS routine: take a manual snapshot of the ops VM boot disk, for example right before
# patching. Scheduled snapshots (daily, 7 day retention) come from the resource policy
# labtrack-ops-daily-snapshot in infra/terraform/iaas.tf. Manual ones are kept until deleted.
#
# Usage: scripts/ops/vm-snapshot-now.sh [suffix]
set -euo pipefail
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"

DISK="$VM_NAME-boot"
NAME="$VM_NAME-manual-${1:-$(date -u +%Y%m%d-%H%M%S)}"
SNAP_REGION="${ZONE%-*}"

step "Snapshotting disk $DISK to $NAME (stored in $SNAP_REGION)"
run gcloud compute disks snapshot "$DISK" --project="$PROJECT_ID" --zone="$ZONE" \
  --snapshot-names="$NAME" --storage-location="$SNAP_REGION" --labels=app=labtrack,type=manual

step "Snapshots of $DISK"
run gcloud compute snapshots list --project="$PROJECT_ID" \
  --filter="sourceDisk ~ /$DISK\$" --sort-by='~creationTimestamp' --limit=10 \
  --format='table(name,creationTimestamp,diskSizeGb,storageBytes,status)'
