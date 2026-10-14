import { useRef, useState } from "react";
import { api, putToStorage } from "@/shared/api/client";
import type { Rec } from "@/shared/api/types";
import { useAuth } from "@/shared/auth/AuthProvider";
import { useAksi, useApi } from "@/shared/lib/hooks";
import { ukuranBerkas } from "@/shared/lib/format";
import { Button, ErrorBox, Field, Icon, Modal } from "@/shared/ui";

const MIME: Record<string, string> = {
  pdf: "application/pdf", jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", csv: "text/csv",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
};
const mimeDari = (f: File) => MIME[f.name.split(".").pop()?.toLowerCase() ?? ""] ?? f.type ?? "application/octet-stream";

/** Tambah bukti: unggah berkas (URL sementara ke penyimpanan) ATAU tautan (US-B3). Berlaku untuk banyak prodi sekaligus. */
export function TambahBuktiModal({ onSelesai, onTutup, prodiAwal }: { onSelesai: (b: Rec) => void; onTutup: () => void; prodiAwal?: string[] }) {
  const { punya, aktif } = useAuth();
  const bisaPilihProdi = punya("staf_fakultas", "dekan");
  const prodi = useApi<Rec[]>("/prodi", undefined, { enabled: bisaPilihProdi });
  const [jenis, setJenis] = useState<"tautan" | "berkas">("tautan");
  const [judul, setJudul] = useState("");
  const [url, setUrl] = useState("");
  const [akses, setAkses] = useState("publik");
  const [sumber, setSumber] = useState("");
  const [tgl, setTgl] = useState("");
  const [berkas, setBerkas] = useState<File | null>(null);
  const [berlaku, setBerlaku] = useState<string[]>(prodiAwal ?? (aktif?.prodi ? [aktif.prodi.id] : []));
  const [over, setOver] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const simpan = useAksi(
    async () => {
      const dasar = { judul, sumber: sumber || null, tanggal_dokumen: tgl || null, berlaku_untuk: berlaku };
      if (jenis === "tautan") return api.post("/bukti", { ...dasar, jenis, url, akses_tautan: akses });
      const f = berkas!;
      const mime = mimeDari(f);
      const u = await api.post("/bukti/unggahan", { nama_berkas: f.name, mime_type: mime, ukuran_byte: f.size });
      await putToStorage(u.url_unggah, f, mime);
      return api.post("/bukti", { ...dasar, jenis, objek_key: u.objek_key, nama_berkas: f.name });
    },
    { sukses: "Bukti ditambahkan", invalidate: ["/bukti"], onSuccess: onSelesai },
  );
  const siap = judul.trim().length >= 3 && (jenis === "tautan" ? /^https?:\/\//i.test(url) : !!berkas);

  return (
    <Modal
      judul="Tambah bukti"
      onTutup={onTutup}
      footer={
        <>
          <Button variant="ghost" onClick={onTutup}>Batal</Button>
          <Button onClick={() => simpan.mutate()} disabled={!siap || simpan.isPending}>{simpan.isPending && <span className="spinner" />} Simpan bukti</Button>
        </>
      }
    >
      <div className="tabs">
        {(["tautan", "berkas"] as const).map((j) => (
          <button key={j} className={`tab${jenis === j ? " is-active" : ""}`} onClick={() => setJenis(j)}>
            <Icon name={j === "tautan" ? "link" : "upload"} size={14} /> {j === "tautan" ? "Tautan (URL)" : "Unggah berkas"}
          </button>
        ))}
      </div>
      <Field label="Judul bukti" wajib><input value={judul} onChange={(e) => setJudul(e.target.value)} placeholder="mis. SK Pembentukan Gugus Penjaminan Mutu" autoFocus /></Field>
      {jenis === "tautan" ? (
        <div className="form-grid">
          <Field label="Alamat tautan" wajib span2 bantuan="Repositori, Google Drive, SharePoint, dsb. Diperiksa link-checker secara berkala."><input type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://" /></Field>
          <Field label="Akses tautan" bantuan="Tautan terbatas tidak dihitung rusak bila meminta login (401/403).">
            <select value={akses} onChange={(e) => setAkses(e.target.value)}><option value="publik">Publik</option><option value="terbatas">Terbatas (perlu login)</option></select>
          </Field>
        </div>
      ) : (
        <Field label="Berkas" wajib bantuan="PDF, JPG/PNG, XLSX/CSV, DOCX. Batas ukuran mengikuti pengaturan sistem (bawaan 25 MB).">
          <div
            className={`dropzone${over ? " is-over" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setOver(true); }}
            onDragLeave={() => setOver(false)}
            onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) setBerkas(f); }}
          >
            {berkas ? <><strong>{berkas.name}</strong> · {ukuranBerkas(berkas.size)}</> : <>Seret berkas ke sini atau </>}
            <Button variant="ghost" size="sm" onClick={() => input.current?.click()} style={{ marginLeft: "0.4rem" }}>Pilih berkas</Button>
            <input ref={input} type="file" hidden accept=".pdf,.jpg,.jpeg,.png,.xlsx,.csv,.docx" onChange={(e) => setBerkas(e.target.files?.[0] ?? null)} />
          </div>
        </Field>
      )}
      <div className="form-grid">
        <Field label="Sumber / pemilik dokumen"><input value={sumber} onChange={(e) => setSumber(e.target.value)} placeholder="mis. Satuan Penjaminan Mutu" /></Field>
        <Field label="Tanggal dokumen"><input type="date" value={tgl} onChange={(e) => setTgl(e.target.value)} /></Field>
      </div>
      {bisaPilihProdi && (
        <Field label="Berlaku untuk" bantuan="Satu bukti bersama dapat dipakai beberapa prodi tanpa diunggah ulang. Kosong = tingkat UPPS.">
          <div className="chips">
            {prodi.data?.map((p) => (
              <label key={p.id} className="check">
                <input type="checkbox" checked={berlaku.includes(p.id)} onChange={(e) => setBerlaku(e.target.checked ? [...berlaku, p.id] : berlaku.filter((x) => x !== p.id))} />
                {p.nama}
              </label>
            ))}
          </div>
        </Field>
      )}
      {simpan.error && <ErrorBox error={simpan.error} />}
    </Modal>
  );
}
