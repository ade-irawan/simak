import { useState } from "react";
import { api } from "@/shared/api/client";
import type { Halaman, Rec } from "@/shared/api/types";
import { useAuth } from "@/shared/auth/AuthProvider";
import { useAksi, useApi } from "@/shared/lib/hooks";
import { angka, tanggal } from "@/shared/lib/format";
import { Alert, Button, Empty, ErrorBox, Field, Icon, Modal, Muat, PageHead, Pager, Pill, StatusPill, Tabel, type Kolom } from "@/shared/ui";
import { PilihBuktiModal } from "../bukti/BuktiPage";

const JENIS = [
  ["tracer_study", "Tracer study"], ["kepuasan_mahasiswa", "Kepuasan mahasiswa"], ["kepuasan_dosen", "Kepuasan dosen"], ["kepuasan_tendik", "Kepuasan tenaga kependidikan"],
  ["kepuasan_lulusan", "Kepuasan lulusan"], ["kepuasan_pengguna_lulusan", "Kepuasan pengguna lulusan"], ["kepuasan_mitra", "Kepuasan mitra"],
] as const;
const namaJenis = (j: string) => JENIS.find((x) => x[0] === j)?.[1] ?? j;
const INV = ["/dokumen-eksternal", "/prodi", "/siklus", "/butir-siklus", "/dasbor"];

export function DokumenEksternalPage() {
  const { punya } = useAuth();
  const [page, setPage] = useState(1);
  const [baru, setBaru] = useState(false);
  const [indikator, setIndikator] = useState<Rec | null>(null);
  const q = useApi<Halaman<Rec>>("/dokumen-eksternal", { page, per_page: 15 }, { keep: true });
  const kolom: Kolom<Rec>[] = [
    { kunci: "judul", judul: "Dokumen", render: (d) => <div><div className="cell-title">{d.judul}</div><div className="cell-sub">{namaJenis(d.jenis)} · {d.sumber_unit}</div></div> },
    { kunci: "periode", judul: "Periode", render: (d) => `${tanggal(d.periode_mulai)} – ${tanggal(d.periode_selesai)}` },
    { kunci: "resp", judul: "Responden", num: true, render: (d) => (d.populasi ? `${angka(d.jumlah_responden)} / ${angka(d.populasi)}` : angka(d.jumlah_responden)) },
    { kunci: "prodi", judul: "Prodi sasaran", render: (d) => <div className="chips">{d.prodi.map((p: Rec) => <Pill key={p.id}>{p.kode}</Pill>)}</div> },
    { kunci: "bukti", judul: "Dokumen resmi", render: (d) => (d.bukti ? <StatusPill status={d.bukti.status_cek} /> : "—") },
    ...(punya("staf_fakultas") ? [{ kunci: "aksi", judul: "", render: (d: Rec) => <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); setIndikator(d); }}>Indikator</Button> }] : []),
  ];
  return (
    <div className="stack">
      <PageHead judul="Tracer study & kepuasan" sub="SIMAK menerima, mengarsipkan, dan memetakan dokumen hasil dari Direktorat Kemahasiswaan — survei diselenggarakan di tingkat institusi, bukan di SIMAK." aksi={punya("staf_fakultas") && <Button onClick={() => setBaru(true)}><Icon name="plus" size={16} /> Catat dokumen</Button>} />
      <Alert jenis="info">Staf Admin Fakultas adalah kanal resmi penerima dokumen Direktorat, sehingga satu dokumen institusi dapat dibagikan ke beberapa prodi tanpa duplikasi. Prodi hanya membaca ringkasan dan indikatornya.</Alert>
      <Muat q={q}>{(d) => (<><Tabel kolom={kolom} baris={d.data} id={(x) => x.id} kosong="Belum ada dokumen dari Direktorat Kemahasiswaan." /><Pager page={d.meta.page} perPage={d.meta.per_page} total={d.meta.total} onGanti={setPage} /></>)}</Muat>
      {baru && <DokumenModal onTutup={() => setBaru(false)} onSelesai={(d) => { setBaru(false); setIndikator(d); }} />}
      {indikator && <IndikatorModal dokumen={indikator} onTutup={() => setIndikator(null)} />}
    </div>
  );
}

