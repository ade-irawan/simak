import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, ApiError, refreshSession, setAccessToken, setOnSessionExpired } from "../api/client";
import type { Peran, PeranPengguna, Profil } from "../api/types";

interface AuthState {
  profil: Profil | null;
  memuat: boolean;
  /** Penugasan yang sedang dipakai (satu pengguna dapat memiliki beberapa peran). */
  aktif: PeranPengguna | null;
  setAktif: (id: string) => void;
  punya: (...peran: Peran[]) => boolean;
  masuk: (email: string, password: string) => Promise<Profil>;
  keluar: () => Promise<void>;
  muatUlang: () => Promise<void>;
  /** Prodi pertama milik pemanggil (Kaprodi/Staf Prodi/Asesor), bila ada. */
  prodiSaya: () => PeranPengguna["prodi"];
}

const Ctx = createContext<AuthState | null>(null);
const URUTAN: Peran[] = ["dekan", "kaprodi", "staf_fakultas", "staf_prodi", "asesor", "admin_it"];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [profil, setProfil] = useState<Profil | null>(null);
  const [memuat, setMemuat] = useState(true);
  const [aktifId, setAktifId] = useState<string | null>(null);
  const qc = useQueryClient();

  const terapkan = useCallback((p: Profil | null) => {
    setProfil(p);
    setAktifId((lama) => {
      if (!p) return null;
      if (lama && p.peran.some((x) => x.penugasan_id === lama)) return lama;
      return [...p.peran].sort((a, b) => URUTAN.indexOf(a.peran) - URUTAN.indexOf(b.peran))[0]?.penugasan_id ?? null;
    });
  }, []);

  const bersihkan = useCallback(() => {
    setAccessToken(null);
    terapkan(null);
    qc.clear();
  }, [qc, terapkan]);

  useEffect(() => {
    setOnSessionExpired(bersihkan);
    (async () => {
      if (await refreshSession()) {
        try {
          terapkan(await api.get<Profil>("/auth/me"));
        } catch {
          bersihkan();
        }
      }
      setMemuat(false);
    })();
    return () => setOnSessionExpired(null);
  }, [bersihkan, terapkan]);

  const value = useMemo<AuthState>(() => {
    const aktif = profil?.peran.find((p) => p.penugasan_id === aktifId) ?? null;
    return {
      profil,
      memuat,
      aktif,
      setAktif: setAktifId,
      punya: (...peran) => !!aktif && peran.includes(aktif.peran),
      masuk: async (email, password) => {
        const r = await api.post<{ access_token: string; pengguna: Profil }>("/auth/login", { email, password });
        setAccessToken(r.access_token);
        qc.clear();
        terapkan(r.pengguna);
        return r.pengguna;
      },
      keluar: async () => {
        try {
          await api.post("/auth/logout");
        } catch (e) {
          if (!(e instanceof ApiError)) throw e;
        }
        bersihkan();
      },
      muatUlang: async () => terapkan(await api.get<Profil>("/auth/me")),
      prodiSaya: () => aktif?.prodi ?? null,
    };
  }, [profil, memuat, aktifId, qc, terapkan, bersihkan]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth harus dipakai di dalam AuthProvider");
  return c;
}
