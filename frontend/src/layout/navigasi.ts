import type { Peran } from "@/shared/api/types";
import type { IconName } from "@/shared/ui";

export interface ItemNav {
  to: string;
  label: string;
  ikon: IconName;
  peran: Peran[];
  /** pencocokan awalan; default hanya path yang sama persis */
  awalan?: boolean;
}
export interface GrupNav {
  judul: string;
  item: ItemNav[];
}

const SEMUA_KONTEN: Peran[] = ["dekan", "kaprodi", "staf_prodi", "staf_fakultas"];

/** Menu sidebar per peran. Admin IT sengaja tidak punya menu konten (pemisahan tugas). */
export const NAVIGASI: GrupNav[] = [
  {
    judul: "Pemantauan",
    item: [
      { to: "/", label: "Beranda", ikon: "home", peran: ["dekan", "kaprodi", "staf_prodi", "staf_fakultas", "asesor", "admin_it"] },
      { to: "/papan-kerja", label: "Papan kerja saya", ikon: "clipboard", peran: ["staf_prodi", "staf_fakultas"] },
      { to: "/analisis", label: "Gap & benchmarking", ikon: "compare", peran: ["dekan"] },
    ],
  },
  {
    judul: "Akreditasi",
    item: [
      { to: "/siklus", label: "Siklus & butir", ikon: "layers", peran: SEMUA_KONTEN, awalan: true },
      { to: "/ppepp", label: "Penjaminan mutu (PPEPP)", ikon: "target", peran: SEMUA_KONTEN, awalan: true },
      { to: "/usulan-asesor", label: "Usulan asesor", ikon: "user", peran: ["kaprodi"] },
      { to: "/asesmen", label: "Telaah asesmen", ikon: "eye", peran: ["asesor"], awalan: true },
    ],
  },
  {
    judul: "Data inti Tridharma",
    item: [
      { to: "/data/dosen", label: "Dosen", ikon: "users", peran: SEMUA_KONTEN },
      { to: "/data/statistik-mahasiswa", label: "Mahasiswa", ikon: "user", peran: SEMUA_KONTEN },
      { to: "/data/statistik-lulusan", label: "Lulusan", ikon: "award", peran: SEMUA_KONTEN },
      { to: "/data/kurikulum", label: "Kurikulum", ikon: "book", peran: SEMUA_KONTEN },
      { to: "/data/penelitian", label: "Penelitian", ikon: "flask", peran: SEMUA_KONTEN },
      { to: "/data/pkm", label: "Pengabdian (PkM)", ikon: "heart", peran: SEMUA_KONTEN },
      { to: "/data/publikasi", label: "Publikasi & luaran", ikon: "file", peran: SEMUA_KONTEN },
      { to: "/data/kerja-sama", label: "Kerja sama", ikon: "handshake", peran: SEMUA_KONTEN },
      { to: "/data/sarana", label: "Sarana & prasarana", ikon: "building", peran: SEMUA_KONTEN },
      { to: "/data/keuangan", label: "Keuangan", ikon: "wallet", peran: SEMUA_KONTEN },
    ],
  },
  {
    judul: "Bukti & dokumen",
    item: [
      { to: "/bukti", label: "Bukti (berkas/tautan)", ikon: "paperclip", peran: SEMUA_KONTEN },
      { to: "/dokumen-eksternal", label: "Tracer & kepuasan", ikon: "inbox", peran: SEMUA_KONTEN },
    ],
  },
  {
    judul: "Konfigurasi",
    item: [
      { to: "/instrumen", label: "Instrumen & pemetaan", ikon: "database", peran: ["dekan", "staf_fakultas", "kaprodi", "staf_prodi"], awalan: true },
      { to: "/llm", label: "Generator LED (LLM)", ikon: "sparkles", peran: ["dekan", "staf_fakultas"] },
    ],
  },
  {
    judul: "Administrasi",
    item: [
      { to: "/pengguna", label: "Akun & penugasan", ikon: "users", peran: ["dekan", "admin_it"], awalan: true },
      { to: "/audit", label: "Log audit", ikon: "history", peran: ["dekan", "admin_it"] },
      { to: "/pengaturan", label: "Pengaturan sistem", ikon: "settings", peran: ["admin_it"] },
    ],
  },
];
