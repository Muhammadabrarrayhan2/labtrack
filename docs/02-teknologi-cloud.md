# Teknologi Cloud Computing pada LabTrack

Unit kompetensi: **J.631120.002.01 Mengidentifikasi teknologi cloud computing**

Dokumen ini mengidentifikasi teknologi yang mendasari setiap layanan yang dipakai LabTrack, membandingkannya dengan layanan setara di penyedia lain, dan menjelaskan alasan pemilihan layanan beserta konsekuensinya.

## 1. Teknologi dasar

### 1.1 Virtualisasi dan hypervisor

Virtualisasi adalah teknik membagi satu server fisik menjadi beberapa mesin virtual (VM) yang masing-masing memiliki CPU virtual, memori, disk, dan kartu jaringan virtual sendiri. Pembagian ini dilakukan oleh hypervisor.

- **Hypervisor tipe 1** (*bare metal*) berjalan langsung di atas perangkat keras, misalnya KVM, VMware ESXi, Microsoft Hyper-V, dan Xen. Seluruh penyedia awan publik memakai tipe ini.
- **Hypervisor tipe 2** (*hosted*) berjalan di atas sistem operasi, misalnya VirtualBox dan VMware Workstation. Umumnya dipakai untuk pengembangan di laptop.

Compute Engine memakai hypervisor berbasis KVM. VM `labtrack-ops` (`infra/terraform/iaas.tf`) adalah contoh langsung: tipe mesin `e2-micro` memberikan 2 vCPU bersama (*shared core*, rata-rata 0,25 vCPU berkelanjutan dengan kemampuan *burst*) dan 1 GB memori yang diambil dari server fisik bersama.

### 1.2 Kontainer (Docker dan image OCI)

Kontainer adalah proses yang diisolasi memakai fitur kernel Linux (*namespaces* untuk isolasi proses, jaringan, dan sistem berkas; *cgroups* untuk pembatasan CPU dan memori). Berbeda dengan VM, kontainer tidak membawa kernel sendiri sehingga ukurannya kecil dan waktu mulainya singkat.

Image kontainer LabTrack dibangun dari `Dockerfile`:

- *Base image* `python:3.12-slim` untuk ukuran kecil.
- Dependensi dipasang sebelum kode disalin agar *layer* dependensi tetap ter-*cache* saat hanya kode yang berubah.
- Proses berjalan sebagai pengguna non-root (`uid 10001`).
- Port dibaca dari variabel `PORT` yang disuntikkan Cloud Run.

Image mengikuti spesifikasi **OCI** (*Open Container Initiative*) Image Format, sehingga image yang sama dapat dijalankan di Docker lokal (`docker-compose.yml`), Cloud Run, GKE, AWS ECS, atau Azure Container Apps tanpa perubahan.

### 1.3 Serverless container (Cloud Run dan Knative)

Cloud Run menjalankan image kontainer tanpa pengguna mengelola server atau klaster. Model sumber dayanya mengikuti API **Knative Serving** (objek *Service*, *Revision*, dan *Route*), standar terbuka untuk beban kerja serverless di atas Kubernetes. Cloud Run versi terkelola penuh berjalan di infrastruktur internal Google dengan isolasi *sandbox* (gVisor pada lingkungan eksekusi generasi pertama, *microVM* pada generasi kedua).

Konsep Knative yang terlihat langsung di LabTrack:

| Konsep | Penerapan |
|---|---|
| *Service* | `labtrack-api`, titik akses tetap dengan URL `*.run.app` |
| *Revision* | Setiap deploy dari GitHub Actions membuat revisi baru yang tidak dapat diubah |
| *Traffic splitting* | `scripts/ops/rollback.sh` memindahkan 100% trafik ke revisi sebelumnya |
| *Scale to zero* | `min_instance_count = 0` |
| *Concurrency-based autoscaling* | Instans baru dibuat saat permintaan bersamaan melebihi 40 per instans |

### 1.4 Managed database (Cloud SQL)

Cloud SQL adalah layanan basis data relasional terkelola (DBaaS) untuk PostgreSQL, MySQL, dan SQL Server. Google mengelola instalasi, *patch* versi minor, backup otomatis, pencatatan WAL untuk *point-in-time recovery*, dan pemantauan. Pelanggan memilih tier mesin, ukuran disk, jadwal backup, dan jendela pemeliharaan.

