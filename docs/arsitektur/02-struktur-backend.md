# SIMAK — Struktur Proyek Backend

Dokumen 2 dari 3 · Arsitektur awal Sistem Informasi Manajemen Akreditasi

Backend dirancang sebagai **monolit modular**: satu aplikasi FastAPI, satu basis data, tetapi kode dipisah per modul domain, dan tiap modul berlapis mengikuti *clean architecture*. Untuk fakultas dengan tiga prodi, pendekatan ini memberi batas yang jelas antarbagian tanpa beban operasional layanan mikro.

---

## 1. Pilihan pada stack yang masih terbuka

| Pilihan | Rekomendasi | Alasan |
|---|---|---|
| Next.js atau Vite + React | **Vite + React** | Seluruh aplikasi berada di balik login, sehingga SSR dan SEO tidak dibutuhkan. Hasil build statis cukup dilayani Nginx, dan hanya ada satu backend |
| Celery atau BullMQ | **Celery + Redis** | Satu bahasa dengan FastAPI, sehingga tugas latar memakai ulang use case dan model yang sama. BullMQ menuntut layanan Node.js terpisah |
| WeasyPrint atau Typst | **WeasyPrint** | Templat LED ditulis dalam HTML/CSS dengan Jinja2, mudah disesuaikan saat format LAM berubah. Typst layak dipertimbangkan bila kebutuhan tata letak melampaui CSS |
| DOCX | **python-docx** | Sesuai rencana; dijalankan di worker |

Komponen pendukung: SQLAlchemy 2 (async, `asyncpg`), Alembic, Pydantic 2, `pydantic-settings`, Argon2 untuk hash sandi, JWT untuk token akses.

---

## 2. Susunan repositori

```
simak/
├── docker-compose.yml            # pengembangan
├── docker-compose.prod.yml       # produksi
├── .env.example
├── nginx/
│   └── templates/default.conf.template  # /api -> api:8000, sisanya -> berkas statis frontend
├── backend/
├── frontend/                     # Vite + React + Tailwind + shadcn/ui + TanStack Query
└── docs/                         # SKPL dan tiga dokumen arsitektur ini
```

## 3. Susunan backend

```
backend/
├── Dockerfile
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── main.py                   # create_app(): router, middleware, penangan galat
│   ├── core/                     # lintas modul, tanpa logika bisnis
│   │   ├── config.py             # pengaturan dari variabel lingkungan
│   │   ├── database.py           # engine, session factory, Base, mixin (row_version, audit, soft delete)
│   │   ├── unit_of_work.py       # batas transaksi satu use case
│   │   ├── security.py           # hash sandi, pembuatan dan verifikasi JWT
│   │   ├── permissions.py        # Pemanggil (peran + cakupan prodi), aturan otorisasi
│   │   ├── exceptions.py         # galat domain dan pemetaannya ke HTTP
│   │   ├── pagination.py
│   │   ├── audit.py              # pencatat log_audit
│   │   ├── events.py             # peristiwa domain di dalam proses
│   │   └── logging.py
│   ├── modules/
│   │   ├── auth/                 # login, token, kunci akun, reset sandi
│   │   ├── pengguna/             # akun, penugasan peran, jendela asesor
│   │   ├── referensi/            # fakultas, prodi, tahun akademik, pengaturan
│   │   ├── instrumen/            # versi, kriteria, butir, rubrik, peringkat, pemetaan
│   │   ├── siklus/               # siklus akreditasi, butir_siklus, narasi, penugasan butir
│   │   ├── tridharma/            # dosen, statistik, kurikulum, kegiatan, publikasi, kerja sama, sarana, keuangan
│   │   ├── bukti/                # unggah berkas, tautan, link-checker
│   │   ├── ppepp/                # standar SPM, penetapan, tahapan
│   │   ├── dokumen_eksternal/    # hasil tracer dan kepuasan dari Direktorat Kemahasiswaan
│   │   ├── laporan/              # pengajuan, validasi, cuplikan, ekspor
│   │   ├── penilaian/            # simulasi skor, gap analysis, benchmarking, dasbor
│   │   ├── asesmen/              # tampilan baca asesor, telaah
│   │   ├── llm/                  # konfigurasi, permintaan draf narasi
│   │   ├── notifikasi/
│   │   └── audit/                # pembacaan log audit
│   ├── infrastructure/           # adaptor ke sistem luar (implementasi port)
│   │   ├── storage/minio_storage.py
│   │   ├── llm/openai_compatible.py
│   │   ├── documents/
│   │   │   ├── docx_renderer.py
│   │   │   ├── pdf_renderer.py
│   │   │   └── templates/
│   │   │       ├── lamsama_3_1/
│   │   │       └── lam_infokom_2_1/
│   │   ├── mail/smtp_mailer.py
│   │   ├── cache/redis_cache.py
│   │   └── http/link_probe.py
│   └── worker/
│       ├── celery_app.py
│       ├── beat_schedule.py
│       └── tasks/                # pembungkus tipis yang memanggil use case
└── tests/
    ├── unit/                     # domain dan use case dengan repository palsu
    ├── integration/              # repository terhadap PostgreSQL sungguhan
    └── api/                      # uji end-to-end per peran, termasuk isolasi prodi
```

