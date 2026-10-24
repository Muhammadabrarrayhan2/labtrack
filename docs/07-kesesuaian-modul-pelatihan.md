# Kesesuaian Portofolio dengan Modul Pelatihan Insinyur Cloud Computing

Dokumen ini memetakan materi *Modul Pelatihan Insinyur Cloud Computing Revisi* (pelatihan intensif 2 hari, 40 slide, berbasis SKKNI 456 Tahun 2015) ke bukti pada proyek LabTrack. Modul mencakup 6 unit kompetensi, 22 elemen kompetensi, dan 61 kriteria unjuk kerja (KUK): 20 KUK terminologi dan konsep, 16 KUK teknologi, dan 25 KUK perangkat keras, pemeliharaan, SLA, serta dukungan teknis.

## 1. Perbedaan lingkungan praktik

Laboratorium modul memakai Windows, VMware Workstation, Proxmox VE (*nested virtualization*), VM Ubuntu berisi PostgreSQL dan REST API Node.js/Express, serta Prometheus dan Grafana. Modul sendiri menegaskan bahwa Proxmox di dalam VM adalah laboratorium virtualisasi, bukan *private cloud* produksi.

LabTrack menerapkan kompetensi yang sama di *public cloud* (Google Cloud). Padanan komponennya:

| Komponen modul | Padanan di LabTrack | Catatan |
|---|---|---|
| Host virtualisasi Proxmox (KVM) | Compute Engine (hypervisor berbasis KVM milik Google) | VM `labtrack-ops`, `infra/terraform/iaas.tf` |
| VM Ubuntu Server | VM Debian 12 `labtrack-ops` | Distribusi berbeda, pengelolaan sama: apt, systemd, lscpu, free, df |
| Bridge `vmbr0`, NAT/bridged | VPC `labtrack-ops-vpc`, subnet, Cloud NAT | Tanpa IP publik, keluar melalui NAT |
| PostgreSQL di VM | Cloud SQL for PostgreSQL 16 | Versi mesin sama (16) |
| REST API Node.js/Express | REST API Python/FastAPI | Konsep sama: HTTP, JSON, endpoint health |
| `/api/health` | `/health` | Juga memeriksa koneksi basis data |
| Backup VM Proxmox (vzdump) | Snapshot disk terjadwal, backup Cloud SQL, `pg_dump` | Tiga lapis backup |
| Restore ke VM ID baru | Restore ke instans Cloud SQL sementara | `scripts/ops/sql-restore-test.sh` |
| Node Exporter, Prometheus, Grafana | Ops Agent, Cloud Monitoring, dasbor | `monitoring.tf`, `slo.tf` |
| Blackbox Exporter (pemeriksaan HTTP) | Uptime check `/health` dari beberapa region | `google_monitoring_uptime_check_config.health` |
| Tiket helpdesk | GitHub Issues dengan templat | `.github/ISSUE_TEMPLATE/` |

Seluruh skenario praktik modul juga sudah dijalankan pada lingkungan lokal berbasis Docker (API dan PostgreSQL 16) dengan hasil nyata di `docs/bukti/lokal/`, sehingga prosedurnya terbukti berjalan sebelum diulang di Google Cloud.

## 2. Pemetaan per slide

### Hari 1: Fundamental dan infrastruktur