function DokumenModal({ onTutup, onSelesai }: { onTutup: () => void; onSelesai: (d: Rec) => void }) {
  const prodi = useApi<Rec[]>("/prodi");
  const tahun = useApi<Rec[]>("/tahun-akademik");
  const [f, setF] = useState<Rec>({ jenis: "tracer_study", sumber_unit: "Direktorat Kemahasiswaan", prodi_id: [] });
  const [bukti, setBukti] = useState<Rec | null>(null);
  const [pilih, setPilih] = useState(false);
  const set = (k: string, v: any) => setF((x) => ({ ...x, [k]: v }));
  const num = (v: any) => (v === "" || v === undefined ? null : Number(v));
  const simpan = useAksi(() => api.post("/dokumen-eksternal", {
    jenis: f.jenis, judul: f.judul, sumber_unit: f.sumber_unit, tahun_akademik_id: f.tahun_akademik_id, periode_mulai: f.periode_mulai || null, periode_selesai: f.periode_selesai || null,
    populasi: num(f.populasi), jumlah_responden: num(f.jumlah_responden), metodologi: f.metodologi || null, bukti_id: bukti!.id, diterima_pada: f.diterima_pada || null, prodi_id: f.prodi_id,
  }), { sukses: "Dokumen dicatat", invalidate: INV, onSuccess: onSelesai });
  return (
    <Modal judul="Catat dokumen dari Direktorat" onTutup={onTutup} lebar footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button disabled={!f.judul || !f.tahun_akademik_id || !bukti || !f.prodi_id.length || simpan.isPending} onClick={() => simpan.mutate()}>Simpan</Button></>}>
      <div className="form-grid">
        <Field label="Jenis" wajib><select value={f.jenis} onChange={(e) => set("jenis", e.target.value)}>{JENIS.map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
        <Field label="Tahun akademik" wajib><select value={f.tahun_akademik_id ?? ""} onChange={(e) => set("tahun_akademik_id", e.target.value)}><option value="">— pilih —</option>{tahun.data?.map((t) => <option key={t.id} value={t.id}>{t.kode}</option>)}</select></Field>
        <Field label="Judul" wajib span2><input value={f.judul ?? ""} onChange={(e) => set("judul", e.target.value)} /></Field>
        <Field label="Periode mulai"><input type="date" value={f.periode_mulai ?? ""} onChange={(e) => set("periode_mulai", e.target.value)} /></Field>
        <Field label="Periode selesai"><input type="date" value={f.periode_selesai ?? ""} onChange={(e) => set("periode_selesai", e.target.value)} /></Field>
        <Field label="Populasi"><input type="number" min={0} value={f.populasi ?? ""} onChange={(e) => set("populasi", e.target.value)} /></Field>
        <Field label="Jumlah responden"><input type="number" min={0} value={f.jumlah_responden ?? ""} onChange={(e) => set("jumlah_responden", e.target.value)} /></Field>
        <Field label="Metodologi" span2><textarea style={{ minHeight: 70 }} value={f.metodologi ?? ""} onChange={(e) => set("metodologi", e.target.value)} /></Field>
        <Field label="Diterima pada"><input type="date" value={f.diterima_pada ?? ""} onChange={(e) => set("diterima_pada", e.target.value)} /></Field>
        <Field label="Dokumen resmi (berkas/tautan)" wajib>
          <div className="row">{bukti ? <Pill warna="lime" dot>{bukti.judul}</Pill> : <span className="faint">belum dipilih</span>}<Button size="sm" variant="ghost" onClick={() => setPilih(true)}>{bukti ? "Ganti" : "Pilih / unggah"}</Button></div>
        </Field>
      </div>
      <Field label="Prodi sasaran" wajib bantuan="Dokumen yang sama dapat ditautkan ke banyak prodi.">
        <div className="chips">{prodi.data?.map((p) => <label key={p.id} className="check"><input type="checkbox" checked={f.prodi_id.includes(p.id)} onChange={(e) => set("prodi_id", e.target.checked ? [...f.prodi_id, p.id] : f.prodi_id.filter((x: string) => x !== p.id))} />{p.nama}</label>)}</div>
      </Field>
      {simpan.error && <ErrorBox error={simpan.error} />}
      {pilih && <PilihBuktiModal sudah={[]} onTutup={() => setPilih(false)} onPilih={(b) => { setBukti(b); setPilih(false); }} />}
    </Modal>
  );
}

