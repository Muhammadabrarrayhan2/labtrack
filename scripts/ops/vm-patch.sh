#!/usr/bin/env bash
# IaaS routine: patch the ops VM operating system (Debian 12) over IAP.
# Under the shared responsibility model the guest OS is our job on Compute Engine,
# unlike Cloud Run and Cloud SQL where Google patches the platform.
#
# Follows the controlled change procedure: identify pending changes, back up (snapshot),
# apply, run a post-maintenance test, and record the change in a change log.
#
# Usage: scripts/ops/vm-patch.sh [--snapshot] [--reboot]
#   --snapshot  take a manual boot disk snapshot first (recommended)
#   --reboot    reboot when /var/run/reboot-required exists after the upgrade
# Appends one row per run to $CHANGE_LOG (default docs/bukti/013/change-log.md).
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

SSH=(gcloud compute ssh "$VM_NAME" --project="$PROJECT_ID" --zone="$ZONE" --tunnel-through-iap --command)

step "1. Identify: pending upgrades"
run "${SSH[@]}" "sudo apt-get update -q && apt list --upgradable 2>/dev/null"

BACKUP_NOTE="no snapshot taken"
if [ "$SNAPSHOT" = true ]; then
  step "2. Back up: boot disk snapshot"
  SNAP_SUFFIX="prepatch-$(date -u +%Y%m%d-%H%M%S)"
  "$(dirname "$0")/vm-snapshot-now.sh" "$SNAP_SUFFIX"
  BACKUP_NOTE="snapshot $VM_NAME-manual-$SNAP_SUFFIX"
fi

step "3. Apply upgrades"
run "${SSH[@]}" "sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q -o Dpkg::Options::=--force-confold upgrade"

step "4. Post-maintenance test: services and reboot flag"
# Single quotes on purpose: this runs on the VM.
# shellcheck disable=SC2016
POST_CHECK='echo "$(systemctl is-active cloud-sql-proxy google-cloud-ops-agent | paste -sd, -) $(test -f /var/run/reboot-required && echo REBOOT_REQUIRED || echo NO_REBOOT_REQUIRED)"'
printf '+ %s %s\n' "${SSH[*]}" "$POST_CHECK"
POST_RESULT=$("${SSH[@]}" "$POST_CHECK" | tail -n 1)
echo "$POST_RESULT"

if [ "$REBOOT" = true ]; then
  step "Rebooting $VM_NAME if the kernel or libc changed"
  run "${SSH[@]}" "if [ -f /var/run/reboot-required ]; then sudo systemctl reboot; else echo 'No reboot needed'; fi" || true
fi

step "5. Record the change"
CHANGE_LOG="${CHANGE_LOG:-docs/bukti/013/change-log.md}"
mkdir -p "$(dirname "$CHANGE_LOG")"
if [ ! -f "$CHANGE_LOG" ]; then
  {
    echo "# Change Log VM labtrack-ops"
    echo
    echo "| Waktu (WIB) | VM | Perubahan | Risiko | Backup sebelum perubahan | Uji pasca-pemeliharaan | Pelaksana |"
    echo "|---|---|---|---|---|---|---|"
  } > "$CHANGE_LOG"
fi
printf '| %s | %s | apt-get upgrade (Debian 12) | Layanan restart, kemungkinan perlu reboot kernel | %s | %s | %s |\n' \
  "$(TZ=WIB-7 date '+%Y-%m-%d %H:%M')" "$VM_NAME" "$BACKUP_NOTE" "$POST_RESULT" "${USER:-unknown}" >> "$CHANGE_LOG"
echo "Change recorded in $CHANGE_LOG"
