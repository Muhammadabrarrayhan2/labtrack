#!/usr/bin/env bash
# PaaS routine: prove that backups can actually be restored.
#
# 1. Create a temporary Cloud SQL instance (db-f1-micro, no backups of its own)
# 2. Restore the latest successful backup of the production instance into it
# 3. Compare row counts between production and the restored copy
# 4. Delete the temporary instance, also when a step fails
#
# Usage: scripts/ops/sql-restore-test.sh
# Writes a restore verification report to $REPORT
# (default docs/bukti/013/restore-verification-<date>.md).
# Needs: gcloud, psql (PostgreSQL client) and cloud-sql-proxy v2 on PATH. Cloud Shell has
# gcloud and psql; install the proxy from
# https://cloud.google.com/sql/docs/postgres/sql-proxy#install
# Takes 15 to 25 minutes and costs a few cents (the temporary instance runs under an hour).
set -euo pipefail
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"

for bin in psql cloud-sql-proxy; do
  command -v "$bin" >/dev/null || {
    echo "$bin not found on PATH" >&2
    exit 1
  }
done

SOURCE=$(sql_instance)
TEMP="labtrack-restore-test-$(date -u +%Y%m%d%H%M)"
TABLES=(users students courses enrollments practicum_sessions attendances lab_reports)
PROXY_PID=""
START=$(date -u +%s)
REPORT="${REPORT:-docs/bukti/013/restore-verification-$(date +%Y%m%d-%H%M).md}"
PROXY_WAIT="${PROXY_WAIT:-8}"

cleanup() {
  if [ -n "$PROXY_PID" ]; then
    kill "$PROXY_PID" 2>/dev/null || true
  fi
  # Only ever delete the instance this script created
  if gcloud sql instances describe "$TEMP" --project="$PROJECT_ID" >/dev/null 2>&1; then
    step "Deleting temporary instance $TEMP"
    run gcloud sql instances delete "$TEMP" --project="$PROJECT_ID" --quiet
  fi
}
trap cleanup EXIT

step "Latest successful backup of $SOURCE"
BACKUP_ID=$(gcloud sql backups list --instance="$SOURCE" --project="$PROJECT_ID" \
  --filter='status=SUCCESSFUL' --sort-by='~windowStartTime' --limit=1 --format='value(id)')
BACKUP_TIME=$(gcloud sql backups describe "$BACKUP_ID" --instance="$SOURCE" --project="$PROJECT_ID" \
  --format='value(windowStartTime)' 2>/dev/null || true)
if [ -z "$BACKUP_ID" ]; then
  echo "No successful backup found. Run scripts/ops/sql-backup-now.sh first." >&2
  exit 1
fi
run gcloud sql backups describe "$BACKUP_ID" --instance="$SOURCE" --project="$PROJECT_ID" \
  --format='table(id,windowStartTime,type,status)'

step "Creating temporary instance $TEMP (about 5 to 10 minutes)"
run gcloud sql instances create "$TEMP" --project="$PROJECT_ID" --region="$REGION" \
  --database-version=POSTGRES_16 --edition=ENTERPRISE --tier=db-f1-micro \
  --storage-type=SSD --storage-size=10 --no-backup --availability-type=zonal \

step "Restoring backup $BACKUP_ID into $TEMP"
run gcloud sql backups restore "$BACKUP_ID" --restore-instance="$TEMP" \
  --backup-instance="$SOURCE" --project="$PROJECT_ID" --quiet

step "Opening Cloud SQL Auth Proxy to both instances"
cloud-sql-proxy --port 6541 "$PROJECT_ID:$REGION:$SOURCE" "$PROJECT_ID:$REGION:$TEMP" &
PROXY_PID=$!
sleep "$PROXY_WAIT"

# The restore copies users and passwords, so the app credentials work on both
PGPASSWORD=$(gcloud secrets versions access latest --secret=labtrack-db-password --project="$PROJECT_ID")
export PGPASSWORD

count() {
  psql "host=127.0.0.1 port=$1 user=labtrack dbname=labtrack sslmode=disable" -Atc "SELECT count(*) FROM $2"
}

step "Row counts (production on port 6541, restored copy on port 6542)"
printf '%-20s %12s %12s %s\n' table production restored check
FAIL=0
ROWS=""
for t in "${TABLES[@]}"; do
  prod=$(count 6541 "$t")
  rest=$(count 6542 "$t")
  # Rows written after the backup window can make production larger, never smaller
  if [ "$rest" -le "$prod" ] && { [ "$rest" -gt 0 ] || [ "$prod" -eq 0 ]; }; then
    verdict=OK
  else
    verdict=CHECK
    FAIL=1
  fi
  printf '%-20s %12s %12s %s\n' "$t" "$prod" "$rest" "$verdict"
  ROWS+="| $t | $prod | $rest | $verdict |"$'\n'
done
unset PGPASSWORD

ELAPSED=$(( ($(date -u +%s) - START) / 60 ))
step "Restore test finished in about $ELAPSED minutes (compare with RTO 2 hours)"

if [ "$FAIL" -eq 0 ]; then RESULT="LULUS"; else RESULT="PERLU DIPERIKSA"; fi
if [ "$ELAPSED" -le 120 ]; then RTO_OK="memenuhi"; else RTO_OK="melebihi"; fi
mkdir -p "$(dirname "$REPORT")"
cat > "$REPORT" <<MD
# Laporan Verifikasi Restore Cloud SQL

| Butir | Nilai |
|---|---|
| Waktu uji (WIB) | $(TZ=WIB-7 date '+%Y-%m-%d %H:%M') |
| Proyek | $PROJECT_ID |
| Instans sumber | $SOURCE |
| Backup yang dipulihkan | ID $BACKUP_ID, jendela backup $BACKUP_TIME |
| Instans uji sementara | $TEMP (dihapus otomatis setelah uji) |
| Durasi total | sekitar $ELAPSED menit, $RTO_OK RTO 2 jam |
| Hasil | **$RESULT** |

## Perbandingan jumlah baris

Salinan hasil restore boleh lebih kecil dari produksi karena data yang ditulis setelah jendela backup belum ada di backup. Salinan tidak boleh kosong bila produksi berisi data, dan tidak boleh lebih besar dari produksi.

| Tabel | Produksi | Hasil restore | Status |
|---|---|---|---|
$ROWS
Dihasilkan oleh scripts/ops/sql-restore-test.sh.
MD
echo "Report written to $REPORT"
if [ "$FAIL" -ne 0 ]; then
  echo "Some tables need a closer look (restored copy empty or larger than production)." >&2
  exit 1
fi
echo "Restore test passed. Backup $BACKUP_ID is usable."
