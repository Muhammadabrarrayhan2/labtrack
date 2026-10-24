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


Menurut *Modul Pelatihan Insinyur Cloud Computing Revisi*, skema ini terdiri atas 6 unit, 22 elemen kompetensi, dan 61 KUK (20 KUK terminologi dan konsep, 16 KUK teknologi, 25 KUK perangkat keras, pemeliharaan, SLA, dan dukungan teknis). Pemetaan setiap slide dan lab modul ke bukti LabTrack ada di [07-kesesuaian-modul-pelatihan.md](07-kesesuaian-modul-pelatihan.md), termasuk lima bukti minimum evaluasi akhir.

Catatan: berkas `docs/apl02-units.txt` dari LSP belum tersedia saat dokumen ini disusun. Nama elemen di bawah adalah placeholder yang harus disalin persis dari formulir APL02. Tabel di bawah menyediakan empat baris per unit (24 baris); karena total elemen menurut modul adalah 22, gabungkan atau hapus baris yang tidak sesuai saat menyalin APL02. Kolom "Cakupan" berisi perkiraan isi elemen untuk membantu penyelarasan.

Bukti terbagi dua:

- **Sudah ada sekarang**: dokumen, kode, konfigurasi, test otomatis, dan keluaran nyata dari lingkungan lokal di `docs/bukti/lokal/`.
- **Diisi setelah deploy ke Google Cloud**: kode `B-xxx-yy` dan berkas di `docs/bukti/<unit>/`.

---

## Unit 1. J.631120.001.01 Mendefinisikan terminologi dan konsep cloud computing

| No | Elemen kompetensi (dari APL02) | Cakupan | Bukti |
|---|---|---|---|
| 1.1 | > [ISI DARI APL02: elemen 1] | Definisi, karakteristik esensial, arsitektur berlapis | `docs/01-konsep-cloud-computing.md` bagian 1, 2, dan 7; resource `main.tf: google_cloud_run_v2_service.api` (blok `scaling`); B-001-01, B-001-02, B-001-03, B-001-05 |
| 1.2 | > [ISI DARI APL02: elemen 2] | Model layanan IaaS, PaaS, SaaS; *scaling* horizontal dan vertikal; *multitenancy* | `docs/01-konsep-cloud-computing.md` bagian 3 dan 8; `iaas.tf: google_compute_instance.ops` (IaaS); `main.tf: google_cloud_run_v2_service.api` dan `google_sql_database_instance.db` (PaaS); `scripts/ops/scale.sh`; B-001-04, B-013-15 |
| 1.3 | > [ISI DARI APL02: elemen 3] | Model penerapan, tanggung jawab bersama, topologi jaringan | `docs/01-konsep-cloud-computing.md` bagian 4, 5, dan 9 |
| 1.4 | > [ISI DARI APL02: elemen 4] | Terminologi | `docs/01-konsep-cloud-computing.md` bagian 6 (glosarium 33 istilah, masing-masing dengan rujukan penerapan di repositori) |

## Unit 2. J.631120.002.01 Mengidentifikasi teknologi cloud computing

| No | Elemen kompetensi (dari APL02) | Cakupan | Bukti |
|---|---|---|---|
| 2.1 | > [ISI DARI APL02: elemen 1] | Teknologi virtualisasi, kontainer, mekanisme *failover*, *resiliency*, *replication* | `docs/02-teknologi-cloud.md` bagian 1.1 sampai 1.3 dan 4; `Dockerfile`; `docker-compose.yml`; B-002-01, B-002-03 |
| 2.2 | > [ISI DARI APL02: elemen 2] | Teknologi penyimpanan, basis data, keamanan dan ancamannya | `docs/02-teknologi-cloud.md` bagian 1.4 sampai 1.6, 5, dan 6; `main.tf: google_sql_database_instance.db`, `google_storage_bucket.reports`, `google_secret_manager_secret.s`; `app/storage.py`, `app/security.py`; B-002-04, B-002-05 |
| 2.3 | > [ISI DARI APL02: elemen 3] | Otomasi (IaC, CI/CD, federasi identitas) dan pengujian integrasi | `docs/02-teknologi-cloud.md` bagian 1.7 sampai 1.9 dan 7; folder `infra/terraform/`; `.github/workflows/ci-cd.yml` (job `test-postgres`); `scripts/api_integration_check.py`; bukti lokal `docs/bukti/lokal/integration-report.md`; B-002-06, B-002-07, B-002-08, B-002-09 |
| 2.4 | > [ISI DARI APL02: elemen 4] | Perbandingan penyedia dan pemilihan layanan | `docs/02-teknologi-cloud.md` bagian 2 dan 3; B-002-02 |

