# Dokumen Spesifikasi Kebutuhan Perangkat Lunak (SKPL / SRS)
## Sistem Informasi Manajemen Akreditasi (SIMAK)
### Instrumen LAMSAMA & LAM INFOKOM

| | |
|---|---|
| **Nama Sistem** | Sistem Informasi Manajemen Akreditasi (SIMAK) |
| **Versi Dokumen** | 1.1 |
| **Tanggal** | 4 Oktober 2026 |
| **Lingkup** | Fakultas (UPPS) dengan 3 Program Studi |
| **Lembaga Akreditasi** | LAMSAMA (Kimia, Sains Aktuaria) & LAM INFOKOM (Ilmu Komputer) |
| **Instrumen Acuan** | IAPS 3.1 LAMSAMA dan IAPS 2.1 LAM INFOKOM (Program Sarjana) |
| **Status** | Draft untuk Reviu |

### Riwayat Perubahan

| Versi | Perubahan |
|---|---|
| 1.1 | Struktur instrumen dikoreksi sesuai dokumen IAPS 3.1 LAMSAMA dan IAPS 2.1 LAM INFOKOM (§2.2, US-D1, US-D3, US-F4, Epik E, glosarium). Staf Admin Fakultas menyusun instrumen dan aturan pemetaan, Dekan menyetujui (US-G5). Narasi hanya disunting Kaprodi. Asesor melihat versi laporan yang sudah disetujui. |
| 1.0 | Versi awal. |

---

## Daftar Isi

