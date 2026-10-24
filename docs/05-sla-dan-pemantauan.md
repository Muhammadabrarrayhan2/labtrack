# SLA dan Pemantauan Sarana Prasarana LabTrack

Unit kompetensi: **J.631120.014.01 Memantau sarana dan prasarana agar bisa digunakan oleh user sesuai dengan SLA**

Dokumen ini menetapkan perjanjian tingkat layanan (SLA) LabTrack bagi pengguna, indikator yang diukur, cara pengukurannya di Cloud Monitoring, inventaris pemantauan, dan templat laporan SLA bulanan.

## 1. Perjanjian Tingkat Layanan (SLA)

### 1.1 Para pihak dan cakupan

| Butir | Isi |
|---|---|
| Penyedia layanan | Pengelola sistem LabTrack (peran L2, cloud engineer) |
| Pengguna layanan | Asisten praktikum (peran `assistant`) dan koordinator laboratorium (peran `admin`) |
| Layanan | LabTrack API pada `https://<labtrack-api>.run.app`, termasuk Swagger UI di `/docs` |
| Di luar cakupan | Gangguan jaringan di sisi pengguna, gangguan regional Google Cloud yang tercantum di Google Cloud Service Health, dan pemeliharaan terjadwal yang telah diumumkan |

### 1.2 Jam layanan

| Jenis | Waktu |
|---|---|
| Ketersediaan sistem | 24 jam setiap hari, diukur terus-menerus |
| Jam dukungan (respons terhadap laporan) | Senin sampai Sabtu, 07.00 sampai 21.00 WIB, mengikuti jadwal praktikum |
| Jendela pemeliharaan terjadwal | Minggu 02.00 sampai 03.00 WIB (sesuai `maintenance_window` Cloud SQL), diumumkan paling lambat 2 hari sebelumnya bila berdampak |

### 1.3 Target tingkat layanan

| Indikator | Target | Periode evaluasi |
|---|---|---|
| Ketersediaan | 99,5% permintaan berhasil (bukan galat 5xx) | Bulanan dan 30 hari bergulir |
| Latensi | 95% permintaan API selesai di bawah 800 ms (p95 < 800 ms) | Bulanan dan 30 hari bergulir |
| RPO (*Recovery Point Objective*) | Maksimum 24 jam data hilang | Per insiden |
| RTO (*Recovery Time Objective*) | Layanan pulih paling lama 2 jam | Per insiden |

Dasar RPO 24 jam: backup otomatis Cloud SQL berjalan sekali sehari pukul 01.00 WIB, ditambah `pg_dump` pukul 02.30 WIB bila VM `labtrack-ops` aktif. Kehilangan data terburuk adalah perubahan sejak backup terakhir.

Dasar RTO 2 jam: pemulihan dari backup ke instans baru diuji dengan `scripts/ops/sql-restore-test.sh`, yang mencatat durasi aktual (lihat `docs/04-aktivitas-rutin-iaas-paas-saas.md`, aktivitas P9). Rollback revisi Cloud Run memerlukan kurang dari 1 menit.

### 1.4 Waktu respons dukungan

Definisi tingkat keparahan dan alur penanganan ada di `docs/06-sop-dukungan-teknis.md`.

| Tingkat | Contoh | Respons awal | Target penyelesaian atau solusi sementara |
|---|---|---|---|
| P1 Kritis | API tidak dapat diakses semua pengguna, `/health` 503 | 15 menit | 2 jam (sesuai RTO) |
| P2 Tinggi | Satu fitur utama gagal (misalnya input kehadiran), banyak pengguna terdampak | 1 jam | 4 jam |
| P3 Sedang | Gangguan sebagian dengan solusi alternatif, latensi tinggi | 4 jam kerja | 2 hari kerja |
| P4 Rendah | Pertanyaan, permintaan akun, perbaikan kecil | 1 hari kerja | 5 hari kerja |

## 2. Indikator tingkat layanan (SLI) dan cara pengukuran