## Unit 3. J.631120.003.01 Mengidentifikasi berbagai jenis perangkat keras yang dibutuhkan

| No | Elemen kompetensi (dari APL02) | Cakupan | Bukti |
|---|---|---|---|
| 3.1 | > [ISI DARI APL02: elemen 1] | Klasifikasi perangkat keras server dan klien | `docs/03-kebutuhan-perangkat-keras.md` bagian 1; laporan provisioning VM `scripts/ops/vm-report.sh`, B-013-18 |
| 3.2 | > [ISI DARI APL02: elemen 2] | Estimasi beban dan penentuan kapasitas | `docs/03-kebutuhan-perangkat-keras.md` bagian 2 dan 3 (RPS, anggaran koneksi, pertumbuhan penyimpanan); `main.tf` blok `resources` dan `scaling`; `app/database.py` (*pool*); B-003-04, B-003-05 |
| 3.3 | > [ISI DARI APL02: elemen 3] | Perbandingan dengan *on-premise* (CapEx dan OpEx) | `docs/03-kebutuhan-perangkat-keras.md` bagian 4 |
| 3.4 | > [ISI DARI APL02: elemen 4] | Verifikasi kapasitas dengan uji *performance* dan *stress* | `scripts/loadtest/locustfile.py`, `scripts/loadtest/stages.py`, `tests/test_loadtest_stages.py`; `docs/03-kebutuhan-perangkat-keras.md` bagian 5 dan 6; hasil lokal nyata bagian 5.4 dan `docs/bukti/lokal/locust_stats.csv`; B-003-01, B-003-02, B-003-03, B-003-06, B-003-07 |

## Unit 4. J.631120.013.01 Menjalankan aktivitas rutin pada IaaS, PaaS, dan SaaS

| No | Elemen kompetensi (dari APL02) | Cakupan | Bukti |
|---|---|---|---|
| 4.1 | > [ISI DARI APL02: elemen 1] | Aktivitas rutin IaaS, termasuk *patching* dengan prosedur perubahan terkontrol | `infra/terraform/iaas.tf` (VM tanpa IP publik, IAP, Cloud NAT, `google_compute_resource_policy.ops_daily_snapshot`); `infra/terraform/templates/ops-startup.sh.tftpl` (pg_dump terjadwal); `scripts/ops/vm-*.sh`; `docs/04-aktivitas-rutin-iaas-paas-saas.md` bagian 3.2, 6, dan 7; B-013-08 sampai B-013-11, B-013-15 sampai B-013-19 |
| 4.2 | > [ISI DARI APL02: elemen 2] | Aktivitas rutin PaaS, termasuk siklus *backup, restore, verify* | `scripts/ops/deploy-image.sh`, `rollback.sh`, `scale.sh`, `rotate-secret.sh`, `sql-start-stop.sh`, `sql-backup-now.sh`, `sql-restore-test.sh`; `docs/04-aktivitas-rutin-iaas-paas-saas.md` bagian 3.1 dan 5; `tests/test_ops_scripts.py`; bukti lokal `docs/bukti/lokal/backup-restore-verify.txt`; B-013-01 sampai B-013-07, B-013-20 |
| 4.3 | > [ISI DARI APL02: elemen 3] | Aktivitas rutin SaaS (sebagai pelanggan dan penyedia) | `docs/04-aktivitas-rutin-iaas-paas-saas.md` bagian 3.3 dan 3.4; endpoint `POST /auth/users` di `app/routers/auth.py`; B-013-12 sampai B-013-14 |
| 4.4 | > [ISI DARI APL02: elemen 4] | Pencatatan aktivitas dan perubahan | `docs/04-aktivitas-rutin-iaas-paas-saas.md` bagian 4 (log aktivitas); `docs/bukti/013/log/`; `docs/bukti/013/change-log.md` (ditulis otomatis oleh `vm-patch.sh`) |

## Unit 5. J.631120.014.01 Memantau sarana dan prasarana agar bisa digunakan oleh user sesuai dengan SLA

