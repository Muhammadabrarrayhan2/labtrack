# Bukti Unit J.631120.001.01

| Kode | Yang ditangkap | Perintah atau halaman | Sudah |
|---|---|---|---|
| B-001-01 | Grafik "Container instances" naik dari 0 lalu turun kembali (*rapid elasticity*) | Monitoring > Dashboards > LabTrack Overview, rentang waktu mencakup uji beban | [ ] |
| B-001-02 | Keluaran `terraform apply` bagian "Apply complete" (*on-demand self-service*) | `terraform apply tfplan` di `infra/terraform` | [ ] |
| B-001-03 | Swagger UI dengan URL `*.run.app` terlihat di bilah alamat (*broad network access*) | Peramban, `$API/docs` | [ ] |
| B-001-04 | Pengaturan *autoscaling* revisi: minimum 0, maksimum 3, konkurensi 40 | Cloud Run > labtrack-api > Revisions > revisi terbaru > tab Containers dan Scaling | [ ] |
| B-001-05 | Laporan biaya per layanan (*measured service*) | Billing > Reports, kelompokkan per Service | [ ] |