| SLI | Definisi | Metrik Cloud Monitoring | Filter | Implementasi |
|---|---|---|---|---|
| Ketersediaan | Permintaan bukan 5xx dibagi seluruh permintaan | `run.googleapis.com/request_count` (DELTA, INT64) | Total: `resource.type="cloud_run_revision" AND resource.label."service_name"="labtrack-api"`. Buruk: ditambah `metric.label."response_code_class"="5xx"` | `google_monitoring_slo.availability` di `slo.tf` |
| Latensi | Permintaan dengan latensi di bawah 800 ms dibagi seluruh permintaan | `run.googleapis.com/request_latencies` (DELTA, DISTRIBUTION, satuan ms) | Filter layanan yang sama, potongan distribusi `range { max = 800 }` | `google_monitoring_slo.latency` di `slo.tf` |
| Kesehatan *end-to-end* | `/health` mengembalikan 2xx dari beberapa lokasi pemeriksa | `monitoring.googleapis.com/uptime_check/check_passed` | `metric.label.check_id` = ID uptime check | `google_monitoring_uptime_check_config.health` di `monitoring.tf` |
| Kesehatan basis data | `/health` memeriksa `SELECT 1` ke Cloud SQL | Ikut tercermin pada uptime check dan 5xx | | `app/main.py`, fungsi `health` |

Galat 4xx (token kedaluwarsa, validasi gagal, NIM duplikat) dihitung sebagai permintaan yang baik karena disebabkan oleh masukan klien, bukan kegagalan layanan.

## 3. Perhitungan anggaran galat (*error budget*)

```
Target ketersediaan              = 99,5%
Anggaran galat                   = 100% - 99,5%         = 0,5%
Menit dalam 30 hari              = 30 x 24 x 60          = 43.200 menit
Waktu henti yang diizinkan       = 0,5% x 43.200         = 216 menit (3 jam 36 menit)
Per minggu (rata-rata)           = 216 / 30 x 7          = sekitar 50 menit
```

Karena SLO berbasis permintaan, anggaran galat juga dapat dinyatakan dalam jumlah permintaan. Contoh: bila dalam 30 hari terdapat 100.000 permintaan, maka paling banyak 0,5% x 100.000 = 500 permintaan boleh berakhir 5xx.

*Burn rate* adalah kecepatan pemakaian anggaran dibanding laju yang diizinkan. *Burn rate* 1 berarti anggaran habis tepat di akhir 30 hari. Alert *fast burn* dipasang pada *burn rate* 10 dalam jendela 1 jam:

```
Burn rate 10 berarti anggaran 30 hari habis dalam 30 / 10 = 3 hari
Rasio galat yang memicu alert    = 10 x 0,5%             = 5% permintaan dalam 1 jam terakhir
Anggaran terpakai dalam 1 jam    = 10 x (1 jam / 720 jam) = sekitar 1,4% anggaran bulanan
```

Kebijakan anggaran galat:

| Sisa anggaran | Tindakan |
|---|---|
| Lebih dari 50% | Deploy berjalan normal |
| 10% sampai 50% | Deploy fitur ditunda bila tidak mendesak, prioritaskan perbaikan keandalan |
| Kurang dari 10% atau habis | Hanya perbaikan keandalan dan keamanan yang di-deploy sampai periode berikutnya |

## 4. Inventaris pemantauan

| No | Objek dipantau | Metrik atau sumber | Ambang | Durasi | Tingkat | Tujuan alert | Resource Terraform |
|---|---|---|---|---|---|---|---|
| M1 | Endpoint `/health` | Uptime check setiap 5 menit dari beberapa region | Gagal di lebih dari satu region | 60 detik | P1 | Email `alert_email` | `google_monitoring_alert_policy.uptime` |
| M2 | SLO ketersediaan | `select_slo_burn_rate(..., "3600s")` | > 10 | Seketika | P1 / P2 | Email | `google_monitoring_alert_policy.slo_fast_burn` |
| M3 | Rasio 5xx | `request_count` 5xx dibagi total | > 5% | 5 menit | P2 | Email | `google_monitoring_alert_policy.error_ratio` |
| M4 | CPU Cloud SQL | `cloudsql.googleapis.com/database/cpu/utilization` | > 80% | 10 menit | P3 | Email | `google_monitoring_alert_policy.sql_cpu` |
| M5 | Disk Cloud SQL | `cloudsql.googleapis.com/database/disk/utilization` | > 80% | 5 menit | P3 | Email | `google_monitoring_alert_policy.sql_disk` |
| M6 | Koneksi Cloud SQL | `cloudsql.googleapis.com/database/postgresql/num_backends` | > 20 (batas 25) | 2 menit | P3 | Email | `google_monitoring_alert_policy.sql_connections` |
| M7 | SLO latensi | Sisa anggaran galat SLO latensi | Di bawah 50% (kuning), di bawah 10% (merah) | Dipantau di dasbor | P3 | Dasbor | Widget di `google_monitoring_dashboard.labtrack` |
| M8 | Jumlah instans Cloud Run | `run.googleapis.com/container/instance_count` | Mendekati 3 (maksimum) | Dipantau di dasbor | Informasi | Dasbor | Widget dasbor |
| M9 | Backup Cloud SQL | `gcloud sql backups list` | Tidak ada backup `SUCCESSFUL` dalam 24 jam | Harian | P3 | Pemeriksaan manual P4 | `backup_configuration` di `main.tf` |
| M10 | Backup `pg_dump` (opsional) | Log `labtrack-backup: success` | Tidak ada dalam 24 jam | Harian | P3 | Pemeriksaan manual I1 | `iaas.tf` |
| M11 | Biaya | Budget alert Billing | 50%, 90%, 100% dari US$10 | Bulanan | P4 | Email pemilik billing | Dibuat di Console (langkah 1 panduan) |

