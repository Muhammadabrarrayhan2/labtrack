# Aktivitas Rutin pada IaaS, PaaS, dan SaaS

Unit kompetensi: **J.631120.013.01 Menjalankan aktivitas rutin pada IaaS, PaaS, dan SaaS**

Dokumen ini menetapkan aktivitas operasional rutin LabTrack untuk ketiga model layanan, alat yang dipakai untuk menjalankannya, serta log aktivitas sebagai bukti pelaksanaan.

## 1. Komponen per model layanan

| Model | Komponen LabTrack | Berkas definisi |
|---|---|---|
| IaaS | VM `labtrack-ops` (Compute Engine e2-micro, Debian 12), boot disk dan jadwal snapshot, VPC, firewall IAP, Cloud NAT | `infra/terraform/iaas.tf`, `infra/terraform/templates/ops-startup.sh.tftpl` |
| PaaS | Cloud Run `labtrack-api`, Cloud SQL PostgreSQL 16, Cloud Storage, Secret Manager, Artifact Registry | `infra/terraform/main.tf` |
| SaaS (dipakai) | GitHub dan GitHub Actions, Google Cloud Console, Gmail | `.github/`, `infra/terraform/monitoring.tf` |
| SaaS (ditawarkan) | LabTrack API bagi asisten dan koordinator laboratorium | `app/` |

VM `labtrack-ops` bersifat opsional dan diaktifkan dengan `enable_ops_vm = true` di `terraform.tfvars`. Fungsinya nyata: menjalankan backup logis `pg_dump` setiap malam pukul 02.30 WIB ke bucket `<project>-labtrack-backups`. Backup logis ini melengkapi backup otomatis Cloud SQL karena berkas *dump* dapat dipulihkan ke PostgreSQL 16 mana pun, termasuk di luar Google Cloud.

## 2. Persiapan menjalankan skrip

Semua skrip di `scripts/ops/` membaca target dari variabel lingkungan dan mencetak setiap perintah sebelum menjalankannya (baris berawalan `+`), sehingga keluaran terminal dapat langsung dipakai sebagai bukti.

```bash
export PROJECT_ID=labtrack-<suffix-unik>
export REGION=asia-southeast2
# Hanya bila VM ditempatkan di region lain, misalnya us-central1 untuk tier gratis:
# export ZONE=us-central1-a
```

Skrip dapat dijalankan dari Cloud Shell, Linux, macOS, atau Git Bash di Windows.

## 3. Daftar aktivitas rutin

Pelaksana: **L2** adalah pengelola sistem (cloud engineer), **L1** adalah asisten laboratorium atau *helpdesk*, **KL** adalah koordinator laboratorium. Lihat matriks eskalasi di `docs/06-sop-dukungan-teknis.md`.

### 3.1 PaaS

| No | Aktivitas | Frekuensi | Pelaksana | Skrip atau perintah | Hasil yang diharapkan |
|---|---|---|---|---|---|
| P1 | Memeriksa kesehatan layanan | Harian | L2 | `curl $API/health` | `{"status":"ok","database":"ok",...}` dengan HTTP 200 |
| P2 | Meninjau dasbor dan alert | Harian | L2 | Console: Monitoring > Dashboards > LabTrack Overview | Tidak ada insiden terbuka, latensi p95 di bawah 800 ms |
| P3 | Meninjau log galat | Harian | L2 | Logs Explorer, kueri `severity>=ERROR` (lihat `docs/06-sop-dukungan-teknis.md`) | Tidak ada galat baru yang belum ditangani |
| P4 | Memastikan backup otomatis berhasil | Harian | L2 | `gcloud sql backups list --instance=<instance> --limit=3` | Backup terbaru berstatus `SUCCESSFUL` dalam 24 jam terakhir |
| P5 | Deploy versi baru | Sesuai kebutuhan | L2 | Otomatis melalui GitHub Actions; manual `scripts/ops/deploy-image.sh <tag>` | Revisi baru melayani 100% trafik, *smoke test* `/health` lulus |
| P6 | Rollback revisi | Sesuai kebutuhan (insiden) | L2 | `scripts/ops/rollback.sh` lalu `scripts/ops/rollback.sh --to-latest` setelah perbaikan | Trafik kembali ke revisi sebelumnya dalam kurang dari 1 menit |
| P7 | Mengatur kapasitas | Mingguan (awal dan akhir jam praktikum) atau sesuai kebutuhan | L2 | `scripts/ops/scale.sh 1 3` saat jam praktikum, `scripts/ops/scale.sh 0 3` setelahnya | Tidak ada *cold start* saat jam praktikum; biaya instans idle hanya selama jam tersebut |
| P8 | Backup *on-demand* | Sebelum perubahan berisiko | L2 | `scripts/ops/sql-backup-now.sh "Sebelum <perubahan>"` | Backup tipe `ON_DEMAND` berstatus `SUCCESSFUL` |
| P9 | Uji pemulihan backup | Bulanan | L2 | `scripts/ops/sql-restore-test.sh` | Jumlah baris salinan sama atau lebih kecil dari produksi, durasi di bawah RTO 2 jam, instans sementara terhapus |
| P10 | Rotasi kunci JWT | Per semester atau saat dicurigai bocor | L2 | `scripts/ops/rotate-secret.sh` | Versi secret baru, revisi baru, semua token lama ditolak (401) |
| P11 | Menghentikan atau menyalakan Cloud SQL | Awal dan akhir libur semester | L2 | `scripts/ops/sql-start-stop.sh stop` atau `start` | Status `STOPPED` atau `RUNNABLE`; biaya instans berhenti saat `STOPPED` |
| P12 | Meninjau biaya | Mingguan | L2 | Console: Billing > Reports, filter proyek | Biaya sesuai perkiraan di `docs/02-teknologi-cloud.md` bagian 3.3 |
| P13 | Membersihkan image lama | Otomatis | Sistem | Kebijakan `keep-recent` di Artifact Registry | Maksimal 10 versi image tersimpan |

