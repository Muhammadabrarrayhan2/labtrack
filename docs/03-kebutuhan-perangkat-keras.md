# Kebutuhan Perangkat Keras dan Penentuan Kapasitas LabTrack

Unit kompetensi: **J.631120.003.01 Mengidentifikasi berbagai jenis perangkat keras yang dibutuhkan**

Dokumen ini mengklasifikasikan sumber daya perangkat keras yang dibutuhkan LabTrack, menurunkan estimasi beban kerja dari kasus penggunaan nyata, menentukan ukuran setiap komponen, dan membandingkan biaya awan dengan server di lokasi sendiri (*on-premise*). Bagian hasil uji beban diisi setelah uji Locust dijalankan pada lingkungan yang sudah di-deploy.

## 1. Klasifikasi sumber daya perangkat keras

### 1.1 Sisi server (di awan)

| Kelompok | Sumber daya | Satuan | Pemakaian di LabTrack |
|---|---|---|---|
| Komputasi | vCPU | Jumlah inti virtual, detik vCPU | Cloud Run 1 vCPU per instans; Cloud SQL vCPU bersama; VM e2-micro 2 vCPU bersama |
| Komputasi | Memori (RAM) | MiB atau GB | Cloud Run 512 MiB per instans; Cloud SQL 0,6 GB; VM 1 GB |
| Penyimpanan blok | SSD *persistent disk* | GB, IOPS, *throughput* MB/s | Disk data Cloud SQL 10 GB PD-SSD |
| Penyimpanan blok | *Standard persistent disk* (HDD) | GB | Boot disk VM `labtrack-ops` 10 GB `pd-standard` |
| Penyimpanan objek | Cloud Storage Standard | GB tersimpan, jumlah operasi | Laporan PDF praktikum dan backup `pg_dump` |
| Jaringan | *Bandwidth* keluar (*egress*) | GB | Respons API dan unduhan PDF melalui signed URL |
| Jaringan | Latensi | ms | Jarak pengguna di Indonesia ke region Jakarta |
| Jaringan | *Load balancer* | Permintaan | *Front end* Google bawaan Cloud Run (tidak perlu disediakan terpisah) |
| Jaringan | NAT | Jam *gateway*, GB diproses | Cloud NAT untuk VM tanpa IP publik |

Perbedaan penting antara dua jenis penyimpanan yang dipakai:

| Aspek | SSD persistent disk (Cloud SQL) | Object storage (Cloud Storage) |
|---|---|---|
| Model akses | Blok, dipasang ke satu mesin, diakses sistem berkas | Objek melalui HTTP API |
| Kinerja | IOPS tinggi dan latensi rendah, berbanding lurus dengan ukuran disk | Latensi lebih tinggi per objek, *throughput* besar |
| Kapasitas | Harus disediakan di muka (dengan *autoresize*) | Tidak perlu disediakan, dibayar sesuai pemakaian |
| Cocok untuk | Basis data transaksional | Berkas besar yang jarang berubah (PDF, backup) |

Pada PD-SSD, kinerja diskalakan menurut ukuran: Google mendokumentasikan sekitar 30 IOPS baca dan 30 IOPS tulis per GB. Dengan 10 GB, disk Cloud SQL mendapat kurang lebih 300 IOPS, cukup untuk beban transaksi LabTrack yang sebagian besar berupa baca dan tulis baris kecil.

### 1.2 Sisi klien (perangkat pengguna)

| Perangkat | Spesifikasi minimum yang disarankan | Alasan |
|---|---|---|
| Laptop asisten atau koordinator | Prosesor dua inti, RAM 4 GB, sistem operasi yang masih menerima pembaruan keamanan | Cukup untuk peramban modern dan Swagger UI |
| Peramban | Versi terbaru Chrome, Firefox, atau Edge | Mendukung TLS 1.2 ke atas yang diwajibkan endpoint `*.run.app` |
| Koneksi internet | Minimal 5 Mbps unggah | Unggah PDF 10 MB (batas maksimum) memerlukan sekitar 16 detik pada 5 Mbps |
| Ponsel (opsional) | Peramban modern | Untuk melihat rekap kehadiran |