> [BUKTI: screenshot B-014-01, halaman Monitoring > SLOs (Services > LabTrack API) dengan dua SLO, status, dan sisa anggaran galat]

> [BUKTI: screenshot B-014-02, Monitoring > Alerting yang menampilkan seluruh alert policy LabTrack]

> [BUKTI: screenshot B-014-03, dasbor LabTrack Overview lengkap dengan widget SLO]

> [BUKTI: screenshot B-014-04, Monitoring > Uptime checks dengan status hijau dari beberapa region]

## 5. Prosedur pemantauan

| Waktu | Kegiatan | Keluaran |
|---|---|---|
| Harian, sebelum jam praktikum pertama | Periksa dasbor, alert terbuka, dan hasil backup (P1 sampai P4, I1) | Catatan di log aktivitas |
| Saat alert diterima | Tangani sesuai `docs/06-sop-dukungan-teknis.md` | Issue `laporan-insiden` di GitHub |
| Mingguan | Tinjau sisa anggaran galat kedua SLO dan tren latensi | Keputusan sesuai kebijakan anggaran galat |
| Bulanan, hari kerja pertama | Jalankan `scripts/sla_report.py` untuk bulan sebelumnya, lengkapi bagian insiden dan tindak lanjut | `docs/laporan-sla/YYYY-MM.md` |

Perintah laporan bulanan:

```bash
gcloud auth application-default login
python scripts/sla_report.py --project "$PROJECT_ID" --month 2026-10
# Rentang tertentu, misalnya sampai hari sebelum asesmen:
python scripts/sla_report.py --project "$PROJECT_ID" --start 2026-10-01 --end 2026-10-26
```

Skrip mengambil `request_count` per kelas kode respons dan distribusi `request_latencies` per jam, menggabungkan *bucket* distribusi untuk menghitung p95 seluruh periode, lalu menghitung ketersediaan, anggaran galat, dan status SLA. Logika perhitungan diuji dengan data tiruan di `tests/test_sla_report.py`.

## 6. Templat laporan SLA bulanan

Berkas `docs/laporan-sla/YYYY-MM.md` dihasilkan otomatis dengan struktur di bawah. Bagian insiden dan tindak lanjut diisi manual.

| Indikator | Target | Realisasi | Status |
|---|---|---|---|
| Ketersediaan (permintaan non-5xx) | 99,5% | > [ISI SETELAH DEPLOY: dari sla_report.py] | |
| Latensi p95 | < 800 ms | > [ISI SETELAH DEPLOY] | |
| Permintaan di bawah 800 ms | 95% | > [ISI SETELAH DEPLOY] | |

| Besaran | Nilai |
|---|---|
| Total permintaan | > [ISI SETELAH DEPLOY] |
| Permintaan 5xx | > [ISI SETELAH DEPLOY] |
| Anggaran galat terpakai | > [ISI SETELAH DEPLOY] |
| Insiden (jumlah, total durasi) | > [ISI SETELAH DEPLOY: dari issue berlabel insiden] |
| Status SLA | > [ISI SETELAH DEPLOY: Tercapai atau Tidak tercapai] |

> [BUKTI: B-014-05, berkas docs/laporan-sla/2026-10.md hasil skrip, ditambah screenshot terminal saat skrip dijalankan]
