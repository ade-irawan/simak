# SIMAK — Spesifikasi API

Dokumen 3 dari 3 · Arsitektur awal Sistem Informasi Manajemen Akreditasi

Dokumen ini menetapkan kontrak API utama. Skema OpenAPI lengkap dihasilkan otomatis oleh FastAPI dari kode (`/api/v1/openapi.json`, Swagger UI di `/api/v1/docs`), sehingga tidak ditulis tangan di sini.

---

## 1. Konvensi

| Hal | Aturan |
|---|---|
| Alamat dasar | `/api/v1` |
| Format | JSON, UTF-8. Waktu dalam ISO 8601 dengan zona waktu |
| Autentikasi | `Authorization: Bearer <access_token>` (JWT, berlaku 15 menit) |
| Token penyegar | Cookie `HttpOnly; Secure; SameSite=Strict`, dirotasi pada setiap penyegaran |
| Penamaan | Nama sumber daya dan kolom domain berbahasa Indonesia sesuai skema basis data; parameter teknis (`page`, `sort`) berbahasa Inggris |
| Hak akses | Dihitung di server dari seluruh penugasan peran aktif milik pengguna. Klien tidak pernah mengirim peran |

### Kode peran

| Kode | Peran |
|---|---|
| D | Dekan |
| K | Kaprodi |
| SP | Staf Admin Prodi |
| SF | Staf Admin Fakultas |
| A | Asesor |
| IT | Administrator Sistem/IT |

Tanda ¹ berarti hanya untuk prodi atau butir yang ditugaskan Dekan kepada pengguna tersebut. K dan SP selalu terbatas pada prodinya sendiri; A terbatas pada satu prodi selama jendela asesmen.

### Daftar dan penomoran halaman

Parameter: `page` (bawaan 1), `per_page` (bawaan 20, maksimal 100), `sort` (misalnya `-updated_at`), `q` (pencarian teks).

```json
{
  "data": [],
  "meta": { "page": 1, "per_page": 20, "total": 57 }
}
```

Sumber daya tunggal dikembalikan langsung tanpa pembungkus.

### Galat

```json
{
  "error": {
    "code": "AKSES_DITOLAK",
    "message": "Akses ditolak.",
    "details": [],
    "request_id": "01JABCDXYZ"
  }
}
```

| Status | Kode galat | Arti |
|---|---|---|
| 400 | `PERMINTAAN_TIDAK_SAH` | Bentuk permintaan salah |
| 401 | `TIDAK_TERAUTENTIKASI`, `KREDENSIAL_SALAH` | Token tidak ada, kedaluwarsa, atau login gagal |
| 403 | `AKSES_DITOLAK` | Di luar peran atau cakupan prodi. Dicatat di log audit, tanpa membocorkan isi data |
| 404 | `TIDAK_DITEMUKAN` | |
| 409 | `KONFLIK_VERSI` | `row_version` tidak cocok; respons memuat data terbaru (EC-10) |
| 409 | `DUPLIKAT` | Data serupa sudah ada; respons memuat kandidatnya (EC-03) |
| 409 | `LAPORAN_TERKUNCI` | Siklus sedang menunggu validasi atau sudah disetujui (EC-07, EC-09) |
| 409 | `BUKTI_BERMASALAH` | Ada bukti tidak terjangkau (EC-23) |
| 409 | `LAPORAN_BELUM_DISETUJUI` | Asesor belum dapat diaktifkan karena laporan prodi belum disetujui (EC-28) |
| 422 | `VALIDASI_GAGAL` | Isian tidak sah; `details` memuat kolom yang salah |
| 422 | `LAPORAN_BELUM_LENGKAP` | `details` memuat butir yang kurang (EC-06) |
| 423 | `AKUN_TERKUNCI` | Terkunci sementara setelah lima kali gagal login |
| 503 | `LLM_TIDAK_TERSEDIA` | Tidak ada konfigurasi LLM aktif atau koneksi gagal (EC-24) |

### Penguncian optimistik

Sumber daya yang dapat disunting bersama membawa `row_version`. Klien mengirimkannya kembali pada `PATCH` atau `PUT`. Bila berbeda dari nilai di server, jawabannya `409 KONFLIK_VERSI`.

### Tugas latar

Operasi lama (ekspor, impor, draf LLM) menjawab `202 Accepted` dengan sumber daya tugas berisi `id` dan `status` (`antre`, `diproses`, `selesai`, `gagal`). Klien memantau lewat `GET` pada sumber daya itu.

---

## 2. Autentikasi

| Method | Endpoint | Peran | Fungsi |
|---|---|---|---|
| POST | `/auth/login` | publik | Masuk |
| POST | `/auth/refresh` | cookie | Menukar token penyegar dengan token akses baru |
| POST | `/auth/logout` | semua | Mencabut token penyegar |
| GET | `/auth/me` | semua | Profil, peran aktif, cakupan prodi, instrumen |
| PUT | `/auth/sandi` | semua | Mengganti sandi sendiri |
| POST | `/auth/lupa-sandi` | publik | Mengirim tautan reset ke surel. Selalu menjawab `202` |
| POST | `/auth/reset-sandi` | publik (token) | Menetapkan sandi baru |
| POST | `/auth/buka-kunci/minta` | publik | Mengirim tautan buka kunci swalayan. Selalu menjawab `202` |
| POST | `/auth/buka-kunci` | publik (token) | Membuka kunci akun sendiri |

### `POST /auth/login`

Permintaan:

```json
{ "email": "kaprodi.kimia@kampus.ac.id", "password": "••••••••" }
```

