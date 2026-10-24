# Bukti Unit J.631120.013.01

Untuk setiap aktivitas, simpan keluaran terminal lengkap di `log/<YYYY-MM-DD>-<kode-aktivitas>.txt` (misalnya `log/2026-10-25-P6.txt`), lalu isi baris yang sesuai di log aktivitas `docs/04-aktivitas-rutin-iaas-paas-saas.md` bagian 4. Contoh menyimpan keluaran:

```bash
scripts/ops/rollback.sh 2>&1 | tee docs/bukti/013/log/2026-10-25-P6.txt
```

| Kode | Yang ditangkap | Perintah atau halaman | Sudah |
|---|---|---|---|
| B-013-01 | Cek kesehatan layanan | `curl -s $API/health` | [ ] |
| B-013-02 | Deploy manual image dan *smoke test* | `scripts/ops/deploy-image.sh <tag>` | [ ] |
| B-013-03 | Rollback ke revisi sebelumnya lalu kembali ke latest, ditambah daftar revisi dengan persentase trafik | `scripts/ops/rollback.sh`, `scripts/ops/rollback.sh --to-latest`, Cloud Run > Revisions | [ ] |
| B-013-04 | Pengaturan kapasitas jam praktikum | `scripts/ops/scale.sh 1 3` lalu `scripts/ops/scale.sh 0 3` | [ ] |
| B-013-05 | Backup *on-demand* Cloud SQL | `scripts/ops/sql-backup-now.sh` dan SQL > Backups | [ ] |
| B-013-06 | Uji restore dengan tabel jumlah baris dan durasi | `scripts/ops/sql-restore-test.sh` | [ ] |
| B-013-07 | Rotasi kunci JWT: versi secret baru dan revisi baru, token lama ditolak 401 | `scripts/ops/rotate-secret.sh`, lalu panggil `/auth/me` dengan token lama | [ ] |
| B-013-08 | Daftar berkas `pg_dump` di bucket backup dan log `labtrack-backup: success` | `gcloud storage ls -l gs://$PROJECT_ID-labtrack-backups/backups/` dan Logs Explorer | [ ] |
| B-013-09 | *Patch* OS VM dengan snapshot pra-*patch* | `scripts/ops/vm-patch.sh --snapshot` | [ ] |
| B-013-10 | SSH melalui IAP dan status timer backup | `scripts/ops/vm-ssh.sh "hostname; systemctl list-timers labtrack-backup.timer --no-pager"` | [ ] |
| B-013-11 | Stop dan start VM | `scripts/ops/vm-start-stop.sh stop`, lalu `start` | [ ] |
| B-013-12 | Aturan proteksi cabang `main` | GitHub > Settings > Branches | [ ] |
| B-013-13 | Penyediaan akun asisten (HTTP 201) | `POST /auth/users` di Swagger atau curl | [ ] |
| B-013-14 | Penonaktifan akun, lalu login akun tersebut ditolak 401 | Cloud SQL Studio, `UPDATE users SET is_active = false ...`, lalu `POST /auth/login` | [ ] |
| B-013-15 | Detail VM `labtrack-ops`: e2-micro, Debian 12, tanpa IP eksternal, service account `labtrack-ops` | Compute Engine > VM instances > labtrack-ops | [ ] |
| B-013-16 | Jadwal snapshot harian terpasang pada boot disk, retensi 7 hari | Compute Engine > Snapshots > Snapshot schedules, dan Disks > labtrack-ops-boot | [ ] |
| B-013-17 | SSH langsung tanpa IAP gagal (tidak ada akses dari internet) | `gcloud compute ssh labtrack-ops --zone=<zone>` tanpa `--tunnel-through-iap` | [ ] |
| B-013-18 | Laporan provisioning VM (konfigurasi, lscpu, free, df, IP, gateway, NAT, layanan) | `scripts/ops/vm-report.sh`, berkas `docs/bukti/013/vm-provisioning-<tanggal>.txt` | [ ] |
| B-013-19 | Change log patching yang ditulis otomatis | Berkas `docs/bukti/013/change-log.md` setelah `scripts/ops/vm-patch.sh --snapshot` | [ ] |
| B-013-20 | Restore verification report | Berkas `docs/bukti/013/restore-verification-<tanggal>.md` dari `scripts/ops/sql-restore-test.sh` | [ ] |