| Slide | Materi | Bukti LabTrack |
|---|---|---|
| 5 | Sumber daya, layanan, pengelolaan | `docs/01-konsep-cloud-computing.md` bagian 1 dan 2 |
| 6 | Arsitektur berlapis (fisik, virtualisasi, manajemen, layanan, konsumen) | `docs/01-konsep-cloud-computing.md` bagian 7 |
| 7 | *Horizontal* dan *vertical scaling* | `docs/01-konsep-cloud-computing.md` bagian 8; `scripts/ops/scale.sh` (horizontal); variabel `db_tier` (vertikal) |
| 8 | *On-demand*, *multitenancy*, *elasticity* | `docs/01-konsep-cloud-computing.md` bagian 2 dan 8 |
| 9 | IaaS, PaaS, SaaS | `docs/01-konsep-cloud-computing.md` bagian 3 dan 5; `docs/04-aktivitas-rutin-iaas-paas-saas.md` |
| 10 | *Public*, *private*, *hybrid* | `docs/01-konsep-cloud-computing.md` bagian 4 |
| 11 | SLA: *availability* dan p95 | `docs/05-sla-dan-pemantauan.md` bagian 1 sampai 3 |
| 12 | Topologi jaringan | `docs/01-konsep-cloud-computing.md` bagian 9 |
| 13 | *Failover*, *resiliency*, *replication*, *access* | `docs/02-teknologi-cloud.md` bagian 4 |
| 14 | Ancaman keamanan (DoS, autentikasi, otorisasi) | `docs/02-teknologi-cloud.md` bagian 5 |
| 15 | Arsitektur REST API | README bagian *API overview*; `app/`; uji integrasi `scripts/api_integration_check.py` |
| 16 | *File*, *block*, *relational*, *non-relational storage* | `docs/02-teknologi-cloud.md` bagian 6 |
| 17 | Pengujian *integration*, *performance*, *stress* | `docs/02-teknologi-cloud.md` bagian 7; `docs/03-kebutuhan-perangkat-keras.md` bagian 5 dan 6 |
| 18 | Hasil *stress testing* (p95 terhadap jumlah VU) | Profil `LOAD_SHAPE=stress` 100 sampai 300 VU (`scripts/loadtest/stages.py`); `docs/03-kebutuhan-perangkat-keras.md` bagian 6 |
| 19 | Perangkat keras: *compute*, *storage*, *network*, operasional | `docs/03-kebutuhan-perangkat-keras.md` bagian 1 dan 4 |
| 20 | Persiapan lab, identifikasi VT-x, `/dev/kvm` | Bagian 1 dokumen ini; laporan provisioning VM `scripts/ops/vm-report.sh` (baris `Hypervisor vendor`, `Virtualization type`) |

### Hari 2: Operasional, monitoring, dan evaluasi

| Slide | Materi | Bukti LabTrack |
|---|---|---|
| 22 | Backup *full*, *incremental*, *differential* | `docs/04-aktivitas-rutin-iaas-paas-saas.md` bagian 5 |
| 23 | RPO dan RTO; frekuensi backup saja belum menjamin RPO | `docs/05-sla-dan-pemantauan.md` bagian 1.3; uji restore P9 |
| 24 | Siklus *backup, restore, verify* dan *restore verification report* | `scripts/ops/sql-restore-test.sh` menulis laporan verifikasi; bukti lokal `docs/bukti/lokal/backup-restore-verify.txt` |
| 25 | *Patching* dengan prosedur perubahan terkontrol dan *change log* | `scripts/ops/vm-patch.sh` (identifikasi, snapshot, terapkan, uji pasca, catat); `docs/04-aktivitas-rutin-iaas-paas-saas.md` bagian 6 |
| 26 | Monitoring CPU, memori, *storage*, jaringan | `docs/05-sla-dan-pemantauan.md` bagian 7 |
| 27 | Prometheus dan Grafana, Blackbox Exporter, laporan SLA | Cloud Monitoring, uptime check, `scripts/sla_report.py` |
| 28 | *Availability* target dan aktual (99,9% dan 99,8958%) | `scripts/sla_report.py` bagian ketersediaan berbasis waktu; contoh perhitungan di `docs/05-sla-dan-pemantauan.md` bagian 3.1, diuji di `tests/test_sla_report.py` |
| 29 | Analisis penyimpangan SLA: bukti, evaluasi, tindak lanjut, kompensasi | `docs/05-sla-dan-pemantauan.md` bagian 8 |
| 30 | Alur tiket helpdesk dan eskalasi | `docs/06-sop-dukungan-teknis.md` bagian 2 dan 4 |
| 31 | Prioritas insiden P1 sampai P4 | `docs/06-sop-dukungan-teknis.md` bagian 3, termasuk matriks *impact* dan *urgency* |
| 32 | Arsitektur praktik terintegrasi | README bagian *Architecture* |
| 33 | Lab 1: VM dan jaringan | `scripts/ops/vm-report.sh` (lscpu, free -h, df -h, IP, *route*, uji *gateway*) |
| 34 | Lab 2: PostgreSQL dan REST API | `scripts/api_integration_check.py`; job CI `test-postgres`; bukti lokal `docs/bukti/lokal/integration-report.md` |
| 35 | Lab 3: backup, restore, *patching*, monitoring | `sql-backup-now.sh`, `sql-restore-test.sh`, `vm-patch.sh`, dasbor |
| 36 | Lab 4: simulasi insiden | `docs/06-sop-dukungan-teknis.md` bagian 6; bukti lokal `docs/bukti/lokal/simulasi-insiden.txt` |
| 37 | Evaluasi: pengetahuan, praktik, dokumen, verifikasi | `docs/00-PEMETAAN-UNIT-KOMPETENSI.md` |
| 40 | Evaluasi berdasarkan bukti kerja, bukan tangkapan layar saja | Setiap bukti didukung berkas keluaran perintah, laporan yang dihasilkan skrip, dan riwayat commit |

