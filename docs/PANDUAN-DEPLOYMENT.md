# Panduan Deployment LabTrack ke Google Cloud Platform

Panduan ini menjalankan seluruh stack dari nol sampai aplikasi live, lalu mengumpulkan bukti untuk portofolio sertifikasi. Tandai tiap langkah yang menghasilkan bukti dengan screenshot (ikon 📸).

Perkiraan waktu: 2 sampai 3 jam, sebagian besar menunggu Cloud SQL dibuat (sekitar 10 menit) dan build image.

## 0. Persiapan

Yang perlu terpasang di laptop:

- Google Cloud CLI (`gcloud`)
- Terraform 1.5 atau lebih baru
- Git dan akun GitHub
- Python 3.12 (untuk test dan script seed)

Akun GCP baru mendapat kredit trial US$300. Biaya utama stack ini adalah Cloud SQL db-f1-micro, kira-kira US$10 sampai 15 per bulan kalau dibiarkan menyala (angka pastinya cek di Pricing Calculator untuk region asia-southeast2). Cloud Run, Cloud Storage, dan Artifact Registry untuk skala demo masuk free tier.

## 1. Buat project dan budget alert

```bash
gcloud auth login
gcloud auth application-default login
gcloud projects create labtrack-<suffix-unik> --name="LabTrack"
gcloud config set project labtrack-<suffix-unik>
```

Hubungkan billing di Console: **Billing > Link a billing account**.

Lalu buat budget alert sebelum membuat resource apa pun: **Billing > Budgets & alerts > Create budget**, nominal US$10, alert di 50%, 90%, 100%. 📸 Screenshot halaman budget.

## 2. Push repo ke GitHub

Repositori lokal sudah berisi riwayat commit per tahap pengerjaan (`git log --oneline`), yang sekaligus menjadi bukti keaslian. Buat repositori kosong di GitHub (tanpa README), lalu:

```bash
cd labtrack
git remote add origin https://github.com/<username>/labtrack.git
git push -u origin main
```

Workflow akan berjalan: job `test` dan `terraform` hijau, job `deploy` gagal karena variabel GCP belum diisi. Itu normal.

Ganti `OWNER` di `.github/ISSUE_TEMPLATE/config.yml` dengan username GitHub kamu.

## 3. Terraform tahap 1: API dan Artifact Registry

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
```

Isi `terraform.tfvars`:

```hcl
project_id        = "labtrack-<suffix-unik>"
region            = "asia-southeast2"
image             = "asia-southeast2-docker.pkg.dev/labtrack-<suffix-unik>/labtrack/api:v1"
github_repository = "<username>/labtrack"
alert_email       = "email-kamu@gmail.com"
enable_sla_alerts = true   # lima alert SLA di slo.tf, lihat catatan biaya di variables.tf
```

```bash
terraform init
terraform apply \
  -target=google_project_service.apis \
  -target=google_artifact_registry_repository.repo
```

Tahap ini perlu dipisah karena Cloud Run butuh image yang sudah ada di registry.

## 4. Build image pertama dengan Cloud Build

Dari root repo (tidak perlu Docker di laptop):

```bash
cd ../..
gcloud builds submit --tag asia-southeast2-docker.pkg.dev/labtrack-<suffix-unik>/labtrack/api:v1 .
```

📸 Screenshot riwayat build di **Cloud Build > History** dan image di **Artifact Registry**.

Kalau gagal dengan error permission push ke Artifact Registry, beri role ke service account default Cloud Build/Compute:

```bash
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
```

## 5. Terraform tahap 2: seluruh infrastruktur

```bash
cd infra/terraform
terraform plan -out=tfplan     # 📸 screenshot ringkasan "Plan: N to add"
terraform apply tfplan
terraform output
```

Yang dibuat: Cloud SQL (PostgreSQL 16 + database + user), 3 secret di Secret Manager, bucket laporan, 2 service account dengan role minimum, Cloud Run, akses publik, Workload Identity Federation untuk GitHub, uptime check, alert policy, dan dashboard.

📸 Screenshot output `terraform apply` (bagian "Apply complete") dan `terraform output`.

## 6. Verifikasi aplikasi live

```bash
API=$(terraform output -raw api_url)
curl $API/health
# {"status":"ok","database":"ok","version":"1.0.0","environment":"production"}
```

Buka `$API/docs` di browser. 📸 Screenshot Swagger UI dengan URL `*.run.app` terlihat.

Ambil password admin dari Secret Manager lalu isi data demo:

```bash
export ADMIN_PASSWORD=$(gcloud secrets versions access latest --secret=labtrack-admin-password)
cd ../..
pip install httpx
BASE_URL=$API python scripts/seed_demo.py

