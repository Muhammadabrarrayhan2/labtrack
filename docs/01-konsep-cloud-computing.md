# Terminologi dan Konsep Cloud Computing pada LabTrack

Unit kompetensi: **J.631120.001.01 Mendefinisikan terminologi dan konsep cloud computing**

Dokumen ini menjelaskan konsep dasar komputasi awan berdasarkan definisi NIST SP 800-145 dan menunjukkan penerapan setiap konsep secara konkret pada proyek LabTrack. Setiap klaim dirujuk ke berkas di repositori agar dapat diverifikasi oleh asesor.

## 1. Definisi

NIST SP 800-145 (*The NIST Definition of Cloud Computing*, 2011) mendefinisikan komputasi awan sebagai model yang memungkinkan akses jaringan yang mudah dan sesuai permintaan ke kumpulan sumber daya komputasi yang dapat dikonfigurasi (jaringan, server, penyimpanan, aplikasi, dan layanan), yang dapat disediakan dan dilepaskan dengan cepat dengan upaya pengelolaan atau interaksi penyedia layanan yang minimal.

Definisi tersebut terdiri atas tiga bagian: lima karakteristik esensial, tiga model layanan, dan empat model penerapan.

## 2. Lima karakteristik esensial dan penerapannya pada LabTrack

| No | Karakteristik | Pengertian | Wujud konkret di LabTrack | Rujukan |
|---|---|---|---|---|
| 1 | *On-demand self-service* | Pengguna menyediakan sumber daya sendiri tanpa interaksi manusia dengan penyedia | Seluruh sumber daya (Cloud Run, Cloud SQL, bucket, secret, service account) dibuat dengan satu perintah `terraform apply` melalui API Google Cloud, tanpa tiket ke Google | `infra/terraform/main.tf`, `docs/PANDUAN-DEPLOYMENT.md` langkah 5 |
| 2 | *Broad network access* | Layanan diakses melalui jaringan dengan mekanisme standar dari berbagai jenis perangkat klien | API diakses melalui HTTPS di domain `*.run.app` dari peramban (Swagger UI di `/docs`), `curl`, atau skrip Python. Asisten laboratorium cukup memakai laptop dan koneksi internet | `app/main.py`, resource `google_cloud_run_v2_service_iam_member.public` |
| 3 | *Resource pooling* | Sumber daya penyedia digabungkan untuk melayani banyak pelanggan (*multi-tenant*), lokasi fisik tidak diketahui secara pasti oleh pelanggan | Cloud Run menjalankan kontainer LabTrack di atas infrastruktur bersama milik Google. Cloud SQL tier `db-f1-micro` memakai vCPU bersama (*shared core*). Pelanggan hanya memilih region `asia-southeast2`, bukan server fisik | `variables.tf` (`region`, `db_tier`) |
| 4 | *Rapid elasticity* | Kapasitas dapat bertambah dan berkurang dengan cepat, bahkan otomatis, sesuai beban | Cloud Run melakukan *autoscaling* dari 0 hingga 3 instans berdasarkan jumlah permintaan bersamaan (konkurensi 40 per instans). Saat tidak ada trafik, jumlah instans kembali ke 0 | `main.tf`, blok `scaling { min_instance_count = 0, max_instance_count = 3 }` dan `max_instance_request_concurrency = 40` |
| 5 | *Measured service* | Pemakaian sumber daya diukur, dipantau, dan dilaporkan secara transparan | Cloud Monitoring mencatat `request_count`, `request_latencies`, `instance_count`, dan CPU Cloud SQL pada dasbor "LabTrack Overview". Tagihan dihitung per detik vCPU dan memori pada Cloud Run dan dipantau melalui budget alert | `monitoring.tf`, `slo.tf`, `docs/PANDUAN-DEPLOYMENT.md` langkah 1 (budget) |

> [BUKTI: screenshot B-001-01, dasbor "LabTrack Overview" yang menampilkan grafik jumlah instans naik dari 0 lalu turun kembali setelah uji beban]

## 3. Model layanan