Pengelola sistem (peran L2) membutuhkan tambahan Google Cloud CLI, Terraform 1.5 atau lebih baru, Git, dan Python 3.12, sesuai `docs/PANDUAN-DEPLOYMENT.md` langkah 0.

## 2. Estimasi beban kerja

### 2.1 Asumsi kasus penggunaan

| Parameter | Nilai | Dasar asumsi |
|---|---|---|
| Kelas praktikum aktif | 10 kelas | Satu laboratorium, satu semester |
| Mahasiswa per kelas | 40 | Kapasitas ruang laboratorium |
| Total mahasiswa | 400 | 10 x 40 |
| Asisten per kelas | 2 | Satu pencatat kehadiran, satu pemeriksa laporan |
| Modul (sesi) per semester | 10 | Jadwal praktikum mingguan |
| Kelas yang mulai bersamaan (kondisi terburuk) | 10 | Seluruh kelas dijadwalkan pada slot yang sama |

### 2.2 Aktivitas per asisten pada 5 menit pertama sesi

| Aktivitas | Endpoint | Jumlah permintaan |
|---|---|---|
| Login | `POST /auth/login` | 1 |
| Membuka daftar mahasiswa kelas | `GET /courses/{id}/students` | 2 |
| Mencari mahasiswa | `GET /students?q=` | 3 |
| Mengirim dan mengoreksi kehadiran | `PUT /sessions/{id}/attendance` | 2 |
| Melihat rekap kehadiran | `GET /courses/{id}/attendance-summary` | 2 |
| Jumlah | | 10 |

### 2.3 Penurunan permintaan per detik (RPS)

```
Asisten aktif saat puncak        = 10 kelas x 2 asisten        = 20 asisten
Permintaan pada jendela puncak   = 20 asisten x 10 permintaan   = 200 permintaan
Jendela puncak                   = 5 menit                      = 300 detik
RPS rata-rata saat puncak        = 200 / 300                    = 0,67 RPS
Faktor lonjakan (burst) x10      = 0,67 x 10                    = sekitar 7 RPS
```

Faktor lonjakan 10 dipakai karena permintaan tidak tersebar merata: banyak asisten menekan tombol kirim pada detik yang hampir sama setelah absen dibacakan.

Unggahan laporan terjadi setelah sesi: 400 laporan per modul dalam sekitar 60 menit, atau 400 / 3.600 = 0,11 unggahan per detik dengan ukuran rata-rata 1,5 MB (asumsi, lihat bagian 3.3).

Uji beban dirancang jauh di atas angka ini agar terlihat batas kapasitas: 50 pengguna virtual dengan jeda 1 sampai 3 detik menghasilkan target sekitar 25 RPS, kurang lebih 3,5 kali beban lonjakan.

## 3. Penentuan ukuran per komponen

### 3.1 Cloud Run

| Parameter | Nilai | Rujukan |
|---|---|---|
| vCPU per instans | 1 | `main.tf`, `resources.limits.cpu` |
| Memori per instans | 512 MiB | `resources.limits.memory` |
| Konkurensi | 40 permintaan per instans | `max_instance_request_concurrency` |
| Instans minimum dan maksimum | 0 dan 3 | `scaling` |
| Batas waktu permintaan | 30 detik | `timeout` |
| CPU hanya dialokasikan saat melayani permintaan | Ya | `cpu_idle = true` |

Kapasitas permintaan bersamaan maksimum adalah 3 x 40 = 120 permintaan. Pada beban puncak 7 RPS dengan latensi rata-rata 100 ms (perkiraan untuk kueri sederhana), jumlah permintaan bersamaan menurut hukum Little adalah 7 x 0,1 = 0,7, sehingga satu instans sudah memadai dan dua instans tambahan menjadi cadangan lonjakan.