# Uji integrasi API + Cloud SQL (bukti minimum #2 modul), B-002-09
BASE_URL=$API python scripts/api_integration_check.py --out docs/bukti/002/integration-report.md
```

Hasil yang diharapkan: "9 dari 9 pemeriksaan lulus". Bandingkan dengan hasil lokal di `docs/bukti/lokal/integration-report.md`.

Di Swagger: klik **Authorize**, login `admin@labtrack.dev` dengan password tadi, lalu coba:

1. `GET /courses/1/attendance-summary` 📸
2. `GET /sessions/1/reports`, ambil satu `id`, lalu `GET /reports/{id}/download-url`, buka URL-nya di browser (PDF terunduh, link kedaluwarsa 15 menit) 📸
3. Coba buka objek yang sama langsung lewat `https://storage.googleapis.com/<bucket>/<key>` dan tunjukkan hasilnya ditolak. Ini bukti bucket privat. 📸

## 7. Aktifkan CI/CD

Di GitHub: **Settings > Secrets and variables > Actions > Variables**, buat 4 variabel dari `terraform output github_vars`:

| Nama | Isi |
|---|---|
| `GCP_PROJECT_ID` | project ID |
| `GCP_REGION` | asia-southeast2 |
| `GCP_WIF_PROVIDER` | projects/.../providers/github |
| `GCP_DEPLOYER_SA` | labtrack-deployer@...iam.gserviceaccount.com |

Uji pipeline dengan perubahan kecil, misalnya ubah `__version__` di `app/__init__.py` menjadi `1.0.1`, commit, push. Workflow akan menjalankan test, build, push, deploy, dan smoke test.

📸 Screenshot run GitHub Actions yang hijau, daftar revisi di **Cloud Run > labtrack-api > Revisions**, dan `curl $API/health` yang menunjukkan versi 1.0.1.

Poin yang layak dijelaskan ke asesor: pipeline ini tidak memakai file JSON key. GitHub menukar token OIDC dengan kredensial GCP berumur pendek, dan hanya repo kamu yang diizinkan (lihat `attribute_condition` di `cicd.tf`).

## 8. Monitoring dan logging

- **Monitoring > Dashboards > LabTrack Overview**: request per detik, latency p95, jumlah instance, CPU Cloud SQL. Jalankan seed sekali lagi supaya grafiknya terisi. 📸
- **Monitoring > Uptime checks**: status check `/health` dari beberapa region. 📸
- **Monitoring > Alerting**: policy "LabTrack API is down" dan notification channel email. 📸
- **Logging > Logs Explorer**, query:

```
resource.type="cloud_run_revision"
resource.labels.service_name="labtrack-api"
jsonPayload.logger="labtrack"
```

Tunjukkan field `severity`, `latency_ms`, dan `request_id` yang terstruktur. 📸

Opsional, demo alert: ubah sementara path uptime check ke `/tidak-ada` di Console, tunggu email alert masuk (sekitar 5 sampai 10 menit), lalu kembalikan ke `/health`. 📸 Screenshot email alert. Demo yang lebih lengkap ada di langkah 14 (simulasi insiden).

SLO dan alert tambahan dari `slo.tf` sudah ikut dibuat pada langkah 5:

- **Monitoring > SLOs**: layanan "LabTrack API" dengan SLO ketersediaan 99,5% dan latensi 800 ms. 📸 B-014-01
- **Monitoring > Alerting > Policies**: uptime, *fast burn*, rasio 5xx, CPU, disk, dan koneksi Cloud SQL. 📸 B-014-02
- Dasbor kini memuat widget sisa anggaran galat, *burn rate*, dan koneksi Cloud SQL. 📸 B-014-03