---

## 4. Anatomi satu modul

Setiap modul memiliki empat lapisan. Contoh pada modul `laporan`:

```
modules/laporan/
├── domain/                       # Python murni: tanpa FastAPI, tanpa SQLAlchemy
│   ├── entities.py               # Laporan, Pengajuan, CatatanValidasi
│   ├── rules.py                  # transisi status, syarat pengajuan
│   ├── ports.py                  # LaporanRepository, PenyusunCuplikan (Protocol)
│   └── events.py                 # LaporanDiajukan, LaporanDisetujui, LaporanDikembalikan
├── application/                  # use case: otorisasi, transaksi, orkestrasi
│   ├── ajukan_laporan.py
│   ├── setujui_laporan.py
│   ├── kembalikan_laporan.py
│   ├── buka_kembali_laporan.py
│   ├── minta_ekspor.py
│   └── dto.py
├── infrastructure/               # implementasi port
│   ├── models.py                 # model SQLAlchemy
│   └── repository.py
├── api/                          # antarmuka HTTP
│   ├── router.py
│   ├── schemas.py                # skema Pydantic permintaan dan respons
│   └── dependencies.py
└── public.py                     # satu-satunya pintu yang boleh diimpor modul lain
```

### Arah ketergantungan

```
api  ──►  application  ──►  domain  ◄──  infrastructure
```

- `domain` tidak mengimpor lapisan lain. Aturan bisnis dapat diuji tanpa basis data.
- `application` hanya mengenal port (antarmuka) yang didefinisikan `domain`.
- `infrastructure` mengimplementasikan port tersebut dengan SQLAlchemy, MinIO, HTTP, dan sebagainya.
- `api` menerjemahkan HTTP menjadi pemanggilan use case, lalu hasilnya menjadi respons.
- Implementasi port disambungkan ke use case lewat `Depends` di `api/dependencies.py`.

### Ketergantungan antarmodul

Sebuah modul hanya boleh mengimpor `public.py` milik modul lain, tidak isi dalamnya. Efek samping lintas modul berjalan lewat peristiwa domain: `laporan` menerbitkan `LaporanDiajukan`, lalu `notifikasi` dan `audit` menanggapinya. Kedua aturan ini ditegakkan otomatis dengan `import-linter` di CI.

### Modul sederhana

Modul yang isinya hampir seluruhnya CRUD (`referensi`, sebagian besar `tridharma`) boleh memakai bentuk ringkas: `router.py`, `schemas.py`, `service.py`, `repository.py`, `models.py`. Empat lapisan penuh dipakai di modul yang memiliki aturan bisnis nyata: `auth`, `siklus`, `laporan`, `ppepp`, `penilaian`, `instrumen`, `bukti`.

---