Konfigurasi LabTrack (`main.tf`, `google_sql_database_instance.db`):

- PostgreSQL 16, edisi ENTERPRISE, tier `db-f1-micro`.
- Disk SSD 10 GB dengan *autoresize*.
- Backup otomatis harian pukul 01.00 WIB, retensi 7 backup.
- IP publik tanpa *authorized networks* dan `ssl_mode = ENCRYPTED_ONLY`, sehingga koneksi hanya dapat dilakukan melalui **Cloud SQL Auth Proxy** yang mengautentikasi memakai IAM dan mengenkripsi lalu lintas dengan TLS.
- Cloud Run terhubung lewat soket Unix `/cloudsql/<connection_name>` yang disediakan oleh *proxy* bawaan Cloud Run.

### 1.5 Object storage (Cloud Storage)

Object storage menyimpan data sebagai objek di dalam bucket. Setiap objek memiliki kunci, data, dan metadata. Tidak ada hierarki direktori sebenarnya; awalan seperti `reports/SIDM01/session-01/` hanya bagian dari nama kunci. Kapasitas tidak perlu disediakan di muka.

Bucket laporan LabTrack (`google_storage_bucket.reports`):

- *Uniform bucket-level access* dan *public access prevention* `enforced`, sehingga objek tidak mungkin dibuat publik.
- *Versioning* aktif dengan aturan siklus hidup yang menghapus versi lama setelah ada 3 versi lebih baru.
- Akses unduh melalui **V4 signed URL** berumur 15 menit. Karena kredensial Cloud Run tidak memiliki kunci privat, penandatanganan dilakukan lewat API IAM `signBlob` (`app/storage.py`).

### 1.6 Secret Manager

Secret Manager menyimpan data rahasia (password basis data, kunci JWT, password admin) dalam bentuk terenkripsi dengan versi. Cloud Run membaca nilai versi `latest` sebagai variabel lingkungan saat instans dimulai. Hak baca diberikan per secret kepada `labtrack-run` saja (`google_secret_manager_secret_iam_member.run_access`). Rotasi dilakukan dengan menambah versi baru lalu membuat revisi baru (`scripts/ops/rotate-secret.sh`).

### 1.7 Infrastructure as Code (Terraform)

Terraform mendefinisikan infrastruktur secara deklaratif dalam bahasa HCL. Alur kerjanya:

1. `terraform init` mengunduh *provider* (`hashicorp/google ~> 6.0`, `hashicorp/random`).
2. `terraform plan` membandingkan konfigurasi dengan **state** dan sumber daya nyata, lalu menampilkan rencana perubahan (*add*, *change*, *destroy*).
3. `terraform apply` mengeksekusi rencana melalui API Google Cloud dan memperbarui state.

**State** (`terraform.tfstate`) memetakan setiap blok `resource` ke ID sumber daya nyata. State dapat berisi data sensitif (misalnya nilai `random_password`), sehingga dikecualikan dari Git (`.gitignore`) dan sebaiknya disimpan di backend GCS bila dikerjakan oleh tim (contoh disediakan dalam komentar di `versions.tf`).

Keuntungan yang diperoleh: infrastruktur dapat diulang di proyek lain, perubahan dapat ditinjau sebagai *diff*, dan biaya dapat dihentikan dengan `terraform destroy`.

### 1.8 CI/CD (GitHub Actions)

*Workflow* `.github/workflows/ci-cd.yml` terdiri atas dua *job*:

1. **test**: memasang dependensi dan menjalankan `pytest` pada setiap *push* dan *pull request*.
2. **deploy**: hanya pada *push* ke `main` setelah *test* lulus. Langkahnya autentikasi ke GCP, build image, push ke Artifact Registry, deploy revisi baru Cloud Run, lalu *smoke test* ke `/health`.

### 1.9 Workload Identity Federation

Workload Identity Federation (WIF) memungkinkan GitHub Actions mengakses GCP tanpa kunci JSON service account. Alurnya:

1. GitHub menerbitkan token OIDC berumur pendek untuk *job* yang berjalan, berisi klaim seperti `repository` dan `ref`.
2. Google Security Token Service (STS) memverifikasi token terhadap penerbit `https://token.actions.githubusercontent.com` dan memeriksa `attribute_condition` (hanya repositori yang ditentukan di `var.github_repository` yang diterima).
3. STS menukar token tersebut menjadi kredensial federasi, yang kemudian dipakai untuk meniru (*impersonate*) service account `labtrack-deployer` melalui peran `roles/iam.workloadIdentityUser`.
4. Kredensial berlaku sekitar satu jam dan tidak pernah disimpan.

