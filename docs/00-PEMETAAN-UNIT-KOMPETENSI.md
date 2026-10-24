# Pemetaan Bukti terhadap Unit Kompetensi

**Skema:** Sertifikasi BNSP Cloud Computing Engineer, berdasarkan SKKNI Keputusan Menteri Ketenagakerjaan Nomor 456 Tahun 2015 (Bidang Cloud Computing)

**Asesi:** > [ISI: nama lengkap asesi]

**Tanggal asesmen:** Selasa, 27 Oktober 2026

**Proyek bukti:** LabTrack, REST API manajemen praktikum laboratorium di Google Cloud Platform

**Repositori:** > [ISI: URL repositori GitHub]

**URL aplikasi:** > [ISI SETELAH DEPLOY: URL `*.run.app` dari `terraform output api_url`]

## Cara membaca dokumen ini

Dokumen ini adalah pintu masuk portofolio. Setiap unit kompetensi memiliki satu bagian yang berisi elemen kompetensi sesuai APL02 dan, untuk setiap elemen, bukti yang dapat diperiksa langsung:

- **Dokumen**: berkas di folder `docs/`.
- **Kode atau konfigurasi**: berkas di repositori, termasuk resource Terraform dengan format `berkas.tf: tipe.nama`.
- **Skrip**: perintah di `scripts/` yang dapat dijalankan ulang di depan asesor.
- **Test**: pengujian otomatis di `tests/`, dijalankan dengan `pytest -q --cov=app`.
- **Tangkapan layar**: kode `B-<unit>-<nomor>`, tersimpan di `docs/bukti/<unit>/` dengan daftar lengkap di `docs/bukti/<unit>/README.md`.

Kesesuaian dengan prinsip bukti VATM:

| Prinsip | Cara pemenuhan |
|---|---|
| Valid | Setiap elemen dipetakan ke bukti yang menunjukkan kemampuan elemen tersebut secara langsung, bukan hanya uraian teori |
| Asli | Riwayat commit Git atas nama asesi, infrastruktur yang di-deploy ke proyek GCP milik asesi, dan tangkapan layar yang memuat project ID dan waktu. Tidak ada hasil yang diisi sebelum benar-benar dijalankan; nilai yang belum ada ditandai sebagai placeholder |
| Terkini | Seluruh bukti dibuat pada Oktober 2026 dengan Terraform provider google 6.x, Cloud Run v2, dan PostgreSQL 16 |
| Memadai | Setiap unit memiliki kombinasi dokumen analisis, implementasi kode atau konfigurasi, dan bukti eksekusi |

Catatan: berkas `docs/apl02-units.txt` dari LSP belum tersedia saat dokumen ini disusun. Nama elemen di bawah adalah placeholder yang harus disalin persis dari formulir APL02. Kolom "Cakupan" berisi perkiraan isi elemen untuk membantu penyelarasan; sesuaikan bila berbeda.

---

## Unit 1. J.631120.001.01 Mendefinisikan terminologi dan konsep cloud computing

| No | Elemen kompetensi (dari APL02) | Cakupan | Bukti |
|---|---|---|---|
| 1.1 | > [ISI DARI APL02: elemen 1] | Definisi dan karakteristik esensial cloud computing | `docs/01-konsep-cloud-computing.md` bagian 1 dan 2; resource `main.tf: google_cloud_run_v2_service.api` (blok `scaling`); B-001-01, B-001-02, B-001-03, B-001-05 |
| 1.2 | > [ISI DARI APL02: elemen 2] | Model layanan IaaS, PaaS, SaaS | `docs/01-konsep-cloud-computing.md` bagian 3 dan tabel 3.1; `iaas.tf: google_compute_instance.ops` (IaaS); `main.tf: google_cloud_run_v2_service.api` dan `google_sql_database_instance.db` (PaaS); B-001-04, B-013-15 |
| 1.3 | > [ISI DARI APL02: elemen 3] | Model penerapan dan model tanggung jawab bersama | `docs/01-konsep-cloud-computing.md` bagian 4 dan 5 |
| 1.4 | > [ISI DARI APL02: elemen 4] | Terminologi | `docs/01-konsep-cloud-computing.md` bagian 6 (glosarium 33 istilah, masing-masing dengan rujukan penerapan di repositori) |

