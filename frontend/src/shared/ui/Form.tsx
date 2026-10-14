import { useState, type ReactNode } from "react";
import { Button } from "./Button";
import { Icon } from "./Icon";

export function Field({
  label,
  wajib,
  bantuan,
  galat,
  children,
  span2,
}: {
  label: string;
  wajib?: boolean;
  bantuan?: ReactNode;
  galat?: string;
  children: ReactNode;
  span2?: boolean;
}) {
  return (
    <div className={`field${galat ? " field--invalid" : ""}${span2 ? " span-2" : ""}`}>
      <label>
        {label}
        {wajib && <span className="field__req">*</span>}
      </label>
      {children}
      {bantuan && <div className="field__help">{bantuan}</div>}
      {galat && <div className="field__error">{galat}</div>}
    </div>
  );
}

export type JenisField = "teks" | "angka" | "tanggal" | "pilihan" | "teksArea" | "centang" | "email" | "url";

export interface DefField {
  nama: string;
  label: string;
  jenis?: JenisField;
  wajib?: boolean;
  pilihan?: { nilai: string; label: string }[];
  bantuan?: string;
  span2?: boolean;
  langkah?: string;
  min?: number;
  max?: number;
}

type Nilai = Record<string, any>;

/** Formulir berbasis konfigurasi: satu definisi → bidang, validasi dasar, dan konversi tipe. */
export function FormFields({
  def,
  nilai,
  onUbah,
  galat = {},
  disabled,
}: {
  def: DefField[];
  nilai: Nilai;
  onUbah: (n: string, v: any) => void;
  galat?: Record<string, string>;
  disabled?: boolean;
}) {
  return (
    <div className="form-grid">
      {def.map((f) => {
        const v = nilai[f.nama] ?? (f.jenis === "centang" ? false : "");
        const set = (x: any) => onUbah(f.nama, x);
        let input: ReactNode;
        switch (f.jenis) {
          case "teksArea":
            input = <textarea value={v} onChange={(e) => set(e.target.value)} disabled={disabled} rows={4} />;
            break;
          case "pilihan":
            input = (
              <select value={v} onChange={(e) => set(e.target.value)} disabled={disabled}>
                <option value="">— pilih —</option>
                {f.pilihan?.map((p) => (
                  <option key={p.nilai} value={p.nilai}>
                    {p.label}
                  </option>
                ))}
              </select>
            );
            break;
          case "centang":
            return (
              <div key={f.nama} className={`field${f.span2 ? " span-2" : ""}`}>
                <label className="check">
                  <input type="checkbox" checked={!!v} onChange={(e) => set(e.target.checked)} disabled={disabled} />
                  {f.label}
                </label>
                {f.bantuan && <div className="field__help">{f.bantuan}</div>}
              </div>
            );
          case "angka":
            input = (
              <input type="number" inputMode="decimal" value={v} step={f.langkah ?? "any"} min={f.min} max={f.max} onChange={(e) => set(e.target.value)} disabled={disabled} />
            );
            break;
          case "tanggal":
            input = <input type="date" value={v ?? ""} onChange={(e) => set(e.target.value)} disabled={disabled} />;
            break;
          default:
            input = <input type={f.jenis === "email" ? "email" : f.jenis === "url" ? "url" : "text"} value={v ?? ""} onChange={(e) => set(e.target.value)} disabled={disabled} />;
        }
        return (
          <Field key={f.nama} label={f.label} wajib={f.wajib} bantuan={f.bantuan} galat={galat[f.nama]} span2={f.span2 || f.jenis === "teksArea"}>
            {input}
          </Field>
        );
      })}
    </div>
  );
}

/** Mengubah nilai formulir menjadi payload API: "" → null, angka → number, centang → boolean. */
export function keMuatan(def: DefField[], nilai: Nilai): Nilai {
  const out: Nilai = { ...nilai };
  for (const f of def) {
    const v = nilai[f.nama];
    if (f.jenis === "centang") out[f.nama] = !!v;
    else if (f.jenis === "angka") out[f.nama] = v === "" || v === undefined || v === null ? null : Number(v);
    else if (v === "" || v === undefined) out[f.nama] = null;
  }
  return out;
}

export function validasiWajib(def: DefField[], nilai: Nilai): Record<string, string> {
  const g: Record<string, string> = {};
  for (const f of def) {
    const v = nilai[f.nama];
    if (f.wajib && f.jenis !== "centang" && (v === "" || v === undefined || v === null)) g[f.nama] = "Wajib diisi";
  }
  return g;
}

/** Penyunting daftar objek kecil (mis. penulis, afiliasi, dosen kegiatan). */
export function ListEditor({
  judul,
  item,
  onUbah,
  def,
  kosong,
  disabled,
}: {
  judul: string;
  item: Nilai[];
  onUbah: (x: Nilai[]) => void;
  def: DefField[];
  kosong: Nilai;
  disabled?: boolean;
}) {
  const [, paksa] = useState(0);
  return (
    <div className="field span-2">
      <div className="row row--between">
        <label className="field__label">{judul}</label>
        <Button variant="ghost" size="sm" disabled={disabled} onClick={() => { onUbah([...item, { ...kosong }]); paksa((x) => x + 1); }}>
          <Icon name="plus" size={14} /> Tambah
        </Button>
      </div>
      {item.length === 0 && <div className="field__help">Belum ada.</div>}
      {item.map((it, i) => (
        <div key={i} className="card" style={{ padding: "0.9rem 1rem", marginTop: "0.3rem" }}>
          <FormFields def={def} nilai={it} disabled={disabled} onUbah={(n, v) => onUbah(item.map((x, j) => (j === i ? { ...x, [n]: v } : x)))} />
          <div style={{ textAlign: "right", marginTop: "-0.4rem" }}>
            <Button variant="danger" size="sm" disabled={disabled} onClick={() => onUbah(item.filter((_, j) => j !== i))}>
              <Icon name="trash" size={13} /> Hapus
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}
