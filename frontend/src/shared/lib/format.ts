const ID = "id-ID";

export const tanggal = (v?: string | null): string =>
  v ? new Date(v.length <= 10 ? `${v}T00:00:00` : v).toLocaleDateString(ID, { day: "2-digit", month: "short", year: "numeric" }) : "—";

export const waktu = (v?: string | null): string =>
  v
    ? new Date(v).toLocaleString(ID, { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })
    : "—";

export const angka = (v?: number | string | null, desimal = 0): string => {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  return Number.isNaN(n) ? "—" : n.toLocaleString(ID, { maximumFractionDigits: desimal, minimumFractionDigits: 0 });
};

export const rupiah = (v?: number | string | null): string => {
  if (v === null || v === undefined || v === "") return "—";
  return Number(v).toLocaleString(ID, { style: "currency", currency: "IDR", maximumFractionDigits: 0 });
};

export const persen = (v?: number | null): string => (v === null || v === undefined ? "—" : `${angka(v, 1)}%`);

export const ukuranBerkas = (b?: number | null): string => {
  if (b === null || b === undefined) return "—";
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
};

/** "belum_mulai" → "Belum mulai" */
export const labelEnum = (v?: string | null): string => {
  if (!v) return "—";
  const s = v.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
};

export const inisial = (nama: string): string =>
  nama
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join("");

export const namaLam = (lam?: string | null): string => (lam ? lam.replace(/_/g, " ") : "—");
