title: Manual Pengguna LabTrack
file: Manual-Pengguna-LabTrack
kicker: Manual pengguna · Versi aplikasi 1.0.2
subtitle: Panduan untuk asisten praktikum dan koordinator laboratorium
header: Manual Pengguna LabTrack
numbered: yes
meta: **Alamat aplikasi:** https://labtrack-api-b26757zszq-et.a.run.app
meta: **Berlaku untuk:** antarmuka web di /app/ dan API di /docs
meta: **Disusun oleh:** [Nama lengkap peserta]
meta: **Tanggal:** 26 Oktober 2026
---
# Mengenal LabTrack

LabTrack membantu laboratorium mencatat kehadiran praktikum, mengumpulkan laporan PDF mahasiswa, dan memberi nilai dari satu tempat. Data tersimpan di server Google Cloud, jadi Anda bisa membukanya dari komputer laboratorium, laptop pribadi, atau ponsel selama ada koneksi internet.

Manual ini ditulis untuk dua jenis pengguna:

- **Asisten praktikum**, yang mengisi kehadiran setiap sesi, mendaftarkan mahasiswa, mengunggah laporan, dan memberi nilai.
- **Koordinator laboratorium**, yang selain bisa melakukan semua tugas asisten juga membuat mata kuliah, jadwal sesi, dan akun asisten.

Mahasiswa tidak punya akun di LabTrack. Laporan mahasiswa diunggah oleh asisten.

Tabel: Apa yang bisa dilakukan setiap peran
| Kegiatan | Asisten | Koordinator |
|---|---|---|
| Melihat rekap kehadiran | Ya | Ya |
| Mengisi dan memperbaiki kehadiran | Ya | Ya |
| Menambah dan mencari mahasiswa | Ya | Ya |
| Mendaftarkan mahasiswa ke mata kuliah | Ya | Ya |
| Mengunggah, mengunduh, dan menilai laporan | Ya | Ya |
| Menghapus data mahasiswa | Tidak | Ya (lewat API) |
| Membuat mata kuliah dan sesi | Tidak | Ya |
| Membuat akun staf | Tidak | Ya |

## Yang Anda perlukan

- Peramban versi terbaru: Microsoft Edge, Google Chrome, Firefox, atau Safari.
- Akun LabTrack berupa email dan kata sandi sementara dari koordinator.
- Untuk mengunggah laporan: berkas PDF berukuran maksimal 10 MB.

## Istilah yang dipakai

Tabel: Istilah di layar
| Istilah | Arti |
|---|---|
| Mata kuliah | Mata kuliah praktikum, misalnya "Komputasi Awan". Satu mata kuliah punya beberapa sesi. |
| Sesi atau modul | Satu pertemuan praktikum dengan nomor, judul, jadwal, dan ruang. |
| Peserta | Mahasiswa yang sudah didaftarkan ke mata kuliah tertentu. |
| Ambang | Batas persentase kehadiran minimal, bawaannya 75%. |
| Berisiko | Mahasiswa yang persentase kehadirannya di bawah ambang. |
| Kode laporan (request_id) | Kode unik yang muncul di setiap pesan galat. Sertakan kode ini saat melapor masalah. |

# Masuk dan keluar

## Masuk ke aplikasi

1. Buka alamat aplikasi di peramban. Anda akan langsung diarahkan ke halaman masuk.
2. Isi **Email** dan **Kata sandi**.
3. Klik **Masuk**.

![Halaman masuk LabTrack](docs/word/assets/web-login-kartu.png 7.5)

Bila email atau kata sandi salah, muncul pesan "Email atau kata sandi salah." beserta kode. Periksa huruf besar dan kecil pada kata sandi, lalu coba lagi. Demi keamanan, aplikasi tidak memberi tahu bagian mana yang salah.

![Pesan saat login gagal, lengkap dengan kode laporan](docs/word/assets/web-login-gagal-kartu.png 7.5)

Halaman masuk juga bisa dibuka di ponsel. Tampilannya menyesuaikan lebar layar.

![Halaman masuk di layar ponsel](docs/word/assets/web-login-ponsel.png 6)

## Sesi login dan keluar