Risiko kebocoran kunci jangka panjang di GitHub Secrets dengan demikian dihilangkan.

## 2. Perbandingan antarpenyedia

| Fungsi | Google Cloud (dipakai) | Amazon Web Services | Microsoft Azure |
|---|---|---|---|
| Serverless container | Cloud Run | AWS App Runner, ECS on Fargate | Azure Container Apps |
| Basis data PostgreSQL terkelola | Cloud SQL for PostgreSQL | Amazon RDS for PostgreSQL | Azure Database for PostgreSQL Flexible Server |
| Object storage | Cloud Storage | Amazon S3 | Azure Blob Storage |
| Penyimpanan rahasia | Secret Manager | AWS Secrets Manager | Azure Key Vault |
| Registry kontainer | Artifact Registry | Amazon ECR | Azure Container Registry |
| Mesin virtual | Compute Engine | Amazon EC2 | Azure Virtual Machines |
| Snapshot disk terjadwal | Resource policy snapshot schedule | Amazon Data Lifecycle Manager | Azure Backup (disk backup) |
| NAT keluar untuk VM privat | Cloud NAT | NAT Gateway | Azure NAT Gateway |
| SSH tanpa IP publik | IAP TCP forwarding | AWS Systems Manager Session Manager | Azure Bastion |
| Identitas layanan | Service account | IAM role | Managed identity |
| Federasi CI tanpa kunci | Workload Identity Federation | IAM OIDC identity provider | Workload identity federation (Entra ID) |
| Pemantauan dan alert | Cloud Monitoring | Amazon CloudWatch | Azure Monitor |
| Log terpusat | Cloud Logging | CloudWatch Logs | Azure Monitor Logs (Log Analytics) |
| Objek SLO | Service Monitoring SLO | CloudWatch Application Signals SLO | Tidak ada layanan SLO bawaan setara; umumnya memakai Azure Monitor alert dan workbook |
| IaC bawaan penyedia | Infrastructure Manager (berbasis Terraform) | AWS CloudFormation | Azure Resource Manager / Bicep |

Terraform dapat dipakai di ketiga penyedia dengan *provider* masing-masing, sehingga keterampilan IaC pada proyek ini dapat dipindahkan.

## 3. Analisis pemilihan layanan

Kriteria pemilihan disusun dari kebutuhan nyata LabTrack:

1. Trafik rendah dan tidak merata: ramai saat awal sesi praktikum, hampir nol di luar jam praktikum dan selama libur semester.
2. Dikelola oleh satu orang (asisten laboratorium) sehingga beban operasional harus kecil.
3. Biaya harus minimal karena dibiayai kredit trial atau anggaran pribadi.
4. Data mahasiswa harus aman dan tidak terbuka ke publik.

### 3.1 Komputasi: Cloud Run dibanding Compute Engine dan GKE

| Aspek | Cloud Run (dipilih) | Compute Engine (VM) | GKE Autopilot |
|---|---|---|---|
| Model | PaaS serverless | IaaS | Kubernetes terkelola |
| Pengelolaan OS dan *patch* | Tidak ada | Penuh oleh pengelola | Node dikelola Google, manifest Kubernetes oleh pengelola |
| *Scaling* | Otomatis 0 sampai N, per permintaan | Manual atau Managed Instance Group dengan *autoscaler* | Otomatis, pod dan node |
| Biaya saat idle | Nol (skala ke nol) | Tetap per jam selama VM menyala | Biaya klaster per jam (*cluster management fee*) ditambah pod yang berjalan |
| HTTPS dan sertifikat | Bawaan | Perlu *load balancer* atau konfigurasi sendiri | Perlu Ingress atau Gateway |
| *Cold start* | Ada, beberapa detik setelah idle | Tidak ada | Tidak ada bila pod tetap berjalan |
| Kesesuaian untuk LabTrack | Tinggi | Sedang | Rendah, terlalu kompleks untuk satu layanan |

Keputusan: **Cloud Run**. Pola trafik yang tidak merata membuat skala ke nol sangat menguntungkan. Kekurangan utamanya, yaitu *cold start*, diterima dan dimitigasi dengan `startup_cpu_boost = true`. Bila latensi permintaan pertama menjadi masalah saat jam praktikum, `scripts/ops/scale.sh` dapat menaikkan `min_instances` menjadi 1 selama jam tersebut dengan konsekuensi biaya instans idle.