### 3.2 IaaS

| No | Aktivitas | Frekuensi | Pelaksana | Skrip atau perintah | Hasil yang diharapkan |
|---|---|---|---|---|---|
| I1 | Memastikan backup `pg_dump` malam berhasil | Harian | L2 | `gcloud storage ls -l gs://$PROJECT_ID-labtrack-backups/backups/ \| tail -3` dan Logs Explorer `"labtrack-backup: success"` | Berkas *dump* baru dalam 24 jam terakhir, ukuran tidak nol |
| I2 | Memastikan snapshot harian terbentuk | Mingguan | L2 | `gcloud compute snapshots list --filter="sourceDisk~labtrack-ops-boot"` | Tujuh snapshot terjadwal, yang tertua tidak lebih dari 7 hari |
| I3 | *Patch* sistem operasi | Mingguan | L2 | `scripts/ops/vm-patch.sh --snapshot --reboot` | Snapshot pra-*patch* terbentuk, `apt` selesai tanpa galat, layanan `cloud-sql-proxy` dan `google-cloud-ops-agent` aktif |
| I4 | Snapshot manual | Sebelum perubahan pada VM | L2 | `scripts/ops/vm-snapshot-now.sh` | Snapshot `labtrack-ops-manual-*` berstatus `READY` |
| I5 | Akses administratif | Sesuai kebutuhan | L2 | `scripts/ops/vm-ssh.sh` | Masuk melalui IAP tanpa IP publik; koneksi SSH dari internet langsung ditolak |
| I6 | Menjalankan backup di luar jadwal | Sesuai kebutuhan | L2 | `scripts/ops/vm-ssh.sh "sudo systemctl start labtrack-backup.service"` | Baris `labtrack-backup: success` muncul di log |
| I7 | Menghentikan atau menyalakan VM | Sesuai kebutuhan (hemat biaya) | L2 | `scripts/ops/vm-start-stop.sh stop` atau `start` | Status `TERMINATED` atau `RUNNING`; backup yang terlewat dijalankan setelah VM menyala (`Persistent=true`) |
| I8 | Meninjau metrik VM | Mingguan | L2 | Console: Compute Engine > VM instances > labtrack-ops > Observability | CPU dan memori tersedia dari Ops Agent, disk tidak penuh |
| I9 | Meninjau aturan firewall | Bulanan | L2 | `gcloud compute firewall-rules list --filter="network~labtrack-ops-vpc"` | Hanya `labtrack-ops-allow-iap-ssh` dengan sumber `35.235.240.0/20` |

### 3.3 SaaS yang dipakai sebagai pelanggan

