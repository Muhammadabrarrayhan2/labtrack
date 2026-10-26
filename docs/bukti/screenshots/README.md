# Indeks Bukti Visual

Semua gambar di folder ini dibuat pada 26 Oktober 2026 dari sistem yang berjalan di proyek Google Cloud `labtrack-1026146` dan repositori publik `Muhammadabrarrayhan2/labtrack`. Ada tiga jenis gambar, dan sumber masing-masing tertulis di bawah agar keasliannya dapat diperiksa.

| Jenis | Cara dibuat | Skrip |
|---|---|---|
| Screenshot browser | Microsoft Edge (headless) membuka halaman publik yang live | `scripts/evidence/screenshot_public.py`, `scripts/evidence/screenshot_evidence.py` (bagian Swagger) |
| Grafik Cloud Monitoring | Data metrik asli diambil dari Cloud Monitoring API lalu digambar; setiap gambar mencantumkan nama metrik | `scripts/evidence/monitoring_charts.py` |
| Render terminal | Isi berkas keluaran perintah yang tersimpan di repositori ditampilkan apa adanya (tanpa diketik ulang) | `scripts/evidence/screenshot_evidence.py` |

## Daftar gambar

| Kode | Berkas | Jenis | Isi |
|---|---|---|---|
| B-001-03 | `B-001-03-swagger-ui.png` | Browser | Swagger UI live, versi 1.0.1 |
| B-001-04 | `B-001-04-swagger-attendance-summary.png` | Browser | Login lewat Authorize lalu `GET /courses/1/attendance-summary`, respons 200 dengan data dan header `x-request-id` |
| B-002-07 | `B-002-07-github-actions-run.png` | Browser | Run GitHub Actions 40246377597: test, test-postgres, terraform, deploy lulus |
| B-002-08 | `B-002-08-terraform-apply.png` | Terminal | Bagian akhir `terraform apply`: 62 resource dibuat, output |
| B-002-09 | `B-002-09-integration-report.png` | Terminal | Uji integrasi 9 dari 9 lulus terhadap Cloud Run |
| B-002-10 | `B-002-10-github-repo.png` | Browser | Halaman repositori publik |
| B-003-01 | `B-003-01-locust-terminal.png` | Terminal | Ringkasan Locust 50 pengguna, 5 menit |
| B-003-02 | `B-003-02-cloud-run-instances.png` | Grafik | Jumlah instans Cloud Run: naik ke batas 3 saat beban, turun saat idle |
| B-003-03 | `B-003-03-latency-p95.png` | Grafik | Latensi p95 per menit dengan garis target 800 ms |
| B-003-07 | `B-003-07-stress-monitoring.png` | Terminal | Instans, CPU, dan koneksi Cloud SQL per tahap uji stress |
| B-003-08 | `B-003-08-cloudsql-cpu.png` | Grafik | CPU Cloud SQL dengan ambang alert 80% |
| B-013-01 | `B-013-01-health.png` | Browser | `/health` 200, basis data ok |
| B-013-03 | `B-013-03-rollback.png` | Terminal | Rollback ke revisi sebelumnya dan kembali |
| B-013-08 | `B-013-08-pgdump-backup.png` | Terminal | Backup `pg_dump` dari VM ke bucket |
| B-013-09 | `B-013-09-patch-change-log.png` | Terminal | *Change log* patching VM |
| B-013-14 | `B-013-14-account-deactivation.png` | Terminal | Penonaktifan akun dan reset password |
| B-013-16 | `B-013-16-iaas-iam-config.png` | Terminal | IAM per service account, VM, firewall, jadwal snapshot |
| B-013-18 | `B-013-18-vm-provisioning.png` | Terminal | Laporan provisioning VM |
| B-013-20 | `B-013-20-restore-verification.png` | Terminal | Laporan verifikasi restore Cloud SQL |
| B-014-01 | `B-014-01-monitoring-inventory.png` | Terminal | SLO, alert, uptime check, kanal, dasbor dari Cloud Monitoring API |
| B-014-04 | `B-014-04-uptime-check.png` | Grafik | Uptime check `/health`, turun saat simulasi insiden |
| B-014-05 | `B-014-05-sla-report.png` | Terminal | Laporan SLA 26 Oktober 2026 |
| B-014-07 | `B-014-07-requests-by-class.png` | Grafik | Permintaan per detik per kelas kode respons (2xx, 4xx, 5xx) |
| B-014-08 | `B-014-08-cloudsql-connections.png` | Grafik | Koneksi PostgreSQL dengan ambang alert 20 dan batas 25 |
| B-015-01 | `B-015-01-error-401-request-id.png`, `B-015-01b-swagger-401-request-id.png` | Browser | Respons 401 dengan `request_id` di badan dan header |
| B-015-02 | `B-015-02-request-id-trace.png` | Terminal | `request_id` dari respons 404 ditemukan di Cloud Logging |
| B-015-03 | `B-015-03-incident-timeline.png` | Terminal | Linimasa simulasi insiden Cloud SQL |
| B-015-07 | `B-015-07-issue-templates.png` | Browser | Pilihan templat issue di GitHub |

## Screenshot yang hanya bisa diambil pemilik akun

Bagian berikut memerlukan login ke Google Cloud Console atau Gmail milik pemilik akun. Data yang sama sudah tersedia dalam bentuk grafik atau keluaran API di atas; screenshot konsol ini melengkapi tampilannya.

| Kode | Halaman | Waktu yang perlu |
|---|---|---|
| B-002-02 | Billing > Reports (filter proyek labtrack-1026146) dan Budgets & alerts | 1 menit |
| B-014-01 | Monitoring > SLOs > LabTrack API | 1 menit |
| B-014-03 | Monitoring > Dashboards > LabTrack Overview, rentang 26 Oktober 01.00 sampai 07.30 WIB | 1 menit |
| B-015-04 | Email alert "LabTrack API is down" di abrarrayhan8@gmail.com sekitar pukul 07.00 WIB 26 Oktober | 1 menit |
| B-015-06 | Monitoring > Alerting > Incidents | 1 menit |