## 5. Tanggung jawab modul

| Modul | Tanggung jawab | Tabel utama |
|---|---|---|
| `auth` | Login, token, kunci setelah lima kali gagal, buka kunci swalayan, reset sandi | `pengguna`, `token_refresh`, `token_akun` |
| `pengguna` | Akun, penugasan peran, usulan dan aktivasi asesor, operasi teknis Admin IT | `pengguna`, `penugasan_peran` |
| `referensi` | Fakultas, prodi, tahun akademik, pengaturan sistem | `fakultas`, `prodi`, `tahun_akademik`, `pengaturan_sistem` |
| `instrumen` | Versi instrumen, impor butir dan rubrik, aturan peringkat, Mapping Engine, padanan antarversi. Disusun Staf Admin Fakultas, berlaku setelah disetujui Dekan | `instrumen_*`, `pemetaan_butir`, `indikator_inti` |
| `siklus` | Membuka siklus, lembar kerja butir, simpan draf, narasi (hanya Kaprodi), penugasan butir ke staf | `siklus_akreditasi`, `butir_siklus`, `narasi_butir` |
| `tridharma` | Data inti, deteksi duplikasi, atribusi lintas prodi, impor | tabel domain 7 |
| `bukti` | Unggah ke MinIO, tautan, "Berlaku untuk", link-checker | `bukti`, `bukti_*` |
| `ppepp` | Katalog standar SPM, penetapan oleh Dekan, tahapan P2 sampai P5, rekap | `standar_spm`, `penetapan_butir`, `tahapan_ppepp` |
| `dokumen_eksternal` | Dokumen tracer dan kepuasan, impor indikator | `dokumen_eksternal`, `indikator_eksternal` |
| `laporan` | Pengajuan, validasi, cuplikan, buka kembali, ekspor | `laporan`, `laporan_pengajuan`, `catatan_validasi`, `ekspor_dokumen` |
| `penilaian` | Simulasi skor, prediksi peringkat, gap analysis, benchmarking, dasbor | `simulasi_skor`, `nilai_indikator`, view pemantauan |
| `asesmen` | Tampilan baca per butir atas cuplikan laporan yang disetujui, tanda telaah | `telaah_asesor`, cuplikan di `laporan_pengajuan` |
| `llm` | Konfigurasi koneksi, permintaan draf narasi | `konfigurasi_llm`, `permintaan_llm` |
| `notifikasi` | Notifikasi dalam aplikasi dan surel | `notifikasi` |
| `audit` | Pembacaan log audit | `log_audit` |

Dua strategi penilaian ada di `penilaian/domain/`: `PenilaiBerbobot` (pola LAM INFOKOM) dan `PenilaiAmbangButir` (pola LAMSAMA). Keduanya memenuhi satu antarmuka `PenilaiPeringkat` dan dipilih berdasarkan data instrumen, sehingga LAM baru tidak menuntut perubahan di modul lain.

---

## 6. Contoh alur: Kaprodi mengajukan laporan

1. `api/router.py` menerima `POST /siklus/{id}/laporan/ajukan`, lalu memanggil use case `AjukanLaporan` dengan objek `Pemanggil` hasil verifikasi token.
2. `AjukanLaporan` memeriksa otorisasi: pemanggil harus Kaprodi pada prodi pemilik siklus. Bila tidak, galat `AksesDitolak` dilempar dan dicatat di log audit.
3. Use case memuat `Laporan` lewat `LaporanRepository`, lalu meminta daftar butir yang belum lengkap dan butir dengan bukti bermasalah dari `siklus.public`.
4. `domain/rules.py` memutuskan: bila masih ada yang kurang, galat `LaporanBelumLengkap` membawa daftar butirnya (EC-06).
5. Bila lolos, entitas `Laporan` berpindah status ke `menunggu_validasi`, dan `Pengajuan` baru dibuat.
6. `UnitOfWork` menyimpan perubahan dalam satu transaksi dan menerbitkan `LaporanDiajukan`.
7. Setelah transaksi berhasil, penangan peristiwa mengirim notifikasi ke Dekan, mencatat audit, dan menjadwalkan tugas Celery untuk menyusun cuplikan.
8. `api` mengubah hasil menjadi respons `201`. Galat domain diubah menjadi `403`, `409`, atau `422` oleh penangan galat di `main.py`.

