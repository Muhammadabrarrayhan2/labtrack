# Bukti Unit J.631120.002.01

| Kode | Yang ditangkap | Perintah atau halaman | Sudah |
|---|---|---|---|
| B-002-01 | Riwayat build dan image kontainer di registry | Cloud Build > History, lalu Artifact Registry > labtrack > api | [ ] |
| B-002-02 | Estimasi biaya bulanan dan biaya aktual | Google Cloud Pricing Calculator (region asia-southeast2) dan Billing > Reports | [ ] |
| B-002-03 | Daftar revisi Cloud Run (konsep *revision* Knative) | Cloud Run > labtrack-api > Revisions | [ ] |
| B-002-04 | Keamanan koneksi Cloud SQL: SSL wajib, tanpa *authorized networks* | SQL > labtrack-db-xxxx > Connections > Security dan Networking | [ ] |
| B-002-05 | Daftar secret dan versinya (tanpa membuka nilai) | Security > Secret Manager | [ ] |
| B-002-06 | Provider Workload Identity dengan *attribute condition* repositori | IAM & Admin > Workload Identity Federation > labtrack-gh-xxxx > github | [ ] |
| B-002-07 | Run GitHub Actions hijau: job test (shellcheck, pytest), terraform (fmt, validate), deploy | GitHub > Actions > run terakhir di main | [ ] |
| B-002-08 | Ringkasan `terraform plan` ("Plan: N to add") | `terraform plan -out=tfplan` | [ ] |
| B-002-09 | Laporan uji integrasi terhadap API di Cloud Run dan Cloud SQL (9 pemeriksaan) | `python scripts/api_integration_check.py --out docs/bukti/002/integration-report.md` dengan `BASE_URL` dan `ADMIN_PASSWORD` | [ ] |
