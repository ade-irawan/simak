/** Peta sumber data inti (nilai `jenis_entitas`) → label dan tujuan tautan. */
export const SUMBER: Record<string, { label: string; to: string }> = {
  dosen: { label: "Dosen", to: "/data/dosen" },
  mahasiswa_statistik: { label: "Statistik mahasiswa", to: "/data/statistik-mahasiswa" },
  lulusan_statistik: { label: "Statistik lulusan", to: "/data/statistik-lulusan" },
  kurikulum: { label: "Kurikulum", to: "/data/kurikulum" },
  mata_kuliah: { label: "Mata kuliah", to: "/data/kurikulum" },
  penelitian: { label: "Penelitian", to: "/data/penelitian" },
  pkm: { label: "Pengabdian kepada masyarakat", to: "/data/pkm" },
  publikasi: { label: "Publikasi & luaran", to: "/data/publikasi" },
  kerja_sama: { label: "Kerja sama", to: "/data/kerja-sama" },
  sarana_prasarana: { label: "Sarana & prasarana", to: "/data/sarana" },
  keuangan: { label: "Keuangan", to: "/data/keuangan" },
  indikator_eksternal: { label: "Tracer study & kepuasan (Direktorat)", to: "/dokumen-eksternal" },
  tahapan_ppepp: { label: "Tahapan PPEPP", to: "/ppepp" },
};

export const MASALAH: Record<string, string> = {
  belum_mulai: "Belum dimulai",
  status_draft: "Masih berstatus draf",
  bukti_tidak_terjangkau: "Bukti tidak terjangkau",
  menunggu_dokumen_eksternal: "Menunggu dokumen dari Direktorat",
  data_kurang: "Data pendukung belum ada",
};
