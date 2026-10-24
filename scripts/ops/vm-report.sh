#!/usr/bin/env bash
# IaaS routine: VM provisioning report. Records the VM configuration from the Compute
# Engine API and, from inside the VM over IAP, CPU, memory, disk, network, gateway
# reachability, outbound access through Cloud NAT and the state of the ops services.
#
# Usage: scripts/ops/vm-report.sh
# Output: printed and saved to $OUT (default docs/bukti/013/vm-provisioning-<date>.txt)
set -euo pipefail
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"

OUT="${OUT:-docs/bukti/013/vm-provisioning-$(date +%Y%m%d-%H%M).txt}"
mkdir -p "$(dirname "$OUT")"

# Runs inside the VM. Single quotes on purpose: expansions happen on the VM, not here.
# shellcheck disable=SC2016
REMOTE='
echo "== identity";   hostname; grep -E "^(PRETTY_NAME)=" /etc/os-release; uname -r
echo "== cpu";        lscpu | grep -E "^(Model name|CPU\(s\)|Thread\(s\) per core|Hypervisor vendor|Virtualization type)"
echo "== memory";     free -h
echo "== disk";       df -h /
echo "== network";    ip -br addr; ip route
GW=$(ip route | awk "/^default/ {print \$3; exit}")
echo "== gateway $GW"; ping -c 3 -W 2 "$GW" || echo "gateway did not answer ICMP"
echo "== egress through Cloud NAT"
curl -s -o /dev/null -m 10 -w "https://deb.debian.org HTTP %{http_code}\n" https://deb.debian.org || echo "egress failed"
echo "== services";   systemctl is-active cloud-sql-proxy google-cloud-ops-agent labtrack-backup.timer || true
'

{
  echo "LabTrack VM provisioning report, $(date -u +%FT%TZ)"
  step "Configuration from the Compute Engine API"
  run gcloud compute instances describe "$VM_NAME" --project="$PROJECT_ID" --zone="$ZONE" \
    --format='yaml(name,status,machineType.basename(),zone.basename(),disks[0].source.basename(),networkInterfaces[0].networkIP,networkInterfaces[0].accessConfigs,serviceAccounts[0].email,shieldedInstanceConfig)'
  step "Inside the VM (via IAP)"
  run gcloud compute ssh "$VM_NAME" --project="$PROJECT_ID" --zone="$ZONE" --tunnel-through-iap --command="$REMOTE"
} 2>&1 | tee "$OUT"

echo
echo "Saved to $OUT"