| No | Produk | Aktivitas | Frekuensi | Pelaksana | Cara | Hasil yang diharapkan |
|---|---|---|---|---|---|---|
| S1 | GitHub | Mengelola akses kolaborator repositori | Per semester atau saat asisten berganti | L2 | Settings > Collaborators and teams | Hanya pengelola aktif yang memiliki akses tulis |
| S2 | GitHub | Proteksi cabang `main` | Sekali, lalu ditinjau per semester | L2 | Settings > Branches > Add rule: wajib *pull request*, wajib *status check* `test` lulus, larang *force push* | Push langsung ke `main` ditolak |
| S3 | GitHub | Meninjau log GitHub Actions | Setiap deploy | L2 | Tab Actions, buka *run* terakhir | Semua *job* hijau; bila merah, lihat SOP bagian WIF |
| S4 | GitHub | Meninjau Dependabot alert dan pembaruan dependensi | Mingguan | L2 | Tab Security > Dependabot | Tidak ada kerentanan kritis yang dibiarkan |
| S5 | GitHub | Meninjau *environment* `production` | Per semester | L2 | Settings > Environments > production | Variabel `GCP_*` sesuai `terraform output github_vars` |
| S6 | Google Cloud Console | Meninjau anggota IAM proyek | Bulanan | L2 | IAM & Admin > IAM | Tidak ada akun pribadi selain pengelola; service account hanya memiliki peran minimum |
| S7 | Google Cloud Console | Meninjau budget alert | Bulanan | L2 | Billing > Budgets & alerts | Budget US$10 dengan ambang 50%, 90%, 100% aktif |
| S8 | Google Cloud Console | Mengaktifkan verifikasi dua langkah akun pengelola | Sekali, ditinjau per semester | L2 | myaccount.google.com > Security | 2-Step Verification aktif |
| S9 | Gmail | Mengelola penerima alert | Saat pengelola berganti | L2 | Ubah `alert_email` di `terraform.tfvars`, `terraform apply` | Email uji dari Monitoring > Alerting > Notification channels > Send test diterima |
| S10 | Gmail | Filter dan label alert | Sekali | L2 | Buat filter `from:alerts-noreply@google.com` dengan label `LabTrack-Alert` | Alert tidak tertimbun email lain |

### 3.4 LabTrack sebagai SaaS bagi pengguna laboratorium

LabTrack ditawarkan kepada asisten dan koordinator laboratorium sebagai aplikasi jadi. Mereka hanya membutuhkan akun dan peramban.

| No | Aktivitas | Frekuensi | Pelaksana | Cara | Hasil yang diharapkan |
|---|---|---|---|---|---|
| U1 | Penyediaan akun (*provisioning*) | Awal semester | L2 atas permintaan KL | `POST /auth/users` dengan token admin (contoh di bawah) | HTTP 201, akun baru dengan peran `assistant` |
| U2 | Meninjau daftar akun | Awal dan akhir semester | L2 | `GET /auth/users` dengan token admin | Daftar sesuai asisten aktif semester berjalan |
| U3 | Penonaktifan akun | Akhir semester atau saat asisten berhenti | L2 atas permintaan KL | Prosedur di bawah | Login akun tersebut ditolak (401) |
| U4 | Reset password | Atas permintaan pengguna | L2 setelah verifikasi oleh KL | Prosedur di bawah | Pengguna dapat login dengan password sementara |
| U5 | Komunikasi gangguan dan pemeliharaan | Sesuai kebutuhan | L2 | Templat komunikasi di `docs/06-sop-dukungan-teknis.md` | Pengguna mengetahui gangguan sebelum melapor |

**Penyediaan akun (U1):**

```bash
TOKEN=$(curl -s -X POST "$API/auth/login" \
  -d "username=admin@labtrack.dev" -d "password=$ADMIN_PASSWORD" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -s -X POST "$API/auth/users" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"email":"asisten.baru@contoh.ac.id","full_name":"Asisten Baru","password":"<password-sementara>","role":"assistant"}'
```

Password sementara dikirim kepada pengguna melalui kanal terpisah dari email akun (misalnya pesan langsung), dan pengguna diminta tidak membagikannya.

**Penonaktifan akun (U3) dan reset password (U4):** versi API saat ini belum memiliki endpoint untuk menonaktifkan akun atau mengganti password. Sesuai batasan proyek, endpoint baru tidak ditambahkan; prosedur dilakukan langsung pada basis data melalui Cloud SQL Studio (Console: SQL > instance > Cloud SQL Studio, login sebagai `labtrack` dengan password dari Secret Manager):

```sql
-- Penonaktifan: token yang masih berlaku langsung ditolak karena get_current_user memeriksa is_active
UPDATE users SET is_active = false WHERE email = 'asisten.lama@contoh.ac.id';
```

