import type { ReactNode } from "react";
import type { Rec } from "@/shared/api/types";
import { angka, rupiah, tanggal } from "@/shared/lib/format";
import { Pill, StatusPill, type DefField, type Kolom } from "@/shared/ui";

/** Opsi dinamis yang dibutuhkan formulir (dimuat sekali oleh halaman). */
export interface Opsi {
  tahun: { nilai: string; label: string }[];
  prodi: { nilai: string; label: string }[];
  dosen: { nilai: string; label: string }[];
}

export type Pengikat = "langsung" | "penghubung" | "afiliasi";

export interface SumberCfg {
  path: string;
  judul: string;
  sub: string;
  /** apakah daftar dapat disaring menurut tahun akademik */
  tahun?: boolean;
  pengikat: Pengikat;
  def: (o: Opsi, sendiri: { prodiId?: string; fakultas: boolean }) => DefField[];
  kolom: Kolom<Rec>[];
  /** nilai awal formulir baru */
  awal: (o: Opsi) => Rec;
  /** bidang bersarang yang dikelola ListEditor */
  bersarang?: ("afiliasi" | "dosen" | "penulis" | "atribusi_prodi" | "prodi_ids")[];
  filter?: { nama: string; label: string; pilihan: { nilai: string; label: string }[] }[];
  kolomImpor: string;
  petunjukImpor?: string;
}

const prodiCell = (r: Rec): ReactNode => (r.prodi?.length ? <div className="chips">{r.prodi.map((p: Rec) => <Pill key={p.id}>{p.kode}</Pill>)}</div> : <Pill>UPPS</Pill>);
const judulCell = (judul: string, sub?: ReactNode): ReactNode => (
  <div>
    <div className="cell-title">{judul}</div>
    {sub && <div className="cell-sub">{sub}</div>}
  </div>
);
const kolomStatus: Kolom<Rec> = { kunci: "status_data", judul: "Verifikasi", render: (r) => <StatusPill status={r.status_data} /> };

const pilihan = (...v: string[]) => v.map((x) => ({ nilai: x, label: x.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase()) }));
const prodiField = (o: Opsi, s: { prodiId?: string; fakultas: boolean }, wajib = true): DefField => ({
  nama: "prodi_id", label: "Program studi", jenis: "pilihan", wajib, pilihan: s.fakultas ? o.prodi : o.prodi.filter((p) => p.nilai === s.prodiId),
  bantuan: s.fakultas ? undefined : "Terkunci pada prodi Anda.",
});
const tahunField = (o: Opsi, nama = "tahun_akademik_id", label = "Tahun akademik"): DefField => ({ nama, label, jenis: "pilihan", wajib: true, pilihan: o.tahun });
const awalTahun = (o: Opsi) => ({ tahun_akademik_id: o.tahun[0]?.nilai ?? "" });

const angkaField = (nama: string, label: string, extra: Partial<DefField> = {}): DefField => ({ nama, label, jenis: "angka", ...extra });