### Sketsa kode

```python
# modules/laporan/domain/ports.py
class LaporanRepository(Protocol):
    async def ambil_untuk_siklus(self, siklus_id: UUID) -> Laporan: ...
    async def simpan(self, laporan: Laporan) -> None: ...


# modules/laporan/application/ajukan_laporan.py
class AjukanLaporan:
    def __init__(self, uow: UnitOfWork, laporan: LaporanRepository, siklus: SiklusPublic):
        self._uow, self._laporan, self._siklus = uow, laporan, siklus

    async def jalankan(self, pemanggil: Pemanggil, siklus_id: UUID) -> PengajuanDTO:
        ringkasan = await self._siklus.ringkasan(siklus_id)
        pemanggil.wajib_kaprodi(ringkasan.prodi_id)              # AksesDitolak bila bukan

        async with self._uow:
            laporan = await self._laporan.ambil_untuk_siklus(siklus_id)
            pengajuan = laporan.ajukan(                          # aturan ada di entitas domain
                oleh=pemanggil.id,
                butir_belum_lengkap=ringkasan.butir_belum_lengkap,
                butir_bukti_bermasalah=ringkasan.butir_bukti_bermasalah,
            )
            await self._laporan.simpan(laporan)
            self._uow.terbitkan(LaporanDiajukan(laporan.id, pengajuan.id))
        return PengajuanDTO.dari(pengajuan)
```

---

## 7. Otorisasi dan isolasi data

Isolasi antarprodi ditegakkan di tiga tempat, sehingga satu kelalaian tidak langsung membocorkan data.

| Lapis | Mekanisme |
|---|---|
| Use case | Setiap use case menerima `Pemanggil` dan memanggil pemeriksa di `core/permissions.py` sebelum bekerja |
| Repository | Kueri daftar selalu menerima `CakupanProdi` dan menambahkan saringan prodi. Tidak ada metode daftar tanpa cakupan |
| Uji | `tests/api/` menjalankan setiap endpoint sebagai setiap peran, termasuk Kaprodi dan asesor prodi lain, dan memastikan jawabannya `403` |

`Pemanggil` dibangun dari `penugasan_peran` yang aktif pada saat permintaan. Jendela asesor diperiksa di sini, sehingga akses berakhir tepat pada `berlaku_sampai`.

Administrator Sistem/IT hanya memiliki izin pada modul `auth`, `pengguna` (operasi teknis), `referensi` (pengaturan), dan `audit`. Use case modul lain menolak peran ini.

Narasi hanya dapat disunting Kaprodi. Use case `SimpanNarasi` menolak Staf Admin Prodi dan Staf Admin Fakultas, termasuk ketika mereka menjadi penanggung jawab butir tersebut; izin mereka terbatas pada data, bukti, dan status kelengkapan (EC-30).

Asesor membaca versi yang sudah disetujui. Modul `asesmen` tidak pernah membuka tabel `butir_siklus` atau `narasi_butir` secara langsung; ia meminta cuplikan pengajuan terakhir yang disetujui lewat `laporan.public`. Use case aktivasi asesor di modul `pengguna` menolak bila laporan prodi belum `disetujui` (EC-28).

Instrumen dan aturan pemetaan disusun Staf Admin Fakultas sebagai draf. Mapping Engine hanya membaca aturan yang sudah disetujui Dekan, sehingga draf tidak pernah memengaruhi butir (EC-31).

