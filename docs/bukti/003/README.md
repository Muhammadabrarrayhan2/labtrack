# Bukti Unit J.631120.003.01

Berkas `locust_stats.csv`, `locust_stats_history.csv`, `locust_failures.csv`, dan `locust-report.html` dihasilkan otomatis di folder ini oleh perintah uji beban (lihat `README.md` repositori, bagian "Load test").

| Kode | Yang ditangkap | Perintah atau halaman | Sudah |
|---|---|---|---|
| B-003-01 | Ringkasan terminal Locust di akhir uji (tabel statistik dan persentil) | `locust -f scripts/loadtest/locustfile.py --host "$API" --headless -u 50 -r 5 -t 5m --csv docs/bukti/003/locust --html docs/bukti/003/locust-report.html` | [ ] |
| B-003-02 | Grafik "Container instances" selama uji | Monitoring > Dashboards > LabTrack Overview, rentang 15 menit | [ ] |
| B-003-03 | Grafik "Request latency p95" dan "Cloud SQL CPU utilization" selama uji | Dasbor yang sama | [ ] |
| B-003-04 | Spesifikasi kontainer Cloud Run: 1 vCPU, 512 MiB, konkurensi 40, maksimum 3 instans | `gcloud run services describe labtrack-api --region=asia-southeast2`, atau Cloud Run > labtrack-api > Revisions | [ ] |
| B-003-05 | Konfigurasi Cloud SQL: db-f1-micro, SSD 10 GB, backup harian | SQL > labtrack-db-xxxx > Overview | [ ] |
| B-003-06 | Laporan HTML Locust | Berkas `docs/bukti/003/locust-report.html` | [ ] |
| B-003-07 | Uji stress bertahap 100 sampai 300 VU lalu pemulihan: grafik p95 dan jumlah pengguna di laporan HTML, grafik instans di dasbor | `LOAD_SHAPE=stress locust ... --csv docs/bukti/003/stress --html docs/bukti/003/stress-report.html` | [ ] |
