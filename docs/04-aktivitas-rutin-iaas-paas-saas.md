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
| > [ISI SETELAH DEPLOY] | P1 | Cek kesehatan layanan | `curl $API/health` | | B-013-01 | |
| > [ISI SETELAH DEPLOY] | P5 | Deploy manual | `scripts/ops/deploy-image.sh v1.0.1` | | B-013-02 | |
| > [ISI SETELAH DEPLOY] | P6 | Rollback dan kembali ke latest | `scripts/ops/rollback.sh`, `scripts/ops/rollback.sh --to-latest` | | B-013-03 | |
| > [ISI SETELAH DEPLOY] | P7 | Atur kapasitas jam praktikum | `scripts/ops/scale.sh 1 3`, lalu `scripts/ops/scale.sh 0 3` | | B-013-04 | |
| > [ISI SETELAH DEPLOY] | P8 | Backup on-demand | `scripts/ops/sql-backup-now.sh` | | B-013-05 | |
| > [ISI SETELAH DEPLOY] | P9 | Uji restore | `scripts/ops/sql-restore-test.sh` | | B-013-06 | |
| > [ISI SETELAH DEPLOY] | P10 | Rotasi kunci JWT | `scripts/ops/rotate-secret.sh` | | B-013-07 | |
| > [ISI SETELAH DEPLOY] | I1 | Cek backup pg_dump | `gcloud storage ls -l gs://...` | | B-013-08 | |
| > [ISI SETELAH DEPLOY] | I3 | Patch OS VM | `scripts/ops/vm-patch.sh --snapshot` | | B-013-09 | |
| > [ISI SETELAH DEPLOY] | I5 | SSH melalui IAP | `scripts/ops/vm-ssh.sh "hostname; systemctl list-timers labtrack-backup.timer"` | | B-013-10 | |
| > [ISI SETELAH DEPLOY] | I7 | Stop dan start VM | `scripts/ops/vm-start-stop.sh stop`, lalu `start` | | B-013-11 | |
| > [ISI SETELAH DEPLOY] | S2 | Proteksi cabang main | GitHub Settings > Branches | | B-013-12 | |
| > [ISI SETELAH DEPLOY] | U1 | Provisioning akun asisten | `POST /auth/users` | | B-013-13 | |
| > [ISI SETELAH DEPLOY] | U3 | Penonaktifan akun | `UPDATE users SET is_active=false ...` | | B-013-14 | |
