# Laporan Verifikasi Restore Cloud SQL

| Butir | Nilai |
|---|---|
| Waktu uji (WIB) | 2026-10-26 06:53 |
| Proyek | labtrack-1026146 |
| Instans sumber | labtrack-db-f6f7 |
| Backup yang dipulihkan | ID 1792970383825, jendela backup 2026-10-25T23:19:43.825Z |
| Instans uji sementara | labtrack-restore-test-202610252325 (dihapus otomatis setelah uji) |
| Durasi total | sekitar 27 menit, memenuhi RTO 2 jam |
| Hasil | **LULUS** |

## Perbandingan jumlah baris

Salinan hasil restore boleh lebih kecil dari produksi karena data yang ditulis setelah jendela backup belum ada di backup. Salinan tidak boleh kosong bila produksi berisi data, dan tidak boleh lebih besar dari produksi.

| Tabel | Produksi | Hasil restore | Status |
|---|---|---|---|
| users | 2 | 1 | OK |
| students | 12 | 12 | OK |
| courses | 1 | 1 | OK |
| enrollments | 12 | 12 | OK |
| practicum_sessions | 4 | 4 | OK |
| attendances | 48 | 48 | OK |
| lab_reports | 41 | 41 | OK |

Dihasilkan oleh scripts/ops/sql-restore-test.sh.
