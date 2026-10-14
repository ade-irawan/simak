import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { labelEnum } from "../lib/format";

type Warna = "blue" | "lime" | "red" | "amber" | "";

export function Pill({ warna = "", dot, children }: { warna?: Warna; dot?: boolean; children: ReactNode }) {
  return <span className={`pill${warna ? ` pill--${warna}` : ""}${dot ? " pill--dot" : ""}`}>{children}</span>;
}

const WARNA_STATUS: Record<string, Warna> = {
  // kelengkapan butir
  belum_mulai: "", draft: "amber", lengkap: "lime",
  // laporan
  menunggu_validasi: "blue", disetujui: "lime", dikembalikan: "red", menunggu: "blue",
  // data inti
  terverifikasi: "lime",
  // bukti
  ok: "lime", tidak_terjangkau: "red", belum_dicek: "",
  // tugas & umum
  antre: "", diproses: "blue", selesai: "lime", gagal: "red",
  aktif: "lime", nonaktif: "", diusulkan: "amber", dicabut: "red", arsip: "", draf: "amber",
  persiapan: "amber", berjalan: "blue", ditetapkan: "blue", dibatalkan: "red", digantikan: "",
  berkas: "blue", tautan: "",
  merah: "red", kuning: "amber", hijau: "lime", abu: "",
};

export function StatusPill({ status }: { status?: string | null }) {
  if (!status) return <span className="faint">—</span>;
  return (
    <Pill warna={WARNA_STATUS[status] ?? ""} dot>
      {labelEnum(status)}
    </Pill>
  );
}

export function Progress({ nilai, warna }: { nilai: number; warna?: "red" | "amber" | "lime" }) {
  const v = Math.max(0, Math.min(100, nilai));
  return (
    <div className={`progress${warna ? ` progress--${warna}` : ""}`} role="progressbar" aria-valuenow={Math.round(v)} aria-valuemin={0} aria-valuemax={100}>
      <div className="progress__bar" style={{ width: `${v}%` }} />
    </div>
  );
}

export function Risiko({ tingkat }: { tingkat: string }) {
  const label: Record<string, string> = { merah: "Berisiko tinggi", kuning: "Perlu perhatian", hijau: "Sesuai jalur", abu: "Belum dimulai" };
  return (
    <span className="risk">
      <span className={`dot dot--${tingkat}`} />
      {label[tingkat] ?? tingkat}
    </span>
  );
}

export function Card({
  judul,
  sub,
  aksi,
  aksen,
  children,
  flush,
  className = "",
}: {
  judul?: ReactNode;
  sub?: ReactNode;
  aksi?: ReactNode;
  aksen?: "blue" | "red" | "lime" | "amber";
  flush?: boolean;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card${flush ? " card--flush" : ""}${aksen ? ` card--accent-${aksen}` : ""} ${className}`}>
      {(judul || aksi) && (
        <div className="card__head" style={flush ? { padding: "1.2rem 1.4rem 0" } : undefined}>
          <div>
            {judul && <h2 className="card__title">{judul}</h2>}
            {sub && <div className="card__sub">{sub}</div>}
          </div>
          {aksi && <div className="row">{aksi}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

export function PageHead({
  judul,
  sub,
  aksi,
  crumbs,
}: {
  judul: ReactNode;
  sub?: ReactNode;
  aksi?: ReactNode;
  crumbs?: { label: string; to?: string }[];
}) {
  return (
    <header>
      {crumbs && (
        <nav className="crumbs" aria-label="Jejak halaman">
          {crumbs.map((c, i) => (
            <span key={i}>
              {c.to ? <Link to={c.to}>{c.label}</Link> : c.label}
              {i < crumbs.length - 1 && " /"}
            </span>
          ))}
        </nav>
      )}
      <div className="page-head">
        <div>
          <h1>{judul}</h1>
          {sub && <p>{sub}</p>}
        </div>
        {aksi && <div className="row">{aksi}</div>}
      </div>
    </header>
  );
}

export function Metric({ nilai, label, warna }: { nilai: ReactNode; label: string; warna?: "blue" | "lime" | "red" | "amber" }) {
  const c = { blue: "var(--blue)", lime: "var(--lime)", red: "var(--red)", amber: "var(--amber)" };
  return (
    <div className="metric">
      <div className="metric__value" style={warna ? { color: c[warna] } : undefined}>
        {nilai}
      </div>
      <div className="metric__label">{label}</div>
    </div>
  );
}

export function KV({ item }: { item: [string, ReactNode][] }) {
  return (
    <dl className="kv">
      {item.map(([k, v]) => (
        <div key={k} style={{ display: "contents" }}>
          <dt>{k}</dt>
          <dd>{v ?? "—"}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <div className="eyebrow">
      <span className="eyebrow__dot" />
      {children}
    </div>
  );
}
