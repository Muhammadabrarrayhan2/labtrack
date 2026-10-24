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

```bash
cd labtrack
git init && git add . && git commit -m "Initial LabTrack API"
git branch -M main
git remote add origin https://github.com/<username>/labtrack.git
git push -u origin main
```

Workflow akan berjalan dan job `test` hijau, job `deploy` gagal karena variabel GCP belum diisi. Itu normal.

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
```

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

Opsional, demo alert: ubah sementara path uptime check ke `/tidak-ada` di Console, tunggu email alert masuk (sekitar 5 sampai 10 menit), lalu kembalikan ke `/health`. 📸 Screenshot email alert.

## 9. Backup dan keamanan database

```bash
INSTANCE=$(gcloud sql instances list --format='value(name)' --filter='name~labtrack-db')
gcloud sql backups create --instance=$INSTANCE --description="Backup sebelum asesmen"
gcloud sql backups list --instance=$INSTANCE
```

📸 Screenshot **SQL > labtrack-db > Backups** (automated harian 01:00 WIB, retensi 7) dan **Connections > Security** (SSL wajib, tidak ada authorized networks).

📸 Screenshot **IAM** yang memperlihatkan `labtrack-run` hanya punya Cloud SQL Client, Log Writer, Metric Writer, plus akses per-resource ke bucket dan secret.

## 10. Setelah asesmen: hentikan biaya

Matikan Cloud SQL tanpa menghapus data:

```bash
gcloud sql instances patch $INSTANCE --activation-policy=NEVER
```

Atau hapus semuanya:

```bash
cd infra/terraform && terraform destroy
```

---

## Checklist bukti untuk APL02

Cocokkan dulu dengan daftar unit kompetensi yang muncul di APL02. Pemetaan di bawah ini mengikuti kelompok kompetensi yang umum di skema cloud computing, jadi sesuaikan nama unitnya.

| Kelompok kompetensi | Bukti dari LabTrack |
|---|---|
| Memahami model layanan cloud (IaaS, PaaS, SaaS) | Bagian "Analisis pemilihan layanan" di dokumen portofolio: alasan memilih Cloud Run (PaaS serverless) dan Cloud SQL (DBaaS) dibanding Compute Engine (IaaS) |
| Merancang arsitektur cloud | Diagram arsitektur (gambar ulang diagram di README memakai ikon resmi GCP di draw.io) |
| Provisioning dan deployment | Terraform plan/apply, Cloud Build, revisi Cloud Run, aplikasi live |
| Infrastructure as Code | Isi folder `infra/terraform` dan penjelasan tiap file |
| Penyimpanan dan database cloud | Cloud SQL, bucket privat, signed URL, versioning |
| Keamanan cloud | IAM least privilege, Secret Manager, bucket privat, SSL wajib, WIF tanpa key |
| Otomasi dan CI/CD | Workflow GitHub Actions dan run yang berhasil |
| Monitoring dan logging | Dashboard, uptime check, alert, log terstruktur |
| Backup dan pemulihan | Konfigurasi backup otomatis dan backup on-demand |
| Pengelolaan biaya | Budget alert, estimasi Pricing Calculator, scale to zero, cleanup |

Susunan PDF portofolio yang disarankan:

1. Halaman judul dan identitas
2. Latar belakang dan kebutuhan (masalah pencatatan praktikum yang kamu alami sebagai asisten lab)
3. Analisis pemilihan layanan dan estimasi biaya
4. Diagram arsitektur
5. Implementasi infrastruktur (Terraform, per resource)
6. Proses deployment dan CI/CD (dengan screenshot)
7. Keamanan
8. Monitoring, logging, backup
9. Pengujian (hasil pytest dan uji API di Swagger)
10. Kesimpulan dan pengembangan lanjutan (Alembic, private IP, multi-region)
11. Lampiran: link repo GitHub dan URL aplikasi