export const SUMBER_DATA: Record<string, SumberCfg> = {
  dosen: {
    path: "dosen", judul: "Dosen", sub: "Data dosen bersifat bersama lintas prodi; kontribusinya dihitung proporsional (tanpa hitung ganda).", pengikat: "afiliasi",
    bersarang: ["afiliasi"], kolomImpor: "nama, pendidikan_tertinggi, status_kepegawaian, nidn, nuptk, jabatan_akademik, email",
    petunjukImpor: "Impor dosen tanpa afiliasi hanya untuk Staf Fakultas; afiliasi prodi diatur dari formulir dosen.",
    awal: () => ({ pendidikan_tertinggi: "s3", status_kepegawaian: "tetap", is_aktif: true, afiliasi: [] }),
    def: () => [
      { nama: "nama", label: "Nama", wajib: true }, { nama: "nidn", label: "NIDN" }, { nama: "nuptk", label: "NUPTK" }, { nama: "email", label: "Surel", jenis: "email" },
      { nama: "gelar_depan", label: "Gelar depan" }, { nama: "gelar_belakang", label: "Gelar belakang" },
      { nama: "pendidikan_tertinggi", label: "Pendidikan tertinggi", jenis: "pilihan", wajib: true, pilihan: [{ nilai: "s1", label: "S1" }, { nilai: "s2", label: "S2" }, { nilai: "s3", label: "S3" }, { nilai: "profesi", label: "Profesi" }, { nilai: "spesialis", label: "Spesialis" }] },
      { nama: "jabatan_akademik", label: "Jabatan akademik", jenis: "pilihan", pilihan: pilihan("tenaga_pengajar", "asisten_ahli", "lektor", "lektor_kepala", "guru_besar") },
      { nama: "status_kepegawaian", label: "Status kepegawaian", jenis: "pilihan", wajib: true, pilihan: pilihan("tetap", "tidak_tetap", "praktisi") },
      { nama: "bidang_keahlian", label: "Bidang keahlian" },
      { nama: "punya_sertifikat_pendidik", label: "Memiliki sertifikat pendidik", jenis: "centang" }, { nama: "is_aktif", label: "Aktif", jenis: "centang" },
    ],
    kolom: [
      { kunci: "nama", judul: "Dosen", render: (r) => judulCell(`${r.gelar_depan ?? ""} ${r.nama}${r.gelar_belakang ? `, ${r.gelar_belakang}` : ""}`.trim(), `NIDN ${r.nidn ?? "—"}`) },
      { kunci: "jab", judul: "Jabatan / pendidikan", render: (r) => <span>{(r.jabatan_akademik ?? "—").replace(/_/g, " ")}<div className="cell-sub">{String(r.pendidikan_tertinggi).toUpperCase()} · {r.status_kepegawaian.replace(/_/g, " ")}</div></span> },
      { kunci: "prodi", judul: "Afiliasi", render: prodiCell }, kolomStatus,
    ],
    filter: [{ nama: "status_kepegawaian", label: "Status", pilihan: pilihan("tetap", "tidak_tetap", "praktisi") }],
  },
  "statistik-mahasiswa": {
    path: "statistik-mahasiswa", judul: "Statistik mahasiswa", sub: "Daya tampung, pendaftar, mahasiswa baru, dan mahasiswa aktif per prodi per tahun.", tahun: true, pengikat: "langsung",
    kolomImpor: "prodi_kode, tahun_akademik_id, daya_tampung, pendaftar, lulus_seleksi, maba_reguler, maba_transfer, aktif_reguler, aktif_transfer, mahasiswa_asing",
    awal: (o) => ({ ...awalTahun(o) }),
    def: (o, s) => [prodiField(o, s), tahunField(o), angkaField("daya_tampung", "Daya tampung", { min: 0 }), angkaField("pendaftar", "Pendaftar", { min: 0 }), angkaField("lulus_seleksi", "Lulus seleksi", { min: 0 }),
      angkaField("maba_reguler", "Mahasiswa baru reguler", { min: 0 }), angkaField("maba_transfer", "Mahasiswa baru transfer", { min: 0 }), angkaField("aktif_reguler", "Aktif reguler", { min: 0 }),
      angkaField("aktif_transfer", "Aktif transfer", { min: 0 }), angkaField("mahasiswa_asing", "Mahasiswa asing", { min: 0 })],
    kolom: [
      { kunci: "prodi", judul: "Prodi", render: prodiCell }, { kunci: "tahun", judul: "Tahun", render: (r) => r._tahun },
      { kunci: "dt", judul: "Daya tampung", num: true, render: (r) => angka(r.daya_tampung) }, { kunci: "pd", judul: "Pendaftar", num: true, render: (r) => angka(r.pendaftar) },
      { kunci: "mb", judul: "Maba", num: true, render: (r) => angka((r.maba_reguler ?? 0) + (r.maba_transfer ?? 0)) }, { kunci: "ak", judul: "Aktif", num: true, render: (r) => angka((r.aktif_reguler ?? 0) + (r.aktif_transfer ?? 0)) }, kolomStatus,
    ],
  },
  "statistik-lulusan": {
    path: "statistik-lulusan", judul: "Statistik lulusan", sub: "Jumlah lulusan, IPK, masa studi, dan kelulusan tepat waktu per tahun lulus.", tahun: true, pengikat: "langsung",
    kolomImpor: "prodi_kode, tahun_akademik_id, jumlah_lulusan, ipk_min, ipk_rata, ipk_maks, masa_studi_rata_tahun, lulus_tepat_waktu",
    awal: (o) => ({ ...awalTahun(o) }),
    def: (o, s) => [prodiField(o, s), tahunField(o, "tahun_akademik_id", "Tahun lulus"), angkaField("jumlah_lulusan", "Jumlah lulusan", { min: 0 }), angkaField("lulus_tepat_waktu", "Lulus tepat waktu", { min: 0 }),
      angkaField("ipk_min", "IPK minimum", { min: 0, max: 4 }), angkaField("ipk_rata", "IPK rata-rata", { min: 0, max: 4 }), angkaField("ipk_maks", "IPK maksimum", { min: 0, max: 4 }), angkaField("masa_studi_rata_tahun", "Masa studi rata-rata (tahun)", { min: 0 })],
    kolom: [
      { kunci: "prodi", judul: "Prodi", render: prodiCell }, { kunci: "tahun", judul: "Tahun lulus", render: (r) => r._tahun }, { kunci: "jl", judul: "Lulusan", num: true, render: (r) => angka(r.jumlah_lulusan) },
      { kunci: "tw", judul: "Tepat waktu", num: true, render: (r) => angka(r.lulus_tepat_waktu) }, { kunci: "ipk", judul: "IPK rata-rata", num: true, render: (r) => angka(r.ipk_rata, 2) },
      { kunci: "ms", judul: "Masa studi", num: true, render: (r) => angka(r.masa_studi_rata_tahun, 1) }, kolomStatus,
    ],
  },
  kurikulum: {
    path: "kurikulum", judul: "Kurikulum", sub: "Kurikulum prodi beserta mata kuliah (dikelola dari rincian kurikulum).", pengikat: "langsung",
    kolomImpor: "prodi_kode, nama, tahun_berlaku, is_aktif",
    awal: () => ({ is_aktif: true, tahun_berlaku: new Date().getFullYear() }),
    def: (o, s) => [prodiField(o, s), { nama: "nama", label: "Nama kurikulum", wajib: true }, angkaField("tahun_berlaku", "Tahun berlaku", { wajib: true, langkah: "1", min: 1950, max: 2100 }), { nama: "is_aktif", label: "Kurikulum aktif", jenis: "centang" }],
    kolom: [{ kunci: "nama", judul: "Kurikulum", render: (r) => judulCell(r.nama, `Berlaku ${r.tahun_berlaku}`) }, { kunci: "prodi", judul: "Prodi", render: prodiCell }, { kunci: "aktif", judul: "Aktif", render: (r) => (r.is_aktif ? <Pill warna="lime">Aktif</Pill> : <Pill>Nonaktif</Pill>) }, kolomStatus],
  },
  penelitian: {
    path: "penelitian", judul: "Penelitian", sub: "Penelitian dosen, hibah, dan pendanaannya. Satu penelitian dapat diatribusikan ke beberapa prodi.", tahun: true, pengikat: "penghubung", bersarang: ["dosen", "atribusi_prodi"],
    kolomImpor: "prodi_kode, judul, tahun_akademik_id, sumber_dana, jumlah_dana, jumlah_mahasiswa, nama_pemberi_dana, nomor_kontrak",
    awal: (o) => ({ ...awalTahun(o), sumber_dana: "pt_mandiri", jumlah_dana: 0, jumlah_mahasiswa: 0, dosen: [], atribusi_prodi: [] }),
    def: (o) => kegiatanDef(o),
    kolom: kolomKegiatan(),
    filter: [{ nama: "sumber_dana", label: "Sumber dana", pilihan: [{ nilai: "pt_mandiri", label: "PT mandiri" }, { nilai: "dalam_negeri", label: "Dalam negeri" }, { nilai: "luar_negeri", label: "Luar negeri" }] }],
  },
  pkm: {
    path: "pkm", judul: "Pengabdian kepada masyarakat", sub: "Kegiatan PkM, hibah, dan pendanaannya.", tahun: true, pengikat: "penghubung", bersarang: ["dosen", "atribusi_prodi"],
    kolomImpor: "prodi_kode, judul, tahun_akademik_id, sumber_dana, jumlah_dana, jumlah_mahasiswa, nama_pemberi_dana, nomor_kontrak",
    awal: (o) => ({ ...awalTahun(o), sumber_dana: "pt_mandiri", jumlah_dana: 0, jumlah_mahasiswa: 0, dosen: [], atribusi_prodi: [] }),
    def: (o) => kegiatanDef(o),
    kolom: kolomKegiatan(),
    filter: [{ nama: "sumber_dana", label: "Sumber dana", pilihan: [{ nilai: "pt_mandiri", label: "PT mandiri" }, { nilai: "dalam_negeri", label: "Dalam negeri" }, { nilai: "luar_negeri", label: "Luar negeri" }] }],
  },
  publikasi: {
    path: "publikasi", judul: "Publikasi & luaran", sub: "Jurnal, prosiding, buku, dan HKI. DOI yang sama selalu ditolak; kemiripan judul memunculkan peringatan.", tahun: true, pengikat: "penghubung", bersarang: ["penulis", "atribusi_prodi"],
    kolomImpor: "prodi_kode, judul, jenis, tingkat, nama_media, tahun_terbit, tahun_akademik_id, doi, url, jumlah_sitasi, jumlah_mahasiswa",
    awal: (o) => ({ ...awalTahun(o), jenis: "jurnal", tahun_terbit: new Date().getFullYear(), jumlah_sitasi: 0, jumlah_mahasiswa: 0, penulis: [], atribusi_prodi: [] }),
    def: (o) => [
      { nama: "judul", label: "Judul", wajib: true, span2: true },
      { nama: "jenis", label: "Jenis", jenis: "pilihan", wajib: true, pilihan: pilihan("jurnal", "prosiding", "buku", "bab_buku", "paten", "paten_sederhana", "hak_cipta", "desain_industri", "teknologi_tepat_guna", "lainnya") },
      { nama: "tingkat", label: "Tingkat", jenis: "pilihan", pilihan: pilihan("internasional_bereputasi", "internasional", "nasional_terakreditasi", "nasional", "lokal") },
      { nama: "nama_media", label: "Nama jurnal / prosiding / penerbit" }, angkaField("tahun_terbit", "Tahun terbit", { wajib: true, langkah: "1", min: 1950, max: 2100 }), tahunField(o),
      { nama: "doi", label: "DOI", bantuan: "mis. 10.1000/xyz123" }, { nama: "url", label: "URL", jenis: "url" }, angkaField("jumlah_sitasi", "Jumlah sitasi", { min: 0, langkah: "1" }), angkaField("jumlah_mahasiswa", "Mahasiswa terlibat", { min: 0, langkah: "1" }),
    ],
    kolom: [
      { kunci: "judul", judul: "Publikasi", render: (r) => judulCell(r.judul, `${r.nama_media ?? "—"}${r.doi ? ` · DOI ${r.doi}` : ""}`) },
      { kunci: "jenis", judul: "Jenis", render: (r) => <span>{String(r.jenis).replace(/_/g, " ")}<div className="cell-sub">{String(r.tingkat ?? "—").replace(/_/g, " ")}</div></span> },
      { kunci: "tahun", judul: "Terbit", num: true, render: (r) => r.tahun_terbit }, { kunci: "prodi", judul: "Atribusi prodi", render: prodiCell }, kolomStatus,
    ],
    filter: [{ nama: "jenis", label: "Jenis", pilihan: pilihan("jurnal", "prosiding", "buku", "paten", "hak_cipta") }],
  },
  "kerja-sama": {
    path: "kerja-sama", judul: "Kerja sama", sub: "Kerja sama dengan mitra di bidang pendidikan, penelitian, dan PkM. Dikelola Staf Fakultas atau prodi terkait.", pengikat: "penghubung", bersarang: ["prodi_ids"],
    kolomImpor: "prodi_kode, nama_mitra, tingkat, judul_kegiatan, tanggal_mulai, tanggal_selesai, bidang_pendidikan, bidang_penelitian, bidang_pkm, nomor_dokumen, manfaat",
    awal: () => ({ tingkat: "nasional", bidang_pendidikan: true, prodi_ids: [] }),
    def: () => [
      { nama: "nama_mitra", label: "Nama mitra", wajib: true }, { nama: "tingkat", label: "Tingkat", jenis: "pilihan", wajib: true, pilihan: pilihan("internasional", "nasional", "lokal") },
      { nama: "judul_kegiatan", label: "Judul kegiatan", wajib: true, span2: true }, { nama: "nomor_dokumen", label: "Nomor dokumen / PKS" },
      { nama: "tanggal_mulai", label: "Mulai", jenis: "tanggal", wajib: true }, { nama: "tanggal_selesai", label: "Selesai", jenis: "tanggal" },
      { nama: "bidang_pendidikan", label: "Bidang pendidikan", jenis: "centang" }, { nama: "bidang_penelitian", label: "Bidang penelitian", jenis: "centang" }, { nama: "bidang_pkm", label: "Bidang PkM", jenis: "centang" },
      { nama: "manfaat", label: "Manfaat bagi prodi", jenis: "teksArea" },
    ],
    kolom: [
      { kunci: "mitra", judul: "Mitra", render: (r) => judulCell(r.nama_mitra, r.judul_kegiatan) }, { kunci: "tingkat", judul: "Tingkat", render: (r) => <Pill warna={r.tingkat === "internasional" ? "blue" : ""}>{r.tingkat}</Pill> },
      { kunci: "masa", judul: "Masa", render: (r) => `${tanggal(r.tanggal_mulai)} – ${tanggal(r.tanggal_selesai)}` },
      { kunci: "bidang", judul: "Bidang", render: (r) => <div className="chips">{r.bidang_pendidikan && <Pill>Pendidikan</Pill>}{r.bidang_penelitian && <Pill>Penelitian</Pill>}{r.bidang_pkm && <Pill>PkM</Pill>}</div> },
      { kunci: "prodi", judul: "Prodi", render: prodiCell }, kolomStatus,
    ],
    filter: [{ nama: "tingkat", label: "Tingkat", pilihan: pilihan("internasional", "nasional", "lokal") }],
  },
  sarana: {
    path: "sarana", judul: "Sarana & prasarana", sub: "Ruang, laboratorium, perpustakaan, dan peralatan. Sarana bersama fakultas dikelola Staf Fakultas.", pengikat: "penghubung", bersarang: ["prodi_ids"],
    kolomImpor: "prodi_kode, nama, jenis, lokasi, kapasitas, jumlah, kepemilikan, kondisi",
    awal: () => ({ jenis: "laboratorium", jumlah: 1, kepemilikan: "milik_sendiri", kondisi: "baik", is_bersama: false, prodi_ids: [] }),
    def: (_o, s) => [
      { nama: "nama", label: "Nama", wajib: true }, { nama: "jenis", label: "Jenis", jenis: "pilihan", wajib: true, pilihan: pilihan("ruang_kuliah", "laboratorium", "perpustakaan", "peralatan", "perangkat_lunak", "lainnya") },
      { nama: "lokasi", label: "Lokasi" }, angkaField("kapasitas", "Kapasitas", { min: 0, langkah: "1" }), angkaField("jumlah", "Jumlah unit", { min: 0, langkah: "1" }),
      { nama: "kepemilikan", label: "Kepemilikan", jenis: "pilihan", pilihan: pilihan("milik_sendiri", "sewa", "kerja_sama") }, { nama: "kondisi", label: "Kondisi", jenis: "pilihan", pilihan: pilihan("baik", "rusak_ringan", "rusak_berat") },
      ...(s.fakultas ? [{ nama: "is_bersama", label: "Sarana bersama (milik fakultas)", jenis: "centang" as const, bantuan: "Hanya Staf Fakultas yang dapat mengubahnya." }] : []),
    ],
    kolom: [
      { kunci: "nama", judul: "Sarana", render: (r) => judulCell(r.nama, r.lokasi ?? undefined) }, { kunci: "jenis", judul: "Jenis", render: (r) => String(r.jenis).replace(/_/g, " ") },
      { kunci: "jml", judul: "Jumlah", num: true, render: (r) => angka(r.jumlah) }, { kunci: "kondisi", judul: "Kondisi", render: (r) => <Pill warna={r.kondisi === "baik" ? "lime" : r.kondisi === "rusak_ringan" ? "amber" : "red"}>{String(r.kondisi).replace(/_/g, " ")}</Pill> },
      { kunci: "prodi", judul: "Prodi", render: (r) => (r.is_bersama ? <Pill warna="blue">Bersama</Pill> : prodiCell(r)) }, kolomStatus,
    ],
    filter: [{ nama: "jenis", label: "Jenis", pilihan: pilihan("ruang_kuliah", "laboratorium", "perpustakaan", "peralatan") }],
  },
  keuangan: {
    path: "keuangan", judul: "Keuangan", sub: "Perolehan dan penggunaan dana per tahun. Baris tanpa prodi adalah tingkat UPPS (Staf Fakultas).", tahun: true, pengikat: "langsung",
    kolomImpor: "prodi_kode, tahun_akademik_id, arah, kategori, jumlah",
    awal: (o) => ({ ...awalTahun(o), arah: "penggunaan" }),
    def: (o, s) => [{ ...prodiField(o, s, false), bantuan: s.fakultas ? "Kosongkan untuk tingkat UPPS/fakultas." : "Terkunci pada prodi Anda." }, tahunField(o),
      { nama: "arah", label: "Arah", jenis: "pilihan", wajib: true, pilihan: [{ nilai: "perolehan", label: "Perolehan" }, { nilai: "penggunaan", label: "Penggunaan" }] },
      { nama: "kategori", label: "Kategori", wajib: true, bantuan: "mis. operasional_pendidikan, penelitian, pkm, investasi_sdm" }, angkaField("jumlah", "Jumlah (Rp)", { wajib: true, min: 0 })],
    kolom: [
      { kunci: "kat", judul: "Kategori", render: (r) => judulCell(String(r.kategori).replace(/_/g, " "), r.arah === "perolehan" ? "Perolehan" : "Penggunaan") },
      { kunci: "tahun", judul: "Tahun", render: (r) => r._tahun }, { kunci: "prodi", judul: "Cakupan", render: prodiCell }, { kunci: "jml", judul: "Jumlah", num: true, render: (r) => rupiah(r.jumlah) }, kolomStatus,
    ],
    filter: [{ nama: "arah", label: "Arah", pilihan: [{ nilai: "perolehan", label: "Perolehan" }, { nilai: "penggunaan", label: "Penggunaan" }] }],
  },
};