| Model | Pengertian | Yang dikelola pelanggan | Yang dikelola penyedia | Contoh di Google Cloud |
|---|---|---|---|---|
| IaaS (*Infrastructure as a Service*) | Penyedia menyewakan sumber daya komputasi dasar (VM, disk, jaringan) | Sistem operasi, *patch*, *runtime*, aplikasi, data | Perangkat keras fisik, hypervisor, jaringan pusat data | Compute Engine, Persistent Disk, VPC |
| PaaS (*Platform as a Service*) | Penyedia menyediakan platform untuk menjalankan aplikasi; pelanggan tidak mengelola OS | Kode aplikasi, konfigurasi layanan, data | OS, *runtime*, *scaling*, *patch*, infrastruktur | Cloud Run, Cloud SQL, App Engine |
| SaaS (*Software as a Service*) | Penyedia menyediakan aplikasi jadi yang langsung dipakai | Data dan pengaturan akun pengguna | Seluruh tumpukan hingga aplikasi | GitHub, Gmail, Google Cloud Console |

### 3.1 Penempatan komponen LabTrack dalam model layanan

| Komponen | Layanan | Model | Alasan |
|---|---|---|---|
| API LabTrack | Cloud Run | PaaS (serverless container) | Pengembang hanya menyerahkan image kontainer. OS, *scaling*, TLS, dan *load balancing* dikelola Google |
| Basis data | Cloud SQL for PostgreSQL 16 | PaaS (DBaaS) | Instalasi, *patch* mesin basis data, backup otomatis, dan *failover* dikelola Google. Pengembang mengelola skema dan data |
| Penyimpanan laporan PDF | Cloud Storage | PaaS / *Storage as a Service* | Kapasitas tidak perlu disediakan di muka, dibayar per GB tersimpan |
| Rahasia (password, kunci JWT) | Secret Manager | PaaS | Penyimpanan terenkripsi dengan versi dan kontrol akses IAM |
| Registry image | Artifact Registry | PaaS | Registry kontainer terkelola |
| VM operasional `labtrack-ops` (opsional) | Compute Engine e2-micro | IaaS | Pengembang mengelola OS Debian 12, *patch*, paket, dan *job* backup sendiri |
| Cloud NAT dan aturan firewall | VPC | IaaS (jaringan) | Komponen jaringan virtual yang dikonfigurasi sendiri |
| Repositori kode dan CI/CD | GitHub, GitHub Actions | SaaS (dipakai sebagai pelanggan) | Aplikasi jadi, pengembang hanya mengelola repositori dan *workflow* |
| Notifikasi alert | Gmail | SaaS | Penerima email alert Cloud Monitoring |
| Konsol pengelolaan | Google Cloud Console | SaaS | Antarmuka web untuk mengelola proyek |
| LabTrack bagi pengguna laboratorium | LabTrack API | SaaS (ditawarkan) | Asisten dan koordinator laboratorium memakai aplikasi jadi tanpa mengelola infrastruktur apa pun |

## 4. Model penerapan

| Model | Pengertian | Relevansi dengan LabTrack |
|---|---|---|
| *Public cloud* | Infrastruktur dimiliki penyedia dan dibuka untuk umum | **Model yang dipakai.** LabTrack berjalan di Google Cloud region Jakarta (`asia-southeast2`) |
| *Private cloud* | Infrastruktur dipakai eksklusif oleh satu organisasi, dapat berada di lokasi sendiri atau dikelola pihak ketiga | Alternatif bila universitas mewajibkan data mahasiswa tetap di pusat data kampus, misalnya memakai OpenStack atau VMware. Perbandingan biayanya ada di `docs/03-kebutuhan-perangkat-keras.md` bagian CapEx dan OpEx |
| *Hybrid cloud* | Gabungan dua atau lebih model yang terhubung dan memungkinkan portabilitas data atau aplikasi | Dapat diterapkan bila basis data tetap di server kampus dan API di Cloud Run, terhubung melalui Cloud VPN. Karena LabTrack dikemas sebagai image kontainer OCI, aplikasi yang sama dapat berjalan di kedua sisi (`docker-compose.yml` sudah membuktikan aplikasi berjalan di luar GCP) |
| *Community cloud* | Infrastruktur dipakai bersama oleh beberapa organisasi dengan kebutuhan yang sama | Contohnya platform awan bersama antarperguruan tinggi. Tidak dipakai pada proyek ini |

## 5. Model tanggung jawab bersama (*shared responsibility model*)

Keamanan dan operasi di awan dibagi antara penyedia dan pelanggan. Semakin tinggi tingkat abstraksi layanan, semakin banyak tanggung jawab yang diambil alih penyedia.