Grafik SLO baru terisi setelah ada trafik; jalankan langkah 10 terlebih dahulu bila masih kosong.

## 9. Backup dan keamanan database

```bash
INSTANCE=$(gcloud sql instances list --format='value(name)' --filter='name~labtrack-db')
gcloud sql backups create --instance=$INSTANCE --description="Backup sebelum asesmen"
gcloud sql backups list --instance=$INSTANCE
```

📸 Screenshot **SQL > labtrack-db > Backups** (automated harian 01:00 WIB, retensi 7) dan **Connections > Security** (SSL wajib, tidak ada authorized networks).

📸 Screenshot **IAM** yang memperlihatkan `labtrack-run` hanya punya Cloud SQL Client, Log Writer, Metric Writer, plus akses per-resource ke bucket dan secret.


## 10. Uji beban (unit 003)

Jalankan setelah data demo terisi (langkah 6), dari laptop atau Cloud Shell:

```bash
cd ../..   # root repo
pip install -r requirements-dev.txt
export API=$(terraform -chdir=infra/terraform output -raw api_url)
export LABTRACK_PASSWORD=$(gcloud secrets versions access latest --secret=labtrack-admin-password)
locust -f scripts/loadtest/locustfile.py --host "$API" \
  --headless -u 50 -r 5 -t 5m \
  --csv docs/bukti/003/locust --html docs/bukti/003/locust-report.html
```

📸 B-003-01 ringkasan terminal. Segera buka dasbor dan ambil B-003-02 dan B-003-03 (rentang 15 menit terakhir), juga B-001-01. Isi tabel hasil di `docs/03-kebutuhan-perangkat-keras.md` bagian 5.2 dari `docs/bukti/003/locust_stats.csv`, lalu tulis analisis di bagian 5.3.

Uji *stress* bertahap (12 menit, 100 sampai 300 pengguna lalu pemulihan), jalankan terpisah di luar jam praktikum:

```bash
LOAD_SHAPE=stress locust -f scripts/loadtest/locustfile.py --host "$API" --headless \
  --csv docs/bukti/003/stress --html docs/bukti/003/stress-report.html
```

📸 B-003-07. Isi tabel di `docs/03-kebutuhan-perangkat-keras.md` bagian 6 dari `docs/bukti/003/stress_stats_history.csv`.

## 11. VM operasional `labtrack-ops` (IaaS, unit 013)

Tambahkan ke `terraform.tfvars`:

```hcl
enable_ops_vm = true
# Opsional, tier gratis e2-micro hanya di us-west1, us-central1, us-east1:
# ops_vm_region = "us-central1"
```

```bash
cd infra/terraform
terraform plan -out=tfplan    # periksa: VPC, subnet, router, NAT, firewall, SA, bucket backup, disk, snapshot policy, VM
terraform apply tfplan
terraform output ops_vm
```

Biaya tambahan sekitar US$8 sampai 10 per bulan di asia-southeast2 (rincian di deskripsi variabel `enable_ops_vm`). Matikan dengan `scripts/ops/vm-start-stop.sh stop` bila tidak dipakai.

Startup script memasang PostgreSQL client 16, Cloud SQL Auth Proxy, Ops Agent, dan timer backup. Tunggu sekitar 5 menit, lalu verifikasi:

```bash
export PROJECT_ID=$(gcloud config get-value project) REGION=asia-southeast2
# export ZONE=us-central1-a   # bila ops_vm_region diubah
scripts/ops/vm-ssh.sh "sudo journalctl -u google-startup-scripts --no-pager | tail -5"
scripts/ops/vm-ssh.sh "sudo systemctl start labtrack-backup.service && sudo journalctl -u labtrack-backup --no-pager | tail -3"
gcloud storage ls -l gs://$PROJECT_ID-labtrack-backups/backups/
```