| No | Elemen kompetensi (dari APL02) | Cakupan | Bukti |
|---|---|---|---|
| 5.1 | > [ISI DARI APL02: elemen 1] | Penetapan SLA dan SLI | `docs/05-sla-dan-pemantauan.md` bagian 1 sampai 3 (target, SLI, anggaran galat, ketersediaan berbasis waktu) |
| 5.2 | > [ISI DARI APL02: elemen 2] | Konfigurasi pemantauan per lapisan dan alert | `infra/terraform/slo.tf` (`google_monitoring_slo.availability`, `google_monitoring_slo.latency`, `google_monitoring_alert_policy.slo_fast_burn`, `error_ratio`, `sql_cpu`, `sql_disk`, `sql_connections`, aktif dengan `enable_sla_alerts = true`); `monitoring.tf` (uptime check, dasbor); `docs/05-sla-dan-pemantauan.md` bagian 4 dan 7; B-014-01 sampai B-014-04, B-014-06 |
| 5.3 | > [ISI DARI APL02: elemen 3] | Pelaksanaan pemantauan, laporan SLA, dan analisis penyimpangan | `scripts/sla_report.py` (ketersediaan berbasis permintaan dan berbasis waktu); `tests/test_sla_report.py`; `docs/laporan-sla/`; `docs/05-sla-dan-pemantauan.md` bagian 5, 6, dan 8; B-014-05 |
| 5.4 | > [ISI DARI APL02: elemen 4] | Pemulihan sesuai RPO dan RTO | `scripts/ops/sql-restore-test.sh` (mencatat durasi terhadap RTO); backup otomatis di `main.tf: google_sql_database_instance.db`; B-013-06, B-013-20 |

## Unit 6. J.631120.015.01 Memberikan dukungan teknis atas masalah user dan report next layer

| No | Elemen kompetensi (dari APL02) | Cakupan | Bukti |
|---|---|---|---|
| 6.1 | > [ISI DARI APL02: elemen 1] | Penerimaan, identifikasi, dan prioritas masalah pengguna | `.github/ISSUE_TEMPLATE/laporan-masalah.yml`; `request_id` pada respons galat (`app/main.py`, fungsi `error_response`); `tests/test_request_id.py`; `docs/06-sop-dukungan-teknis.md` bagian 1 sampai 3 (termasuk matriks *impact* dan *urgency*); B-015-01, B-015-07 |
| 6.2 | > [ISI DARI APL02: elemen 2] | Diagnosis dan penyelesaian masalah | `docs/06-sop-dukungan-teknis.md` bagian 5 (sembilan kasus dengan kueri dan perintah diagnosis); B-015-02 |
| 6.3 | > [ISI DARI APL02: elemen 3] | Eskalasi ke lapis berikutnya | `docs/06-sop-dukungan-teknis.md` bagian 4 (matriks eskalasi L1, L2, L3); `.github/ISSUE_TEMPLATE/laporan-insiden.yml` |
| 6.4 | > [ISI DARI APL02: elemen 4] | Dokumentasi dan komunikasi insiden | `docs/06-sop-dukungan-teknis.md` bagian 6 (gladi lokal yang sudah dijalankan dan simulasi Google Cloud) dan 7 (templat komunikasi); bukti lokal `docs/bukti/lokal/simulasi-insiden.txt`; B-015-03 sampai B-015-06, B-015-08 |

---

## Ringkasan bukti otomatis

| Bukti | Perintah | Hasil saat dokumen disusun (24 Oktober 2026) |
|---|---|---|
| Pengujian aplikasi dan skrip | `pytest -q --cov=app` | 65 test lulus, cakupan kode `app/` 94% |
| Pengujian API di PostgreSQL 16 | `TEST_DATABASE_URL=postgresql+psycopg://... pytest tests/test_api.py tests/test_request_id.py tests/test_integration_check.py` | 33 test lulus |
| Validasi Terraform | `terraform fmt -recursive && terraform validate` di `infra/terraform` | Valid (Terraform 1.9.8, provider google 6.50.0) |
| Lint skrip operasional | `shellcheck -x scripts/ops/*.sh` | Tanpa temuan |
| Uji integrasi end-to-end (lokal) | `scripts/api_integration_check.py` | 9 dari 9 lulus |
| Uji beban (lokal) | Locust 50 pengguna, 2 menit | 2.953 permintaan, 0 gagal, p95 65 ms |
| *Backup, restore, verify* (lokal) | `pg_dump`, `pg_restore`, perbandingan jumlah baris | 7 dari 7 tabel identik |
| Simulasi insiden (lokal) | Basis data dihentikan lalu dinyalakan | 503 dengan `request_id`, pulih sekitar 39 detik |

> [BUKTI: B-002-07, run GitHub Actions hijau yang menjalankan job test, test-postgres, dan terraform pada commit terakhir]
