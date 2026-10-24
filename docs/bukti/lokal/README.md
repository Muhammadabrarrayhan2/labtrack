# Bukti Lingkungan Lokal

Berkas di folder ini adalah keluaran nyata yang dihasilkan pada 24 Oktober 2026 dari tumpukan lokal `docker compose` (satu kontainer API LabTrack dan PostgreSQL 16) di laptop pengembang. Bukti ini **bukan** hasil Google Cloud. Fungsinya membuktikan bahwa setiap skenario praktik berjalan dan menjadi garis dasar pembanding. Bukti Google Cloud disimpan di folder unit masing-masing setelah deploy.

| Berkas | Isi | Skenario modul | Hasil |
|---|---|---|---|
| `seed-output.txt` | Pengisian data demo melalui API | Lab 2 | 1 mata kuliah, 12 mahasiswa, 4 sesi |
| `integration-report.md` | Uji integrasi API dan PostgreSQL (`scripts/api_integration_check.py`) | Lab 2, bukti minimum #2 | 9 dari 9 pemeriksaan lulus |
| `locust_stats.csv`, `locust_stats_history.csv`, `locust_failures.csv`, `locust-report.html` | Uji beban 50 pengguna, 2 menit | Uji *performance* | 2.953 permintaan, 0 gagal, p95 65 ms, 24,87 RPS |
| `backup-restore-verify.txt` | Backup penuh `pg_dump`, *restore* ke basis data uji, verifikasi jumlah baris dan isi data | Lab 3, bukti minimum #3 | 7 dari 7 tabel identik |
| `simulasi-insiden.txt` | Basis data dihentikan, `/health` 503 dengan `request_id`, pelacakan log, pemulihan | Lab 4, bukti minimum #5 | Pulih dalam sekitar 39 detik |

Cara mengulang:

```bash
docker compose up -d --build
BASE_URL=http://localhost:8080 ADMIN_PASSWORD=AdminPass123 python scripts/seed_demo.py
ADMIN_PASSWORD=AdminPass123 python scripts/api_integration_check.py --base-url http://localhost:8080 --out docs/bukti/lokal/integration-report.md
LABTRACK_PASSWORD=AdminPass123 locust -f scripts/loadtest/locustfile.py --host http://localhost:8080 \
  --headless -u 50 -r 5 -t 2m --csv docs/bukti/lokal/locust --html docs/bukti/lokal/locust-report.html
```

Perintah backup, *restore*, dan simulasi insiden tercantum di awal setiap berkas keluarannya.