function IndikatorModal({ dokumen, onTutup }: { dokumen: Rec; onTutup: () => void }) {
  const { punya } = useAuth();
  const [baris, setBaris] = useState<Rec[]>([]);
  const [berkas, setBerkas] = useState<File | null>(null);
  const simpan = useAksi(() => api.put(`/dokumen-eksternal/${dokumen.id}/indikator`, baris.map((b) => ({ ...b, nilai: b.nilai === "" ? null : Number(b.nilai), jumlah_responden: b.jumlah_responden === "" || b.jumlah_responden === undefined ? null : Number(b.jumlah_responden) }))),
    { sukses: (r) => `${r.baris_berhasil} indikator disimpan${r.butir_dibebaskan ? `; ${r.butir_dibebaskan} butir tidak lagi menunggu Direktorat` : ""}`, invalidate: INV, onSuccess: () => setBaris([]) });
  const impor = useAksi(() => { const f = new FormData(); f.append("berkas", berkas!); return api.upload(`/dokumen-eksternal/${dokumen.id}/indikator/impor`, f); }, { invalidate: INV, diam: true });
  const tambah = () => setBaris([...baris, { prodi_id: dokumen.prodi[0]?.id ?? "", kode: "", nama: "", nilai: "", satuan: "" }]);
  const upd = (i: number, k: string, v: string) => setBaris(baris.map((b, j) => (j === i ? { ...b, [k]: v } : b)));
  const sasaran = dokumen.prodi as Rec[];
  const lihat = useApi<Rec[]>(`/prodi/${sasaran[0]?.id}/indikator-eksternal`, undefined, { enabled: !!sasaran[0] });
  return (
    <Modal judul={`Indikator — ${dokumen.judul}`} onTutup={onTutup} lebar footer={<Button variant="ghost" onClick={onTutup}>Tutup</Button>}>
      <Alert jenis="info">Bila responden terlalu sedikit (&lt; 30), indikator ditampilkan sebagai “data tidak memadai” alih-alih angka yang menyesatkan. Bila Direktorat hanya memberi dokumen naratif, catat indikator dari ringkasan resminya.</Alert>
      {punya("staf_fakultas") && (
        <div className="stack" style={{ marginTop: "1rem" }}>
          <div className="row row--between"><strong>Isi manual</strong><Button size="sm" variant="ghost" onClick={tambah}><Icon name="plus" size={14} /> Baris</Button></div>
          {baris.map((b, i) => (
            <div key={i} className="card" style={{ padding: "0.7rem" }}>
              <div className="form-grid">
                <Field label="Prodi"><select value={b.prodi_id} onChange={(e) => upd(i, "prodi_id", e.target.value)}>{sasaran.map((p) => <option key={p.id} value={p.id}>{p.nama}</option>)}</select></Field>
                <Field label="Kode"><input value={b.kode} onChange={(e) => upd(i, "kode", e.target.value)} placeholder="masa_tunggu_bulan" /></Field>
                <Field label="Nama indikator"><input value={b.nama} onChange={(e) => upd(i, "nama", e.target.value)} /></Field>
                <Field label="Nilai"><input type="number" step="any" value={b.nilai} onChange={(e) => upd(i, "nilai", e.target.value)} /></Field>
                <Field label="Satuan"><input value={b.satuan} onChange={(e) => upd(i, "satuan", e.target.value)} /></Field>
                <Field label="Responden (opsional)"><input type="number" value={b.jumlah_responden ?? ""} onChange={(e) => upd(i, "jumlah_responden", e.target.value)} /></Field>
              </div>
            </div>
          ))}
          {baris.length > 0 && <div><Button onClick={() => simpan.mutate()} disabled={simpan.isPending || baris.some((b) => !b.kode || !b.nama)}>Simpan indikator</Button></div>}
          {simpan.error && <ErrorBox error={simpan.error} />}
          <hr className="divider" />
          <strong>Atau impor CSV/XLSX</strong>
          <div className="muted" style={{ fontSize: "0.82rem" }}>Kolom: <span className="mono">prodi_kode, kode, nama, nilai, satuan, jumlah_responden, catatan</span></div>
          <div className="row"><input type="file" accept=".csv,.xlsx" onChange={(e) => setBerkas(e.target.files?.[0] ?? null)} /><Button size="sm" disabled={!berkas || impor.isPending} onClick={() => impor.mutate()}>Impor</Button></div>
          {impor.data && (
            <Alert jenis={impor.data.baris_gagal.length ? "warn" : "ok"} judul={`${impor.data.baris_berhasil} baris berhasil`}>
              {impor.data.baris_gagal.length > 0 && <ul>{impor.data.baris_gagal.map((g: Rec, i: number) => <li key={i}>Baris {g.baris} ({g.kolom}): {g.pesan}</li>)}</ul>}
            </Alert>
          )}
          {impor.error && <ErrorBox error={impor.error} />}
        </div>
      )}
      <hr className="divider" />
      <strong>Indikator tercatat ({sasaran[0]?.nama})</strong>
      <Muat q={lihat}>{(d) => (d.length ? <div className="stack stack--sm" style={{ marginTop: "0.5rem" }}>{d.map((i) => <div key={i.id} className="row row--between card" style={{ padding: "0.5rem 0.9rem" }}><span>{i.nama}</span><span>{i.data_memadai ? <strong>{angka(i.nilai, 2)} {i.satuan}</strong> : <Pill warna="amber">data tidak memadai</Pill>}</span></div>)}</div> : <Empty judul="Belum ada indikator" />)}</Muat>
    </Modal>
  );
}
