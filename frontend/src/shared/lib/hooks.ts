import { keepPreviousData, useMutation, useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { api, ApiError, type Query } from "../api/client";
import { useToast } from "../ui/Toast";

/** GET dengan cache. Kunci = [path, query] sehingga `invalidate(path)` membersihkan semua variannya. */
export function useApi<T = any>(path: string | null, query?: Query, options: { enabled?: boolean; keep?: boolean; refetchInterval?: number } = {}) {
  return useQuery<T, ApiError>({
    queryKey: [path, query ?? {}] as QueryKey,
    queryFn: () => api.get<T>(path as string, query),
    enabled: path !== null && options.enabled !== false,
    placeholderData: options.keep ? keepPreviousData : undefined,
    refetchInterval: options.refetchInterval,
  });
}

/** Mutasi dengan toast sukses/galat dan pembatalan cache berdasarkan awalan path. */
export function useAksi<TArg = void, TRes = any>(
  fn: (arg: TArg) => Promise<TRes>,
  opts: { sukses?: string | ((r: TRes) => string); invalidate?: string[]; onSuccess?: (r: TRes) => void; diam?: boolean } = {},
) {
  const qc = useQueryClient();
  const toast = useToast();
  return useMutation<TRes, ApiError, TArg>({
    mutationFn: fn,
    onSuccess: (r) => {
      (opts.invalidate ?? []).forEach((p) =>
        qc.invalidateQueries({ predicate: (q) => typeof q.queryKey[0] === "string" && (q.queryKey[0] as string).startsWith(p) }),
      );
      if (opts.sukses && !opts.diam) toast.ok(typeof opts.sukses === "function" ? opts.sukses(r) : opts.sukses);
      opts.onSuccess?.(r);
    },
    onError: (e) => {
      if (!opts.diam) toast.galat(e);
    },
  });
}

export function useInvalidate() {
  const qc = useQueryClient();
  return (...prefix: string[]) =>
    prefix.forEach((p) => qc.invalidateQueries({ predicate: (q) => typeof q.queryKey[0] === "string" && (q.queryKey[0] as string).startsWith(p) }));
}

export function useDebounced<T>(value: T, ms = 350): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

/** Simpan otomatis (EC-19): menunda penyimpanan sampai pengguna berhenti mengetik dan menyimpan status. */
export function useAutosave<T>(nilai: T, simpan: (v: T) => Promise<void>, aktif: boolean, ms = 1200) {
  const [status, setStatus] = useState<"diam" | "menyimpan" | "tersimpan" | "gagal">("diam");
  const awal = useRef(nilai);
  const terakhir = useRef(nilai);
  const simpanRef = useRef(simpan);
  simpanRef.current = simpan;
  useEffect(() => {
    if (!aktif || nilai === terakhir.current || nilai === awal.current) return;
    const t = setTimeout(async () => {
      setStatus("menyimpan");
      try {
        await simpanRef.current(nilai);
        terakhir.current = nilai;
        setStatus("tersimpan");
      } catch {
        setStatus("gagal");
      }
    }, ms);
    return () => clearTimeout(t);
  }, [nilai, aktif, ms]);
  return { status, setAwal: (v: T) => { awal.current = v; terakhir.current = v; } };
}