Analisis memori: unggahan dibaca utuh ke memori (hingga 10 MB). Bila 40 unggahan 10 MB terjadi bersamaan di satu instans, kebutuhan memori mencapai sekitar 400 MB ditambah sekitar 120 MB untuk proses Python dan pustaka, sehingga melebihi 512 MiB. Kondisi ini tidak realistis untuk beban yang diestimasi (0,11 unggahan per detik), tetapi dicatat sebagai risiko. Mitigasi bila dibutuhkan: menaikkan memori ke 1 GiB atau menurunkan konkurensi.

Login memakai bcrypt yang sengaja berat secara komputasi (sekitar 0,2 sampai 0,3 detik CPU per verifikasi). Karena itu skrip Locust melakukan login hanya sekali per pengguna virtual, sesuai perilaku pengguna nyata yang memakai token selama 120 menit.

### 3.2 Cloud SQL

| Parameter | Nilai | Keterangan |
|---|---|---|
| Tier | `db-f1-micro` | vCPU bersama, memori 0,6 GB |
| Batas koneksi bawaan | 25 | Nilai `max_connections` bawaan Cloud SQL PostgreSQL untuk memori 0,6 GB |
| Disk | 10 GB PD-SSD, *autoresize* | Sekitar 300 IOPS |
| Ketersediaan | ZONAL | Tanpa *standby*, sesuai target 99,5% |
| Backup | Harian, 7 retensi | Menentukan RPO 24 jam |

Perkiraan ukuran data per semester: 400 mahasiswa, 4.000 baris kehadiran, 4.000 baris laporan, dengan ukuran kurang dari 1 KB per baris, sehingga kurang dari 10 MB. Disk 10 GB jauh di atas kebutuhan data; ukuran 10 GB dipilih karena merupakan ukuran minimum dan karena IOPS bergantung pada ukuran disk.

### 3.3 Anggaran koneksi basis data

Setiap instans Cloud Run memiliki *connection pool* SQLAlchemy (`app/database.py`): `pool_size = 5`, `max_overflow = 2`.

```
Koneksi per instans Cloud Run    = pool_size + max_overflow   = 5 + 2  = 7
Koneksi maksimum Cloud Run       = max_instances x 7          = 3 x 7  = 21
Koneksi VM labtrack-ops (pg_dump) = 1                                    = 1
Total kebutuhan                                                          = 22
Batas max_connections db-f1-micro                                        = 25
Sisa untuk koneksi administratif (Cloud SQL Studio, psql)                = 3
```

Kesimpulan: anggaran koneksi terpenuhi dengan sisa tipis. Dua kondisi dapat melampaui batas:

1. **Saat pergantian revisi.** Cloud Run dapat menjalankan instans revisi lama dan revisi baru secara bersamaan selama beberapa saat. Bila keduanya dalam keadaan penuh, kebutuhan sementara bisa mencapai 2 x 21 = 42 koneksi. Kondisi ini akan terlihat sebagai galat `too many connections` dan `/health` mengembalikan 503 (lihat `docs/06-sop-dukungan-teknis.md`, bagian 503).
2. **Menaikkan `max_instances`** dengan `scripts/ops/scale.sh` tanpa menyesuaikan *pool*.

Rumus umum yang dipakai sebelum mengubah *scaling*:

```
max_instances x (pool_size + max_overflow) + koneksi lain  <  max_connections
```

Alert "Cloud SQL connections near limit" di `infra/terraform/slo.tf` memberi peringatan saat jumlah koneksi melewati 20.

### 3.4 Cloud Storage

