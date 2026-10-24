# Bukti Unit J.631120.014.01

| Kode | Yang ditangkap | Perintah atau halaman | Sudah |
|---|---|---|---|
| B-014-01 | Dua SLO (ketersediaan 99,5% dan latensi 800 ms) dengan status dan sisa anggaran galat | Monitoring > SLOs, layanan "LabTrack API" | [ ] |
| B-014-02 | Daftar alert policy LabTrack (uptime, *fast burn*, rasio 5xx, CPU, disk, koneksi) | Monitoring > Alerting > Policies | [ ] |
| B-014-03 | Dasbor lengkap termasuk widget SLO dan koneksi Cloud SQL | Monitoring > Dashboards > LabTrack Overview | [ ] |
| B-014-04 | Uptime check `/health` hijau dari beberapa region | Monitoring > Uptime checks > LabTrack API /health | [ ] |
| B-014-05 | Terminal saat `scripts/sla_report.py` dijalankan, dan berkas laporan yang dihasilkan | `python scripts/sla_report.py --project $PROJECT_ID --start 2026-10-01 --end 2026-10-26` | [ ] |
| B-014-06 | Metrik VM dari Ops Agent: CPU, memori, disk, jaringan | Compute Engine > VM instances > labtrack-ops > Observability | [ ] |