1. [Pendahuluan](#1-pendahuluan)
2. [Deskripsi Umum Sistem](#2-deskripsi-umum-sistem)
3. [Peran Pengguna dan Hak Akses](#3-peran-pengguna-dan-hak-akses)
4. [User Stories dan Acceptance Criteria](#4-user-stories-dan-acceptance-criteria)
5. [Alur Kerja Utama (Core Workflows)](#5-alur-kerja-utama-core-workflows)
6. [Edge Cases dan Alur Pengecualian](#6-edge-cases-dan-alur-pengecualian)
7. [Kebutuhan Non-Fungsional (Ringkas)](#7-kebutuhan-non-fungsional-ringkas)
8. [Lampiran: Glosarium](#8-lampiran-glosarium)

---

## 1. Pendahuluan

### 1.1 Tujuan
Dokumen ini mendefinisikan kebutuhan fungsional dan non-fungsional dari **Sistem Informasi Manajemen Akreditasi (SIMAK)**. Sistem dirancang sebagai **satu basis data tunggal (single source of truth)** yang melayani dua instrumen akreditasi berbeda — LAMSAMA dan LAM INFOKOM — tanpa mewajibkan duplikasi input data Tridharma.

### 1.2 Lingkup Produk
SIMAK memfasilitasi:
- Pengumpulan data akademik (Tata Kelola, Pendidikan, Penelitian, PkM) di tingkat Program Studi dan UPPS/Fakultas.
- Pemetaan satu data mentah ke dua instrumen berbeda: IAPS 3.1 LAMSAMA (kriteria A–F) dan IAPS 2.1 LAM INFOKOM (bagian A, B, enam kriteria, dan Suplemen).
- Pengelolaan siklus penjaminan mutu **PPEPP** sebagai fondasi alur kerja.
- Pemantauan terpusat tingkat Dekan (dashboard, *gap analysis*, *benchmarking* antarprodi).
- Penetapan butir standar sasaran (PPEPP P1) oleh Dekan berbasis katalog Standar SPM.
- Integrasi dokumen hasil *tracer study*/kepuasan dari Direktorat Kemahasiswaan (bukan penyelenggaraan surveinya).
- Pembuatan draf LED berbantuan LLM (offline/online) dan telaah bukti read-only oleh asesor.

### 1.3 Di Luar Lingkup (Out of Scope) — Versi 1.0
- Submisi otomatis ke portal resmi LAM (data diekspor manual dalam format dokumen).
- **Penyelenggaraan survei/tracer study** (dilakukan Direktorat Kemahasiswaan; SIMAK hanya menerima & memetakan hasilnya).
- Integrasi *real-time* dengan PDDikti/SISTER (ditangani via impor berkala pada versi mendatang).
- Penilaian/skoring resmi final oleh asesor (sistem hanya menyajikan data & skor estimasi internal; asesor berakses read-only).

### 1.4 Pemangku Kepentingan Utama
- **Dekan** (pemilik proses tingkat UPPS; penetapan, validasi, penugasan, aktivasi asesor).
- **Ketua Program Studi (Kaprodi)** Ilmu Komputer, Kimia, dan Sains Aktuaria.
- **Staf Admin Prodi** dan **Staf Admin Fakultas** (operator input/edit data sesuai cakupan).
- **Asesor** (peninjau eksternal, read-only, per prodi).
- **Administrator Sistem/IT** (pengelola teknis akun & sistem; tanpa akses konten akreditasi).
- **Direktorat Kemahasiswaan** (sumber dokumen tracer/kepuasan — eksternal UPPS).
- Gugus/Satuan Penjaminan Mutu (pengguna laporan; SPM sebagai sumber katalog Standar).

---

## 2. Deskripsi Umum Sistem

### 2.1 Arsitektur Konseptual
Sistem dibangun di atas tiga lapisan logis:

| Lapisan | Fungsi |
|---|---|
| **Lapisan Data Inti (Core Data)** | Entitas akademik universal: Dosen, Mahasiswa, Lulusan, Publikasi, Penelitian, Hibah, PkM, Sarana-Prasarana, Keuangan, Kurikulum. Netral terhadap instrumen. |
| **Lapisan Pemetaan (Mapping Engine)** | Mengaitkan setiap data inti ke elemen/butir penilaian LAMSAMA **dan** LAM INFOKOM. Satu data dapat memenuhi beberapa butir di kedua instrumen. |
| **Lapisan Keluaran (Output/Report)** | Menghasilkan dokumen evaluasi diri sesuai format masing-masing LAM, laporan *gap analysis*, dan dashboard. |

### 2.2 Instrumen Acuan dan Pemetaan

Struktur berikut mengikuti dokumen IAPS 3.1 LAMSAMA dan IAPS 2.1 LAM INFOKOM untuk Program Sarjana.

**Struktur kedua instrumen**

| Aspek | IAPS 3.1 LAMSAMA (Kimia, Sains Aktuaria) | IAPS 2.1 LAM INFOKOM (Ilmu Komputer) |
|---|---|---|
| Susunan | 35 indikator dalam 6 kriteria: **A** Tata Kelola dan Penjaminan Mutu (1–7), **B** Pendidikan dan Pengajaran (8–20), **C** Penelitian (21–25), **D** Pengabdian kepada Masyarakat (26–29), **E** Capaian dan Luaran (30–34), **F** Analisis dan Penetapan Program Pengembangan (35) | Bagian **A** Kondisi Eksternal, bagian **B** Profil UPPS, 6 kriteria (**1** Budaya Mutu, **2** Relevansi Pendidikan, **3** Relevansi Penelitian, **4** Relevansi PkM, **5** Akuntabilitas, **6** Diferensiasi Misi), dan Suplemen Program Studi |
| Rubrik | Baik Sekali, Baik, Cukup, Kurang | Sangat Baik (4), Baik (3), Cukup (2), Kurang (1) |
| Bobot | Tidak berbobot | Tiap butir berbobot, total 400: Kondisi Eksternal 4, Profil UPPS 4, Budaya Mutu 40, Relevansi Pendidikan 120, Relevansi Penelitian 72, Relevansi PkM 60, Akuntabilitas 40, Diferensiasi Misi 40, Suplemen 20 |
| Penanda butir | Tidak ada | Jenis Input, Proses, atau Output; butir tiap kriteria tersusun per tahap PPEPP |
| Penentuan status | Tingkat minimum per indikator untuk tiap peringkat, ditambah indikator syarat perlu | Rentang nilai akhir, ditambah syarat rerata kriteria dan skor minimum butir |
| Peringkat | Unggul 5 tahun, Unggul 2 tahun, Terakreditasi, Tidak Terakreditasi | Unggul 5 tahun, Unggul 3 tahun, Terakreditasi, Tidak Terakreditasi |

**Pemetaan data inti ke instrumen (tingkat kriteria)**

| Data inti | IAPS 3.1 LAMSAMA (kriteria · indikator) | IAPS 2.1 LAM INFOKOM |
|---|---|---|
| VMTS, tata pamong, tata kelola | A · 1, 2 | Kriteria 1 Budaya Mutu, 5 Akuntabilitas, 6 Diferensiasi Misi |
| SPMI, siklus PPEPP, audit mutu | A · 3, 4 | Kriteria 1 Budaya Mutu dan 5 Akuntabilitas; seluruh kriteria tersusun per tahap PPEPP |
| Kepuasan pemangku kepentingan | A · 5 | Tidak menjadi butir tersendiri; dipakai sebagai bukti pendukung |
| Penerimaan mahasiswa, layanan kemahasiswaan | A · 6, 7 | Kriteria 2 Relevansi Pendidikan |
| Kurikulum dan pembelajaran | B · 8–14 | Kriteria 2 Relevansi Pendidikan; Suplemen Program Studi |
| Dosen dan tenaga kependidikan | B · 16, 17, 18 | Kriteria 2 Relevansi Pendidikan; Kriteria 1 dan 5 (SDM) |
| Keuangan dan pembiayaan | B · 15; C · 24; D · 28 | Kriteria 1 Budaya Mutu; Kriteria 2, 3, 4 (pembiayaan pendidikan, penelitian, PkM) |
| Sarana dan prasarana | B · 20; C · 23; D · 28 | Kriteria 2, 3, 4; Kriteria 5 Akuntabilitas |
| Kerja sama | B · 19; C · 25 | Kriteria 3 dan 4 |
| Penelitian | C · 21, 22 | Kriteria 3 Relevansi Penelitian |
| Pengabdian kepada Masyarakat | D · 26, 27, 29 | Kriteria 4 Relevansi PkM |
| Prestasi mahasiswa dan kompetensi lulusan | E · 30 | Kriteria 2 Relevansi Pendidikan |
| Tracer study | E · 31 | Tidak menjadi butir tersendiri; dipakai sebagai bukti pendukung Kriteria 2 |
| Publikasi dan luaran (termasuk HKI) | E · 32, 33, 34 | Kriteria 3 Relevansi Penelitian; Kriteria 4 Relevansi PkM |
| Analisis capaian dan rencana pengembangan | F · 35 | Bagian A Kondisi Eksternal, bagian B Profil UPPS, Kriteria 6 Diferensiasi Misi |

> Catatan: Tabel ini adalah acuan tingkat kriteria. Pemetaan per butir disusun Staf Admin Fakultas di *Mapping Engine* dan berlaku setelah disetujui Dekan (US-G5), tanpa mengubah struktur data inti.

### 2.3 Asumsi dan Ketergantungan
- Setiap data inti memiliki **tahun akademik** dan **penanda program studi** agar dapat difilter lintas prodi.
- Nomenklatur dan bobot kriteria tiap LAM dapat berubah; sistem harus **berbasis konfigurasi**, bukan *hard-coded*.
- Instrumen (butir, rubrik, aturan peringkat) dan aturan pemetaan disusun Staf Admin Fakultas dan baru berlaku setelah disetujui Dekan.
- Satu dosen dapat terafiliasi ke lebih dari satu prodi (dosen *home base* vs mengajar lintas prodi).

---

## 3. Peran Pengguna dan Hak Akses

### 3.1 Daftar Peran

| Kode | Peran | Deskripsi Singkat | Cakupan Data |
|---|---|---|---|
| R1 | **Dekan** | Pimpinan UPPS. Menetapkan standar sasaran (PPEPP), memantau, memvalidasi, menyetujui laporan, menyetujui instrumen dan aturan pemetaan, mengatur penugasan staf, dan mengaktifkan akses asesor. | Seluruh fakultas (read-all + wewenang penetapan & tata kelola) |
| R2 | **Kaprodi** (Ilmu Komputer / Kimia / Sains Aktuaria) | Penanggung jawab akreditasi prodi. Menyusun evaluasi diri, mengelola data & siklus PPEPP prodi, lalu men-submit laporan. **Satu-satunya peran yang menyunting narasi.** | Satu prodi; instrumen otomatis (IK → LAM INFOKOM; Kimia & Aktuaria → LAMSAMA) |
| R3 | **Staf Admin Prodi** | Operator input/edit data **di dalam kendali prodi** (Tridharma, bukti, data mentah) atas pendampingan Kaprodi. Satu prodi punya satu/lebih staf. Tidak menyunting narasi. | Satu prodi yang ditugaskan |
| R4 | **Staf Admin Fakultas** | Operator untuk **butir/dokumen tingkat UPPS atau yang di luar kendali prodi** (mis. SK fakultas, keuangan fakultas, kerja sama, katalog Standar SPM, dokumen hasil tracer dari direktorat). Dapat ditugaskan Dekan membantu butir prodi tertentu. **Menyusun instrumen dan aturan pemetaan** untuk disetujui Dekan. Tidak menyunting narasi. | Tingkat fakultas + butir prodi sesuai penugasan Dekan |
| R5 | **Asesor** | Peninjau eksternal saat asesmen. **Hanya baca (read-only)**, dengan tampilan khusus telaah **bukti butir per butir**. Melihat **versi laporan yang sudah disetujui Dekan**, bukan data yang sedang dikerjakan. Akses bersifat sementara. | Satu prodi yang ditugaskan saja (tidak dapat melihat prodi lain) |
| R6 | **Administrator Sistem/IT** | Pengelola teknis sistem & akun: reset kata sandi, buka kunci akun, pemeliharaan, cadangan/pemulihan, dan konfigurasi teknis. **Tidak** mengakses isi data akreditasi. | Lapisan akun & sistem (teknis); tanpa akses konten data akreditasi |

> R2 adalah **satu peran fungsional (Kaprodi)** dengan dua pembeda: **(a) prodi yang dilingkupi** dan **(b) instrumen LAM yang aktif** — ditentukan otomatis oleh sistem berdasarkan prodi, bukan dipilih manual.
>
> **Pembeda Staf Admin Prodi vs Fakultas:** Staf Prodi mengurus butir yang datanya dimiliki & dikendalikan prodi. Staf Fakultas mengurus butir tingkat UPPS dan butir yang sumber datanya di luar kendali prodi. **Dekan berwenang memetakan butir/dokumen mana dikerjakan staf mana** (lihat US-G3).
>
> **Pembeda Dekan vs Administrator Sistem/IT:** Dekan memegang wewenang **akademik/kebijakan** atas akun (menetapkan siapa berperan apa, cakupan prodi, aktivasi asesor). Administrator Sistem/IT memegang **operasi teknis** akun (reset kata sandi, buka kunci) dan pemeliharaan sistem — **tanpa** melihat isi data akreditasi, demi pemisahan tugas.

### 3.2 Matriks Hak Akses (RBAC)

Legenda: **C** = Create, **R** = Read, **U** = Update, **D** = Delete, **A** = Approve/Validate, **–** = Tidak ada akses.

| Modul / Aksi | Dekan (R1) | Kaprodi (R2) | Staf Prodi (R3) | Staf Fakultas (R4) | Asesor (R5) | Admin IT (R6) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Dashboard fakultas (lintas prodi) | R | – | – | R | – | – |
| Dashboard prodi sendiri | R | R | R | R¹ | R² | – |
| Data inti Tridharma (kendali prodi) | R | C, R, U, D | C, R, U | C, R, U¹ | R² | – |
| Butir/dokumen tingkat UPPS & di luar kendali prodi | R | R | – | C, R, U | R² | – |
| Hapus data inti (status *Draft*) | – | D | – | – | – | – |
| Katalog Standar & Butir SPM (master) | C, R, U, A | R | – | C, R, U | – | – |
| **Penetapan (P1) PPEPP** — pilih butir sasaran, target/indikator | **C, R, U, A** | R | – | R | R² | – |
| Pelaksanaan–Peningkatan (P2–P5) PPEPP | R | C, R, U | C, R, U | C, R, U¹ | R² | – |
| Bukti dokumen (unggah **atau** tautan/link) | R | C, R, U | C, R, U | C, R, U¹ | R² | – |
| **Narasi evaluasi diri (LED)** | R | **C, R, U** | R | R¹ | R² | – |
| Instrumen akreditasi (versi, butir, rubrik, aturan peringkat) | R, A | R | R | **C, R, U** | R² | – |
| Aturan pemetaan (*Mapping Engine*) | R, A | R | – | **C, R, U** | – | – |
| Pengajuan laporan untuk validasi | R, A | **C (submit)** | – | – | – | – |
| Validasi/approve laporan prodi | **A** | – | – | – | – | – |
| Generator draf LED berbantuan LLM *(opsional)* | R | C (opsional) | – | – | – | – |
| Konfigurasi koneksi LLM (offline/online) | A | – | – | C, R, U | – | – |
| Hasil tracer study & kepuasan (dari Direktorat) | R | R | R | C, R, U | R² | – |
| *Gap analysis* & *benchmarking* antarprodi | R | – | – | – | – | – |
| Ekspor dokumen evaluasi diri (format LAM) | R | R | R | R | – | – |
| Manajemen master data (prodi, tahun, dosen, sarana) | R | – | C, R, U¹ | C, R, U | – | – |
| Penugasan butir/dokumen ke staf | C, R, U, A | – | – | – | – | – |
| **Aktivasi/penonaktifan akses asesor** | **C, R, U, A** | – | – | – | – | – |
| Manajemen peran & cakupan akun (kebijakan) | **C, R, U, A** | – | – | – | – | – |
| **Operasi teknis akun (reset sandi, buka kunci, nonaktif teknis)** | R | – | – | – | – | **C, R, U** |
| Pemeliharaan, cadangan & konfigurasi teknis sistem | R | – | – | – | – | **C, R, U** |
| Audit log | R | – | – | – | – | R |

¹ Hanya untuk prodi/butir yang **ditugaskan Dekan** kepada staf tersebut. &nbsp; ² Hanya **baca**, hanya prodi yang ditugaskan, hanya selama **jendela asesmen** aktif, dan hanya **versi laporan yang sudah disetujui Dekan**.

### 3.3 Aturan Isolasi Data
- **Isolasi antarprodi:** Kaprodi, Staf Admin Prodi, dan **Asesor** hanya dapat mengakses data prodi yang ditugaskan. Upaya mengakses prodi lain ditolak dan dicatat di *audit log*.
- **Isolasi asesor:** Asesor satu prodi **tidak dapat** melihat data prodi lain; data bersama pun hanya ditampilkan sebatas relevansinya dengan prodi yang ia nilai. Tampilan asesor read-only dan berorientasi telaah bukti per butir. Yang ditampilkan adalah versi laporan yang sudah disetujui Dekan; perubahan sesudahnya tidak tampil ke asesor sampai disetujui lagi.
- **Hak hapus terbatas:** Hanya Kaprodi yang dapat menghapus data inti, dan hanya untuk data berstatus *Draft* (lihat §6).
- **Pemisahan tugas (SoD):** Peran yang **membuat/submit** laporan (Kaprodi) berbeda dari peran yang **menetapkan** dan **memvalidasi** (Dekan). Staf admin tidak dapat submit maupun approve. Penyusun instrumen dan aturan pemetaan (Staf Admin Fakultas) juga berbeda dari yang menyetujuinya (Dekan).
- **Narasi hanya oleh Kaprodi:** Staf Admin Prodi dan Staf Admin Fakultas mengelola data dan bukti, tetapi tidak dapat menyunting narasi, termasuk pada butir yang ditugaskan kepadanya.
- **Kendali penugasan oleh Dekan:** Dekan menentukan butir/dokumen mana dikerjakan Staf Prodi vs Staf Fakultas, dan merupakan satu-satunya peran yang berwenang **mengaktifkan akses asesor** (terbatas waktu, per prodi) — rekomendasi rinci pada §3.4.
- **Data bersama lintas prodi:** Data dosen atau sarana-prasarana fakultas yang dipakai banyak prodi dikelola Staf Admin Fakultas sebagai *shared master data*; perubahan tercermin ke semua prodi pengguna.
- **Pemisahan Admin IT vs konten:** Administrator Sistem/IT mengelola akun & teknis sistem, tetapi **tidak** memiliki akses baca ke isi data akreditasi prodi; aksinya terbatas pada lapisan akun/sistem dan tercatat di *audit log*.

### 3.4 Rekomendasi Pengaktifan Akses Asesor
- **Pemberi izin:** **Dekan** (pemilik proses UPPS) adalah satu-satunya peran yang berwenang mengaktifkan/menonaktifkan akun asesor. Ini menjaga pemisahan tugas dan mencegah prodi membuka aksesnya sendiri.
- **Alur usulan:** Kaprodi dapat **mengusulkan** daftar asesor, namun aktivasi tetap di tangan Dekan; Staf Admin Fakultas hanya **menyiapkan akun** setelah disetujui Dekan.
- **Jendela waktu (time-boxed):** Akses asesor otomatis aktif hanya pada rentang tanggal asesmen dan nonaktif sesudahnya tanpa perlu dihapus manual.
- **Audit penuh:** Setiap sesi login dan tindakan baca asesor tercatat di *audit log*.
- **Cakupan terkunci:** Satu akun asesor terikat pada **satu prodi**; untuk menilai prodi lain diperlukan akun/penugasan terpisah.
- **Prasyarat:** Akses asesor hanya dapat diaktifkan setelah laporan prodi tersebut berstatus *Disetujui*.
- **Versi yang dilihat:** Asesor membaca cuplikan laporan yang disetujui (narasi, skor estimasi, dan bukti sebagaimana saat disetujui). Bila laporan dibuka kembali, asesor tetap melihat versi terakhir yang disetujui sampai versi baru disetujui.

---

## 4. User Stories dan Acceptance Criteria

Format acceptance criteria menggunakan gaya **Given–When–Then** (Diberikan–Ketika–Maka).

### Epik A — Autentikasi & Otorisasi

**US-A1 — Masuk sesuai peran**
> Sebagai pengguna, saya ingin masuk ke sistem dan langsung diarahkan ke beranda sesuai peran saya, agar saya hanya melihat fungsi yang relevan.

**Acceptance Criteria:**
- Diberikan kredensial valid, Ketika login berhasil, Maka pengguna diarahkan ke dashboard sesuai peran (Dekan → dashboard fakultas; Kaprodi/Staf Admin → dashboard prodi; Staf Fakultas → dashboard fakultas; Asesor → tampilan telaah bukti prodi yang ditugaskan).
- Diberikan seorang Kaprodi Ilmu Komputer login, Maka menu dan form yang tampil otomatis mengikuti instrumen **LAM INFOKOM**; Kaprodi Kimia/Aktuaria mengikuti **LAMSAMA**.
- Diberikan 5 kali percobaan gagal berturut-turut, Maka akun dikunci sementara dan peristiwa dicatat di *audit log*.
- Akun terkunci **terbuka otomatis** setelah masa tunggu (*cooldown*, mis. 15–30 menit) atau melalui **self-service** verifikasi email pemilik akun.
- Untuk kebutuhan segera, **Administrator Sistem/IT** dapat membuka kunci / mereset kata sandi akun peran mana pun, dan tindakan itu tercatat di *audit log*. (Dekan menetapkan peran & cakupan; operasi teknis akun ada pada Administrator Sistem/IT.)

**US-A2 — Batasan akses data**
> Sebagai sistem, saya harus mencegah pengguna mengakses data prodi di luar kewenangannya.

**Acceptance Criteria:**
- Diberikan Kaprodi Kimia mencoba membuka URL/record milik Prodi Ilmu Komputer, Maka sistem menolak dengan pesan "Akses ditolak" dan tidak membocorkan isi data.
- Diberikan Staf Admin ditugaskan ke Prodi Kimia saja, Maka ia tidak melihat daftar data Prodi lain pada pencarian maupun ekspor.
- Diberikan seorang **Asesor** ditugaskan ke Prodi Ilmu Komputer, Maka ia **hanya** dapat membaca data Prodi Ilmu Komputer; upaya mengakses prodi lain ditolak dan dicatat di *audit log*.
- Diberikan **jendela asesmen telah berakhir**, Maka akun asesor otomatis kehilangan akses tanpa perlu dihapus manual.

---

### Epik B — Pengelolaan Data Inti Tridharma (Single Source of Truth)

**US-B1 — Input data sekali pakai banyak**
> Sebagai Kaprodi/Staf Admin Prodi, saya ingin menginput satu data (mis. publikasi) satu kali saja, agar tidak perlu mengetik ulang untuk instrumen berbeda.

**Acceptance Criteria:**
- Diberikan sebuah publikasi dosen diinput, Maka data otomatis terpetakan ke butir penilaian LAM yang relevan tanpa input tambahan.
- Diberikan data yang sama dibutuhkan oleh dua butir kriteria, Maka data cukup tersimpan satu kali dan dirujuk dari kedua butir.
- Ketika pengguna mencoba menyimpan publikasi dengan DOI/judul yang identik, Maka sistem menampilkan peringatan **duplikasi** dan menawarkan "gabungkan" atau "tetap simpan".

**US-B2 — Kelola data Penelitian, PkM, Hibah**
> Sebagai Kaprodi/Staf Admin Prodi, saya ingin mencatat penelitian, PkM, dan hibah beserta atribut tahun, dana, dan dosen pelaksana.

**Acceptance Criteria:**
- Setiap entri wajib memiliki: tahun akademik, prodi, dosen/aktor terkait, dan status verifikasi.
- Diberikan field wajib kosong, Ketika disimpan, Maka sistem menolak dan menyorot field yang kurang.
- Diberikan data tersimpan, Maka ia muncul di dashboard prodi dan pada agregat fakultas (untuk Dekan).

**US-B3 — Lampirkan bukti: unggah berkas atau tautan**
> Sebagai Kaprodi/Staf Admin, saya ingin melampirkan bukti pada setiap data **dengan dua pilihan**: mengunggah berkas, atau memberikan tautan (link) ke lokasi bukti, agar fleksibel untuk dokumen yang sudah tersimpan di repositori/cloud.

**Acceptance Criteria:**
- Setiap bukti dapat berupa **(a) berkas unggahan** (PDF, JPG/PNG, XLSX/CSV, DOCX, dengan batas ukuran yang dikonfigurasi) **atau (b) tautan URL** ke sumber bukti (mis. repositori, Google Drive, SharePoint).
- Untuk tautan, sistem menyimpan metadata (judul, pemilik/sumber, tanggal) dan memvalidasi format URL; opsi penanda akses (publik/terbatas) dapat dicatat.
- Ketika format/ukuran berkas tidak sesuai, Maka unggahan ditolak dengan pesan yang jelas.
- Setiap bukti (berkas maupun tautan) tertaut ke butir kriteria yang relevan dan dapat ditinjau Dekan/Asesor saat validasi/asesmen.
- Satu bukti bersama (mis. fasilitas laboratorium dasar) dapat ditautkan ke beberapa prodi sekaligus melalui penanda "Berlaku untuk" (Ilmu Komputer/Kimia/Sains Aktuaria), sehingga tidak perlu diinput berulang.
- Baik berkas maupun tautan diperiksa modul *link-checker* secara berkala (lihat EC-23): berkas hilang/rusak atau tautan tak terjangkau (mis. 404/akses ditolak) menandai butir terkait sebagai bermasalah.

**US-B4 — Simpan draf & pengisian bertahap (menyicil)**
> Sebagai Kaprodi/Staf Admin, saya ingin menyimpan data sebagai draf dan mengisinya bertahap, karena SIMAK juga alat **monitoring** sehingga wajar bila sebagian data belum lengkap pada satu waktu.

**Acceptance Criteria:**
- Setiap data/butir dapat disimpan sebagai **Draft** kapan saja tanpa harus lengkap; field yang belum terisi tidak memblokir penyimpanan draf.
- Sistem menampilkan status kelengkapan per butir (*Belum Mulai / Draft / Lengkap*) dan persentase kesiapan prodi secara berjalan.
- Pengisian dapat dilanjutkan pada sesi berikutnya tanpa kehilangan progres (*auto-save* + simpan manual).
- Submit untuk validasi tetap memeriksa kelengkapan (lihat US-F3/EC-06), tetapi **pemantauan harian tidak mensyaratkan kelengkapan**.

---

### Epik C — Siklus Penjaminan Mutu PPEPP

**US-C1 — Penetapan (P pertama) butir standar sasaran oleh Dekan**
> Sebagai Dekan, saya ingin menetapkan dan menuliskan butir standar apa yang akan disasar pada siklus ini — dipilih dari katalog Standar yang dikeluarkan unit Satuan Penjaminan Mutu (SPM) kampus — agar seluruh prodi bergerak ke sasaran mutu yang jelas.

**Acceptance Criteria:**
- Sistem menyediakan **katalog Standar & Butir dari SPM** sebagai master data (diinput/diperbarui Staf Admin Fakultas, divalidasi Dekan).
- Pada tahap Penetapan, Dekan memilih butir dari katalog dan mengisi minimal: **nomor butir, isi/pernyataan standar, target/indikator capaian**, dan (bila relevan) periode berlaku serta penanggung jawab.
- Butir yang ditetapkan menjadi acuan resmi siklus; tahap Pelaksanaan–Peningkatan prodi hanya dapat mengacu pada butir yang telah ditetapkan Dekan.
- Dekan dapat menetapkan butir berbeda per prodi bila diperlukan, namun kerangka tahap PPEPP tetap seragam.
- Setiap penetapan/perubahan butir sasaran tercatat berversi di *audit log*.

**US-C2 — Menjalankan siklus PPEPP per standar (Kaprodi)**
> Sebagai Kaprodi, saya ingin mendokumentasikan Pelaksanaan, Evaluasi, Pengendalian, dan Peningkatan atas butir yang telah **ditetapkan Dekan**.

**Acceptance Criteria:**
- Setiap butir sasaran menampilkan 5 tahap PPEPP dengan status: *Belum Mulai / Berjalan / Selesai*; tahap Penetapan ditampilkan **read-only** bagi Kaprodi (isi dari US-C1).
- Diberikan tahap "Evaluasi" diisi temuan, Maka sistem mendorong pembuatan tindak lanjut pada tahap "Pengendalian".
- Diberikan satu siklus selesai, Maka hasil "Peningkatan" dapat diarsipkan sebagai baseline untuk siklus berikutnya.

**US-C3 — Kerangka PPEPP seragam lintas prodi (Dekan)**
> Sebagai Dekan, saya ingin seluruh prodi memakai kerangka PPEPP yang seragam, agar perbandingan antarprodi adil.

**Acceptance Criteria:**
- Template tahapan PPEPP bersifat universal fakultas; perbedaan hanya pada isi, bukan struktur.
- Dekan dapat melihat rekap kemajuan PPEPP semua prodi dalam satu tampilan, termasuk status pencapaian terhadap butir sasaran yang ia tetapkan.

---

### Epik D — Pemetaan & Keluaran Multi-Instrumen

**US-D1 — Lihat data dari sudut pandang instrumen**
> Sebagai Kaprodi, saya ingin melihat seluruh data prodi saya tersusun sesuai kriteria LAM yang berlaku bagi prodi saya.

**Acceptance Criteria:**
- Kaprodi Ilmu Komputer melihat susunan IAPS 2.1 LAM INFOKOM: bagian A Kondisi Eksternal, bagian B Profil UPPS, enam kriteria (Budaya Mutu, Relevansi Pendidikan, Relevansi Penelitian, Relevansi PkM, Akuntabilitas, Diferensiasi Misi), dan Suplemen Program Studi. Tiap butir menampilkan bobot, jenis (Input/Proses/Output), dan tahap PPEPP-nya.
- Kaprodi Kimia & Sains Aktuaria melihat susunan IAPS 3.1 LAMSAMA: 35 indikator dalam enam kriteria (A Tata Kelola dan Penjaminan Mutu, B Pendidikan dan Pengajaran, C Penelitian, D Pengabdian kepada Masyarakat, E Capaian dan Luaran, F Analisis dan Penetapan Program Pengembangan). Tiap indikator menampilkan tingkat minimum per peringkat dan tanda syarat perlu.
- Diberikan sebuah butir kriteria belum memiliki data, Maka butir ditandai "Belum Lengkap" beserta daftar data yang kurang.

**US-D2 — Ekspor dokumen evaluasi diri**
> Sebagai Kaprodi, saya ingin mengekspor laporan evaluasi diri dalam format sesuai LAM saya.

**Acceptance Criteria:**
- Ekspor menghasilkan dokumen terstruktur per kriteria (PDF dan/atau DOCX).
- Data yang diekspor identik dengan basis data inti pada saat ekspor (konsistensi *single source of truth*).
- Metadata ekspor mencantumkan tanggal, prodi, instrumen, dan versi data.

**US-D3 — Form naratif spesifik instrumen**
> Sebagai Kaprodi, saya ingin form evaluasi kualitatif yang sesuai aturan narasi instrumen saya, karena format analisis tiap LAM berbeda meski basis datanya tunggal.

**Acceptance Criteria:**
- Meski basis data inti tunggal, UI form naratif dirender terpisah sesuai template teks instrumen prodi (mis. LAM INFOKOM memiliki butir Kondisi Eksternal berupa analisis lingkungan makro dan mikro beserta peluang dan ancaman; LAMSAMA memiliki kriteria F berupa analisis capaian kinerja dan penetapan program pengembangan).
- Form naratif tidak bersifat generik lintas instrumen; struktur dan panduan pengisian mengikuti butir instrumen terkait.
- Narasi tersimpan otomatis (*auto-save*) agar tidak hilang saat input panjang.
- Narasi hanya dapat disunting Kaprodi. Staf Admin Prodi dan Staf Admin Fakultas hanya dapat membacanya; tugas mereka adalah data dan bukti.

**US-D4 — Generator draf LED berbantuan LLM (offline/online)**
> Sebagai Kaprodi, saya ingin sistem membantu menyusun draf narasi LED dari data yang sudah terkumpul, agar penyusunan lebih cepat tanpa mengetik dari nol.

**Acceptance Criteria:**
- Sistem dapat terhubung ke **model LLM lokal/offline** (*on-premise*) **atau model daring (online) via API** yang endpoint dan kuncinya dikonfigurasi (lihat US-G4).
- Generator menyusun draf per butir dari data inti + bukti + hasil evaluasi; keluaran selalu berstatus **draf** yang wajib ditinjau dan disunting Kaprodi sebelum dipakai.
- Diberikan data sensitif akreditasi, Maka mode **offline** menjadi default yang direkomendasikan; mode online hanya berjalan setelah dikonfigurasi eksplisit dan diberi persetujuan.
- Sistem mencatat sumber draf (model, mode, tanggal) pada metadata narasi untuk ketertelusuran.
- Diberikan koneksi LLM gagal/timeout, Maka Kaprodi tetap dapat menulis manual tanpa kehilangan data (lihat EC-24).
- **Fitur ini opsional**: Kaprodi dapat menyusun seluruh narasi LED secara manual. Memakai atau tidak memakai generator LLM **bukan** syarat untuk submit maupun validasi laporan.

---

### Epik E — Integrasi Hasil Tracer Study & Kepuasan (dari Direktorat Kemahasiswaan)

> **Catatan desain:** Survei kepuasan pemangku kepentingan dan *tracer study* **tidak** diselenggarakan oleh fakultas/prodi, melainkan oleh **Direktorat Kemahasiswaan** tingkat institusi. Karena itu SIMAK tidak menjalankan penyebaran kuesioner; sistem berfungsi sebagai **penerima, pengarsip, dan pemetaan** dokumen hasil yang diberikan direktorat. Rekomendasi penanganan ada pada akhir epik ini.
>
> **Catatan instrumen:** *Tracer study* dan pengukuran kepuasan pemangku kepentingan disebut eksplisit pada IAPS 3.1 LAMSAMA (indikator 31 dan 5). Dua dokumen IAPS 2.1 LAM INFOKOM yang menjadi acuan (Matriks Penilaian dan Kriteria Unggul) tidak menjadikannya butir tersendiri, sehingga untuk Prodi Ilmu Komputer hasilnya dipakai sebagai bukti pendukung.

**US-E1 — Terima & tautkan dokumen hasil tracer/kepuasan**
> Sebagai Staf Admin Fakultas, saya ingin mengunggah atau menautkan dokumen hasil tracer study/kepuasan dari Direktorat Kemahasiswaan, lalu memetakannya ke prodi dan butir kriteria terkait.

**Acceptance Criteria:**
- Dokumen hasil dapat berupa berkas unggahan atau tautan, disertai metadata: **sumber (Direktorat Kemahasiswaan), periode, populasi/jumlah responden, metodologi**.
- Dokumen dapat ditautkan ke satu atau beberapa prodi dan ke butir kriteria LAMSAMA/LAM INFOKOM yang relevan.
- Setelah tertaut, Kaprodi/Dekan dapat **membaca** ringkasan/indikatornya; prodi tidak mengelola kuesioner.

**US-E2 — Gunakan indikator tracer untuk evaluasi**
> Sebagai Kaprodi, saya ingin memanfaatkan indikator dari dokumen tracer (mis. masa tunggu, kesesuaian bidang, kepuasan pengguna) untuk narasi evaluasi diri.

**Acceptance Criteria:**
- Bila direktorat menyediakan data terstruktur (CSV/XLSX), Staf Admin Fakultas dapat mengimpornya agar indikator kunci terhitung per prodi/tahun; bila hanya dokumen naratif/PDF, indikator dicatat manual dari ringkasan resmi.
- Dekan dapat membandingkan indikator tracer antarprodi berdasarkan data yang diterima.
- Butir yang membutuhkan data tracer ditandai "Menunggu dokumen dari Direktorat" bila belum tersedia (lihat EC-25).

**Rekomendasi penanganan di aplikasi:**
- **Jadikan Staf Admin Fakultas sebagai kanal resmi penerima** dokumen dari Direktorat Kemahasiswaan, bukan prodi masing-masing, agar satu dokumen institusi dapat didistribusikan ke beberapa prodi tanpa duplikasi.
- **Opsi lanjutan (versi berikutnya):** sediakan akun **kontributor terbatas** bagi Direktorat Kemahasiswaan yang hanya dapat mengunggah hasil + metadata, tanpa akses ke data akreditasi lain.
- Simpan dokumen sebagai **sumber rujukan tunggal** yang di-*link* oleh butir di beberapa prodi (konsisten dengan prinsip anti-duplikasi).

---

### Epik F — Pemantauan, Validasi & Analisis (Dekan)

**US-F1 — Dashboard holistik UPPS**
> Sebagai Dekan, saya ingin satu dashboard yang menampilkan profil UPPS, kondisi internal/eksternal, dan tata kelola semua prodi.

**Acceptance Criteria:**
- Dashboard menampilkan ringkasan kemajuan tiap prodi (kelengkapan data, kemajuan PPEPP, skor estimasi internal).
- Setiap prodi menampilkan **progress bar kesiapan dokumen (0–100%)** untuk Ilmu Komputer, Kimia, dan Sains Aktuaria.
- Data dapat difilter per tahun akademik dan per prodi.
- Indikator "berisiko" (data kurang/kedaluwarsa, atau skor simulasi di bawah ambang peringkat target) tersorot secara visual (mis. merah/kuning).
- Dekan dapat menelusuri **daftar butir yang masih berstatus Draft atau Belum Lengkap** per prodi, sebagai fungsi monitoring progres berjalan (bukan hanya laporan final).

**US-F2 — Gap analysis & benchmarking antarprodi**
> Sebagai Dekan, saya ingin menganalisis kesenjangan dan membandingkan antarprodi sebelum visitasi.

**Acceptance Criteria:**
- Sistem menyajikan selisih antara capaian dan target per standar/butir.
- Benchmarking menampilkan prodi sejenis secara berdampingan dengan indikator yang setara (mis. rasio dosen, produktivitas penelitian).
- Perbandingan tetap adil meski instrumen berbeda, dengan memakai indikator inti yang dapat disetarakan (bukan skor mentah lintas-LAM).

**US-F3 — Validasi & persetujuan laporan**
> Sebagai Dekan, saya ingin memvalidasi laporan prodi sebelum difinalkan.

**Acceptance Criteria:**
- Diberikan Kaprodi men-submit laporan, Maka status berubah menjadi *Menunggu Validasi* dan Dekan menerima notifikasi.
- Dekan dapat **menyetujui** atau **mengembalikan dengan catatan**; laporan yang dikembalikan kembali ke status *Draft* dengan komentar tampil ke Kaprodi.
- Hanya laporan berstatus *Disetujui* yang dapat diekspor sebagai dokumen final.
- Syarat submit/validasi **tidak** mencakup penggunaan generator LED berbantuan LLM (fitur opsional).

**US-F4 — Simulasi skor & prediksi peringkat**
> Sebagai Dekan/Kaprodi, saya ingin melihat skor estimasi dan prediksi peringkat berdasarkan ambang (*threshold*) masing-masing LAM, agar tahu butir mana yang perlu diperkuat sebelum visitasi.

**Acceptance Criteria:**
- Cara hitung mengikuti instrumen prodi, lalu sistem menampilkan prediksi peringkat.
- **LAM INFOKOM:** sistem menghitung nilai akhir berbobot (skala 400). Di bawah 200 Tidak Terakreditasi; 200 sampai di bawah 321 Terakreditasi; 321 sampai di bawah 361 Unggul 3 tahun; 361 ke atas Unggul 5 tahun. Kedua peringkat Unggul mensyaratkan rerata kriteria Budaya Mutu, Relevansi Pendidikan, dan Relevansi Penelitian masing-masing minimal 3,20 dengan skor butir minimal 3,00; bila syarat ini gagal, prediksinya Terakreditasi.
- **LAMSAMA:** sistem membandingkan tingkat tiap indikator dengan tingkat minimum untuk Unggul 5 tahun, Unggul 2 tahun, dan Terakreditasi, termasuk indikator syarat perlu.
- Diberikan sebuah kriteria berada di bawah ambang target, Maka kriteria tersebut ditandai visual dan muncul dalam daftar prioritas perbaikan.
- Skor ditegaskan sebagai **estimasi internal**, bukan penilaian resmi asesor, dan selalu menyertakan tanggal perhitungan.
- Simulasi tidak membandingkan skor mentah LAMSAMA vs LAM INFOKOM secara langsung (lihat EC-20).

---

### Epik G — Administrasi Sistem

**US-G1 — Manajemen master data (Staf Admin)**
> Sebagai Staf Admin Prodi/Fakultas, saya ingin mengelola data master sesuai cakupan saya (Staf Prodi: data dalam kendali prodi; Staf Fakultas: data tingkat UPPS, katalog Standar SPM, dosen/sarana bersama).

**Acceptance Criteria:**
- Staf Prodi dapat menambah/ubah master data hanya untuk prodi yang ditugaskan; Staf Fakultas mengelola master tingkat fakultas dan data bersama.
- Perubahan master yang dipakai lintas prodi (mis. dosen/sarana bersama) tercermin ke semua prodi terkait.
- Setiap perubahan master data tercatat di *audit log*.

**US-G2 — Manajemen akun & peran (Dekan)**
> Sebagai Dekan, saya ingin mengatur akun dan menetapkan cakupan prodi bagi Kaprodi, Staf Prodi, Staf Fakultas, dan Asesor.

**Acceptance Criteria:**
- Dekan dapat membuat/menonaktifkan akun, mengatur ulang peran, dan menetapkan cakupan prodi/fakultas.
- Perubahan peran berlaku pada sesi login berikutnya pengguna terkait.

**US-G3 — Penugasan butir/dokumen ke staf (Dekan)**
> Sebagai Dekan, saya ingin menentukan butir atau dokumen mana dikerjakan Staf Prodi dan mana yang diserahkan ke Staf Admin Fakultas, karena sebagian butir berada di luar kendali prodi.

**Acceptance Criteria:**
- Dekan dapat memetakan setiap butir/kelompok dokumen ke penanggung jawab: Staf Prodi tertentu atau Staf Fakultas.
- Diberikan sebuah butir ditandai "di luar kendali prodi", Maka butir tersebut muncul di antrean kerja Staf Fakultas, bukan Staf Prodi.
- Papan kerja tiap staf menampilkan hanya butir yang ditugaskan kepadanya, beserta status kelengkapannya.
- Perubahan penugasan tercatat di *audit log* dan langsung memperbarui antrean kerja staf terkait.

**US-G4 — Konfigurasi koneksi LLM (Dekan/Staf Fakultas)**
> Sebagai Dekan (disiapkan Staf Admin Fakultas), saya ingin mengonfigurasi koneksi model LLM untuk generator LED, baik model lokal/offline maupun daring via API.

**Acceptance Criteria:**
- Sistem menyediakan pengaturan: pilih mode **offline (model lokal)** atau **online (endpoint + API key)**; kredensial disimpan terenkripsi.
- Mode default direkomendasikan **offline** demi kerahasiaan data akreditasi; mengaktifkan mode online memerlukan konfirmasi eksplisit Dekan.
- Sistem dapat menguji koneksi (*test connection*) dan menampilkan status aktif/nonaktif.
- Perubahan konfigurasi tercatat di *audit log*.

**US-G5 — Menyusun instrumen dan aturan pemetaan (Staf Admin Fakultas), disetujui Dekan**
> Sebagai Staf Admin Fakultas, saya ingin memuat instrumen akreditasi dan menyusun aturan pemetaan data inti ke butir, lalu mengajukannya ke Dekan, agar sistem selalu memakai konfigurasi yang sudah disetujui.

**Acceptance Criteria:**
- Staf Admin Fakultas dapat memuat versi instrumen (kriteria, butir, rubrik, aturan peringkat) lewat impor atau isian, dan menyusun aturan pemetaan untuk tiap butir.
- Instrumen dan aturan pemetaan berstatus draf sampai disetujui Dekan. Hanya yang sudah disetujui yang dipakai sistem.
- Diberikan aturan pemetaan yang sudah berlaku diubah, Maka aturan lama tetap dipakai sampai perubahan disetujui Dekan (lihat EC-31).
- Setiap pengajuan dan persetujuan tercatat di *audit log*.

---

### Epik H — Asesmen (Asesor, Read-Only)

**US-H1 — Telaah bukti butir per butir**
> Sebagai Asesor, saya ingin menelusuri setiap butir kriteria prodi yang saya nilai beserta buktinya, agar dapat melakukan asesmen tanpa mengubah data apa pun.

**Acceptance Criteria:**
- Asesor memperoleh tampilan khusus (berbeda dari pengguna biasa) yang menyusun data **per butir kriteria** dengan daftar bukti (berkas/tautan) langsung dapat dibuka.
- Seluruh akses asesor bersifat **read-only**; tidak ada tombol tambah/ubah/hapus/submit.
- Yang ditampilkan adalah **versi laporan yang sudah disetujui Dekan**: narasi, skor estimasi, dan bukti sebagaimana saat disetujui, bukan data yang sedang dikerjakan.
- Asesor hanya melihat **satu prodi** yang ditugaskan; data prodi lain tidak terlihat sama sekali.
- Akses hanya aktif selama **jendela asesmen** yang ditetapkan Dekan (US-G2/§3.4) dan tercatat penuh di *audit log*.
- (Opsional) Asesor dapat menandai butir "sudah ditelaah" atau memberi catatan baca yang tidak mengubah data sumber.

---

## 5. Alur Kerja Utama (Core Workflows)

### 5.1 Alur Besar End-to-End (Siklus Akreditasi)

```
[1] Persiapan & Penetapan (P1)
     Staf Admin Fakultas memuat katalog Standar/Butir SPM & master data
     Staf Admin Fakultas menyusun instrumen & aturan pemetaan → disetujui Dekan
     Dekan menetapkan periode + memilih butir sasaran (nomor, isi, target/indikator)
     Dekan memetakan butir ke penanggung jawab (Staf Prodi / Staf Fakultas)
        │
        ▼
[2] Pengumpulan Data Inti
     Kaprodi/Staf Admin input data Tridharma + lampirkan bukti (unggah ATAU tautan)
     Butir di luar kendali prodi dikerjakan Staf Admin Fakultas
     Sistem memetakan otomatis ke butir LAM yang relevan
        │
        ▼
[3] Siklus PPEPP (P2–P5)
     Kaprodi mendokumentasikan Pelaksanaan→Evaluasi→Pengendalian→Peningkatan
                              atas butir yang telah ditetapkan Dekan
        │
        ▼
[4] Integrasi Hasil Tracer/Kepuasan
     Staf Admin Fakultas menerima dokumen dari Direktorat Kemahasiswaan
     → ditautkan ke prodi & butir terkait (prodi hanya membaca)
        │
        ▼
[5] Penyusunan Laporan per Instrumen
     Sistem menyusun data ke format IAPS 3.1 LAMSAMA / IAPS 2.1 LAM INFOKOM
     Kaprodi menulis narasi (staf admin tidak menyunting narasi)
     Generator LED berbantuan LLM (offline/online, OPSIONAL) menyusun draf narasi → ditinjau Kaprodi
     Sistem menandai butir "Belum Lengkap"
     Sistem menghitung skor estimasi internal thd ambang LAM (prediksi peringkat)
        │
        ▼
[6] Submit & Validasi
     Kaprodi submit → Status: Menunggu Validasi
     Dekan: Setujui  ──► lanjut ke [7]
             Kembalikan (dgn catatan) ──► balik ke [2]/[3]
        │
        ▼
[7] Ekspor Dokumen Final
     Dokumen evaluasi diri diekspor per prodi sesuai instrumennya
     (format PDF/Excel siap unggah ke portal nasional masing-masing LAM)
        │
        ▼
[8] Asesmen (Asesor, read-only)
     Setelah laporan Disetujui, Dekan mengaktifkan akses asesor (time-boxed, per prodi)
     Asesor menelaah versi yang disetujui, butir per butir → akses nonaktif saat jendela berakhir
        │
        ▼
[9] Pemantauan Berkelanjutan
     Dekan: gap analysis, benchmarking, pemantauan risiko
     Hasil peningkatan menjadi baseline siklus berikutnya
```

### 5.2 Alur Rinci A — Input Data Tridharma (Kaprodi/Staf Admin)
1. Pengguna memilih modul (Pendidikan / Penelitian / PkM / Tata Kelola); butir yang tampil sesuai penugasan Dekan (Staf Prodi vs Staf Fakultas).
2. Mengisi form data inti (field wajib tervalidasi).
3. Melampirkan bukti: **unggah berkas atau memberi tautan URL** ke sumber bukti.
4. Sistem menjalankan **deteksi duplikasi** (DOI/judul/identitas).
5. Data disimpan sebagai *Draft* → otomatis terpetakan ke butir LAM.
6. Data muncul di dashboard prodi dan agregat fakultas.

### 5.3 Alur Rinci B — Pemetaan Dua Instrumen (Mapping Engine)
1. Staf Admin Fakultas menyusun aturan pemetaan; aturan berlaku setelah disetujui Dekan.
2. Saat data disimpan, sistem membaca aturan pemetaan yang berlaku.
3. Satu record dirujuk oleh satu/lebih butir pada LAMSAMA **dan/atau** LAM INFOKOM.
4. Perubahan satu data memperbarui semua butir yang merujuknya (tanpa duplikasi).
5. Butir tanpa data dirujuk ditandai "Belum Lengkap".

### 5.4 Alur Rinci C — Submit → Validasi → Ekspor
1. Kaprodi menekan **Submit Laporan** (seluruh butir wajib minimal terisi).
2. Status: *Menunggu Validasi*; Dekan ternotifikasi.
3. Dekan meninjau data + bukti:
   - **Setujui** → status *Disetujui*; tombol ekspor aktif.
   - **Kembalikan** → status *Draft*; catatan Dekan tampil per butir ke Kaprodi.
4. Kaprodi memperbaiki → submit ulang (loop sampai disetujui).
5. Kaprodi/Staf Admin/Dekan mengekspor dokumen final sesuai instrumen.

### 5.5 Alur Rinci D — Integrasi Hasil Tracer/Kepuasan (dari Direktorat Kemahasiswaan)
1. Direktorat Kemahasiswaan menyelenggarakan survei/tracer di tingkat institusi (**di luar SIMAK**).
2. Staf Admin Fakultas menerima dokumen hasil resmi → mengunggah/menautkannya ke SIMAK beserta metadata (sumber, periode, populasi, metodologi).
3. Dokumen ditautkan ke prodi dan butir kriteria LAMSAMA/LAM INFOKOM yang relevan.
4. Bila ada data terstruktur, indikator kunci dihitung per prodi/tahun; bila naratif, indikator dicatat dari ringkasan resmi.
5. Kaprodi membaca indikator untuk narasi evaluasi; Dekan membandingkan antarprodi.

### 5.6 Alur Rinci E — Generator LED Berbantuan LLM
1. Kaprodi membuka butir yang datanya telah lengkap, menekan "Susun Draf".
2. Sistem mengirim konteks (data inti + bukti + hasil evaluasi) ke LLM sesuai konfigurasi (offline default / online via API).
3. LLM mengembalikan **draf narasi**; sistem menandainya sebagai draf + metadata sumber (model/mode/tanggal).
4. Kaprodi meninjau, menyunting, dan menyetujui narasi sebelum masuk ke LED.
5. Bila koneksi gagal, sistem memberi tahu dan Kaprodi melanjutkan penulisan manual (EC-24).

### 5.7 Alur Rinci F — Asesmen oleh Asesor (Read-Only)
1. Setelah laporan prodi berstatus *Disetujui*, Dekan mengaktifkan akun asesor untuk prodi tersebut pada jendela asesmen (§3.4).
2. Asesor login → memperoleh tampilan telaah **bukti butir per butir** atas versi laporan yang disetujui.
3. Asesor membuka berkas/tautan bukti; seluruh akses read-only dan tercatat di *audit log*.
4. (Opsional) Asesor menandai butir "sudah ditelaah"/memberi catatan baca.
5. Jendela asesmen berakhir → akses asesor otomatis nonaktif.

---

## 6. Edge Cases dan Alur Pengecualian

### 6.1 Data & Integritas

| ID | Skenario | Perilaku Sistem yang Diharapkan |
|---|---|---|
| EC-01 | **Dosen lintas prodi** (home base Kimia, mengajar di Aktuaria). | Data dosen bersifat *shared*; kontribusinya dihitung di prodi sesuai peran, tanpa dobel-hitung pada agregat fakultas. Aturan atribusi dikonfigurasi. |
| EC-02 | **Publikasi berpenulis >1 dosen lintas prodi.** | Sistem menanyakan atribusi (prodi penanggung jawab) atau membagi sesuai kebijakan; mencegah penghitungan ganda di dashboard fakultas. |
| EC-03 | **Duplikasi data** (DOI/judul sama diinput dua kali). | Peringatan duplikasi + opsi gabungkan/tolak. Tidak boleh ada dua record untuk satu objek yang sama. |
| EC-04 | **Data lintas tahun akademik.** | Setiap data wajib bertahun. Laporan selalu difilter per periode; data di luar periode akreditasi tidak ikut terhitung. |
| EC-05 | **Perubahan data inti setelah sudah terpetakan ke banyak butir.** | Semua butir yang merujuk diperbarui otomatis; jika data dihapus, butir terkait kembali "Belum Lengkap" dan pengguna diperingatkan dampaknya. |

### 6.2 Alur Status & Validasi

| ID | Skenario | Perilaku Sistem yang Diharapkan |
|---|---|---|
| EC-06 | **Submit laporan belum lengkap.** | Submit diblokir; sistem menampilkan daftar butir/field yang masih kurang. |
| EC-07 | **Edit data saat status *Menunggu Validasi*.** | Data dikunci (read-only) untuk Kaprodi/Staf Admin hingga Dekan menyetujui atau mengembalikan; mencegah perubahan di belakang validator. |
| EC-08 | **Dekan mengembalikan laporan.** | Status kembali *Draft*; catatan per butir tampil; versi sebelumnya tersimpan di riwayat (tidak hilang). |
| EC-09 | **Hapus data yang sudah disetujui.** | Ditolak. Data berstatus *Disetujui* hanya bisa diubah setelah laporan dibuka kembali (reopen) oleh Dekan, tercatat di audit log. |
| EC-10 | **Dua Staf Admin mengedit record sama bersamaan (concurrency).** | Penguncian optimistik: penyimpan kedua mendapat peringatan konflik dan opsi muat-ulang versi terbaru sebelum menimpa. |

### 6.3 Peran & Keamanan

| ID | Skenario | Perilaku Sistem yang Diharapkan |
|---|---|---|
| EC-11 | **Kaprodi mencoba akses prodi lain (ganti URL/ID).** | Ditolak ("Akses ditolak"); upaya dicatat di audit log; isi data tidak bocor. |
| EC-12 | **Staf Admin mencoba submit atau approve laporan.** | Ditolak; staf admin tidak punya hak submit/approve (pemisahan tugas). |
| EC-13 | **Penugasan prodi Staf Admin dicabut saat sesi aktif.** | Akses ditutup pada aksi berikutnya/sesi berikutnya; data yang sudah dibuka tidak dapat disimpan ke prodi tersebut. |
| EC-14 | **Instrumen LAM prodi berubah kebijakan (nomenklatur/bobot) di tengah siklus.** | Ditangani lewat konfigurasi Mapping Engine tanpa migrasi ulang data inti. Sistem menyimpan **versi instrumen**: draf berjalan dapat dibekukan pada versi lama, lalu ada fungsi "Migrasi ke Versi Baru" yang memetakan ulang data ke kriteria terbaru **tanpa menghapus narasi** yang sudah ditulis. Versi pemetaan dicatat. |
| EC-26 | **Asesor mencoba akses prodi lain atau di luar jendela asesmen.** | Ditolak total; data prodi lain tidak pernah dimuat. Di luar jendela asesmen, sesi asesor otomatis nonaktif. Semua upaya tercatat di *audit log*. |
| EC-27 | **Butir belum ditetapkan penanggung jawabnya (Staf Prodi/Fakultas).** | Butir masuk antrean "Belum Ditugaskan" yang hanya terlihat Dekan; sistem mengingatkan Dekan agar menetapkan penanggung jawab sebelum pengumpulan data dimulai. |
| EC-28 | **Dekan mengaktifkan asesor saat laporan prodi belum disetujui.** | Ditolak; sistem menampilkan status laporan. Usulan asesor tetap tersimpan dan dapat diaktifkan setelah laporan disetujui. |
| EC-29 | **Laporan dibuka kembali (reopen) saat jendela asesmen masih aktif.** | Dekan diperingatkan bahwa ada asesor aktif. Asesor tetap melihat versi terakhir yang disetujui; perubahan baru tampil hanya setelah diajukan dan disetujui lagi. |
| EC-30 | **Staf Admin mencoba menyunting narasi.** | Ditolak; narasi hanya dapat disunting Kaprodi. Staf tetap dapat mengelola data dan bukti butir tersebut. |
| EC-31 | **Aturan pemetaan atau instrumen diubah tetapi belum disetujui Dekan.** | Sistem tetap memakai versi terakhir yang disetujui; perubahan berstatus draf dan tidak memengaruhi butir sampai disetujui. |

### 6.4 Bukti, Dokumen Eksternal, LLM & Teknis

| ID | Skenario | Perilaku Sistem yang Diharapkan |
|---|---|---|
| EC-15 | **Dokumen tracer/kepuasan belum diterima dari Direktorat Kemahasiswaan.** | Butir terkait ditandai "Menunggu dokumen dari Direktorat"; tidak memblokir butir lain. Dekan melihat daftar butir yang tertunda sumber eksternalnya. |
| EC-16 | **Hasil tracer menunjukkan populasi/responden sangat kecil.** | Sistem menampilkan indikator "data tidak memadai" alih-alih skor menyesatkan; butir ditandai perlu perhatian. |
| EC-17 | **Impor CSV/XLSX tracer dengan format salah.** | Validasi pra-impor; baris bermasalah dilaporkan beserta nomor baris, tanpa membatalkan baris yang valid (atau rollback penuh sesuai pilihan pengguna). |
| EC-18 | **Unggahan bukti melebihi batas / format tak didukung.** | Ditolak dengan pesan spesifik; data teks tetap tersimpan, bukti bisa ditambah menyusul. |
| EC-19 | **Koneksi putus saat input panjang.** | Draft otomatis tersimpan sementara agar input tidak hilang. |
| EC-20 | **Benchmarking antarprodi beda instrumen.** | Perbandingan hanya memakai indikator inti yang setara; sistem tidak membandingkan skor mentah LAMSAMA vs LAM INFOKOM secara langsung agar tidak menyesatkan. |
| EC-23 | **Bukti tidak terjangkau: berkas terhapus/rusak ATAU tautan URL mati/privat (404/403).** | Modul *link-checker* memeriksa berkas **dan** tautan secara berkala. Jika bukti kosong/*null*/tak terjangkau terdeteksi, butir terkait ditandai merah dan **validasi final Dekan diblokir** hingga Staf Admin memperbaiki/mengganti bukti. |
| EC-24 | **Koneksi LLM gagal/timeout, atau kekhawatiran privasi mode online.** | Generator LED gagal ditangani tanpa kehilangan data; Kaprodi dapat menulis manual. Untuk data sensitif, sistem mengutamakan mode **offline**; mode online hanya aktif setelah konfigurasi & persetujuan eksplisit Dekan. Draf LLM selalu wajib ditinjau manusia sebelum dipakai. |

### 6.5 Waktu & Siklus

| ID | Skenario | Perilaku Sistem yang Diharapkan |
|---|---|---|
| EC-21 | **Periode akreditasi berakhir saat laporan belum final.** | Sistem memperingatkan tenggat; Dekan dapat memperpanjang periode; data tetap tersimpan sebagai carry-over. |
| EC-22 | **Memulai siklus PPEPP baru.** | Hasil "Peningkatan" siklus lama menjadi baseline "Penetapan" siklus baru; data historis tetap dapat ditelusuri. |

---

## 7. Kebutuhan Non-Fungsional (Ringkas)

| Aspek | Kebutuhan |
|---|---|
| **Keamanan** | RBAC ketat, isolasi data antarprodi **dan antar-asesor**, akses asesor *time-boxed* read-only, enkripsi kredensial (termasuk API key LLM), audit log untuk aksi sensitif. |
| **Privasi & LLM** | Dukungan model LLM **offline/on-premise** sebagai default untuk data sensitif; mode online via API hanya atas persetujuan Dekan; keluaran LLM selalu ditinjau manusia. |
| **Konfigurabilitas** | Kriteria, bobot, pemetaan LAM, katalog Standar SPM, dan penugasan butir berbasis konfigurasi (tidak *hard-coded*). |
| **Integritas Data** | Satu objek = satu record (single source of truth); referensi, bukan salinan, antarbutir. Bukti dapat berupa berkas atau tautan dan diperiksa *link-checker* berkala. |
| **Ketertelusuran** | Riwayat versi laporan, butir sasaran (Penetapan), penugasan staf, dan perubahan data; siapa mengubah apa dan kapan. |
| **Kinerja** | Dashboard agregat lintas prodi responsif pada volume data beberapa tahun akademik. |
| **Ketersediaan** | Draft otomatis tersimpan; cadangan data berkala. |
| **Usability** | Antarmuka Kaprodi otomatis menyesuaikan instrumen prodinya; papan kerja staf menampilkan hanya butir yang ditugaskan; tampilan asesor berorientasi telaah bukti per butir; bahasa Indonesia. |
| **Interoperabilitas** | Ekspor dokumen (PDF/DOCX) & impor data (CSV/XLSX), termasuk dokumen hasil tracer dari Direktorat Kemahasiswaan; siap integrasi PDDikti/SISTER pada versi berikutnya. |

---

## 8. Lampiran: Glosarium

| Istilah | Keterangan |
|---|---|
| **SIMAK** | Sistem Informasi Manajemen Akreditasi — nama sistem pada dokumen ini. |
| **UPPS** | Unit Pengelola Program Studi — pada konteks ini setingkat Fakultas. |
| **SPM** | Satuan Penjaminan Mutu — unit kampus yang mengeluarkan katalog Standar & butir mutu; menjadi acuan tahap Penetapan (P1). |
| **Asesor** | Peninjau eksternal berakses read-only, terpisah per prodi, aktif hanya selama jendela asesmen, dan hanya melihat versi laporan yang sudah disetujui. |
| **Administrator Sistem/IT** | Pengelola teknis akun & sistem (reset sandi, buka kunci, pemeliharaan); tidak mengakses isi data akreditasi. |
| **Staf Admin Prodi / Fakultas** | Operator data; Staf Prodi untuk butir dalam kendali prodi, Staf Fakultas untuk butir tingkat UPPS & di luar kendali prodi serta penyusunan instrumen dan aturan pemetaan. Keduanya tidak menyunting narasi. |
| **Direktorat Kemahasiswaan** | Unit institusi penyelenggara survei kepuasan & tracer study; SIMAK menerima dokumen hasilnya, bukan menjalankan surveinya. |
| **LLM** | *Large Language Model* — model bahasa pembantu penyusunan draf LED, dapat dijalankan offline (lokal) atau online (via API). |
| **LAMSAMA** | Lembaga Akreditasi Mandiri Sains Alam dan Ilmu Formal. Instrumen IAPS 3.1: 35 indikator dalam 6 kriteria (A–F), tanpa bobot. Dipakai Prodi Kimia & Sains Aktuaria. |
| **LAM INFOKOM** | Lembaga Akreditasi Mandiri Informatika dan Komputer. Instrumen IAPS 2.1: bagian A Kondisi Eksternal, B Profil UPPS, 6 kriteria (Budaya Mutu, Relevansi Pendidikan, Relevansi Penelitian, Relevansi PkM, Akuntabilitas, Diferensiasi Misi), dan Suplemen; berbobot total 400. Dipakai Prodi Ilmu Komputer. |
| **IAPS** | Instrumen Akreditasi Program Studi. |
| **Syarat perlu** | Indikator yang wajib mencapai tingkat tertentu agar suatu peringkat dapat diperoleh. |
| **Cuplikan laporan** | Salinan isi laporan pada saat diajukan. Cuplikan dari pengajuan yang disetujui adalah versi yang dilihat asesor. |
| **PPEPP** | Siklus penjaminan mutu: Penetapan, Pelaksanaan, Evaluasi, Pengendalian, Peningkatan. |
| **SPMI** | Sistem Penjaminan Mutu Internal. |
| **Tridharma** | Pendidikan, Penelitian, dan Pengabdian kepada Masyarakat (ditambah Tata Kelola). |
| **PkM** | Pengabdian kepada Masyarakat. |
| **Tracer Study** | Studi pelacakan lulusan (masa tunggu, kesesuaian bidang, kepuasan pengguna). |
| **Single Source of Truth** | Prinsip satu basis data tunggal sebagai sumber kebenaran semua laporan. |
| **Mapping Engine** | Komponen yang memetakan data inti ke butir penilaian tiap LAM. Aturannya disusun Staf Admin Fakultas dan disetujui Dekan. |
| **SoD** | Separation of Duties — pemisahan peran pembuat dan pemvalidasi. |
| **RBAC** | Role-Based Access Control — kontrol akses berbasis peran. |
| **LED** | Laporan Evaluasi Diri — dokumen evaluasi diri yang disusun per prodi sesuai instrumen LAM. |
| **Link-checker** | Modul pemeriksa berkala yang mendeteksi bukti tak terjangkau, baik berkas hilang/rusak maupun tautan URL mati/privat. |

---

*Dokumen ini adalah draf SKPL v1.1 untuk direviu bersama Dekan, para Kaprodi, Staf Admin (Prodi & Fakultas), Administrator Sistem/IT, dan Satuan/Gugus Penjaminan Mutu sebelum masuk tahap desain teknis.*
