# SIMAK — Sistem Informasi Manajemen Akreditasi

Satu basis data, dua instrumen akreditasi: **IAPS 3.1 LAMSAMA** (Kimia, Sains Aktuaria) dan **IAPS 2.1 LAM INFOKOM** (Ilmu Komputer).
Data Tridharma diinput sekali, dipetakan otomatis ke butir kedua instrumen lewat *Mapping Engine* berbasis konfigurasi, lalu disusun menjadi
Laporan Evaluasi Diri (LED) dengan siklus PPEPP, validasi Dekan, dan telaah bukti asesor yang terkendali.

Spesifikasi lengkap ada di [`docs/`](docs/README.md): SKPL/SRS, skema basis data, struktur backend, dan spesifikasi API.

## Mulai cepat

Langkah di bawah berlaku untuk mesin baru. Semua perintah dijalankan dari folder proyek (tempat `Makefile` berada). Jalankan `make` tanpa argumen untuk melihat daftar target.

### Prasyarat

| Perangkat | Keterangan |
|---|---|
| Docker + Docker Compose | Compose ≥ 2.24 |
| `make` | Hanya pintasan; tiap target bisa dijalankan manual (lihat `Makefile`) |
| Port `8088` bebas | Bila terpakai, ubah `HTTP_PORT`, `APP_BASE_URL`, dan `MINIO_PUBLIC_ENDPOINT` di `.env` setelah langkah 1 |
| [uv](https://docs.astral.sh/uv/) | Hanya untuk mengembangkan/menguji backend di luar Docker |

### Jalur A: mencoba dengan data contoh (pengembangan)

1. **Jalankan semua layanan**
   ```bash
   make naik
   ```
   Pertama kali, perintah ini membuat `.env` dari `.env.example` dengan rahasia acak, membangun image, menjalankan migrasi, dan memuat data referensi.
   Tunggu sampai selesai (beberapa menit untuk build pertama). Periksa: `curl http://localhost:8088/api/v1/health`.

2. **Muat data contoh**
   ```bash
   make seed-demo
   ```
   Perintah ini membuat akun untuk semua peran (tabel di bawah), instrumen demo, dan data Tridharma contoh.
   **Kata sandi acak dicetak sekali di terminal** — salin saat itu juga; kata sandi tidak disimpan di berkas mana pun.
   Untuk menentukan sendiri: `make seed-demo DEMO_PASSWORD='sandi-pilihan-anda'` (atau isi `DEMO_PASSWORD` di `.env`).

3. **Buka aplikasi** di **http://localhost:8088** dan masuk dengan salah satu email di tabel, memakai kata sandi dari langkah 2.
   Dokumentasi API interaktif: http://localhost:8088/api/v1/docs.

Akun demo (satu kata sandi yang sama untuk semuanya):

| Email | Peran | Cakupan |
|---|---|---|
| `dekan@simak.test` | Dekan | Fakultas |
| `staf.fakultas@simak.test` | Staf Admin Fakultas | Fakultas |
| `admin.it@simak.test` | Administrator Sistem/IT | Sistem (tanpa akses konten) |
| `kaprodi.ilkom@simak.test` | Kaprodi | Ilmu Komputer |
| `kaprodi.kimia@simak.test` | Kaprodi | Kimia |
| `kaprodi.aktuaria@simak.test` | Kaprodi | Sains Aktuaria |
| `staf.ilkom@simak.test`, `staf.kimia@simak.test`, `staf.aktuaria@simak.test` | Staf Admin Prodi | Prodi masing-masing |
| `asesor.ilkom@simak.test` | Asesor | Belum punya penugasan (lihat catatan) |

Catatan:
- Kata sandi hanya diterapkan saat akun **pertama kali dibuat**. Menjalankan `make seed-demo` lagi tidak mengubahnya (dan perintah akan memberi tahu). Bila lupa, ulangi dari awal dengan `make reset` lalu langkah 1–2.
- Akun asesor baru dapat melihat laporan setelah prodi mengajukan laporan, Kaprodi mengusulkan asesor (menu **Usulan asesor**), dan Dekan menyetujui penugasan berjendela waktu.

### Jalur B: pemakaian nyata (tanpa data contoh)

1. `make naik` (sama seperti di atas).
2. Buat akun Dekan pertama; kata sandi ditanyakan di terminal:
   ```bash
   make buat-dekan EMAIL=dekan@kampus.ac.id NAMA="Prof. Nama Dekan"
   ```
3. Masuk sebagai Dekan (kata sandi sementara wajib diganti saat masuk pertama), lalu buat akun lain dan penugasan perannya di menu **Akun & penugasan**.
4. Staf Admin Fakultas memuat instrumen resmi lewat **Instrumen & pemetaan → Impor instrumen (XLSX)**; Dekan menyetujui dan mengaktifkannya.

### Perintah sehari-hari

| Perintah | Fungsi |
|---|---|
| `make log` | Ikuti log api dan worker |
| `make turun` | Hentikan semua layanan, data tetap |
| `make naik` | Jalankan lagi (data tetap) |
| `make reset` | Hentikan dan **hapus seluruh data**; setelahnya mulai lagi dari langkah 1 |

### Bila ada masalah

- *Port sudah dipakai*: ubah `HTTP_PORT` (dan `APP_BASE_URL`, `MINIO_PUBLIC_ENDPOINT`) di `.env`, lalu `make naik`.
- *`make` tidak ada*: jalankan padanannya, mis. `docker compose up -d --build` dan `docker compose exec -T api python -m app.cli seed-demo` (`.env` dibuat manual: `cp .env.example .env && python3 scripts/buat_rahasia.py .env`).
- *Lupa kata sandi demo*: `make reset`, `make naik`, `make seed-demo`.
- *Email (reset sandi) saat SMTP belum diatur*: isi email hanya tercatat di log worker (`make log`).

### Produksi

Isi `.env` dengan rahasia produksi, letakkan sertifikat di `nginx/tls/`, lalu
`docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` dan buat Dekan pertama dengan `make buat-dekan`. Jangan menjalankan `seed-demo` di produksi.

### Dipasang di sub-path (mis. `https://kampus.ac.id/simak/`)

Bila SIMAK berada di balik proxy lain pada sub-path, atur satu variabel di `.env`, lalu bangun ulang (frontend menanam sub-path saat build):

```bash
BASE_PATH=/simak
APP_BASE_URL=https://kampus.ac.id/simak     # dipakai untuk tautan di surel
MINIO_PUBLIC_ENDPOINT=kampus.ac.id          # hanya host; prefiks disisipkan otomatis ke URL unggah/unduh
MINIO_PUBLIC_SECURE=true
COOKIE_SECURE=true                          # bila diakses lewat HTTPS
```

`make naik` menerapkannya. Kosongkan `BASE_PATH` untuk kembali melayani dari akar. Dengan `BASE_PATH` terisi, alamat akar (`http://host:8088/`) tidak lagi dipakai; gunakan `http://host:8088/simak/`.

Proxy di depan boleh **melepas** prefiks (`proxy_pass http://10.10.72.50:8088/;`) atau **meneruskannya**; keduanya diterima. Yang wajib: teruskan `Host` asli
(tanda tangan URL MinIO mencakup host) dan izinkan unggahan besar. Contoh:

```nginx
location = /simak { return 301 /simak/; }
location /simak/ {
    proxy_pass http://10.10.72.50:8088;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    client_max_body_size 30m;
    proxy_request_buffering off;
}
```

## Arsitektur

Backend adalah **monolit modular** (satu kode, satu basis data, batas modul ditegakkan otomatis) yang dijalankan sebagai beberapa **kontainer** terpisah:

| Layanan | Isi | Catatan |
|---|---|---|
| `nginx` | Reverse proxy | Satu-satunya pintu ke luar; `/api` → api, `/simak-bukti` → MinIO (URL bertanda tangan), selainnya → frontend |
| `frontend` | React + Vite, disajikan Nginx | Gaya visual mengikuti cdscan.universitaspertamina.ac.id |
| `api` | FastAPI (Uvicorn) | Menjalankan migrasi Alembic dan `seed-referensi` saat start |
| `worker` / `beat` | Celery | Ekspor DOCX/PDF/XLSX, draf LLM, link-checker, indikator & simulasi malam, pengingat tenggat |
| `postgres` | PostgreSQL 16 | Skema dari `db/schema.sql` (satu sumber DDL) |
| `redis` | Broker Celery | |
| `minio` | Penyimpanan berkas bukti & hasil ekspor | Bucket privat; akses lewat URL sementara |
| `llm` *(profil `llm`)* | Ollama | Opsional, untuk mode LLM offline |

```
simak/
├── backend/          FastAPI (uv). app/core, app/modules/<domain>, app/infrastructure, app/worker, tests/
├── frontend/         Vite + React + TypeScript. src/features/<fitur>, src/shared (api, auth, ui)
├── db/               schema.sql (DDL) dan seed.sql (kerangka instrumen) — dijalankan migrasi Alembic
├── docs/             SRS dan dokumen arsitektur (lihat docs/README.md)
├── nginx/            konfigurasi proxy (dev) dan nginx/prod (TLS)
├── scripts/          pembantu (pembuat rahasia .env)
├── docker-compose.yml · docker-compose.prod.yml · Makefile · .env.example
```

Modul backend (`backend/app/modules/`): `auth`, `pengguna`, `referensi`, `instrumen`, `pemetaan` (runtime Mapping Engine), `siklus`, `tridharma`,
`bukti`, `ppepp`, `dokumen_eksternal`, `laporan`, `penilaian`, `asesmen`, `llm`, `notifikasi`, `audit`.
Modul beraturan bisnis berlapis `domain → application → infrastructure/api`; modul CRUD memakai bentuk ringkas (`tridharma` memakai satu
registri sumber daya, menambah sumber baru = menambah satu entri `Spec`). Antarmodul hanya lewat `public.py`; aturan ini diuji otomatis
(`tests/unit/test_arsitektur.py`).

## Peran dan hak akses

Dekan · Kaprodi · Staf Admin Prodi · Staf Admin Fakultas · Asesor · Administrator Sistem/IT — sesuai matriks SKPL §3.2. Hak akses dihitung
di server dari penugasan peran aktif; klien tidak pernah mengirim peran. Isolasi antarprodi, pemisahan tugas (penyusun ≠ penyetuju), narasi hanya
oleh Kaprodi, asesor hanya-baca pada **versi laporan yang disetujui** dan berjendela waktu, serta Admin IT tanpa akses konten semuanya ditegakkan
di use case dan diuji per peran.

Admin IT mengelola akun: membuat pengguna beserta peran dan prodinya, menetapkan sandi sementara (pengguna wajib menggantinya saat masuk), membuka kunci, dan menonaktifkan.
Pagar pemisahan tugas: Admin IT dapat mengganti alamat surel semua akun, termasuk akunnya sendiri (surel lama dan baru tercatat di audit). Admin IT tidak dapat menetapkan atau mencabut peran Dekan (tetapi dapat mengatur sandi sementara akun Dekan yang lupa sandi; Dekan wajib menggantinya saat masuk), dan asesor dari Admin IT hanya berstatus usulan sampai Dekan menyetujui. Semua tindakan tercatat di log audit.

## Data awal

`make naik` memuat `db/seed.sql` (fakultas, LAM, tiga prodi, kerangka kriteria dan peringkat, satu butir contoh per instrumen). Instrumen itu berstatus **draf**.
Butir/rubrik resmi IAPS dimuat Staf Admin Fakultas lewat **Instrumen & pemetaan → Impor instrumen (XLSX)** (templat tersedia di halaman itu), lalu disetujui Dekan.
### Mengisi data inti lewat impor

Di setiap halaman **Data inti Tridharma** (Dosen, Mahasiswa, Lulusan, dst.) klik **Impor CSV/XLSX**, lalu:

1. Klik **Unduh templat XLSX** (atau CSV). Buka lembar `petunjuk` untuk arti tiap kolom dan `prodi`/`tahun_akademik` untuk kode yang sah.
2. Isi lembar `data` mulai baris 2; jangan mengubah judul kolom. Kolom oranye wajib diisi.
3. Simpan, unggah di jendela impor. Baris bermasalah dilaporkan dengan nomornya; centang "Batalkan semuanya" bila ingin semua-atau-tidak-sama-sekali.

Hanya Staf Admin Prodi dan Staf Admin Fakultas yang dapat mengimpor. Impor indikator tracer/kepuasan (Staf Admin Fakultas) memakai alur yang sama di halaman **Tracer & kepuasan**.

`make seed-demo` membuat versi terpisah `3.1-demo` dan `2.1-demo` (teks butir generik, bukan isi resmi) agar bisa mencoba alur penuh tanpa mengotori instrumen resmi.

## Pengembangan dan pengujian

```bash
make uji-unit      # 64 uji unit (aturan domain, penilai peringkat, arsitektur) — tanpa basis data
make uji           # + 71 uji API terhadap PostgreSQL sungguhan (matriks peran, alur laporan, EC-xx SKPL)
make lint          # ruff
make tipe-fe       # tsc frontend lewat Docker
```

Backend: `cd backend && uv sync && uv run uvicorn app.main:create_app --factory --reload` (set `DATABASE_URL`, `REDIS_URL`; lihat `.env.example`).
Frontend: `cd frontend && npm install && npm run dev` (proxy `/api` ke `localhost:8088`).

## Keputusan desain dan simpangan dari dokumen

- **"Microservices"**: dokumen arsitektur memutuskan monolit modular; kebutuhan Docker dipenuhi dengan memisahkan proses (api, worker, beat, frontend, proxy, penyimpanan) ke kontainer sendiri. Modul sudah berbatas jelas bila kelak ada yang perlu dipisah.
- **Frontend** memakai CSS token buatan sendiri (mengikuti cdscan), bukan Tailwind + shadcn/ui yang disebut di dokumen — agar tampilan setia pada gaya rujukan tanpa dependensi UI.
- **Cuplikan laporan** disusun sinkron saat pengajuan (ukurannya kecil), bukan lewat tugas Celery; ekspor dokumen, draf LLM, dan link-checker tetap di Celery.
- **Templat impor** diunduh dari jendela impor tiap halaman data (juga impor indikator eksternal dan impor instrumen). Kolomnya dibangkitkan dari skema validasi, jadi selalu sesuai aturan. Rujukan prodi dan tahun akademik memakai kode yang terbaca (`KIMIA`, `2025/2026`), bukan UUID.
- **Impor** CSV/XLSX diproses sinkron dan mengembalikan laporan baris (bentuk respons sama dengan tugas `202` pada spesifikasi).
- **MinIO** memakai image Chainguard (`chainguard/minio`) karena image resmi `minio/minio` tidak tersedia di Docker Hub; ganti di `docker-compose.yml` bila perlu.
- **Aturan LAMSAMA**: dokumen hanya memberi ambang per butir + tanda syarat perlu; penilai menganggap peringkat tercapai bila semua ambangnya terpenuhi (toleransi dapat diatur lewat `syarat.toleransi` pada peringkat). Sesuaikan bila pedoman resmi menetapkan aturan agregasi lain.
- **Skor selalu berlabel estimasi internal**; benchmarking hanya memakai indikator inti yang setara (EC-20).

## Keterbatasan yang diketahui

- Integrasi PDDikti/SISTER dan akun kontributor Direktorat Kemahasiswaan sengaja di luar lingkup v1.0 (SKPL §1.3, Epik E).
- Frontend lolos pemeriksaan tipe dan build, dan halaman utama diperiksa visual; alur formulir belum diuji end-to-end di peramban otomatis. Alur bisnis yang sama diuji lewat API.
- Kunci enkripsi API LLM bersumber dari `LLM_ENCRYPTION_KEY`; rotasi kunci belum diotomatisasi.