Laporan provisioning VM (bukti minimum #1 modul):

```bash
scripts/ops/vm-report.sh     # disimpan ke docs/bukti/013/vm-provisioning-<tanggal>.txt
```

📸 B-013-08, B-013-10, B-013-15, B-013-16, B-013-17, B-013-18, dan B-014-06 (tab Observability VM). Snapshot terjadwal pertama terbentuk setelah pukul 03.00 WIB.

## 12. Aktivitas rutin (unit 013)

Jalankan skrip berikut satu per satu, simpan keluarannya dengan `tee` ke `docs/bukti/013/log/`, dan isi log aktivitas di `docs/04-aktivitas-rutin-iaas-paas-saas.md` bagian 4. Urutan ini aman karena setiap langkah mengembalikan kondisi semula:

```bash
L=docs/bukti/013/log; D=$(date +%F)
curl -s "$API/health" | tee $L/$D-P1.txt                                  # B-013-01
scripts/ops/sql-backup-now.sh "Sebelum aktivitas rutin" 2>&1 | tee $L/$D-P8.txt   # B-013-05
scripts/ops/scale.sh 1 3 2>&1 | tee $L/$D-P7.txt                          # B-013-04
scripts/ops/scale.sh 0 3 2>&1 | tee -a $L/$D-P7.txt
scripts/ops/rollback.sh 2>&1 | tee $L/$D-P6.txt                           # B-013-03 (butuh minimal 2 revisi, lihat langkah 7)
scripts/ops/rollback.sh --to-latest 2>&1 | tee -a $L/$D-P6.txt
scripts/ops/vm-patch.sh --snapshot 2>&1 | tee $L/$D-I3.txt                # B-013-09
scripts/ops/vm-start-stop.sh stop 2>&1 | tee $L/$D-I7.txt                 # B-013-11
scripts/ops/vm-start-stop.sh start 2>&1 | tee -a $L/$D-I7.txt
```

Lalu aktivitas SaaS: aktifkan proteksi cabang `main` di GitHub (B-013-12), buat akun asisten lewat `POST /auth/users` (B-013-13), dan uji penonaktifan akun (B-013-14).

Rotasi kunci JWT (B-013-07) membuat semua token tidak berlaku. Jalankan paling akhir, setelah uji beban dan pengambilan screenshot Swagger:

```bash
scripts/ops/rotate-secret.sh 2>&1 | tee $L/$D-P10.txt
```

## 13. Uji pemulihan backup (unit 013 dan 014)

Butuh `psql` dan `cloud-sql-proxy` di PATH (Cloud Shell sudah memiliki `psql`). Memakan waktu 15 sampai 25 menit dan membuat instans sementara yang otomatis dihapus.

```bash
scripts/ops/sql-restore-test.sh 2>&1 | tee docs/bukti/013/log/$(date +%F)-P9.txt
```

📸 B-013-06 (tabel jumlah baris dan durasi). Catat durasi sebagai bukti RTO di `docs/05-sla-dan-pemantauan.md`.

## 14. Simulasi insiden (unit 015)

Ikuti `docs/06-sop-dukungan-teknis.md` bagian 6: umumkan simulasi, buat issue `laporan-insiden`, hentikan Cloud SQL dengan `scripts/ops/sql-start-stop.sh stop`, amati `/health` 503 dan email alert, pulihkan dengan `start`, lalu isi kronologi. 📸 B-015-03 sampai B-015-06, B-015-08.

Sebelumnya ambil B-015-01 dan B-015-02 (respons galat dengan `request_id` dan pencarian log-nya), serta B-015-07 (issue contoh dari templat laporan masalah).

Simulasi ini memakai anggaran galat SLO ketersediaan; hal tersebut wajar dan akan terlihat pada laporan SLA.

## 15. Laporan SLA (unit 014)

```bash
gcloud auth application-default login
python scripts/sla_report.py --project "$PROJECT_ID" --start 2026-10-01 --end 2026-10-26 \
  --uptime-check-id "$(terraform -chdir=infra/terraform output -raw uptime_check_id)"
```

📸 B-014-05. Lengkapi bagian insiden dan tindak lanjut di berkas yang dihasilkan di `docs/laporan-sla/`, lalu salin angkanya ke templat di `docs/05-sla-dan-pemantauan.md` bagian 6.

## 16. Setelah asesmen: hentikan biaya

Matikan Cloud SQL dan VM tanpa menghapus data:

```bash
scripts/ops/sql-start-stop.sh stop
scripts/ops/vm-start-stop.sh stop          # bila enable_ops_vm = true
```

Atau hapus VM saja dengan `enable_ops_vm = false` lalu `terraform apply`, atau hapus semuanya:

```bash
cd infra/terraform && terraform destroy
```

---

## Checklist bukti untuk APL02

Pemetaan lengkap per elemen ada di [00-PEMETAAN-UNIT-KOMPETENSI.md](00-PEMETAAN-UNIT-KOMPETENSI.md), dan pemetaan ke modul pelatihan (slide dan lab) di [07-kesesuaian-modul-pelatihan.md](07-kesesuaian-modul-pelatihan.md). Daftar tangkapan layar per unit ada di `docs/bukti/<unit>/README.md`. Bukti lokal yang sudah terisi ada di `docs/bukti/lokal/`.

`vm-patch.sh` (langkah 12) menulis *change log* ke `docs/bukti/013/change-log.md` (B-013-19), dan `sql-restore-test.sh` (langkah 13) menulis *restore verification report* ke `docs/bukti/013/restore-verification-<tanggal>.md` (B-013-20).

| Unit | Dokumen utama | Bukti eksekusi | Langkah panduan |
|---|---|---|---|
| J.631120.001.01 Terminologi dan konsep | `docs/01-konsep-cloud-computing.md` | B-001-01 sampai B-001-05 | 5, 6, 10 |
| J.631120.002.01 Teknologi cloud | `docs/02-teknologi-cloud.md` | B-002-01 sampai B-002-09 | 4, 5, 7, 9 |
| J.631120.003.01 Perangkat keras | `docs/03-kebutuhan-perangkat-keras.md` | B-003-01 sampai B-003-07, hasil Locust | 10 |
| J.631120.013.01 Aktivitas rutin IaaS, PaaS, SaaS | `docs/04-aktivitas-rutin-iaas-paas-saas.md` | B-013-01 sampai B-013-20, log di `docs/bukti/013/log/` | 11, 12, 13 |
| J.631120.014.01 Pemantauan sesuai SLA | `docs/05-sla-dan-pemantauan.md` | B-014-01 sampai B-014-06, `docs/laporan-sla/` | 8, 15 |
| J.631120.015.01 Dukungan teknis dan eskalasi | `docs/06-sop-dukungan-teknis.md` | B-015-01 sampai B-015-08 | 14 |

Checklist sebelum asesmen:

- [ ] `pytest -q --cov=app` lulus di laptop dan di GitHub Actions
- [ ] Semua placeholder `[ISI SETELAH DEPLOY]` dan `[BUKTI]` sudah diganti dengan data nyata
- [ ] Nama elemen kompetensi di `00-PEMETAAN-UNIT-KOMPETENSI.md` sudah disalin dari APL02
- [ ] Semua berkas `B-xxx-yy.png` ada di folder `docs/bukti/`
- [ ] URL repositori dan URL aplikasi tercantum di dokumen pemetaan
- [ ] Cloud SQL dalam keadaan menyala pada hari asesmen (`scripts/ops/sql-start-stop.sh status`)

Susunan PDF portofolio yang disarankan:

1. Halaman judul dan identitas
2. Pemetaan unit kompetensi (`00-PEMETAAN-UNIT-KOMPETENSI.md`)
3. Latar belakang dan kebutuhan (masalah pencatatan praktikum yang kamu alami sebagai asisten lab)
4. Konsep dan teknologi (`01`, `02`), termasuk analisis pemilihan layanan dan estimasi biaya
5. Diagram arsitektur (gambar ulang diagram di README memakai ikon resmi GCP di draw.io)
6. Kebutuhan perangkat keras dan hasil uji beban (`03`)
7. Implementasi infrastruktur dan CI/CD (Terraform per resource, screenshot deployment)
8. Aktivitas rutin dan log operasional (`04`)
9. SLA, pemantauan, dan laporan SLA (`05`)
10. SOP dukungan teknis dan laporan simulasi insiden (`06`)
11. Kesimpulan dan pengembangan lanjutan (Alembic, private IP, endpoint penonaktifan akun dan reset password)
12. Lampiran: link repo GitHub, URL aplikasi, berkas bukti
