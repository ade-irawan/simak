import type { ReactNode } from "react";
import { Button } from "./Button";
import { Empty } from "./Feedback";

export interface Kolom<T> {
  kunci: string;
  judul: string;
  render: (baris: T) => ReactNode;
  num?: boolean;
  lebar?: string;
}

export function Tabel<T>({
  kolom,
  baris,
  id,
  onKlik,
  kosong = "Belum ada data",
}: {
  kolom: Kolom<T>[];
  baris: T[];
  id: (b: T) => string;
  onKlik?: (b: T) => void;
  kosong?: ReactNode;
}) {
  if (baris.length === 0) return <div className="table-wrap"><Empty judul={typeof kosong === "string" ? kosong : "Belum ada data"}>{typeof kosong === "string" ? null : kosong}</Empty></div>;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            {kolom.map((k) => (
              <th key={k.kunci} className={k.num ? "num" : ""} style={k.lebar ? { width: k.lebar } : undefined}>
                {k.judul}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {baris.map((b) => (
            <tr
              key={id(b)}
              className={onKlik ? "is-clickable" : ""}
              onClick={onKlik ? () => onKlik(b) : undefined}
              onKeyDown={onKlik ? (e) => e.key === "Enter" && onKlik(b) : undefined}
              tabIndex={onKlik ? 0 : undefined}
            >
              {kolom.map((k) => (
                <td key={k.kunci} className={k.num ? "num" : ""}>
                  {k.render(b)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Pager({ page, perPage, total, onGanti }: { page: number; perPage: number; total: number; onGanti: (p: number) => void }) {
  const akhir = Math.max(1, Math.ceil(total / perPage));
  if (total <= perPage) return total ? <div className="pager"><span>{total} data</span></div> : null;
  const dari = (page - 1) * perPage + 1;
  return (
    <div className="pager">
      <span>
        {dari}–{Math.min(page * perPage, total)} dari {total}
      </span>
      <div className="row">
        <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => onGanti(page - 1)}>
          ← Sebelumnya
        </Button>
        <span>
          {page} / {akhir}
        </span>
        <Button variant="ghost" size="sm" disabled={page >= akhir} onClick={() => onGanti(page + 1)}>
          Berikutnya →
        </Button>
      </div>
    </div>
  );
}

export function Tabs<K extends string>({ tabs, aktif, onGanti }: { tabs: { kunci: K; label: string; jumlah?: number }[]; aktif: K; onGanti: (k: K) => void }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button key={t.kunci} role="tab" aria-selected={aktif === t.kunci} className={`tab${aktif === t.kunci ? " is-active" : ""}`} onClick={() => onGanti(t.kunci)}>
          {t.label}
          {t.jumlah !== undefined && <span className="tab__count">{t.jumlah}</span>}
        </button>
      ))}
    </div>
  );
}
