import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { ApiError } from "../api/client";
import { Icon } from "./Icon";

type Jenis = "ok" | "warn" | "danger" | "info";
interface Item {
  id: number;
  jenis: Jenis;
  teks: string;
}
interface ToastApi {
  ok: (t: string) => void;
  info: (t: string) => void;
  warn: (t: string) => void;
  galat: (e: unknown) => void;
}

const Ctx = createContext<ToastApi | null>(null);
let seq = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Item[]>([]);
  const tambah = useCallback((jenis: Jenis, teks: string) => {
    const id = ++seq;
    setItems((x) => [...x, { id, jenis, teks }]);
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), jenis === "danger" ? 7000 : 4200);
  }, []);
  const api = useMemo<ToastApi>(
    () => ({
      ok: (t) => tambah("ok", t),
      info: (t) => tambah("info", t),
      warn: (t) => tambah("warn", t),
      galat: (e) => tambah("danger", e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Terjadi kesalahan."),
    }),
    [tambah],
  );
  const ikon: Record<Jenis, "checkCircle" | "alert" | "info"> = { ok: "checkCircle", warn: "alert", danger: "alert", info: "info" };
  return (
    <Ctx.Provider value={api}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {items.map((i) => (
          <div key={i.id} className={`alert alert--${i.jenis} toast`}>
            <Icon name={ikon[i.jenis]} />
            <div>{i.teks}</div>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export function useToast(): ToastApi {
  const c = useContext(Ctx);
  if (!c) throw new Error("useToast harus dipakai di dalam ToastProvider");
  return c;
}