Setelah masuk, Anda tetap tercatat masuk selama 2 jam atau sampai tab peramban ditutup. Setelah itu aplikasi meminta Anda masuk lagi. Ini disengaja supaya komputer laboratorium yang dipakai bergantian tidak meninggalkan akun dalam keadaan terbuka.

Untuk keluar, klik **Keluar** di pojok kanan atas. Biasakan keluar sebelum meninggalkan komputer bersama.

## Lupa kata sandi

LabTrack tidak punya tombol "lupa kata sandi". Hubungi koordinator laboratorium. Koordinator akan meneruskan permintaan ke pengelola sistem, yang mengatur ulang kata sandi Anda dan mengirim kata sandi sementara lewat kanal terpisah, misalnya pesan langsung, bukan surel grup.

# Tampilan utama

![Tampilan utama setelah masuk](docs/bukti/screenshots/web-03-rekap.png)

Bagian atas layar berisi:

- **Pilihan mata kuliah.** Semua menu bekerja untuk mata kuliah yang dipilih di sini. Pilihan Anda diingat selama tab terbuka.
- **Nama dan peran Anda.** Label "Koordinator" atau "Asisten".
- **Tombol Keluar.**

Di bawahnya ada menu: **Rekap kehadiran**, **Input kehadiran**, **Mahasiswa**, **Laporan praktikum**, dan **Kelola**. Menu Kelola hanya muncul untuk koordinator.

Di bagian paling bawah ada nomor versi aplikasi dan tautan ke dokumentasi API.

# Rekap kehadiran

Menu ini menjawab pertanyaan yang paling sering diajukan menjelang ujian: siapa saja yang kehadirannya belum memenuhi syarat.

1. Pilih mata kuliah di bagian atas.
2. Buka menu **Rekap kehadiran**.
3. Bila perlu, ubah nilai **Ambang (%)** lalu klik **Terapkan**.

Tiga kotak di atas tabel menunjukkan jumlah sesi yang sudah berlangsung, jumlah mahasiswa terdaftar, dan jumlah mahasiswa di bawah ambang. Baris berwarna merah muda dengan label **Berisiko** adalah mahasiswa yang perlu diperhatikan.

![Rekap kehadiran dengan tiga mahasiswa berisiko (data contoh)](docs/bukti/screenshots/web-08-rekap-setelah-input.png)

Cara aplikasi menghitung persentase:

- Hadir dan terlambat dihitung masuk. Izin dan alpa tidak.
- Pembaginya adalah jumlah sesi yang sudah berlangsung. Sebuah sesi dianggap berlangsung begitu kehadirannya pernah disimpan, minimal untuk satu mahasiswa.
- Mahasiswa yang tidak punya catatan pada sesi yang sudah berlangsung dihitung tidak hadir.

> Contoh: Eka hadir 2 kali dan izin 1 kali dari 3 sesi. Persentasenya (2 + 0) / 3 = 66,7%, di bawah ambang 75%, sehingga Eka ditandai Berisiko. Bila kebijakan laboratorium Anda menganggap izin sebagai hadir, sampaikan ke koordinator karena aturan ini berlaku untuk semua mata kuliah.

# Mengisi kehadiran

Kehadiran diisi sekali per sesi untuk semua peserta.

1. Pilih mata kuliah, lalu buka menu **Input kehadiran**.
2. Pilih sesi di kotak **Sesi praktikum**. Sesi yang paling akhir terpilih otomatis.
3. Untuk setiap mahasiswa, klik status **Hadir**, **Terlambat**, **Izin**, atau **Alpa**. Untuk sesi yang belum pernah diisi, semua status awalnya Hadir, jadi Anda cukup mengubah mahasiswa yang tidak hadir.
4. Isi **Catatan** bila perlu, misalnya "izin sakit, surat menyusul".
5. Klik **Simpan kehadiran**. Pesan hijau "Kehadiran ... mahasiswa tersimpan." menandakan data sudah masuk.

![Mengisi kehadiran satu sesi. Satu mahasiswa ditandai Terlambat.](docs/bukti/screenshots/web-04-input-kehadiran.png)

Tombol **Tandai semua hadir** mengembalikan semua status ke Hadir. Tombol ini hanya mengubah pilihan di layar; data baru tersimpan setelah Anda klik Simpan kehadiran.