## Unit 2. J.631120.002.01 Mengidentifikasi teknologi cloud computing

| No | Elemen kompetensi (dari APL02) | Cakupan | Bukti |
|---|---|---|---|
| 2.1 | > [ISI DARI APL02: elemen 1] | Teknologi virtualisasi dan kontainer | `docs/02-teknologi-cloud.md` bagian 1.1 sampai 1.3; `Dockerfile`; `docker-compose.yml`; B-002-01, B-002-03 |
| 2.2 | > [ISI DARI APL02: elemen 2] | Teknologi penyimpanan, basis data, dan keamanan | `docs/02-teknologi-cloud.md` bagian 1.4 sampai 1.6; `main.tf: google_sql_database_instance.db`, `google_storage_bucket.reports`, `google_secret_manager_secret.s`; `app/storage.py`; B-002-04, B-002-05 |
| 2.3 | > [ISI DARI APL02: elemen 3] | Otomasi: IaC, CI/CD, federasi identitas | `docs/02-teknologi-cloud.md` bagian 1.7 sampai 1.9; folder `infra/terraform/`; `.github/workflows/ci-cd.yml`; `cicd.tf: google_iam_workload_identity_pool_provider.github`; B-002-06, B-002-07, B-002-08 |
| 2.4 | > [ISI DARI APL02: elemen 4] | Perbandingan penyedia dan pemilihan layanan | `docs/02-teknologi-cloud.md` bagian 2 dan 3; B-002-02 |

## Unit 3. J.631120.003.01 Mengidentifikasi berbagai jenis perangkat keras yang dibutuhkan

| No | Elemen kompetensi (dari APL02) | Cakupan | Bukti |
|---|---|---|---|
| 3.1 | > [ISI DARI APL02: elemen 1] | Klasifikasi perangkat keras server dan klien | `docs/03-kebutuhan-perangkat-keras.md` bagian 1 |
| 3.2 | > [ISI DARI APL02: elemen 2] | Estimasi beban dan penentuan kapasitas | `docs/03-kebutuhan-perangkat-keras.md` bagian 2 dan 3 (RPS, anggaran koneksi, pertumbuhan penyimpanan); `main.tf` blok `resources` dan `scaling`; `app/database.py` (*pool*); B-003-04, B-003-05 |
| 3.3 | > [ISI DARI APL02: elemen 3] | Perbandingan dengan *on-premise* (CapEx dan OpEx) | `docs/03-kebutuhan-perangkat-keras.md` bagian 4 |
| 3.4 | > [ISI DARI APL02: elemen 4] | Verifikasi kapasitas dengan uji beban | `scripts/loadtest/locustfile.py`; `docs/03-kebutuhan-perangkat-keras.md` bagian 5; `docs/bukti/003/locust_stats.csv` dan `locust-report.html`; B-003-01, B-003-02, B-003-03 |

## Unit 4. J.631120.013.01 Menjalankan aktivitas rutin pada IaaS, PaaS, dan SaaS

| No | Elemen kompetensi (dari APL02) | Cakupan | Bukti |
|---|---|---|---|
| 4.1 | > [ISI DARI APL02: elemen 1] | Aktivitas rutin IaaS | `infra/terraform/iaas.tf` (VM tanpa IP publik, IAP, Cloud NAT, `google_compute_resource_policy.ops_daily_snapshot`); `infra/terraform/templates/ops-startup.sh.tftpl` (pg_dump terjadwal); `scripts/ops/vm-*.sh`; `docs/04-aktivitas-rutin-iaas-paas-saas.md` bagian 3.2; B-013-08 sampai B-013-11, B-013-15 sampai B-013-17 |
| 4.2 | > [ISI DARI APL02: elemen 2] | Aktivitas rutin PaaS | `scripts/ops/deploy-image.sh`, `rollback.sh`, `scale.sh`, `rotate-secret.sh`, `sql-start-stop.sh`, `sql-backup-now.sh`, `sql-restore-test.sh`; `docs/04-aktivitas-rutin-iaas-paas-saas.md` bagian 3.1; `tests/test_ops_scripts.py`; B-013-01 sampai B-013-07 |
| 4.3 | > [ISI DARI APL02: elemen 3] | Aktivitas rutin SaaS (sebagai pelanggan dan penyedia) | `docs/04-aktivitas-rutin-iaas-paas-saas.md` bagian 3.3 dan 3.4; endpoint `POST /auth/users` di `app/routers/auth.py`; B-013-12 sampai B-013-14 |
| 4.4 | > [ISI DARI APL02: elemen 4] | Pencatatan aktivitas | `docs/04-aktivitas-rutin-iaas-paas-saas.md` bagian 4 (log aktivitas); `docs/bukti/013/log/` |