| Parameter | Nilai | Keterangan |
|---|---|---|
| Ukuran rata-rata PDF | 1,5 MB | Asumsi (contoh), laporan praktikum 10 sampai 20 halaman dengan gambar tangkapan layar |
| Laporan per semester | 400 mahasiswa x 10 modul = 4.000 | |
| Unggahan ulang | 10% | Asumsi (contoh). Unggahan ulang membuat objek baru dengan kunci baru, objek lama tetap tersimpan |
| Pertumbuhan per semester | 4.000 x 1,1 x 1,5 MB = 6,6 GB | |
| Pertumbuhan per tahun | 13,2 GB | Dua semester |
| Backup `pg_dump` (bila VM aktif) | Kurang dari 1 MB per hari terkompresi, 30 hari | Kurang dari 30 MB |

Dengan tarif Cloud Storage Standard sekitar US$0,02 per GB per bulan, biaya penyimpanan tahun pertama tetap di bawah US$0,50 per bulan.

### 3.5 Jaringan

| Aspek | Perkiraan | Keterangan |
|---|---|---|
| Ukuran respons API | 1 sampai 20 KB JSON | Daftar mahasiswa 40 baris sekitar 8 KB |
| *Egress* bulanan API | Kurang dari 1 GB | |
| *Egress* unduhan PDF | 4.000 x 1,5 MB = 6 GB per semester bila setiap laporan diunduh sekali | Melalui signed URL langsung dari Cloud Storage |
| Latensi pengguna ke region Jakarta | Diukur, lihat bagian 5 | |

## 4. Perbandingan dengan server *on-premise*

### 4.1 Spesifikasi server setara

Untuk menjalankan API, PostgreSQL, dan penyimpanan berkas di satu server fisik di laboratorium dengan kapasitas cadangan yang wajar:

| Komponen | Spesifikasi | Alasan |
|---|---|---|
| CPU | 4 inti, 8 *thread* | Setara 3 instans Cloud Run ditambah basis data |
| RAM | 16 GB | 3 x 512 MiB aplikasi, PostgreSQL, OS, dan cadangan |
| Disk | 2 x 480 GB SSD dalam RAID 1 | Redundansi disk |
| Disk backup | 1 x 2 TB HDD eksternal atau NAS | Salinan backup terpisah |
| Jaringan | NIC 1 Gbps, IP publik statis, sertifikat TLS | Akses dari luar kampus |
| Daya | UPS 1.000 VA | Menjaga server saat listrik padam singkat |

### 4.2 CapEx dan OpEx

Seluruh nilai rupiah di bawah adalah **contoh** perkiraan harga pasar untuk perbandingan, dengan asumsi kurs Rp16.000 per US$. Harga perangkat aktual harus diganti dengan penawaran vendor bila dibutuhkan.

| Komponen biaya | On-premise (contoh) | Google Cloud (perkiraan) |
|---|---|---|
| **CapEx** server, disk, UPS | Rp30.000.000 di awal | Rp0 |
| Masa pakai | 4 tahun, penyusutan sekitar Rp625.000 per bulan | Tidak ada |
| **OpEx** listrik (sekitar 150 W, 24 jam, Rp1.500 per kWh) | Sekitar Rp162.000 per bulan | Termasuk tarif layanan |
| OpEx internet dengan IP statis | Sekitar Rp500.000 per bulan | Termasuk tarif layanan |
| OpEx tenaga pengelola (OS, *patch*, backup, perangkat keras) | Sekitar 8 jam per bulan | Sekitar 2 jam per bulan (aktivitas rutin di `docs/04-aktivitas-rutin-iaas-paas-saas.md`) |
| Biaya layanan bulanan | Tidak ada | Sekitar US$10 sampai 15 (Rp160.000 sampai Rp240.000) |
| **Total per bulan** (tanpa tenaga kerja) | Sekitar Rp1.287.000 | Sekitar Rp160.000 sampai Rp240.000 |
| Biaya saat libur semester | Tetap | Dapat ditekan mendekati nol dengan menghentikan Cloud SQL |
| Ketersediaan | Bergantung pada listrik dan jaringan kampus | SLA penyedia per layanan |
| Waktu penyediaan | Pengadaan berminggu-minggu | Menit (`terraform apply`) |