| Lapisan | Compute Engine (IaaS) | Cloud SQL (DBaaS) | Cloud Run (serverless) |
|---|---|---|---|
| Keamanan fisik pusat data | Google | Google | Google |
| Perangkat keras, jaringan fisik, hypervisor | Google | Google | Google |
| Sistem operasi host dan *patch* | **Saya** (Debian 12 di VM `labtrack-ops`, `scripts/ops/vm-patch.sh`) | Google | Google |
| Mesin basis data, versi minor, *patch* | Saya (bila PostgreSQL dipasang di VM) | Google (jendela pemeliharaan Minggu 02.00 WIB, `maintenance_window` di `main.tf`) | Tidak relevan |
| *Runtime* aplikasi dan dependensi | Saya | Tidak relevan | **Saya** (image `python:3.12-slim`, `requirements.txt`) |
| *Scaling* dan ketersediaan | Saya (instance group, health check) | Google untuk infrastruktur; saya memilih ZONAL atau REGIONAL | Google (autoscaling); saya menentukan batas `min`/`max` |
| Backup | Saya (snapshot disk, `pg_dump`) | Google menjalankan backup otomatis; **saya** mengatur jadwal, retensi, dan menguji restore (`scripts/ops/sql-restore-test.sh`) | Tidak relevan (aplikasi *stateless*) |
| Konfigurasi jaringan dan firewall | Saya (firewall IAP, Cloud NAT di `iaas.tf`) | Saya (tanpa *authorized networks*, `ssl_mode = ENCRYPTED_ONLY`) | Saya (`ingress`, akses `allUsers`) |
| Identitas dan akses (IAM) | Saya | Saya | Saya (service account `labtrack-run` dengan peran minimum) |
| Kode aplikasi dan data | Saya | Saya (skema, data) | Saya |
| Rahasia | Saya | Saya | Saya (Secret Manager, rotasi dengan `scripts/ops/rotate-secret.sh`) |

Kesimpulan: pada Cloud Run dan Cloud SQL, tanggung jawab saya terpusat pada kode, data, IAM, dan konfigurasi. Pada Compute Engine, tanggung jawab saya meluas hingga sistem operasi, *patch*, dan backup disk. Karena itu VM `labtrack-ops` dilengkapi jadwal snapshot harian dan skrip *patch*.

## 6. Glosarium