function kegiatanDef(o: Opsi): DefField[] {
  return [
    { nama: "judul", label: "Judul", wajib: true, span2: true }, tahunField(o),
    { nama: "sumber_dana", label: "Sumber dana", jenis: "pilihan", wajib: true, pilihan: [{ nilai: "pt_mandiri", label: "PT mandiri" }, { nilai: "dalam_negeri", label: "Dalam negeri" }, { nilai: "luar_negeri", label: "Luar negeri" }] },
    { nama: "nama_pemberi_dana", label: "Pemberi dana" }, { nama: "nomor_kontrak", label: "Nomor kontrak" }, angkaField("jumlah_dana", "Jumlah dana (Rp)", { min: 0 }), angkaField("jumlah_mahasiswa", "Mahasiswa terlibat", { min: 0, langkah: "1" }),
  ];
}
function kolomKegiatan(): Kolom<Rec>[] {
  return [
    { kunci: "judul", judul: "Kegiatan", render: (r) => judulCell(r.judul, r.nomor_kontrak ? `Kontrak ${r.nomor_kontrak}` : undefined) },
    { kunci: "tahun", judul: "Tahun", render: (r) => r._tahun }, { kunci: "dana", judul: "Dana", num: true, render: (r) => rupiah(r.jumlah_dana) }, { kunci: "sumber", judul: "Sumber", render: (r) => String(r.sumber_dana).replace(/_/g, " ") },
    { kunci: "dosen", judul: "Dosen", num: true, render: (r) => r.dosen?.length ?? 0 }, { kunci: "prodi", judul: "Atribusi prodi", render: prodiCell }, kolomStatus,
  ];
}

