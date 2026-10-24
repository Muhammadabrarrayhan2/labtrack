#!/usr/bin/env bash
# IaaS routine: patch the ops VM operating system (Debian 12) over IAP.
# Under the shared responsibility model the guest OS is our job on Compute Engine,
# unlike Cloud Run and Cloud SQL where Google patches the platform.
#
# Usage: scripts/ops/vm-patch.sh [--snapshot] [--reboot]
#   --snapshot  take a manual boot disk snapshot first (recommended)
#   --reboot    reboot when /var/run/reboot-required exists after the upgrade
set -euo pipefail
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"

SNAPSHOT=false
REBOOT=false
for arg in "$@"; do
  case "$arg" in
    --snapshot) SNAPSHOT=true ;;
    --reboot) REBOOT=true ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

if [ "$SNAPSHOT" = true ]; then
  "$(dirname "$0")/vm-snapshot-now.sh" "prepatch-$(date -u +%Y%m%d-%H%M%S)"
fi

SSH=(gcloud compute ssh "$VM_NAME" --project="$PROJECT_ID" --zone="$ZONE" --tunnel-through-iap --command)

step "Pending upgrades"
run "${SSH[@]}" "sudo apt-get update -q && apt list --upgradable 2>/dev/null"

step "Applying upgrades"
run "${SSH[@]}" "sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q -o Dpkg::Options::=--force-confold upgrade"

step "Checking services and reboot flag"
run "${SSH[@]}" "systemctl is-active cloud-sql-proxy google-cloud-ops-agent; systemctl list-timers labtrack-backup.timer --no-pager; if [ -f /var/run/reboot-required ]; then echo REBOOT_REQUIRED; else echo NO_REBOOT_REQUIRED; fi"

if [ "$REBOOT" = true ]; then
  step "Rebooting $VM_NAME if the kernel or libc changed"
  run "${SSH[@]}" "if [ -f /var/run/reboot-required ]; then sudo systemctl reboot; else echo 'No reboot needed'; fi" || true
fi
