import type { ReactNode } from "react";
import { ApiError } from "../api/client";
import { Icon, type IconName } from "./Icon";

export function Spinner() {
  return <span className="spinner" role="status" aria-label="Memuat" />;
}

export function Loading({ teks = "Memuat…" }: { teks?: string }) {
  return (
    <div className="loading">
      <Spinner />
      <span>{teks}</span>
    </div>
  );
}

export function Empty({ judul, children, ikon = "inbox" }: { judul: string; children?: ReactNode; ikon?: IconName }) {
  return (
    <div className="empty">
      <Icon name={ikon} size={34} style={{ margin: "0 auto 0.8rem", opacity: 0.6 }} />
      <h3>{judul}</h3>
      {children && <div>{children}</div>}
    </div>
  );
}

const IKON: Record<string, IconName> = { info: "info", warn: "alert", danger: "alert", ok: "checkCircle" };

export function Alert({ jenis = "info", judul, children }: { jenis?: "info" | "warn" | "danger" | "ok"; judul?: ReactNode; children?: ReactNode }) {
  return (
    <div className={`alert alert--${jenis}`} role={jenis === "danger" ? "alert" : undefined}>
      <Icon name={IKON[jenis]} />
      <div>
        {judul && <strong>{judul}</strong>}
        {children && <div className={judul ? "muted" : ""}>{children}</div>}
      </div>
    </div>
  );
}

/** Menampilkan galat API lengkap dengan rincian per kolom/butir. */
export function ErrorBox({ error }: { error: unknown }) {
  if (!error) return null;
  const e = error instanceof ApiError ? error : null;
  const rincian = (e?.details ?? []).slice(0, 12);
  return (
    <Alert jenis="danger" judul={e?.message ?? (error instanceof Error ? error.message : "Terjadi kesalahan.")}>
      {rincian.length > 0 && (
        <ul>
          {rincian.map((d, i) => (
            <li key={i}>{detailTeks(d)}</li>
          ))}
        </ul>
      )}
    </Alert>
  );
}

function detailTeks(d: Record<string, unknown>): string {
  const bagian: string[] = [];
  if (d.kolom) bagian.push(String(d.kolom));
  if (d.kode) bagian.push(`butir ${d.kode}`);
  if (d.pesan) bagian.push(String(d.pesan));
  if (Array.isArray(d.masalah)) bagian.push((d.masalah as string[]).map((m) => m.replace(/_/g, " ")).join(", "));
  if (d.alasan) bagian.push(String(d.alasan).replace(/_/g, " "));
  if (d.sisa_percobaan !== undefined) bagian.push(`sisa percobaan: ${d.sisa_percobaan}`);
  if (d.terkunci_sampai) bagian.push(`terkunci sampai ${new Date(String(d.terkunci_sampai)).toLocaleTimeString("id-ID")}`);
  return bagian.length ? bagian.join(" — ") : JSON.stringify(d).slice(0, 160);
}

/** Pembungkus status query: memuat → galat → isi. */
export function Muat<T>({
  q,
  children,
  kosong,
}: {
  q: { isLoading: boolean; error: unknown; data: T | undefined };
  children: (data: T) => ReactNode;
  kosong?: ReactNode;
}) {
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorBox error={q.error} />;
  if (q.data === undefined || q.data === null) return <>{kosong ?? null}</>;
  return <>{children(q.data)}</>;
}