Untuk reset password, buat *hash* bcrypt di laptop pengelola lalu simpan ke basis data:

```bash
python -c "from app.security import hash_password; print(hash_password('<password-sementara>'))"
```

```sql
UPDATE users SET hashed_password = '<hash-dari-perintah-di-atas>' WHERE email = 'asisten@contoh.ac.id';
```

Setiap penonaktifan dan reset dicatat di log aktivitas di bawah, beserta nama pemohon (KL).

## 4. Log aktivitas operasional

Isi satu baris setiap kali aktivitas dijalankan. Tempel keluaran terminal ke berkas `docs/bukti/013/log/<tanggal>-<kode>.txt` dan rujuk berkas tersebut pada kolom bukti.

| Tanggal dan jam (WIB) | Kode | Aktivitas | Perintah | Hasil | Bukti | Pelaksana |
|---|---|---|---|---|---|---|
| 2026-10-26 01.10 | P1 | Cek kesehatan layanan | `curl $API/health` | HTTP 200, `database: ok`, 0,58 detik | B-013-01, `docs/bukti/001/terraform-apply.txt` | Abrar (L2) |
| 2026-10-26 01.13 | P5 | Deploy manual perbaikan JWT | `scripts/ops/deploy-image.sh --build v1.0.1` | Build 55 detik, revisi `labtrack-api-00002-59d` melayani 100% trafik, *smoke test* versi 1.0.1 | B-013-02, `docs/bukti/013/log/2026-10-26-P5.txt` | Abrar (L2) |
| 2026-10-26 06.20 | P6 | Rollback dan kembali ke latest | `scripts/ops/rollback.sh`, `scripts/ops/rollback.sh --to-latest` | Trafik pindah ke `00001-fbc` (versi 1.0.0) lalu kembali ke revisi terbaru (1.0.1); *smoke test* lulus di setiap langkah | B-013-03, `docs/bukti/013/log/2026-10-26-P6.txt` | Abrar (L2) |
| 2026-10-26 06.22 | P7 | Atur kapasitas jam praktikum | `scripts/ops/scale.sh 1 3`, lalu `scripts/ops/scale.sh 0 3` | `minScale` 1 lalu kembali 0, `maxScale` 3 | B-013-04, `docs/bukti/013/log/2026-10-26-P7.txt` | Abrar (L2) |
| 2026-10-26 06.19 | P8 | Backup on-demand | `scripts/ops/sql-backup-now.sh` | Backup `1792970383825` tipe ON_DEMAND berstatus SUCCESSFUL; backup otomatis harian juga tercatat | B-013-05, `docs/bukti/013/log/2026-10-26-P8.txt` | Abrar (L2) |
| 2026-10-26 06.25 sampai 06.53 | P9 | Uji restore | `scripts/ops/sql-restore-test.sh` | LULUS dalam sekitar 27 menit (RTO 2 jam); 7 tabel diverifikasi; `users` 1 di salinan dan 2 di produksi karena akun demo dibuat setelah backup; instans sementara terhapus | B-013-06, B-013-20, `docs/bukti/013/restore-verification-20261026-0625.md` | Abrar (L2) |
| 2026-10-26 07.32 | P10 | Rotasi kunci JWT | `scripts/ops/rotate-secret.sh` | Versi secret 2, revisi `labtrack-api-00006-klr`; token lama 200 sebelum rotasi dan 401 sesudahnya; login ulang 200 | B-013-07, `docs/bukti/013/log/2026-10-26-P10.txt` | Abrar (L2) |
| 2026-10-26 01.23 | I1 | Cek backup pg_dump | `vm-ssh.sh "sudo systemctl start labtrack-backup.service"`, `gcloud storage ls -l` | Berkas `labtrack-20261025T182300Z.dump` 27.521 byte di bucket backup; timer malam aktif | B-013-08, `docs/bukti/013/log/2026-10-26-I6.txt` | Abrar (L2) |
| 2026-10-26 06.29 | I3 | Patch OS VM | `scripts/ops/vm-patch.sh --snapshot` | Snapshot pra-patch READY, 2 paket diperbarui, layanan `active,active`, tidak perlu reboot, *change log* tertulis | B-013-09, B-013-19, `docs/bukti/013/log/2026-10-26-I3.txt`, `docs/bukti/013/change-log.md` | Abrar (L2) |
| 2026-10-26 01.23 | I5 | SSH melalui IAP | `scripts/ops/vm-ssh.sh "..."` | Masuk lewat IAP tanpa IP publik; perintah backup dan `systemctl list-timers` berjalan | B-013-10, `docs/bukti/013/log/2026-10-26-I6.txt` | Abrar (L2) |
| 2026-10-26 06.31 | I7 | Stop dan start VM | `scripts/ops/vm-start-stop.sh stop`, lalu `start` | TERMINATED lalu RUNNING, IP internal tetap `10.10.0.3` | B-013-11, `docs/bukti/013/log/2026-10-26-I7.txt` | Abrar (L2) |
| 2026-10-26 07.05 | S2 | Proteksi cabang main | `gh api -X PUT repos/.../branches/main/protection` | Wajib *pull request*, wajib lulus `test`, `test-postgres`, `terraform`; *force push* dan penghapusan dilarang | B-013-12, `docs/bukti/013/log/2026-10-26-S2.txt` | Abrar (L2) |
| 2026-10-26 06.22 | U1 | Provisioning akun asisten | `POST /auth/users` | HTTP 201 untuk `asisten.demo@labtrack.dev`; akun asisten ditolak 403 saat membuat mata kuliah | B-013-13, `docs/bukti/013/log/2026-10-26-U1.txt` | Abrar (L2) |
| 2026-10-26 06.35 | U3, U4 | Penonaktifan akun dan reset password | `UPDATE users SET is_active=false ...`, `UPDATE users SET hashed_password=...` | Login dengan password benar ditolak 401 saat nonaktif, 200 setelah diaktifkan; akun demo dinonaktifkan lagi | B-013-14, `docs/bukti/013/log/2026-10-26-U3.txt` | Abrar (L2) |
| 2026-10-26 01.16 | I10 | Laporan provisioning VM | `scripts/ops/vm-report.sh` | Debian 12, KVM, 2 vCPU, 969 MiB, IP internal saja, NAT keluar HTTP 200, 3 layanan aktif | B-013-18, `docs/bukti/013/vm-provisioning-20261026-0116.txt` | Abrar (L2) |