Compute Engine tetap dipakai untuk peran yang memang cocok dengan VM: VM operasional `labtrack-ops` yang menjalankan *job* backup logis terjadwal. Pekerjaan semacam ini membutuhkan sistem berkas, *systemd timer*, dan alat CLI PostgreSQL, sehingga lebih sederhana dijalankan di VM daripada di layanan serverless.

### 3.2 Basis data: Cloud SQL dibanding PostgreSQL di VM

| Aspek | Cloud SQL (dipilih) | PostgreSQL di Compute Engine |
|---|---|---|
| Instalasi dan *patch* | Google | Pengelola |
| Backup otomatis dan PITR | Bawaan, cukup dikonfigurasi | Harus dibangun sendiri (`pg_dump`, `pg_basebackup`, WAL archiving) |
| Koneksi aman dari Cloud Run | Bawaan melalui Cloud SQL Auth Proxy dan IAM | Perlu VPC connector atau Direct VPC egress, firewall, dan TLS sendiri |
| Ketersediaan tinggi | Satu pengaturan (`availability_type = "REGIONAL"`) | Perlu replikasi dan *failover* manual |
| Fleksibilitas | Terbatas pada ekstensi dan *flag* yang didukung | Penuh |
| Biaya untuk skala kecil | Lebih tinggi per sumber daya | Lebih rendah, terutama bila memakai e2-micro tier gratis |

Keputusan: **Cloud SQL**. Selisih biaya tidak sebanding dengan waktu yang dibutuhkan untuk membangun dan menguji backup, *patch*, dan koneksi aman sendiri. Waktu tersebut lebih baik dipakai untuk menguji restore (`scripts/ops/sql-restore-test.sh`).

### 3.3 Perkiraan biaya bulanan

Angka di bawah adalah **perkiraan** dari harga katalog publik Google Cloud dan harus diverifikasi ulang di Google Cloud Pricing Calculator untuk region `asia-southeast2` sebelum dilampirkan sebagai bukti.

| Komponen | Konfigurasi | Perkiraan biaya per bulan | Catatan |
|---|---|---|---|
| Cloud Run | 1 vCPU, 512 MiB, skala ke nol | US$0 | Masih dalam kuota gratis bulanan (180.000 vCPU-detik, 360.000 GiB-detik, 2 juta permintaan) untuk trafik praktikum |
| Cloud SQL | db-f1-micro, SSD 10 GB, backup 7 hari | Sekitar US$10 sampai 15 | Biaya terbesar. Dapat dihentikan dengan `scripts/ops/sql-start-stop.sh stop` saat libur |
| Cloud Storage | Kurang dari 5 GB, Standard | Kurang dari US$0,20 | |
| Secret Manager | 3 secret | Kurang dari US$0,50 | |
| Artifact Registry | Kurang dari 1 GB image | Sekitar US$0 sampai 0,10 | Kebijakan pembersihan menyimpan 10 versi |
| Cloud Monitoring dan Logging | Metrik bawaan, log di bawah 50 GiB | US$0 | Dalam kuota gratis |
| VM `labtrack-ops` (opsional, mati secara bawaan) | e2-micro, disk standar 10 GB, Cloud NAT | Sekitar US$7 sampai 9 untuk VM dan disk di luar region tier gratis, ditambah sekitar US$1 per bulan untuk Cloud NAT (tarif per jam per VM) dan US$0,045 per GB data yang diproses NAT | Tier gratis e2-micro hanya berlaku di `us-west1`, `us-central1`, dan `us-east1` |

> [ISI SETELAH DEPLOY: tangkapan layar estimasi Pricing Calculator dan laporan biaya aktual dari Billing > Reports, ID bukti B-002-02]

## 4. Referensi

1. Google Cloud. *Cloud Run: What is Cloud Run*. Dokumentasi resmi.
2. Knative Project. *Knative Serving Documentation*.
3. Open Container Initiative. *OCI Image Format Specification*.
4. HashiCorp. *Terraform Language Documentation: State*.
5. Google Cloud. *Workload Identity Federation with deployment pipelines*.
6. Google Cloud. *Cloud SQL for PostgreSQL: Pricing*, dan *Compute Engine: Free tier*.