## 3. Bukti minimum evaluasi akhir (slide 39)

| No | Bukti minimum | Alat di LabTrack | Bukti lokal (sudah ada) | Bukti Google Cloud (diisi setelah deploy) |
|---|---|---|---|---|
| 1 | *VM provisioning report* dan hasil konektivitas | `scripts/ops/vm-report.sh` | Tidak berlaku (VM hanya di Google Cloud) | `docs/bukti/013/vm-provisioning-<tanggal>.txt`, B-013-18 |
| 2 | *API integration test* dan data PostgreSQL | `scripts/api_integration_check.py`, job CI `test-postgres` | `docs/bukti/lokal/integration-report.md` (9 dari 9 lulus) | `docs/bukti/002/integration-report.md`, B-002-09 |
| 3 | *Backup log* dan *restore verification* | `scripts/ops/sql-backup-now.sh`, `scripts/ops/sql-restore-test.sh` | `docs/bukti/lokal/backup-restore-verify.txt` (7 tabel identik) | `docs/bukti/013/restore-verification-<tanggal>.md`, B-013-06, B-013-20 |
| 4 | *SLA monitoring report* dan perhitungan *availability* | `scripts/sla_report.py` | Contoh perhitungan diuji di `tests/test_sla_report.py` | `docs/laporan-sla/<periode>.md`, B-014-05 |
| 5 | *Incident ticket*, eskalasi, dan *resolution report* | Templat issue, SOP bagian 6 | `docs/bukti/lokal/simulasi-insiden.txt` | Issue `laporan-insiden`, B-015-03 sampai B-015-08 |

## 4. Perbedaan kebijakan dengan contoh modul

| Butir | Contoh modul | LabTrack | Alasan |
|---|---|---|---|
| Target ketersediaan | 99,9% | 99,5% | Cloud SQL tier `db-f1-micro` ZONAL tanpa *standby*; target 99,9% memerlukan konfigurasi REGIONAL dengan biaya kurang lebih dua kali lipat. Anggaran galat 216 menit per 30 hari realistis untuk satu pengelola |
| Latensi p95 | 500 ms | 800 ms | Memberi ruang untuk *cold start* karena layanan berskala ke nol. Hasil uji beban lokal menunjukkan p95 agregat 65 ms, sehingga 500 ms juga dapat dipertimbangkan setelah hasil uji di Google Cloud tersedia |
| Respons awal P1 sampai P4 | 15 menit, 30 menit, 4 jam, 1 hari kerja | Sama | Diselaraskan dengan modul |
