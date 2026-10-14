import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import type { Peran } from "../api/types";
import { Empty, Loading } from "../ui";
import { useAuth } from "./AuthProvider";

/** Halaman yang butuh login; pengguna belum login diarahkan ke /masuk dan kembali ke tujuan semula. */
export function RequireAuth() {
  const { profil, memuat } = useAuth();
  const loc = useLocation();
  if (memuat) return <Loading teks="Menyiapkan sesi…" />;
  if (!profil) return <Navigate to="/masuk" replace state={{ dari: loc.pathname + loc.search }} />;
  if (profil.wajib_ganti_sandi && loc.pathname !== "/profil") return <Navigate to="/profil" replace />;
  return <Outlet />;
}

/** Batasi per peran aktif. Server tetap menjadi penentu akhir; ini hanya mencegah halaman yang pasti ditolak. */
export function RequirePeran({ peran, children }: { peran: Peran[]; children: ReactNode }) {
  const { aktif } = useAuth();
  if (!aktif) return null;
  if (!peran.includes(aktif.peran)) {
    return <Empty judul="Halaman tidak tersedia untuk peran Anda" ikon="lock">Hak akses ditentukan di server berdasarkan penugasan peran Anda.</Empty>;
  }
  return <>{children}</>;
}