Kesimpulan: untuk beban kecil dan tidak merata seperti LabTrack, model OpEx awan lebih murah dan lebih cepat disediakan. Server *on-premise* baru menguntungkan bila beban stabil dan tinggi sepanjang tahun atau bila ada kewajiban data tetap di lokasi kampus.

## 5. Hasil uji beban

### 5.1 Cara menjalankan

Perintah lengkap ada di `README.md` bagian "Load test". Ringkasnya:

```bash
pip install -r requirements-dev.txt
export LABTRACK_PASSWORD=$(gcloud secrets versions access latest --secret=labtrack-admin-password)
locust -f scripts/loadtest/locustfile.py --host "$API" \
  --headless -u 50 -r 5 -t 5m \
  --csv docs/bukti/003/locust --html docs/bukti/003/locust-report.html
```

### 5.2 Hasil

Uji dijalankan pada 26 Oktober 2026 pukul 01.16 sampai 01.21 WIB terhadap `https://labtrack-api-b26757zszq-et.a.run.app` (proyek `labtrack-1026146`, revisi `labtrack-api-00002-59d`, versi 1.0.1), 50 pengguna, laju 5 per detik, 5 menit. Sumber: `docs/bukti/003/locust_stats.csv` dan `docs/bukti/003/locust-terminal.txt`.

| Endpoint | Jumlah permintaan | Gagal | p50 (ms) | p95 (ms) | RPS |
|---|---|---|---|---|---|
| `GET /students` | 2.704 | 0 | 34 | 58 | 9,04 |
| `GET /courses/{id}/attendance-summary` | 2.135 | 0 | 39 | 61 | 7,14 |
| `PUT /sessions/{id}/attendance` | 1.382 | 0 | 47 | 75 | 4,62 |
| `GET /health` | 728 | 0 | 29 | 58 | 2,43 |
| `GET /courses/{id}/students` (sekali per pengguna, saat mulai) | 50 | 0 | 2.300 | 8.000 | 0,17 |
| `POST /auth/login` (sekali per pengguna, saat mulai) | 50 | 0 | 5.900 | 7.800 | 0,17 |
| **Agregat** | **7.049** | **0 (0%)** | **38** | **69** | **23,58** |

> [BUKTI: screenshot B-003-01, ringkasan terminal Locust; keluaran teksnya tersimpan di docs/bukti/003/locust-terminal.txt]

> [BUKTI: screenshot B-003-02 dan B-003-03, grafik "Container instances", "Request latency p95", dan "Cloud SQL CPU utilization" pada dasbor LabTrack Overview, rentang 01.15 sampai 01.25 WIB tanggal 26 Oktober 2026]

### 5.3 Analisis

1. **Target terpenuhi untuk operasi rutin.** Keempat endpoint yang dipakai berulang selama sesi praktikum memiliki p95 58 sampai 75 ms, jauh di bawah target 800 ms. Agregat p95 69 ms dengan 0 kegagalan dari 7.049 permintaan.
2. **Kapasitas memadai.** Laju 23,58 RPS sekitar 3,4 kali beban lonjakan yang diestimasi (7 RPS) dan dilayani tanpa galat 5xx maupun 429.
3. **Lonjakan login di awal adalah titik lemah.** Login dan permintaan pertama setiap pengguna mencapai p95 7,8 sampai 8 detik. Penyebabnya, 50 verifikasi bcrypt (sekitar 0,3 detik CPU masing-masing) datang dalam 10 detik pertama, sementara Cloud Run baru menambah instans dari 1 ke 3 (*cold start*). Pada beban nyata, 20 asisten tidak login pada detik yang sama, tetapi risiko ini tetap ditangani dengan dua rekomendasi: `scripts/ops/scale.sh 1 3` selama jam praktikum agar satu instans selalu siap, dan menaikkan memori atau CPU bila login serentak menjadi pola nyata.
4. **Perbandingan dengan lokal.** Endpoint rutin di Google Cloud sekitar 3 sampai 4 kali lebih lambat dari lokal (p95 58 ms dibanding 15 ms untuk `GET /students`) karena latensi jaringan dari laptop ke region Jakarta dan Cloud SQL vCPU bersama, tetapi tetap di bawah 100 ms.