## Memperbaiki kehadiran

Buka sesi yang sama, ubah statusnya, lalu simpan lagi. Data lama diperbarui dan tidak tercatat ganda, jadi tidak masalah bila Anda menekan Simpan lebih dari sekali.

## Daftar peserta kosong

Bila muncul "Belum ada peserta", mahasiswa belum didaftarkan ke mata kuliah ini. Lihat Bab 6.

# Mengelola mahasiswa

## Mencari mahasiswa

1. Buka menu **Mahasiswa**.
2. Ketik NIM atau sebagian nama di kotak **Cari mahasiswa**, lalu tekan Enter atau klik **Cari**.

Kolom **Mata kuliah ini** menunjukkan apakah mahasiswa sudah terdaftar di mata kuliah yang sedang dipilih.

![Daftar mahasiswa dan status pendaftaran di mata kuliah terpilih](docs/bukti/screenshots/web-05-mahasiswa.png 13)

## Mendaftarkan mahasiswa ke mata kuliah

Klik **Daftarkan** di baris mahasiswa. Labelnya berubah menjadi **Terdaftar** dan mahasiswa langsung muncul di menu Input kehadiran dan Laporan praktikum. Mendaftarkan mahasiswa yang sudah terdaftar tidak menimbulkan galat dan tidak membuat data ganda.

## Menambah mahasiswa baru

1. Di kartu **Tambah mahasiswa**, isi **NIM** (8 sampai 15 digit angka) dan **Nama lengkap**. **Kelas** dan **Email** boleh dikosongkan.
2. Biarkan centang **Langsung daftarkan ke mata kuliah yang dipilih** bila mahasiswa ini peserta mata kuliah yang sedang dibuka.
3. Klik **Tambah**.

NIM harus unik. Bila NIM sudah terdaftar, muncul pesan galat. Cari mahasiswa tersebut lalu klik Daftarkan.

# Laporan praktikum

## Mengunggah laporan

1. Buka menu **Laporan praktikum** dan pilih sesi.
2. Pilih nama mahasiswa di kotak **Mahasiswa**.
3. Klik **Choose File** atau **Pilih berkas**, lalu pilih berkas PDF.
4. Klik **Unggah PDF**.

![Daftar laporan masuk untuk Modul 1 (data contoh)](docs/bukti/screenshots/web-06-laporan.png)

Aturan unggah:

- Hanya PDF asli yang diterima. Berkas lain yang namanya diubah menjadi .pdf akan ditolak karena aplikasi memeriksa isi berkasnya.
- Ukuran maksimal 10 MB. Bila lebih, minta mahasiswa mengekspor ulang PDF dengan kualitas gambar lebih rendah.
- Satu mahasiswa punya satu laporan per sesi. Mengunggah ulang akan mengganti berkas lama dan **mengosongkan nilai**, karena nilai lama mungkin tidak berlaku untuk berkas baru.

## Mengunduh laporan

Klik **Unduh** di baris laporan. Berkas terbuka di tab baru. Tautan unduhan hanya berlaku 15 menit. Bila sudah lewat, klik Unduh lagi untuk mendapat tautan baru. Jangan bagikan tautan unduhan ke grup, karena siapa pun yang memegang tautan itu bisa membuka berkasnya sampai tautan kedaluwarsa.

## Memberi nilai

1. Isi kolom **Nilai** dengan angka 0 sampai 100. Kelipatan 0,5 diperbolehkan.
2. Isi **Umpan balik** bila perlu.
3. Klik **Simpan nilai**.

Kolom Status berubah dari **Belum dinilai** menjadi nilai yang Anda berikan.

# Menu Kelola (koordinator)

![Menu Kelola untuk koordinator](docs/bukti/screenshots/web-07-kelola.png)

## Membuat mata kuliah

Isi **Kode** (3 sampai 20 karakter, huruf, angka, tanda hubung, atau garis bawah), **Nama**, dan **Semester**, lalu klik **Buat**. Mata kuliah baru langsung terpilih di bagian atas layar.

## Membuat sesi