Catatan keaslian waktu: jam laptop pelaksana tercatat sekitar 2 menit lebih cepat dari waktu server Google (dibandingkan dengan header `Date` server Google pada 26 Oktober 2026). Waktu WIB di tabel berasal dari laptop; stempel waktu resmi ada di Cloud Logging dan pada metadata resource Google Cloud.

## 5. Jenis backup dan penerapannya

| Jenis | Pengertian | Kelebihan dan kekurangan | Penerapan di LabTrack |
|---|---|---|---|
| *Full* | Menyalin semua data dalam cakupan | Pemulihan paling sederhana (satu berkas); paling boros ruang dan waktu | `pg_dump` malam hari oleh VM `labtrack-ops` adalah backup logis penuh setiap kali; uji lokal menghasilkan berkas 27 KB untuk data demo (`docs/bukti/lokal/backup-restore-verify.txt`) |
| *Incremental* | Menyalin perubahan sejak backup terakhir (jenis apa pun) | Hemat ruang; pemulihan membutuhkan seluruh rantai backup | Snapshot disk Compute Engine bersifat inkremental: snapshot pertama penuh, berikutnya hanya blok yang berubah, dan Google mengelola rantainya sehingga setiap snapshot tetap dapat dipulihkan sendiri. Backup otomatis Cloud SQL juga disimpan secara inkremental oleh Google |
| *Differential* | Menyalin perubahan sejak backup penuh terakhir | Pemulihan cukup dengan backup penuh dan satu *differential*; ukuran bertambah setiap hari sampai backup penuh berikutnya | Tidak dipakai. Padanannya untuk PostgreSQL adalah *point-in-time recovery* dengan WAL, yang dapat diaktifkan pada Cloud SQL bila RPO perlu diturunkan di bawah 24 jam |

Strategi tiga lapis LabTrack:

1. **Backup otomatis Cloud SQL** harian pukul 01.00 WIB, retensi 7 (dikelola Google, inkremental).
2. **`pg_dump`** harian pukul 02.30 WIB ke bucket terpisah, retensi 30 hari (penuh, portabel ke PostgreSQL mana pun).
3. **Snapshot boot disk VM** harian pukul 03.00 WIB, retensi 7 hari (inkremental), ditambah snapshot manual sebelum *patching*.

Sesuai prinsip modul pelatihan, frekuensi backup saja belum menjamin RPO. Backup baru dianggap sah setelah lulus siklus *backup, restore, verify*:

| Tahap | Pelaksanaan | Keluaran |
|---|---|---|
| Tentukan data dan metode | Basis data `labtrack`; backup Cloud SQL terbaru berstatus `SUCCESSFUL` | Bagian awal keluaran skrip |
| Jalankan backup dan catat log | `scripts/ops/sql-backup-now.sh` | Log P8 |
| *Restore* ke lingkungan uji | `scripts/ops/sql-restore-test.sh` membuat instans sementara dan memulihkan backup ke sana, tanpa menyentuh produksi | Instans `labtrack-restore-test-*` |
| Periksa data | Jumlah baris tujuh tabel dibandingkan dengan produksi | Tabel perbandingan |
| Tutup dengan laporan | Skrip menulis *restore verification report* lalu menghapus instans sementara | `docs/bukti/013/restore-verification-<tanggal>.md` |

Siklus ini sudah dijalankan secara lokal dengan `pg_dump` dan `pg_restore` ke basis data uji terpisah: ketujuh tabel identik (1 pengguna, 12 mahasiswa, 1 mata kuliah, 12 *enrollment*, 4 sesi, 48 kehadiran, 41 laporan), dan rekap kehadiran dapat dihitung dari data hasil *restore*. Keluaran lengkapnya ada di `docs/bukti/lokal/backup-restore-verify.txt`.

## 6. Prosedur perubahan terkontrol (*patching*, *update*, *upgrade*)

| Tahap | Pelaksanaan pada VM `labtrack-ops` | Pelaksanaan pada Cloud Run (deploy versi baru) |
|---|---|---|
| 1. Identifikasi perubahan dan risiko | `vm-patch.sh` menampilkan `apt list --upgradable`; risiko: layanan *restart*, kemungkinan perlu *reboot* kernel | *Pull request* di GitHub menampilkan *diff*; risiko dinilai saat *review* |
| 2. Backup dan rencana pemulihan | `--snapshot` membuat snapshot boot disk sebelum perubahan; pemulihan dengan membuat disk dari snapshot | Revisi lama tetap tersedia; pemulihan dengan `scripts/ops/rollback.sh`. Untuk perubahan skema, `sql-backup-now.sh` dahulu |
| 3. Uji sebelum produksi | Paket Debian berasal dari kanal stabil yang sudah diuji distribusi; untuk perubahan besar, uji dulu pada VM dari snapshot | Job CI `test`, `test-postgres`, dan `terraform` wajib lulus sebelum job `deploy` berjalan |
| 4. Terapkan | `apt-get upgrade` melalui IAP | Job `deploy` membuat revisi baru |
| 5. Uji pasca-pemeliharaan dan *change log* | `vm-patch.sh` memeriksa `cloud-sql-proxy` dan `google-cloud-ops-agent` aktif serta penanda *reboot*, lalu menambahkan satu baris ke `docs/bukti/013/change-log.md` | *Smoke test* `/health` di pipeline; riwayat commit dan *run* GitHub Actions menjadi *change log* |

Format *change log* yang ditulis otomatis:

| Waktu (WIB) | VM | Perubahan | Risiko | Backup sebelum perubahan | Uji pasca-pemeliharaan | Pelaksana |
|---|---|---|---|---|---|---|
| 2026-10-26 06:29 | labtrack-ops | apt-get upgrade (Debian 12) | Layanan restart, kemungkinan perlu reboot kernel | snapshot labtrack-ops-manual-prepatch-20261025-232825 | active,active NO_REBOOT_REQUIRED | abrar |

## 7. Laporan provisioning VM

`scripts/ops/vm-report.sh` merekam konfigurasi VM dari API Compute Engine (tipe mesin, zona, disk, IP internal, tidak adanya IP eksternal, service account, Shielded VM) dan, dari dalam VM melalui IAP, hasil `lscpu`, `free -h`, `df -h /`, `ip -br addr`, `ip route`, `ping` ke *gateway*, akses keluar melalui Cloud NAT, serta status layanan. Baris `Hypervisor vendor: KVM` pada keluaran `lscpu` menunjukkan VM berjalan di atas hypervisor KVM, setara dengan pemeriksaan `/dev/kvm` di lab Proxmox modul.

```bash
scripts/ops/vm-report.sh     # disimpan ke docs/bukti/013/vm-provisioning-<tanggal>.txt
```

> [BUKTI: B-013-18, berkas docs/bukti/013/vm-provisioning-<tanggal>.txt hasil skrip]