Respons `200`:

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 900,
  "pengguna": {
    "id": "5b0c7a52-0d0e-4a0f-9a36-0c7c1f2a9d11",
    "nama": "Dr. Contoh Nama",
    "email": "kaprodi.kimia@kampus.ac.id",
    "wajib_ganti_sandi": false,
    "peran": [
      {
        "penugasan_id": "0f4e3c1a-77b1-4f0e-8d55-2f3f8f0b6a10",
        "peran": "kaprodi",
        "prodi": { "id": "9fd15e1d-6bf8-4663-b0c7-ed5a532bc384", "kode": "KIMIA", "nama": "Kimia" },
        "instrumen": { "lam": "LAMSAMA", "kode_versi": "3.1" },
        "berlaku_sampai": null
      }
    ]
  }
}
```

Respons `401` (sandi salah):

```json
{ "error": { "code": "KREDENSIAL_SALAH", "message": "Email atau sandi salah.", "details": [{ "sisa_percobaan": 2 }] } }
```

Respons `423` (terkunci):

```json
{
  "error": {
    "code": "AKUN_TERKUNCI",
    "message": "Akun terkunci sementara. Coba lagi setelah waktu berikut, atau buka kunci lewat surel.",
    "details": [{ "terkunci_sampai": "2026-10-04T20:45:00+07:00" }]
  }
}
```

---

## 3. Pengguna dan peran

| Method | Endpoint | Peran | Fungsi |
|---|---|---|---|
| GET | `/pengguna` | D, IT | Daftar akun. Saringan: `peran`, `prodi_id`, `status`, `terkunci` |
| POST | `/pengguna` | D | Membuat akun beserta penugasan awal |
| GET | `/pengguna/{id}` | D, IT | Rincian akun |
| PATCH | `/pengguna/{id}` | D | Mengubah nama atau status |
| POST | `/pengguna/{id}/buka-kunci` | IT | Membuka kunci akun |
| POST | `/pengguna/{id}/reset-sandi` | IT | Mengirim tautan reset sandi |
| POST | `/pengguna/{id}/nonaktifkan` | D, IT | Menonaktifkan akun |
| GET | `/penugasan-peran` | D | Daftar penugasan. Saringan: `peran`, `prodi_id`, `status` |
| POST | `/penugasan-peran` | D; K hanya untuk mengusulkan asesor | Menambah penugasan |
| POST | `/penugasan-peran/{id}/setujui` | D | Mengaktifkan usulan asesor dan menetapkan jendela asesmen |
| POST | `/penugasan-peran/{id}/cabut` | D | Mencabut penugasan |

### `POST /pengguna/{id}/buka-kunci`

Permintaan:

```json
{ "alasan": "Permintaan pengguna lewat telepon, identitas sudah diverifikasi." }
```

Respons `200`:

```json
{ "id": "5b0c7a52-0d0e-4a0f-9a36-0c7c1f2a9d11", "status": "aktif", "terkunci_sampai": null, "jumlah_gagal_login": 0 }
```

Tindakan ini dicatat di log audit beserta alasannya.

### `POST /penugasan-peran` (mengaktifkan asesor)

Permintaan:

```json
{
  "pengguna_id": "c1a2b3d4-1111-4222-8333-444455556666",
  "peran": "asesor",
  "prodi_id": "9fd15e1d-6bf8-4663-b0c7-ed5a532bc384",
  "berlaku_mulai": "2026-11-10T00:00:00+07:00",
  "berlaku_sampai": "2026-11-14T23:59:59+07:00",
  "catatan": "Asesmen lapangan Prodi Kimia"
}
```

Respons `201`:

```json
{
  "id": "7d2f1e90-aaaa-4bbb-8ccc-0123456789ab",
  "pengguna": { "id": "c1a2b3d4-1111-4222-8333-444455556666", "nama": "Prof. Asesor Satu" },
  "peran": "asesor",
  "prodi": { "id": "9fd15e1d-6bf8-4663-b0c7-ed5a532bc384", "kode": "KIMIA", "nama": "Kimia" },
  "status": "aktif",
  "berlaku_mulai": "2026-11-10T00:00:00+07:00",
  "berlaku_sampai": "2026-11-14T23:59:59+07:00",
  "disetujui_oleh": { "id": "aa11bb22-0000-4000-8000-000000000001", "nama": "Dekan" }
}
```

Bila pemanggil adalah Kaprodi, penugasan tersimpan dengan `status: "diusulkan"` dan baru aktif setelah Dekan memanggil `/setujui`.

Asesor hanya dapat diaktifkan bila laporan prodi tersebut berstatus `disetujui`. Selain itu jawabannya `409 LAPORAN_BELUM_DISETUJUI`, dan usulan tetap tersimpan (EC-28).

---

## 4. Referensi dan instrumen

| Method | Endpoint | Peran | Fungsi |
|---|---|---|---|
| GET | `/prodi` | D, K, SP, SF, IT | Daftar prodi sesuai cakupan |
| GET | `/tahun-akademik` | semua kecuali A | Daftar tahun akademik |
| POST, PATCH | `/tahun-akademik`, `/tahun-akademik/{id}` | SF | Mengelola tahun akademik |
| GET | `/instrumen` | D, K, SP, SF | Daftar versi instrumen |
| GET | `/instrumen/{id}` | D, K, SP, SF | Versi instrumen, kriteria, dan aturan peringkat |
| GET | `/instrumen/{id}/butir` | D, K, SP, SF | Daftar butir. Saringan: `kriteria`, `tahap_ppepp`, `jenis_ipo` |
| GET | `/butir-instrumen/{id}` | D, K, SP, SF | Butir, rubrik, ambang, skema narasi |
| POST | `/instrumen/impor` | SF | Mengimpor versi instrumen dari XLSX sebagai draf (`202`) |
| PATCH | `/butir-instrumen/{id}` | SF | Menyunting butir, rubrik, atau skema narasi pada instrumen berstatus draf |
| POST | `/instrumen/{id}/aktifkan` | D | Menyetujui dan mengaktifkan versi instrumen |
| GET | `/instrumen/{id}/pemetaan` | D, K, SF | Aturan Mapping Engine beserta status persetujuannya |
| PUT | `/butir-instrumen/{id}/pemetaan` | SF | Menyusun aturan pemetaan satu butir; tersimpan sebagai draf |
| POST | `/pemetaan/{id}/setujui` | D | Menyetujui aturan pemetaan; aturan lama digantikan |

Instrumen dan aturan pemetaan disusun Staf Admin Fakultas dan baru dipakai sistem setelah disetujui Dekan (US-G5). Selama perubahan belum disetujui, versi terakhir yang disetujui tetap berlaku (EC-31).

### `GET /instrumen/{id}`

Respons `200`:

```json
{
  "id": "3a6f0f8e-2222-4333-8444-555566667777",
  "lam": { "kode": "LAM_INFOKOM", "nama": "Lembaga Akreditasi Mandiri Informatika dan Komputer" },
  "kode_versi": "2.1",
  "nama": "IAPS 2.1 LAM INFOKOM - Program Sarjana",
  "status": "aktif",
  "skor_maks": 4,
  "label_skor": { "4": "Sangat Baik", "3": "Baik", "2": "Cukup", "1": "Kurang" },
  "nilai_akhir_maks": 400,
  "kriteria": [
    { "kode": "A", "nama": "Kondisi Eksternal", "bobot": 4, "jumlah_butir": 1 },
    { "kode": "1", "nama": "Budaya Mutu", "bobot": 40, "jumlah_butir": 10 },
    { "kode": "2", "nama": "Relevansi Pendidikan", "bobot": 120, "jumlah_butir": 20 }
  ],
  "peringkat": [
    { "kode": "unggul_5", "nama": "Unggul (berlaku 5 tahun)", "nilai_akhir_min": 361, "nilai_akhir_maks": null,
      "syarat": { "kriteria": ["1", "2", "3"], "rerata_kriteria_min": 3.2, "skor_butir_min": 3.0 } },
    { "kode": "unggul_3", "nama": "Unggul (berlaku 3 tahun)", "nilai_akhir_min": 321, "nilai_akhir_maks": 361,
      "syarat": { "kriteria": ["1", "2", "3"], "rerata_kriteria_min": 3.2, "skor_butir_min": 3.0 } },
    { "kode": "terakreditasi", "nama": "Terakreditasi", "nilai_akhir_min": 200, "nilai_akhir_maks": null, "syarat": {} }
  ]
}
```

---

## 5. Siklus akreditasi dan pengerjaan butir

| Method | Endpoint | Peran | Fungsi |
|---|---|---|---|
| GET | `/siklus` | D, K, SP, SF | Daftar siklus sesuai cakupan |
| POST | `/siklus` | D | Membuka siklus; sistem membuat `butir_siklus` untuk setiap butir instrumen |
| GET | `/siklus/{id}` | D, K, SP, SF | Rincian dan ringkasan kesiapan |
| PATCH | `/siklus/{id}` | D | Mengubah tenggat, target peringkat, status |
| POST | `/siklus/{id}/migrasi-instrumen` | D | Memindahkan siklus ke versi instrumen baru tanpa menghapus narasi (EC-14) |
| GET | `/siklus/{id}/butir` | D, K, SP, SF | Daftar butir dan statusnya |
| GET | `/butir-siklus/{id}` | D, K, SP, SF | Lembar kerja satu butir |
| PATCH | `/butir-siklus/{id}` | K, SP, SF ¹ | Menyimpan status kelengkapan, skor estimasi, catatan |
| GET | `/butir-siklus/{id}/data` | D, K, SP, SF | Data inti yang terpetakan ke butir ini (hasil Mapping Engine) |
| PUT | `/butir-siklus/{id}/narasi/{bagian}` | K | Menyimpan narasi (dipakai simpan otomatis). Peran lain dijawab `403` (EC-30) |
| PUT | `/butir-siklus/{id}/penugasan` | D | Menetapkan pengelola dan penanggung jawab butir |
| POST | `/siklus/{id}/penugasan-massal` | D | Menetapkan banyak butir sekaligus |
| GET | `/saya/butir` | SP, SF | Papan kerja: butir yang ditugaskan kepada pemanggil |

### `GET /siklus/{id}/butir`

Saringan: `status_kelengkapan`, `kriteria`, `pengelola`, `penanggung_jawab_id`, `belum_ditugaskan=true`, `bukti_bermasalah=true`, `menunggu_dokumen_eksternal=true`.

Dekan memakai `status_kelengkapan=draft` atau `belum_mulai` untuk memantau butir yang belum lengkap (US-F1).

Respons `200`:

```json
{
  "data": [
    {
      "id": "e3b0c442-98fc-4c14-9afb-4c8996fb9242",
      "butir": {
        "kode": "3",
        "kriteria": { "kode": "A", "nama": "Tata Kelola dan Penjaminan Mutu" },
        "elemen": "Keterlaksanaan Sistem Penjaminan Mutu Internal ...",
        "jenis_ipo": null,
        "tahap_ppepp": null,
        "bobot": null
      },
      "status_kelengkapan": "draft",
      "pengelola": "fakultas",
      "penanggung_jawab": { "id": "b7e1d2c3-0000-4000-8000-00000000000a", "nama": "Staf Fakultas A" },
      "skor_estimasi": 3.0,
      "jumlah_bukti": 4,
      "jumlah_bukti_bermasalah": 1,
      "menunggu_dokumen_eksternal": false,
      "catatan_validasi_terbuka": 0,
      "updated_at": "2026-10-03T14:12:09+07:00"
    }
  ],
  "meta": { "page": 1, "per_page": 50, "total": 35 }
}
```

### `GET /butir-siklus/{id}`

Respons `200`:

```json
{
  "id": "e3b0c442-98fc-4c14-9afb-4c8996fb9242",
  "siklus_id": "6efebc60-2dbc-4f20-86d7-b96b278f73c2",
  "row_version": 7,
  "butir": {
    "id": "11112222-3333-4444-8555-666677778888",
    "kode": "3",
    "elemen": "Keterlaksanaan Sistem Penjaminan Mutu Internal ...",
    "rubrik": [
      { "skor": 4, "label": "Baik Sekali", "deskriptor": "UPPS telah melaksanakan SPMI ... memenuhi 5 aspek ..." },
      { "skor": 3, "label": "Baik", "deskriptor": "..." }
    ],
    "ambang": [
      { "peringkat": "unggul_5", "skor_min": 4, "is_syarat_perlu": true },
      { "peringkat": "terakreditasi", "skor_min": 3, "is_syarat_perlu": true }
    ],
    "skema_narasi": [{ "bagian": "utama", "judul": "Uraian keterlaksanaan SPMI dan lima aspeknya" }]
  },
  "status_kelengkapan": "draft",
  "pengelola": "fakultas",
  "penanggung_jawab": { "id": "b7e1d2c3-0000-4000-8000-00000000000a", "nama": "Staf Fakultas A" },
  "skor_estimasi": 3.0,
  "sumber_skor": "mandiri",
  "narasi": [
    { "bagian": "utama", "isi": "UPPS melaksanakan SPMI ...", "status": "draft", "sumber": "manual", "row_version": 12 }
  ],
  "bukti": [
    { "id": "0a0a0a0a-1111-4222-8333-444444444444", "judul": "SK Pembentukan GPM", "jenis": "berkas", "status_cek": "ok" },
    { "id": "0b0b0b0b-1111-4222-8333-555555555555", "judul": "Laporan AMI 2025", "jenis": "tautan", "status_cek": "tidak_terjangkau" }
  ],
  "catatan_validasi": [],
  "dapat_disunting": true,
  "narasi_dapat_disunting": true
}
```

`dapat_disunting` bernilai `false` bila laporan terkunci atau pemanggil tidak berhak menyunting butir ini. `narasi_dapat_disunting` hanya bernilai `true` bagi Kaprodi prodi tersebut; staf admin mengelola data dan bukti, tidak narasi.

### `PATCH /butir-siklus/{id}`

Menyimpan draf tidak mensyaratkan kelengkapan (US-B4).

Permintaan:

```json
{ "row_version": 7, "status_kelengkapan": "draft", "skor_estimasi": 3.0, "catatan": "Menunggu laporan benchmarking." }
```

Respons `200`: lembar kerja butir dengan `row_version: 8`.

### `PUT /butir-siklus/{id}/narasi/{bagian}`

Permintaan:

```json
{ "row_version": 12, "isi": "UPPS melaksanakan SPMI sesuai standar perguruan tinggi ...", "status": "draft" }
```

Respons `200`:

```json
{ "bagian": "utama", "status": "draft", "sumber": "manual", "row_version": 13, "updated_at": "2026-10-04T20:15:31+07:00" }
```

Respons `409` (disunting pengguna lain):

```json
{
  "error": {
    "code": "KONFLIK_VERSI",
    "message": "Narasi telah diubah pengguna lain. Muat versi terbaru sebelum menyimpan.",
    "details": [{ "row_version": 14, "updated_by": "Staf Prodi B", "updated_at": "2026-10-04T20:14:58+07:00" }]
  }
}
```

### `PUT /butir-siklus/{id}/penugasan`

Permintaan:

```json
{ "pengelola": "fakultas", "penanggung_jawab_id": "b7e1d2c3-0000-4000-8000-00000000000a" }
```

Respons `200`: lembar kerja butir yang diperbarui. Butir langsung muncul di `/saya/butir` milik penanggung jawab baru.

---

## 6. Data inti Tridharma

Semua sumber daya data inti mengikuti satu pola.

| Sumber daya | Endpoint dasar | Tabel |
|---|---|---|
| Dosen | `/dosen` | `dosen` |
| Afiliasi dosen | `/dosen/{id}/afiliasi` | `dosen_prodi` |
| Statistik mahasiswa | `/statistik-mahasiswa` | `mahasiswa_statistik` |
| Statistik lulusan | `/statistik-lulusan` | `lulusan_statistik` |
| Kurikulum dan mata kuliah | `/kurikulum`, `/kurikulum/{id}/mata-kuliah` | `kurikulum`, `mata_kuliah` |
| Penelitian | `/penelitian` | `kegiatan_tridharma` (`jenis = penelitian`) |
| PkM | `/pkm` | `kegiatan_tridharma` (`jenis = pkm`) |
| Publikasi dan luaran | `/publikasi` | `publikasi` |
| Kerja sama | `/kerja-sama` | `kerja_sama` |
| Sarana dan prasarana | `/sarana` | `sarana_prasarana` |
| Keuangan | `/keuangan` | `keuangan` |

| Method | Endpoint | Peran | Fungsi |
|---|---|---|---|
| GET | `/{sumber}` | D, K, SP, SF | Daftar. Saringan: `prodi_id`, `tahun_akademik_id`, `status_data`, `q` |
| POST | `/{sumber}` | K, SP, SF ¹ | Menambah data (tersimpan sebagai `draft`) |
| GET | `/{sumber}/{id}` | D, K, SP, SF | Rincian |
| PATCH | `/{sumber}/{id}` | K, SP, SF ¹ | Mengubah (wajib `row_version`) |
| DELETE | `/{sumber}/{id}` | K | Menghapus; hanya data berstatus `draft` |
| POST | `/{sumber}/{id}/verifikasi` | K | Mengubah status menjadi `terverifikasi` |
| GET | `/{sumber}/{id}/bukti` | D, K, SP, SF | Bukti terlampir |
| PUT, DELETE | `/{sumber}/{id}/bukti/{bukti_id}` | K, SP, SF ¹ | Melampirkan atau melepas bukti |
| GET | `/{sumber}/{id}/butir` | D, K, SP, SF | Butir instrumen yang merujuk data ini; dipakai untuk peringatan dampak sebelum mengubah atau menghapus (EC-05) |
| POST | `/{sumber}/impor` | SP, SF | Impor XLSX atau CSV (`202`) |

Data bersama lintas prodi (dosen, sarana fakultas, keuangan UPPS) dikelola SF.

### `POST /publikasi`

Permintaan:

```json
{
  "judul": "Sintesis Katalis Heterogen Berbasis Zeolit untuk Produksi Biodiesel",
  "jenis": "jurnal",
  "tingkat": "internasional_bereputasi",
  "nama_media": "Journal of Catalysis Research",
  "tahun_terbit": 2025,
  "tahun_akademik_id": "2f1e0d9c-aaaa-4bbb-8ccc-ddddeeeeffff",
  "doi": "10.1000/jcr.2025.0142",
  "url": "https://doi.org/10.1000/jcr.2025.0142",
  "kegiatan_id": null,
  "jumlah_mahasiswa": 1,
  "penulis": [
    { "dosen_id": "aaaa1111-2222-4333-8444-555566667777", "urutan_penulis": 1, "is_korespondensi": true },
    { "dosen_id": "bbbb1111-2222-4333-8444-555566667777", "urutan_penulis": 2, "is_korespondensi": false }
  ],
  "atribusi_prodi": [
    { "prodi_id": "9fd15e1d-6bf8-4663-b0c7-ed5a532bc384", "proporsi": 0.5 },
    { "prodi_id": "44445555-6666-4777-8888-9999aaaabbbb", "proporsi": 0.5 }
  ]
}
```

Respons `201`:

```json
{
  "id": "cdcdcdcd-1212-4343-8565-787878787878",
  "judul": "Sintesis Katalis Heterogen Berbasis Zeolit untuk Produksi Biodiesel",
  "status_data": "draft",
  "row_version": 1,
  "butir_terkait": [
    { "instrumen": "LAMSAMA 3.1", "kode": "32", "elemen": "Publikasi ilmiah hasil penelitian ..." }
  ],
  "created_at": "2026-10-04T20:20:11+07:00"
}
```

`butir_terkait` menunjukkan butir yang otomatis terpasok oleh data ini.

Respons `409` (terduga duplikat):

```json
{
  "error": {
    "code": "DUPLIKAT",
    "message": "Publikasi serupa sudah tercatat.",
    "details": [
      { "id": "efefefef-0000-4000-8000-121212121212", "judul": "Sintesis Katalis Heterogen Berbasis Zeolit ...", "doi": "10.1000/JCR.2025.0142", "alasan": "doi_sama" }
    ]
  }
}
```

DOI yang sama selalu ditolak. Kemiripan judul saja dapat dilewati dengan `?abaikan_kemiripan=true`. Untuk menyatukan dua catatan: `POST /publikasi/{id}/gabung` dengan badan `{ "sumber_id": "..." }` (K).

Bila jumlah `proporsi` pada `atribusi_prodi` melebihi 1, jawabannya `422 VALIDASI_GAGAL` (EC-02).

---

## 7. Bukti

| Method | Endpoint | Peran | Fungsi |
|---|---|---|---|
| POST | `/bukti/unggahan` | K, SP, SF | Meminta URL unggah sementara ke MinIO |
| POST | `/bukti` | K, SP, SF | Mendaftarkan bukti: berkas yang sudah diunggah, atau tautan |
| GET | `/bukti` | D, K, SP, SF | Daftar. Saringan: `prodi_id`, `jenis`, `status_cek`, `q` |
| GET | `/bukti/{id}` | D, K, SP, SF, A | Rincian dan daftar pemakaian |
| PATCH | `/bukti/{id}` | K, SP, SF ¹ | Mengubah metadata, mengganti berkas atau tautan |
| DELETE | `/bukti/{id}` | K | Menghapus (hapus lunak) |
| GET | `/bukti/{id}/unduh` | D, K, SP, SF, A | URL unduh sementara (berkas) atau alamat tautan |
| POST | `/bukti/{id}/cek` | K, SP, SF | Memeriksa ulang keterjangkauan sekarang |
| PUT | `/butir-siklus/{id}/bukti/{bukti_id}` | K, SP, SF ¹ | Menautkan bukti ke butir |
| DELETE | `/butir-siklus/{id}/bukti/{bukti_id}` | K, SP, SF ¹ | Melepas tautan |

### Alur unggah berkas

1. `POST /bukti/unggahan`

   ```json
   { "nama_berkas": "SK-GPM-2025.pdf", "mime_type": "application/pdf", "ukuran_byte": 482113 }
   ```

   Respons `200`:

   ```json
   {
     "objek_key": "bukti/2026/10/7f3c9e2a-SK-GPM-2025.pdf",
     "url_unggah": "https://simak.kampus.ac.id/penyimpanan/...tanda-tangan...",
     "kedaluwarsa_pada": "2026-10-04T20:35:00+07:00"
   }
   ```

   Format atau ukuran di luar ketentuan dijawab `422` dengan pesan spesifik (EC-18).

2. Klien mengunggah berkas dengan `PUT` ke `url_unggah`.

3. `POST /bukti`

   ```json
   {
     "jenis": "berkas",
     "judul": "SK Pembentukan Gugus Penjaminan Mutu",
     "objek_key": "bukti/2026/10/7f3c9e2a-SK-GPM-2025.pdf",
     "sumber": "Fakultas",
     "tanggal_dokumen": "2025-02-10",
     "berlaku_untuk": ["9fd15e1d-6bf8-4663-b0c7-ed5a532bc384", "44445555-6666-4777-8888-9999aaaabbbb"]
   }
   ```

### `POST /bukti` (tautan)

Permintaan:

```json
{
  "jenis": "tautan",
  "judul": "Laporan Audit Mutu Internal 2025",
  "url": "https://drive.kampus.ac.id/s/ami-2025",
  "akses_tautan": "terbatas",
  "sumber": "Satuan Penjaminan Mutu",
  "tanggal_dokumen": "2025-12-01",
  "berlaku_untuk": ["9fd15e1d-6bf8-4663-b0c7-ed5a532bc384"]
}
```

Respons `201`:

```json
{
  "id": "0b0b0b0b-1111-4222-8333-555555555555",
  "jenis": "tautan",
  "judul": "Laporan Audit Mutu Internal 2025",
  "url": "https://drive.kampus.ac.id/s/ami-2025",
  "akses_tautan": "terbatas",
  "status_cek": "belum_dicek",
  "berlaku_untuk": [{ "id": "9fd15e1d-6bf8-4663-b0c7-ed5a532bc384", "kode": "KIMIA" }],
  "row_version": 1
}
```

Tautan berakses `terbatas` tidak dapat dibuka link-checker tanpa login. Tautan seperti ini hanya diperiksa keberadaan alamatnya: jawaban `401` atau `403` tidak dihitung sebagai rusak, sedangkan pada tautan `publik` jawaban yang sama ditandai tidak terjangkau. Sistem tidak dapat memastikan asesor bisa membuka tautan terbatas, jadi hak aksesnya perlu diberikan di tempat dokumen itu disimpan.

---

## 8. Penjaminan mutu (PPEPP)

| Method | Endpoint | Peran | Fungsi |
|---|---|---|---|
| GET | `/standar-spm` | D, K, SF | Katalog standar dan butir dari SPM |
| POST, PATCH | `/standar-spm`, `/standar-spm/{id}` | SF | Mengelola standar |
| POST, PATCH | `/standar-spm/{id}/butir`, `/butir-standar/{id}` | SF | Mengelola butir standar |
| POST | `/standar-spm/{id}/validasi` | D | Memvalidasi katalog |
| GET, POST | `/siklus-ppepp` | D (baca: K, SP, SF) | Daftar dan pembuatan siklus PPEPP |
| GET | `/siklus-ppepp/{id}/penetapan` | D, K, SF, A | Butir sasaran yang ditetapkan. Saringan: `prodi_id` |
| POST | `/siklus-ppepp/{id}/penetapan` | D | Menambah butir sasaran (P1) |
| PATCH | `/penetapan/{id}` | D | Mengubah butir sasaran |
| POST | `/siklus-ppepp/{id}/tetapkan` | D | Menetapkan resmi; membuat baris tahapan P2 sampai P5 untuk tiap prodi |
| GET | `/penetapan/{id}/tahapan` | D, K, SP, SF, A | Tahapan per prodi. Saringan: `prodi_id` |
| PUT | `/penetapan/{id}/tahapan/{tahap}` | K, SP, SF ¹ | Mengisi tahap (`pelaksanaan`, `evaluasi`, `pengendalian`, `peningkatan`) |
| GET | `/siklus-ppepp/{id}/rekap` | D | Rekap kemajuan semua prodi dalam satu tampilan |

### `POST /siklus-ppepp/{id}/penetapan`

Permintaan:

```json
{
  "butir_standar_id": "12121212-3434-4565-8787-909090909090",
  "prodi_id": null,
  "nomor_butir": "STD-PEN-03",
  "isi": "Setiap dosen tetap menghasilkan publikasi ilmiah pada jurnal bereputasi.",
  "indikator": "Rata-rata publikasi jurnal bereputasi per dosen tetap per tahun",
  "target_nilai": 1.0,
  "target_satuan": "publikasi/dosen/tahun",
  "target_deskripsi": "Minimal satu publikasi per dosen tetap per tahun.",
  "periode_mulai": "2026-08-01",
  "periode_selesai": "2027-07-31",
  "penanggung_jawab_id": null
}
```

`prodi_id: null` berarti berlaku untuk semua prodi.

Respons `201`:

```json
{
  "id": "56565656-7878-4909-8a1a-b2b2b2b2b2b2",
  "nomor_butir": "STD-PEN-03",
  "status": "draf",
  "baseline_nilai": 0.7,
  "baseline_dari": { "siklus": "PPEPP 2025/2026", "capaian_nilai": 0.7 },
  "row_version": 1
}
```

`baseline_nilai` diisi otomatis dari hasil tahap Peningkatan siklus sebelumnya bila ada (EC-22).

### `PUT /penetapan/{id}/tahapan/{tahap}?prodi_id=...`

Permintaan (tahap `evaluasi`):

```json
{
  "row_version": 2,
  "status": "selesai",
  "uraian": "Evaluasi capaian publikasi semester genap.",
  "capaian_nilai": 0.8,
  "temuan": "Empat dosen belum memiliki publikasi bereputasi dalam dua tahun terakhir.",
  "bukti_id": ["0a0a0a0a-1111-4222-8333-444444444444"]
}
```

Respons `200`:

```json
{
  "tahap": "evaluasi",
  "status": "selesai",
  "capaian_nilai": 0.8,
  "selisih_target": -0.2,
  "row_version": 3,
  "saran_berikutnya": { "tahap": "pengendalian", "pesan": "Ada temuan. Susun tindak lanjut pada tahap Pengendalian." }
}
```

Tahap `penetapan` tidak dapat diubah lewat endpoint ini; bagi Kaprodi tahap itu hanya dapat dibaca.

---

## 9. Dokumen eksternal (tracer study dan kepuasan)

| Method | Endpoint | Peran | Fungsi |
|---|---|---|---|
| GET | `/dokumen-eksternal` | D, K, SP, SF | Daftar. Saringan: `jenis`, `prodi_id`, `tahun_akademik_id` |
| POST | `/dokumen-eksternal` | SF | Mencatat dokumen dari Direktorat Kemahasiswaan |
| PATCH | `/dokumen-eksternal/{id}` | SF | Mengubah metadata |
| PUT | `/dokumen-eksternal/{id}/indikator` | SF | Mengisi indikator secara manual |
| POST | `/dokumen-eksternal/{id}/indikator/impor` | SF | Impor indikator dari CSV atau XLSX (`202`) |
| GET | `/prodi/{id}/indikator-eksternal` | D, K, SP, SF | Indikator tracer dan kepuasan satu prodi |

### `POST /dokumen-eksternal`

Permintaan:

```json
{
  "jenis": "tracer_study",
  "judul": "Laporan Tracer Study Lulusan 2024",
  "sumber_unit": "Direktorat Kemahasiswaan",
  "tahun_akademik_id": "2f1e0d9c-aaaa-4bbb-8ccc-ddddeeeeffff",
  "periode_mulai": "2025-03-01",
  "periode_selesai": "2025-06-30",
  "populasi": 412,
  "jumlah_responden": 287,
  "metodologi": "Survei daring terhadap lulusan satu tahun setelah wisuda.",
  "bukti_id": "0c0c0c0c-1111-4222-8333-666666666666",
  "diterima_pada": "2025-08-15",
  "prodi_id": ["9fd15e1d-6bf8-4663-b0c7-ed5a532bc384", "44445555-6666-4777-8888-9999aaaabbbb"]
}
```

Respons `201`: dokumen beserta `butir_dibebaskan`, yaitu jumlah butir yang tanda `menunggu_dokumen_eksternal`-nya dicabut (EC-15).

Hasil impor indikator melaporkan baris bermasalah beserta nomornya tanpa membatalkan baris yang sah (EC-17):

```json
{
  "id": "9a9a9a9a-0000-4000-8000-565656565656",
  "status": "selesai",
  "baris_berhasil": 21,
  "baris_gagal": [{ "baris": 14, "kolom": "nilai", "pesan": "Bukan angka." }]
}
```

---

## 10. Laporan, validasi, dan ekspor

| Method | Endpoint | Peran | Fungsi |
|---|---|---|---|
| GET | `/siklus/{id}/laporan` | D, K, SP, SF | Status laporan dan pengajuan terakhir |
| GET | `/siklus/{id}/laporan/pra-cek` | K | Daftar hal yang masih menghalangi pengajuan |
| POST | `/siklus/{id}/laporan/ajukan` | K | Mengajukan laporan untuk validasi |
| POST | `/laporan/{id}/setujui` | D | Menyetujui |
| POST | `/laporan/{id}/kembalikan` | D | Mengembalikan dengan catatan |
| POST | `/laporan/{id}/buka-kembali` | D | Membuka kembali laporan yang sudah disetujui (EC-09) |
| GET | `/laporan/{id}/pengajuan` | D, K | Riwayat pengajuan |
| GET | `/pengajuan/{id}` | D, K | Cuplikan dan catatan satu pengajuan |
| PATCH | `/catatan-validasi/{id}` | K | Menandai catatan selesai ditindaklanjuti |
| POST | `/siklus/{id}/ekspor` | D, K, SP, SF | Meminta dokumen (`202`) |
| GET | `/ekspor/{id}` | pemohon, D | Status tugas ekspor |
| GET | `/ekspor/{id}/unduh` | pemohon, D | URL unduh sementara |

Alur status: `draft` → `menunggu_validasi` → `disetujui`, atau kembali ke `draft` bila dikembalikan.

Pemakaian generator LLM bukan syarat pengajuan maupun persetujuan.

### `POST /siklus/{id}/laporan/ajukan`

Permintaan:

```json
{ "catatan": "Pengajuan pertama." }
```

Respons `201`:

```json
{
  "laporan_id": "abababab-1111-4222-8333-cdcdcdcdcdcd",
  "status": "menunggu_validasi",
  "pengajuan": { "id": "34343434-5656-4787-8989-010101010101", "nomor": 1, "diajukan_pada": "2026-10-20T09:02:44+07:00" }
}
```

Respons `422` (belum lengkap):

```json
{
  "error": {
    "code": "LAPORAN_BELUM_LENGKAP",
    "message": "Masih ada butir yang belum lengkap.",
    "details": [
      { "butir_siklus_id": "e3b0c442-98fc-4c14-9afb-4c8996fb9242", "kode": "3", "masalah": ["status_draft", "bukti_tidak_terjangkau"] },
      { "butir_siklus_id": "f4c1d553-0000-4000-8000-5d9aa7fc0353", "kode": "31", "masalah": ["menunggu_dokumen_eksternal"] }
    ]
  }
}
```

Setelah pengajuan diterima, seluruh penulisan pada siklus tersebut dijawab `409 LAPORAN_TERKUNCI` sampai Dekan memutuskan.

### `POST /laporan/{id}/kembalikan`

Permintaan:

```json
{
  "catatan_umum": "Lengkapi bukti benchmarking dan perbaiki analisis kriteria C.",
  "catatan_butir": [
    { "butir_siklus_id": "e3b0c442-98fc-4c14-9afb-4c8996fb9242", "isi": "Laporan benchmarking eksternal belum dilampirkan." }
  ]
}
```

Respons `200`:

```json
{ "laporan_id": "abababab-1111-4222-8333-cdcdcdcdcdcd", "status": "draft", "pengajuan": { "nomor": 1, "keputusan": "dikembalikan" } }
```

Cuplikan pengajuan nomor 1 tetap tersimpan (EC-08).

### `POST /laporan/{id}/setujui`

Permintaan: `{ "catatan_umum": "Disetujui." }`

Respons `200`: `status: "disetujui"`.

Respons `409 BUKTI_BERMASALAH` bila masih ada bukti tidak terjangkau; `details` memuat daftar butir dan buktinya (EC-23).

### `POST /siklus/{id}/ekspor`

Permintaan:

```json
{ "jenis": "led", "format": "docx", "final": true }
```

`final: true` hanya diterima bila laporan berstatus `disetujui`; selain itu jawabannya `409`. Dengan `final: false` dokumen diberi tanda air "DRAF" dan dapat diminta kapan saja.

Respons `202`:

```json
{ "id": "78787878-9090-4a1a-8b2b-c3c3c3c3c3c3", "status": "antre", "jenis": "led", "format": "docx" }
```

`GET /ekspor/{id}` setelah selesai:

```json
{
  "id": "78787878-9090-4a1a-8b2b-c3c3c3c3c3c3",
  "status": "selesai",
  "jenis": "led",
  "format": "docx",
  "ukuran_byte": 1843200,
  "metadata": {
    "prodi": "Kimia",
    "instrumen": "LAMSAMA 3.1",
    "pengajuan_nomor": 2,
    "data_per": "2026-10-22T10:00:00+07:00"
  },
  "selesai_pada": "2026-10-22T10:01:12+07:00"
}
```

---

## 11. Pemantauan dan analisis

| Method | Endpoint | Peran | Fungsi |
|---|---|---|---|
| GET | `/dasbor/fakultas` | D, SF | Ringkasan semua prodi |
| GET | `/dasbor/prodi/{prodi_id}` | D, K, SP, SF ¹ | Ringkasan satu prodi |
| GET | `/siklus/{id}/simulasi-skor` | D, K | Simulasi terakhir |
| POST | `/siklus/{id}/simulasi-skor` | D, K | Menghitung ulang simulasi |
| GET | `/analisis/gap` | D | Selisih capaian terhadap target. Parameter: `siklus_id` atau `siklus_ppepp_id` |
| GET | `/analisis/benchmark` | D | Perbandingan antarprodi. Parameter: `indikator`, `tahun_akademik_id` |

### `GET /dasbor/fakultas`

Respons `200`:

```json
{
  "tahun_akademik": "2025/2026",
  "prodi": [
    {
      "prodi": { "id": "77778888-9999-4aaa-8bbb-ccccddddeeee", "kode": "ILKOM", "nama": "Ilmu Komputer" },
      "instrumen": "LAM INFOKOM 2.1",
      "siklus_id": "13131313-2424-4535-8646-575757575757",
      "tenggat": "2026-12-15",
      "persen_siap": 62.5,
      "butir": { "jumlah": 80, "lengkap": 50, "draft": 21, "belum_mulai": 9, "belum_ditugaskan": 3, "bukti_bermasalah": 2, "menunggu_dokumen_eksternal": 1 },
      "ppepp": { "butir_sasaran": 14, "tahap_selesai": 31, "tahap_total": 56 },
      "laporan": "draft",
      "simulasi": { "nilai_akhir": 334.5, "prediksi_peringkat": "Terakreditasi", "dihitung_pada": "2026-10-04T02:00:00+07:00", "estimasi_internal": true },
      "tingkat_risiko": "kuning"
    },
    {
      "prodi": { "id": "9fd15e1d-6bf8-4663-b0c7-ed5a532bc384", "kode": "KIMIA", "nama": "Kimia" },
      "instrumen": "LAMSAMA 3.1",
      "siklus_id": "6efebc60-2dbc-4f20-86d7-b96b278f73c2",
      "tenggat": "2027-02-01",
      "persen_siap": 40.0,
      "butir": { "jumlah": 35, "lengkap": 14, "draft": 15, "belum_mulai": 6, "belum_ditugaskan": 0, "bukti_bermasalah": 1, "menunggu_dokumen_eksternal": 2 },
      "ppepp": { "butir_sasaran": 14, "tahap_selesai": 20, "tahap_total": 56 },
      "laporan": "draft",
      "simulasi": { "nilai_akhir": null, "prediksi_peringkat": "Terakreditasi", "dihitung_pada": "2026-10-04T02:00:00+07:00", "estimasi_internal": true },
      "tingkat_risiko": "merah"
    }
  ]
}
```

### `GET /siklus/{id}/simulasi-skor`

Bentuk `rincian` mengikuti cara penilaian instrumen. Contoh LAM INFOKOM:

```json
{
  "siklus_id": "13131313-2424-4535-8646-575757575757",
  "estimasi_internal": true,
  "dihitung_pada": "2026-10-04T02:00:00+07:00",
  "nilai_akhir": 334.5,
  "nilai_akhir_maks": 400,
  "prediksi_peringkat": { "kode": "terakreditasi", "nama": "Terakreditasi" },
  "target_peringkat": { "kode": "unggul_5", "nama": "Unggul (berlaku 5 tahun)" },
  "butir_belum_dinilai": 9,
  "rincian": {
    "kriteria": [
      { "kode": "1", "nama": "Budaya Mutu", "rerata": 3.4, "memenuhi_syarat": true },
      { "kode": "2", "nama": "Relevansi Pendidikan", "rerata": 3.1, "memenuhi_syarat": false },
      { "kode": "3", "nama": "Relevansi Penelitian", "rerata": 3.3, "memenuhi_syarat": true }
    ],
    "syarat_gagal": [
      { "syarat": "rerata_kriteria_min", "kriteria": "2", "nilai": 3.1, "ambang": 3.2 },
      { "syarat": "skor_butir_min", "butir": "2.2.D", "nilai": 2.0, "ambang": 3.0 }
    ],
    "prioritas_perbaikan": [
      { "butir_siklus_id": "24242424-0000-4000-8000-353535353535", "kode": "2.2.D", "bobot": 30, "skor_estimasi": 2.0 }
    ]
  }
}
```

Pada LAMSAMA `nilai_akhir` bernilai `null`, dan `rincian` memuat butir yang berada di bawah ambang minimum tiap peringkat beserta tanda syarat perlu.

Respons selalu membawa `estimasi_internal: true` dan `dihitung_pada`. Skor ini bukan penilaian resmi asesor.

### `GET /analisis/benchmark?indikator=publikasi_per_dosen&tahun_akademik_id=...`

Respons `200`:

```json
{
  "indikator": { "kode": "publikasi_per_dosen", "nama": "Publikasi per dosen tetap", "satuan": "publikasi/dosen", "makin_tinggi_makin_baik": true },
  "tahun_akademik": "2025/2026",
  "data": [
    { "prodi": "ILKOM", "nilai": 1.4 },
    { "prodi": "KIMIA", "nilai": 1.1 },
    { "prodi": "AKTUARIA", "nilai": 0.6 }
  ]
}
```

Perbandingan hanya tersedia untuk `indikator_inti`. Tidak ada endpoint yang membandingkan skor mentah LAMSAMA dengan LAM INFOKOM (EC-20).

---

## 12. Asesmen (asesor, hanya baca)

| Method | Endpoint | Peran | Fungsi |
|---|---|---|---|
| GET | `/asesmen/siklus` | A | Siklus prodi yang ditugaskan beserta versi laporan yang disetujui, selama jendela asesmen |
| GET | `/asesmen/siklus/{id}/butir` | A | Butir per kriteria beserta tanda sudah ditelaah |
| GET | `/asesmen/butir/{butir_siklus_id}` | A | Butir, rubrik, narasi, skor estimasi, dan bukti sebagaimana saat disetujui |
| PUT | `/asesmen/butir/{butir_siklus_id}/telaah` | A | Menandai sudah ditelaah dan menyimpan catatan baca |

Asesor membaca **versi laporan yang sudah disetujui Dekan**. Seluruh endpoint di bagian ini mengambil data dari cuplikan pengajuan terakhir yang disetujui, tidak dari lembar kerja yang sedang berjalan. Bila laporan dibuka kembali selama jendela asesmen, yang tersaji tetap versi terakhir yang disetujui (EC-29).

Bukti dibuka lewat `GET /bukti/{id}/unduh`, terbatas pada bukti yang tercantum dalam versi tersebut. Asesor tidak memiliki endpoint penulisan selain `telaah`, dan `telaah` tidak mengubah data sumber.

### `GET /asesmen/siklus`

Respons `200`:

```json
{
  "data": [
    {
      "siklus_id": "6efebc60-2dbc-4f20-86d7-b96b278f73c2",
      "prodi": { "kode": "KIMIA", "nama": "Kimia" },
      "instrumen": "LAMSAMA 3.1",
      "versi_laporan": { "pengajuan_id": "34343434-5656-4787-8989-020202020202", "nomor": 2, "disetujui_pada": "2026-10-22T09:40:00+07:00" },
      "jendela_asesmen": { "mulai": "2026-11-10T00:00:00+07:00", "sampai": "2026-11-14T23:59:59+07:00" },
      "butir": { "jumlah": 35, "sudah_ditelaah": 12 }
    }
  ],
  "meta": { "page": 1, "per_page": 20, "total": 1 }
}
```

Permintaan di luar jendela asesmen atau terhadap prodi lain dijawab `403 AKSES_DITOLAK` dan dicatat di log audit (EC-26).

### `PUT /asesmen/butir/{butir_siklus_id}/telaah`

Permintaan:

```json
{ "sudah_ditelaah": true, "catatan": "Bukti aspek 5 perlu dikonfirmasi saat asesmen lapangan." }
```

Respons `200`:

```json
{ "butir_siklus_id": "e3b0c442-98fc-4c14-9afb-4c8996fb9242", "pengajuan_nomor": 2, "sudah_ditelaah": true, "updated_at": "2026-11-11T10:42:00+07:00" }
```

---

## 13. LLM (opsional)

| Method | Endpoint | Peran | Fungsi |
|---|---|---|---|
| GET | `/konfigurasi-llm` | D, SF | Daftar konfigurasi. Kunci API tidak pernah dikembalikan |
| POST, PATCH | `/konfigurasi-llm`, `/konfigurasi-llm/{id}` | SF | Menyiapkan konfigurasi |
| POST | `/konfigurasi-llm/{id}/uji` | D, SF | Menguji koneksi |
| POST | `/konfigurasi-llm/{id}/aktifkan` | D | Mengaktifkan. Untuk mode `online`, ini adalah persetujuan eksplisit Dekan |
| POST | `/butir-siklus/{id}/narasi/{bagian}/draf-llm` | K | Meminta draf narasi (`202`) |
| GET | `/permintaan-llm/{id}` | K | Status dan hasil draf |

### `POST /konfigurasi-llm`

Permintaan:

```json
{
  "nama": "Model lokal fakultas",
  "mode": "offline",
  "base_url": "http://llm:11434/v1",
  "model": "nama-model-lokal",
  "api_key": null,
  "parameter": { "temperature": 0.3, "max_tokens": 1500 }
}
```

### `POST /butir-siklus/{id}/narasi/{bagian}/draf-llm`

Permintaan:

```json
{ "arahan": "Tekankan capaian tiga tahun terakhir.", "sertakan_data_terpetakan": true }
```

Respons `202`:

```json
{ "id": "45454545-6767-4898-8a9a-bcbcbcbcbcbc", "status": "antre", "mode": "offline", "model": "nama-model-lokal" }
```

`GET /permintaan-llm/{id}` setelah selesai:

```json
{
  "id": "45454545-6767-4898-8a9a-bcbcbcbcbcbc",
  "status": "selesai",
  "mode": "offline",
  "model": "nama-model-lokal",
  "hasil": "Program studi telah menetapkan ...",
  "selesai_pada": "2026-10-04T20:31:07+07:00"
}
```

Hasil tidak langsung masuk ke narasi. Kaprodi meninjaunya, lalu menyimpannya lewat `PUT /butir-siklus/{id}/narasi/{bagian}` dengan menyertakan `permintaan_llm_id`; narasi kemudian tercatat dengan `sumber: "llm"` atau `"llm_disunting"`.

Bila tidak ada konfigurasi aktif atau koneksi gagal, jawabannya `503 LLM_TIDAK_TERSEDIA`, dan penulisan manual tetap berjalan.

---

## 14. Notifikasi, audit, dan sistem

| Method | Endpoint | Peran | Fungsi |
|---|---|---|---|
| GET | `/notifikasi` | semua | Notifikasi milik pemanggil. Saringan: `belum_dibaca=true` |
| POST | `/notifikasi/{id}/baca` | semua | Menandai sudah dibaca |
| GET | `/log-audit` | D, IT | Saringan: `pengguna_id`, `aksi`, `entitas`, `prodi_id`, `dari`, `sampai` |
| GET | `/pengaturan` | IT | Pengaturan sistem |
| PUT | `/pengaturan/{kunci}` | IT | Mengubah pengaturan (misalnya lama kunci akun, batas ukuran berkas) |
| GET | `/health` | publik | Pemeriksaan kesehatan layanan |

### `GET /log-audit`

Respons `200`:

```json
{
  "data": [
    {
      "id": 48211,
      "waktu": "2026-10-04T19:58:03+07:00",
      "pengguna": { "id": "5b0c7a52-0d0e-4a0f-9a36-0c7c1f2a9d11", "nama": "Dr. Contoh Nama" },
      "peran": "kaprodi",
      "aksi": "akses.ditolak",
      "entitas": "butir_siklus",
      "entitas_id": "24242424-0000-4000-8000-353535353535",
      "prodi": "ILKOM",
      "ip": "10.20.1.15",
      "detail": { "alasan": "di_luar_cakupan_prodi" }
    }
  ],
  "meta": { "page": 1, "per_page": 20, "total": 1 }
}
```

Administrator Sistem/IT melihat log audit lapisan akun dan sistem. Kolom `detail` yang memuat isi data akreditasi disamarkan untuk peran ini.

---

## 15. Keputusan yang sudah ditetapkan

| Hal | Keputusan | Tercermin di |
|---|---|---|
| Penyusun instrumen dan aturan Mapping Engine | Staf Admin Fakultas menyusun, Dekan menyetujui | Bagian 4; SKPL US-G5 |
| Penyuntingan narasi | Hanya Kaprodi. Staf admin tidak menyunting narasi | Bagian 5; SKPL US-D3, EC-30 |
| Yang dilihat asesor | Versi laporan yang sudah disetujui Dekan | Bagian 3 dan 12; SKPL US-H1, EC-28, EC-29 |
