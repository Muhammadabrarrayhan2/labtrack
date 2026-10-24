#!/usr/bin/env bash
# IaaS routine: SSH into labtrack-ops through IAP TCP forwarding. The VM has no external
# IP; the firewall only admits 35.235.240.0/20 (IAP) on port 22, and OS Login maps your
# Google identity to a Linux user. Your account needs roles/iap.tunnelResourceAccessor and
# roles/compute.osAdminLogin (project Owner already has both).
#
# Usage:
#   scripts/ops/vm-ssh.sh                      # interactive shell
#   scripts/ops/vm-ssh.sh "<remote command>"   # run one command, e.g.
#   scripts/ops/vm-ssh.sh "sudo systemctl start labtrack-backup.service"
#   scripts/ops/vm-ssh.sh "systemctl list-timers labtrack-backup.timer"
set -euo pipefail
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"

ARGS=("$VM_NAME" --project="$PROJECT_ID" --zone="$ZONE" --tunnel-through-iap)

if [ $# -gt 0 ]; then
  step "Running on $VM_NAME via IAP: $*"
  run gcloud compute ssh "${ARGS[@]}" --command="$*"
else
  step "Opening an interactive shell on $VM_NAME via IAP"
  run gcloud compute ssh "${ARGS[@]}"
fi