### 5.4 Hasil pembanding di lingkungan lokal (sudah dijalankan)

Skenario yang sama dijalankan pada 24 Oktober 2026 terhadap tumpukan lokal `docker compose` (satu kontainer API dan PostgreSQL 16 di laptop pengembang), 50 pengguna, laju *spawn* 5 per detik, durasi 2 menit, setelah data demo diisi dengan `scripts/seed_demo.py`. Angka berikut diambil dari `docs/bukti/lokal/locust_stats.csv` dan **bukan** hasil Google Cloud. Fungsinya membuktikan bahwa skenario uji berjalan, serta menjadi garis dasar tanpa latensi jaringan internet, tanpa *cold start*, dan tanpa batas vCPU bersama Cloud SQL.

| Endpoint | Jumlah permintaan | Gagal | p50 (ms) | p95 (ms) | RPS |
|---|---|---|---|---|---|
| `GET /students` | 1.155 | 0 | 8 | 15 | 9,73 |
| `GET /courses/{id}/attendance-summary` | 871 | 0 | 11 | 20 | 7,33 |
| `PUT /sessions/{id}/attendance` | 550 | 0 | 60 | 69 | 4,63 |
| `GET /health` | 277 | 0 | 4 | 10 | 2,33 |
| `GET /courses/{id}/students` | 50 | 0 | 23 | 49 | 0,42 |
| `POST /auth/login` | 50 | 0 | 330 | 360 | 0,42 |
| **Agregat** | **2.953** | **0 (0%)** | **10** | **65** | **24,87** |

Pengamatan:

1. Laju 24,87 RPS sekitar 3,5 kali beban lonjakan yang diestimasi (7 RPS), sesuai rancangan uji di bagian 2.3.
2. Login memakan sekitar 330 ms karena bcrypt, sesuai asumsi 0,2 sampai 0,3 detik CPU per verifikasi di bagian 3.1. Inilah alasan login dilakukan sekali per pengguna.
3. `PUT` kehadiran adalah operasi tulis terberat (p95 69 ms) karena melakukan *upsert* 12 baris dalam satu transaksi.
4. Tidak ada kegagalan. Hasil di Google Cloud diperkirakan lebih lambat karena latensi jaringan dan *cold start*; selisihnya menjadi bahan analisis di bagian 5.3.

## 6. Uji *stress*

Uji *performance* di bagian 5 mengukur kinerja pada beban yang direncanakan. Uji *stress* mencari titik jenuh dan memeriksa apakah sistem pulih setelah beban turun. Profil bertahap didefinisikan di `scripts/loadtest/stages.py` dan diuji di `tests/test_loadtest_stages.py`:

| Tahap | Durasi | Pengguna virtual | Tujuan |
|---|---|---|---|
| 1 | 2 menit | 100 | Dua kali uji *performance* |
| 2 | 2 menit | 150 | |
| 3 | 2 menit | 200 | Diperkirakan mendekati batas 3 instans x 40 konkurensi |
| 4 | 2 menit | 250 | |
| 5 | 2 menit | 300 | Kelebihan beban |
| 6 | 2 menit | 20 | Pemulihan: latensi dan galat harus kembali normal |

```bash
LOAD_SHAPE=stress LABTRACK_PASSWORD=... locust -f scripts/loadtest/locustfile.py \
  --host "$API" --headless --csv docs/bukti/003/stress --html docs/bukti/003/stress-report.html
```