Pastikan mata kuliah yang benar sedang terpilih. Isi **No.** (1 sampai 30), **Judul modul**, **Jadwal**, dan **Ruang**, lalu klik **Buat sesi**. Nomor sesi tidak boleh sama dalam satu mata kuliah.

## Membuat akun staf

Isi **Email**, **Nama**, **Kata sandi sementara** (minimal 8 karakter), dan **Peran**, lalu klik **Buat akun**. Sampaikan kata sandi sementara lewat kanal pribadi dan minta pemilik akun menyimpannya dengan baik. Daftar **Akun staf** di bagian bawah menunjukkan semua akun dan statusnya.

Untuk menonaktifkan akun asisten yang sudah tidak bertugas, hubungi pengelola sistem. Akun yang dinonaktifkan tidak bisa masuk lagi, tetapi data yang pernah dicatatnya tetap tersimpan.

# Jika terjadi masalah

Setiap pesan galat di LabTrack disertai **Kode**, misalnya `d0534c831f04ce315bffea2518a64f63`. Kode ini menunjuk ke catatan teknis permintaan Anda di server. Saat melapor, salin kode tersebut, jangan hanya mengirim foto layar yang kodenya terpotong.

Tabel: Pesan yang sering muncul dan langkah yang disarankan
| Pesan atau gejala | Kemungkinan penyebab | Yang perlu dilakukan |
|---|---|---|
| Email atau kata sandi salah | Salah ketik atau akun belum dibuat | Periksa huruf besar dan kecil; tanyakan ke koordinator |
| Kembali ke halaman masuk saat sedang bekerja | Sesi 2 jam habis | Masuk lagi; data yang sudah disimpan tidak hilang |
| "Pilih mata kuliah terlebih dahulu" | Belum ada mata kuliah terpilih | Pilih di bagian atas layar |
| "Belum ada sesi untuk mata kuliah ini" | Koordinator belum membuat sesi | Minta koordinator membuat sesi di menu Kelola |
| Unggahan ditolak | Bukan PDF atau lebih dari 10 MB | Minta berkas PDF yang benar |
| Pesan 503 atau "Tidak dapat terhubung ke server" | Gangguan sementara di server | Tunggu 5 menit lalu coba lagi; bila berlanjut, laporkan dengan kode dan jam kejadian |
| Halaman galat tanpa kode | Server sedang memulai ulang | Catat jam kejadian, coba lagi beberapa menit kemudian, lalu laporkan |

## Cara melapor

Kirim laporan ke admin laboratorium (dukungan level 1) dengan isi berikut:

1. Nama dan email akun Anda.
2. Menu dan tombol yang sedang Anda pakai.
3. Pesan yang muncul beserta **Kode**.
4. Jam kejadian.
5. Apa yang sudah Anda coba.

Admin laboratorium akan menangani masalah akun dan cara pakai. Masalah teknis diteruskan ke pengelola sistem (level 2), dan bila perlu ke pihak penyedia layanan cloud (level 3). Gangguan yang membuat aplikasi tidak bisa dipakai (prioritas P1) ditanggapi paling lambat 15 menit. Pertanyaan, lupa kata sandi, dan masalah akun lain (prioritas P4) ditanggapi dalam 1 hari kerja.

# Lampiran: memakai API

Pengguna yang ingin mengintegrasikan LabTrack dengan aplikasi lain bisa memakai API REST. Dokumentasi interaktifnya ada di `/docs`. Klik **Authorize**, isi email dan kata sandi, lalu coba setiap endpoint langsung dari halaman tersebut.

![Dokumentasi API interaktif (Swagger UI)](docs/bukti/screenshots/B-001-03-swagger-ui.png)

Contoh memanggil API dari terminal:

```
# 1. Masuk dan ambil token
curl -s -X POST https://labtrack-api-b26757zszq-et.a.run.app/auth/login \
     -d "username=asisten@kampus.ac.id" -d "password=KATA_SANDI"

# 2. Pakai token untuk membaca rekap kehadiran mata kuliah 1
curl -s -H "Authorization: Bearer TOKEN" \
     "https://labtrack-api-b26757zszq-et.a.run.app/courses/1/attendance-summary?threshold=75"
```

Daftar lengkap endpoint ada di Dokumentasi Teknis LabTrack.