| No | Istilah | Definisi | Penerapan di repositori |
|---|---|---|---|
| 1 | Region | Wilayah geografis yang berisi beberapa pusat data | `asia-southeast2` (Jakarta) di `variables.tf` |
| 2 | Zone | Lokasi terisolasi di dalam region, kira-kira setara satu pusat data | VM `labtrack-ops` di `asia-southeast2-a` (variabel `ops_vm_zone`); Cloud SQL `availability_type = "ZONAL"` |
| 3 | Instance | Satu unit sumber daya komputasi yang berjalan, misalnya satu VM, satu instans Cloud SQL, atau satu salinan kontainer di Cloud Run | `google_sql_database_instance.db`, `google_compute_instance.ops` |
| 4 | Virtual machine (VM) | Komputer virtual yang berjalan di atas hypervisor | VM `labtrack-ops` di `iaas.tf` |
| 5 | Hypervisor | Lapisan perangkat lunak yang membagi server fisik menjadi beberapa VM | Compute Engine memakai hypervisor berbasis KVM |
| 6 | Container | Proses terisolasi yang membawa aplikasi beserta dependensinya, berbagi kernel host | Aplikasi LabTrack dikemas dengan `Dockerfile` |
| 7 | Image | Paket *read-only* berisi sistem berkas dan metadata untuk menjalankan kontainer | `asia-southeast2-docker.pkg.dev/<project>/labtrack/api:<tag>` |
| 8 | Registry | Tempat penyimpanan dan distribusi image | Artifact Registry `labtrack`, kebijakan simpan 10 versi terakhir |
| 9 | Revision | Snapshot konfigurasi dan image yang tidak dapat diubah pada Cloud Run; setiap deploy membuat revisi baru | `scripts/ops/rollback.sh` memindahkan trafik ke revisi sebelumnya |
| 10 | Cold start | Jeda saat instans baru harus dibuat karena tidak ada instans yang siap, misalnya setelah skala ke nol | `min_instance_count = 0` dan `startup_cpu_boost = true` di `main.tf` |
| 11 | Autoscaling | Penambahan dan pengurangan instans otomatis berdasarkan beban | Cloud Run 0 sampai 3 instans |
| 12 | Concurrency | Jumlah permintaan yang dilayani satu instans secara bersamaan | `max_instance_request_concurrency = 40` |
| 13 | Serverless | Model eksekusi tanpa pengelolaan server oleh pengembang, ditagih berdasarkan pemakaian | Cloud Run |
| 14 | Managed service | Layanan yang operasionalnya (*patch*, backup, ketersediaan) ditangani penyedia | Cloud SQL, Secret Manager |
| 15 | Object storage | Penyimpanan data sebagai objek (data + metadata + kunci) di dalam bucket, diakses melalui API | Bucket `<project>-labtrack-reports` |
| 16 | Signed URL | URL sementara yang memberi akses ke objek privat tanpa akun | `app/storage.py`, berlaku 15 menit |
| 17 | IAM | *Identity and Access Management*, pengaturan siapa boleh melakukan apa pada sumber daya | `google_project_iam_member.run_roles` |
| 18 | Service account | Identitas untuk aplikasi atau mesin, bukan manusia | `labtrack-run`, `labtrack-deployer`, `labtrack-ops` |
| 19 | Least privilege | Prinsip memberi hak akses minimum yang diperlukan | `labtrack-run` hanya Cloud SQL Client, Log Writer, Metric Writer |
| 20 | OIDC | *OpenID Connect*, protokol identitas berbasis token JWT | GitHub Actions menerbitkan token OIDC yang ditukar ke kredensial GCP |
| 21 | Workload Identity Federation | Mekanisme GCP untuk mempercayai identitas eksternal (misalnya GitHub) tanpa kunci JSON | `cicd.tf` |
| 22 | IaC | *Infrastructure as Code*, pendefinisian infrastruktur dalam berkas teks yang dapat diversikan | Folder `infra/terraform` |
| 23 | State (Terraform) | Berkas yang mencatat pemetaan antara konfigurasi Terraform dan sumber daya nyata | `terraform.tfstate`, opsi backend GCS di `versions.tf` |
| 24 | CI/CD | *Continuous Integration / Continuous Delivery*, otomasi uji, build, dan deploy | `.github/workflows/ci-cd.yml` |
| 25 | SLA | *Service Level Agreement*, perjanjian tingkat layanan dengan pengguna beserta konsekuensinya | `docs/05-sla-dan-pemantauan.md` |
| 26 | SLO | *Service Level Objective*, target internal untuk suatu SLI | Ketersediaan 99,5% dan latensi p95 < 800 ms di `slo.tf` |
| 27 | SLI | *Service Level Indicator*, metrik terukur yang mencerminkan kualitas layanan | Rasio permintaan non-5xx terhadap total permintaan |
| 28 | Error budget | Jumlah kegagalan yang masih diizinkan selama periode SLO, yaitu 100% dikurangi target | 0,5% dari 30 hari = 216 menit |
| 29 | RPO | *Recovery Point Objective*, batas maksimum data yang boleh hilang, diukur dalam waktu | 24 jam (backup harian) |
| 30 | RTO | *Recovery Time Objective*, batas waktu maksimum untuk memulihkan layanan | 2 jam |
| 31 | Snapshot | Salinan disk pada satu titik waktu | Kebijakan snapshot harian boot disk VM, retensi 7 hari |
| 32 | NAT | *Network Address Translation*, memungkinkan VM tanpa IP publik mengakses internet keluar | `google_compute_router_nat.ops` |
| 33 | IAP | *Identity-Aware Proxy*, akses SSH ke VM melalui identitas Google tanpa IP publik | Firewall `35.235.240.0/20` port 22 |

## 7. Referensi

1. Mell, P. dan Grance, T. (2011). *The NIST Definition of Cloud Computing*. NIST Special Publication 800-145.
2. Google Cloud. *Shared responsibilities and shared fate on Google Cloud*. Dokumentasi Google Cloud Architecture Center.
3. Google Cloud. *Cloud Run documentation: About instance autoscaling*.
4. Keputusan Menteri Ketenagakerjaan Republik Indonesia Nomor 456 Tahun 2015 tentang Penetapan SKKNI Kategori Informasi dan Komunikasi Golongan Pokok Kegiatan Pemrograman, Konsultasi Komputer dan Kegiatan YBDI Bidang Cloud Computing.
