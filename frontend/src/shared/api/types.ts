/** Bentuk respons yang dipakai lintas fitur. Respons besar/dinamis memakai `Rec`. */
export type Rec = Record<string, any>;
export type Id = string;

export type Peran = "dekan" | "kaprodi" | "staf_prodi" | "staf_fakultas" | "asesor" | "admin_it";

export const NAMA_PERAN: Record<Peran, string> = {
  dekan: "Dekan",
  kaprodi: "Kaprodi",
  staf_prodi: "Staf Admin Prodi",
  staf_fakultas: "Staf Admin Fakultas",
  asesor: "Asesor",
  admin_it: "Administrator Sistem/IT",
};

export interface ProdiRef {
  id: Id;
  kode: string;
  nama: string;
}

export interface PeranPengguna {
  penugasan_id: Id;
  peran: Peran;
  prodi: ProdiRef | null;
  instrumen: { lam: string; kode_versi: string | null } | null;
  berlaku_sampai: string | null;
}

export interface Profil {
  id: Id;
  nama: string;
  email: string;
  wajib_ganti_sandi: boolean;
  peran: PeranPengguna[];
}

export interface Halaman<T> {
  data: T[];
  meta: { page: number; per_page: number; total: number; belum_dibaca?: number };
}

export type StatusKelengkapan = "belum_mulai" | "draft" | "lengkap";
export type StatusLaporan = "draft" | "menunggu_validasi" | "disetujui";