## Unit 5. J.631120.014.01 Memantau sarana dan prasarana agar bisa digunakan oleh user sesuai dengan SLA

| No | Elemen kompetensi (dari APL02) | Cakupan | Bukti |
|---|---|---|---|
| 5.1 | > [ISI DARI APL02: elemen 1] | Penetapan SLA dan SLI | `docs/05-sla-dan-pemantauan.md` bagian 1 sampai 3 (target, SLI, anggaran galat) |
| 5.2 | > [ISI DARI APL02: elemen 2] | Konfigurasi pemantauan dan alert | `infra/terraform/slo.tf` (`google_monitoring_slo.availability`, `google_monitoring_slo.latency`, `google_monitoring_alert_policy.slo_fast_burn`, `error_ratio`, `sql_cpu`, `sql_disk`, `sql_connections`, aktif dengan `enable_sla_alerts = true`); `monitoring.tf` (uptime check, dasbor); `docs/05-sla-dan-pemantauan.md` bagian 4; B-014-01 sampai B-014-04 |
| 5.3 | > [ISI DARI APL02: elemen 3] | Pelaksanaan pemantauan dan pelaporan SLA | `scripts/sla_report.py`; `tests/test_sla_report.py`; `docs/laporan-sla/`; `docs/05-sla-dan-pemantauan.md` bagian 5 dan 6; B-014-05 |
| 5.4 | > [ISI DARI APL02: elemen 4] | Pemulihan sesuai RPO dan RTO | `scripts/ops/sql-restore-test.sh`; backup otomatis di `main.tf: google_sql_database_instance.db`; B-013-06 |

## Unit 6. J.631120.015.01 Memberikan dukungan teknis atas masalah user dan report next layer

| No | Elemen kompetensi (dari APL02) | Cakupan | Bukti |
|---|---|---|---|
| 6.1 | > [ISI DARI APL02: elemen 1] | Penerimaan dan identifikasi masalah pengguna | `.github/ISSUE_TEMPLATE/laporan-masalah.yml`; `request_id` pada respons galat (`app/main.py`, fungsi `error_response`); `tests/test_request_id.py`; `docs/06-sop-dukungan-teknis.md` bagian 1 sampai 3; B-015-01, B-015-07 |
| 6.2 | > [ISI DARI APL02: elemen 2] | Diagnosis dan penyelesaian masalah | `docs/06-sop-dukungan-teknis.md` bagian 5 (sembilan kasus dengan kueri dan perintah diagnosis); B-015-02 |
| 6.3 | > [ISI DARI APL02: elemen 3] | Eskalasi ke lapis berikutnya | `docs/06-sop-dukungan-teknis.md` bagian 4 (matriks eskalasi L1, L2, L3); `.github/ISSUE_TEMPLATE/laporan-insiden.yml` |
| 6.4 | > [ISI DARI APL02: elemen 4] | Dokumentasi dan komunikasi | `docs/06-sop-dukungan-teknis.md` bagian 6 (simulasi insiden) dan 7 (templat komunikasi); B-015-03 sampai B-015-06, B-015-08 |

---

## Ringkasan bukti otomatis

| Bukti | Perintah | Hasil saat dokumen disusun |
|---|---|---|
| Pengujian aplikasi dan skrip | `pytest -q --cov=app` | 52 test lulus, cakupan kode `app/` 94% |
| Validasi Terraform | `terraform fmt -recursive && terraform validate` di `infra/terraform` | Valid (Terraform 1.9.8, provider google 6.50.0) |
| Lint skrip operasional | `shellcheck -x scripts/ops/*.sh` | Tanpa temuan |

> [BUKTI: B-002-07, run GitHub Actions hijau yang menjalankan ketiga pemeriksaan di atas pada commit terakhir]