Peringatan: uji ini sengaja melampaui kapasitas. Jalankan di luar jam praktikum. Beban 300 pengguna menghasilkan sekitar 150 RPS, sehingga Cloud Run akan mencapai batas 3 instans dan dapat mengembalikan galat 429 atau 503. Kondisi ini memakai anggaran galat SLO, dan hal tersebut memang bagian dari tujuan uji.

Uji dijalankan pada 26 Oktober 2026 mulai pukul 01.22 WIB. Nilai p50, p95, dan RPS adalah rata-rata per tahap dari `docs/bukti/003/stress_stats_history.csv` (30 detik pertama tiap tahap diabaikan sebagai masa transisi). Jumlah instans, CPU, dan koneksi Cloud SQL adalah nilai maksimum per tahap dari Cloud Monitoring (`docs/bukti/003/stress-monitoring.txt`).

| Tahap (VU) | p50 (ms) | p95 (ms) | RPS | Instans Cloud Run (maks) | CPU Cloud SQL (maks) | Koneksi Cloud SQL (maks) |
|---|---|---|---|---|---|---|
| 100 | 38 | 1.352 | 46,5 | 3 | 37,5% | 24 |
| 150 | 214 | 466 | 68,3 | 3 | 27,7% | 23 |
| 200 | 2.680 | 5.584 | 41,6 | 3 | 23,7% | 24 |
| 250 | 4.389 | 8.034 | 39,3 | 3 | 23,9% | 23 |
| 300 | 6.397 | 11.116 | 36,2 | 3 | 11,7% | 17 |

Total 25.440 permintaan dengan 21 galat (0,08%), seluruhnya HTTP 429 *Too Many Requests* dari Cloud Run, bukan galat aplikasi (`docs/bukti/003/stress_failures.csv`).

Riwayat Locust berhenti di detik ke-579, sehingga tahap 6 (20 pengguna) tidak terekam pada run ini. Pemulihan diukur dengan run terpisah 20 pengguna selama 2 menit, yang karena jeda sesi baru dijalankan pukul 06.18 WIB, sekitar 5 jam kemudian, dari kondisi idle (`docs/bukti/003/recovery_stats.csv`): 1.026 permintaan, 0 gagal, p95 endpoint rutin 78 sampai 95 ms. Login pertama pada run itu mencapai p95 19 detik karena 20 pengguna login serentak ke instans yang baru menyala.

> [BUKTI: screenshot B-003-07, grafik laporan HTML docs/bukti/003/stress-report.html dan grafik "Container instances" di dasbor pada rentang 01.20 sampai 01.35 WIB]

Analisis:

1. **Titik jenuh di antara 150 dan 200 pengguna.** Pada 150 pengguna p95 masih 466 ms (di bawah target 800 ms) dengan laju tertinggi 68 RPS. Pada 200 pengguna p95 melonjak ke 5,6 detik dan laju justru turun, tanda antrean di instans.
2. **Hambatan utama adalah batas 3 instans Cloud Run, bukan basis data.** Jumlah instans sudah 3 sejak tahap pertama, sedangkan CPU Cloud SQL tidak pernah melewati 37,5%. Cloud Run menolak kelebihan permintaan dengan 429, sesuai perilaku yang diharapkan saat `max_instance_count` tercapai.
3. **Anggaran koneksi terbukti ketat.** Koneksi Cloud SQL mencapai 24 dari batas 25, sesuai perhitungan bagian 3.3 (21 dari aplikasi ditambah koneksi internal dan VM ops). Alert `connections near limit` (ambang 20) dirancang untuk kondisi ini.
4. **Rekomendasi bila beban tumbuh melampaui 150 pengguna serentak:** naikkan `max_instance_count` bersamaan dengan tier Cloud SQL (misalnya `db-g1-small`, batas 50 koneksi), atau turunkan `pool_size`, sesuai rumus anggaran koneksi. Untuk beban saat ini (estimasi 7 RPS, sekitar 20 asisten), kapasitas 68 RPS pada p95 di bawah target sudah memberi ruang hampir 10 kali.