Saat laporan berstatus `menunggu_validasi` atau `disetujui`, use case penulisan pada `siklus`, `bukti`, dan `tridharma` memeriksa status tersebut lewat `laporan.public` dan menolak perubahan (EC-07, EC-09). Yang terkunci adalah lembar kerja butir, narasi, tautan bukti, dan data inti yang hanya teratribusi ke prodi tersebut. Data bersama lintas prodi (misalnya dosen atau sarana fakultas) tetap dapat diubah agar prodi lain tidak ikut terhenti; isi yang diajukan tetap terjaga oleh cuplikan pengajuan.

---

## 8. Tugas latar

Tugas Celery adalah pembungkus tipis: memuat dependensi, lalu memanggil use case yang sama dengan yang dipakai API.

| Tugas | Pemicu | Antrean |
|---|---|---|
| Menyusun dokumen ekspor (PDF, DOCX, XLSX) | Permintaan ekspor | `dokumen` |
| Menyusun cuplikan laporan (narasi, skor, bukti, data terpetakan) | Laporan diajukan | `dokumen` |
| Memeriksa bukti (berkas di MinIO dan tautan) | Terjadwal tiap jam per kelompok, atau permintaan periksa ulang | `periodik` |
| Menyusun draf narasi dengan LLM | Permintaan Kaprodi | `llm` |
| Menghitung simulasi skor | Permintaan, atau setelah skor butir berubah | `default` |
| Menghitung `nilai_indikator` | Terjadwal tiap malam | `periodik` |
| Mengimpor data (XLSX, CSV) | Permintaan impor | `default` |
| Mengirim surel notifikasi | Peristiwa domain | `default` |
| Mengingatkan tenggat siklus | Terjadwal tiap hari | `periodik` |

Antrean `dokumen` dan `llm` dipisah karena tugasnya lama dan berat, supaya tidak menahan tugas ringan. Hasil tugas ditulis ke tabel (`ekspor_dokumen`, `permintaan_llm`), sehingga status dapat dibaca API tanpa bergantung pada backend hasil Celery.

Cuplikan adalah sumber tampilan asesor, jadi persetujuan Dekan baru dapat dilakukan setelah tugas cuplikan selesai. Bila tugas itu gagal, laporan tetap `menunggu_validasi` dan Dekan diberi tahu.

Adaptor LLM memakai antarmuka yang kompatibel dengan OpenAI. Satu adaptor melayani model lokal (misalnya lewat Ollama atau vLLM di server fakultas) maupun penyedia daring; perbedaannya hanya `base_url`, `model`, dan kunci API di `konfigurasi_llm`.

---

## 9. Layanan Docker Compose

| Layanan | Isi | Catatan |
|---|---|---|
| `nginx` | Reverse proxy, TLS, berkas statis frontend | Satu-satunya layanan yang terbuka ke luar; batas ukuran unggahan diatur di sini |
| `api` | FastAPI (Uvicorn) | Migrasi Alembic dijalankan sebelum layanan dimulai |
| `worker` | Celery worker | Image yang sama dengan `api` |
| `beat` | Celery beat | Satu instans saja |
| `postgres` | PostgreSQL 16 | Volume data, cadangan terjadwal |
| `redis` | Broker Celery dan cache | |
| `minio` | Penyimpanan berkas bukti dan hasil ekspor | Bucket privat; akses lewat URL sementara |
| `llm` (opsional) | Server model lokal | Hanya bila mode offline dipakai |

Unggah dan unduh berkas memakai URL sementara MinIO yang diterbitkan API setelah pemeriksaan izin, sehingga berkas besar tidak melewati proses FastAPI.

---

## 10. Pengujian

| Jenis | Cakupan |
|---|---|
| Unit | Aturan domain: transisi status laporan, syarat pengajuan, kedua strategi penilaian, aturan kunci akun |
| Integrasi | Repository dan batasan basis data terhadap PostgreSQL sungguhan |
| API | Matriks hak akses SKPL §3.2 diterjemahkan menjadi uji: tiap endpoint dijalankan sebagai tiap peran |
| Kontrak | Skema OpenAPI yang dihasilkan FastAPI dibandingkan dengan versi sebelumnya untuk mendeteksi perubahan yang memutus frontend |
