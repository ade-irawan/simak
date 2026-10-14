import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, API, getAccessToken } from "@/shared/api/client";
import type { Rec } from "@/shared/api/types";
import { useAuth } from "@/shared/auth/AuthProvider";
import { useAksi, useApi } from "@/shared/lib/hooks";
import { angka, labelEnum, namaLam } from "@/shared/lib/format";
import { Alert, Button, Card, ErrorBox, Field, Icon, Modal, Muat, PageHead, Pill, StatusPill, Tabel, Tabs, type Kolom } from "@/shared/ui";
import { SUMBER } from "../siklus/konstanta";

const INV = ["/instrumen", "/butir-instrumen", "/pemetaan", "/siklus"];

export function InstrumenList() {
  const { punya } = useAuth();
  const nav = useNavigate();
  const [impor, setImpor] = useState(false);
  const q = useApi<Rec[]>("/instrumen");
  const aktifkan = useAksi((id: string) => api.post(`/instrumen/${id}/aktifkan`), { sukses: "Instrumen diaktifkan dan versi lama diarsipkan", invalidate: INV });
  const kolom: Kolom<Rec>[] = [
    { kunci: "nama", judul: "Instrumen", render: (i) => <div><div className="cell-title">{i.nama}</div><div className="cell-sub">{namaLam(i.lam.kode)} · {i.jenjang}</div></div> },
    { kunci: "versi", judul: "Versi", render: (i) => <span className="mono">{i.kode_versi}</span> },
    { kunci: "status", judul: "Status", render: (i) => <StatusPill status={i.status} /> },
    { kunci: "aksi", judul: "", render: (i) => (
      <div className="row" style={{ justifyContent: "flex-end" }} onClick={(e) => e.stopPropagation()}>
        {punya("dekan") && i.status === "draf" && <Button size="sm" variant="lime" onClick={() => aktifkan.mutate(i.id)} disabled={aktifkan.isPending}>Setujui &amp; aktifkan</Button>}
      </div>
    ) },
  ];
  return (
    <div className="stack">
      <PageHead judul="Instrumen & pemetaan" sub="Struktur butir, rubrik, aturan peringkat, dan aturan pemetaan data berbasis konfigurasi. Staf Admin Fakultas menyusun; hanya yang disetujui Dekan yang dipakai sistem."
        aksi={punya("staf_fakultas") && <><TemplatButton /><Button onClick={() => setImpor(true)}><Icon name="upload" size={15} /> Impor instrumen (XLSX)</Button></>} />
      <Muat q={q}>{(d) => <Tabel kolom={kolom} baris={d} id={(i) => i.id} onKlik={(i) => nav(`/instrumen/${i.id}`)} kosong="Belum ada instrumen." />}</Muat>
      {aktifkan.error && <ErrorBox error={aktifkan.error} />}
      {impor && <ImporModal onTutup={() => setImpor(false)} onSelesai={(id) => { setImpor(false); nav(`/instrumen/${id}`); }} />}
    </div>
  );
}

function TemplatButton() {
  const unduh = async () => {
    const r = await fetch(`${API}/instrumen/impor/templat`, { headers: { Authorization: `Bearer ${getAccessToken()}` } });
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = "templat-instrumen.xlsx";
    a.click();
    URL.revokeObjectURL(url);
  };
  return <Button variant="ghost" onClick={unduh}><Icon name="download" size={15} /> Templat XLSX</Button>;
}

function ImporModal({ onTutup, onSelesai }: { onTutup: () => void; onSelesai: (id: string) => void }) {
  const [f, setF] = useState({ lam_kode: "LAMSAMA", kode_versi: "", nama: "", jenjang: "S1", skor_maks: "4", nilai_akhir_maks: "", label_skor: '{"4":"Baik Sekali","3":"Baik","2":"Cukup","1":"Kurang"}', dasar_hukum: "" });
  const [berkas, setBerkas] = useState<File | null>(null);
  const set = (k: string, v: string) => setF({ ...f, [k]: v });
  const unggah = useAksi(() => {
    const fd = new FormData();
    Object.entries(f).forEach(([k, v]) => v !== "" && fd.append(k, v));
    fd.append("berkas", berkas!);
    return api.upload("/instrumen/impor", fd);
  }, { sukses: (r) => `Dimuat sebagai draf: ${r.butir} butir, ${r.rubrik} rubrik, ${r.peringkat} peringkat`, invalidate: INV, onSuccess: (r) => onSelesai(r.id) });
  return (
    <Modal judul="Impor versi instrumen" onTutup={onTutup} lebar footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button disabled={!berkas || !f.kode_versi || !f.nama || unggah.isPending} onClick={() => unggah.mutate()}>{unggah.isPending && <span className="spinner" />} Impor sebagai draf</Button></>}>
      <Alert jenis="info">Lembar yang dibaca: <span className="mono">kriteria, butir, rubrik, peringkat, ambang</span>. Instrumen dimuat sebagai <strong>draf</strong> dan berlaku setelah disetujui Dekan. Satu baris bermasalah membatalkan seluruh impor dan dilaporkan dengan nomor barisnya.</Alert>
      <div className="form-grid" style={{ marginTop: "1rem" }}>
        <Field label="LAM" wajib><select value={f.lam_kode} onChange={(e) => set("lam_kode", e.target.value)}><option value="LAMSAMA">LAMSAMA</option><option value="LAM_INFOKOM">LAM INFOKOM</option></select></Field>
        <Field label="Kode versi" wajib><input value={f.kode_versi} onChange={(e) => set("kode_versi", e.target.value)} placeholder="mis. 3.1" /></Field>
        <Field label="Nama" wajib span2><input value={f.nama} onChange={(e) => set("nama", e.target.value)} placeholder="IAPS 3.1 LAMSAMA - Program Sarjana" /></Field>
        <Field label="Skor maksimum"><input type="number" value={f.skor_maks} onChange={(e) => set("skor_maks", e.target.value)} /></Field>
        <Field label="Nilai akhir maksimum" bantuan="Isi hanya untuk instrumen berbobot (mis. 400).">
          <input type="number" value={f.nilai_akhir_maks} onChange={(e) => set("nilai_akhir_maks", e.target.value)} /></Field>
        <Field label="Label skor (JSON)" span2><input value={f.label_skor} onChange={(e) => set("label_skor", e.target.value)} /></Field>
        <Field label="Dasar hukum" span2><input value={f.dasar_hukum} onChange={(e) => set("dasar_hukum", e.target.value)} /></Field>
        <Field label="Berkas XLSX" wajib span2><input type="file" accept=".xlsx" onChange={(e) => setBerkas(e.target.files?.[0] ?? null)} /></Field>
      </div>
      {unggah.error && <ErrorBox error={unggah.error} />}
    </Modal>
  );
}

/* ------------------------------------------------------------------ detail */
export function InstrumenDetail() {
  const { id } = useParams();
  const { punya } = useAuth();
  const [tab, setTab] = useState<"butir" | "peringkat" | "pemetaan">("butir");
  const q = useApi<Rec>(`/instrumen/${id}`);
  return (
    <div className="stack">
      <Muat q={q}>
        {(v) => (
          <>
            <PageHead crumbs={[{ label: "Instrumen", to: "/instrumen" }, { label: v.kode_versi }]} judul={v.nama} sub={v.dasar_hukum ?? undefined} aksi={<StatusPill status={v.status} />} />
            {v.status === "draf" && <Alert jenis="warn" judul="Draf — belum dipakai sistem">{punya("dekan") ? "Tinjau lalu aktifkan dari daftar instrumen." : "Staf Admin Fakultas dapat menyunting butir dan aturan pemetaan; Dekan menyetujui."}</Alert>}
            <div className="grid grid--4">
              <Card><Metric nilai={v.kriteria.length} label="Kriteria" /></Card>
              <Card><Metric nilai={v.kriteria.reduce((a: number, k: Rec) => a + k.jumlah_butir, 0)} label="Butir" /></Card>
              <Card><Metric nilai={v.peringkat.length} label="Peringkat" /></Card>
              <Card><Metric nilai={v.nilai_akhir_maks ? angka(v.nilai_akhir_maks) : "tanpa bobot"} label="Nilai akhir maks." /></Card>
            </div>
            <Tabs aktif={tab} onGanti={setTab} tabs={[{ kunci: "butir", label: "Kriteria & butir" }, { kunci: "peringkat", label: "Peringkat" }, { kunci: "pemetaan", label: "Aturan pemetaan" }]} />
            {tab === "butir" && <Butir versi={v} />}
            {tab === "peringkat" && <Peringkat versi={v} />}
            {tab === "pemetaan" && <Pemetaan versi={v} />}
          </>
        )}
      </Muat>
    </div>
  );
}

const Metric = ({ nilai, label }: { nilai: React.ReactNode; label: string }) => <div className="metric"><div className="metric__value" style={{ fontSize: "1.5rem" }}>{nilai}</div><div className="metric__label">{label}</div></div>;

function Butir({ versi }: { versi: Rec }) {
  const q = useApi<Rec[]>(`/instrumen/${versi.id}/butir`);
  const [lihat, setLihat] = useState<string | null>(null);
  const kolom: Kolom<Rec>[] = [
    { kunci: "kode", judul: "Butir", render: (b) => <span className="butir-code">{b.kode}</span> },
    { kunci: "kr", judul: "Kriteria", render: (b) => `${b.kriteria.kode} · ${b.kriteria.nama}` },
    { kunci: "elemen", judul: "Elemen", render: (b) => <span style={{ display: "block", maxWidth: 480 }}>{b.elemen}</span> },
    { kunci: "tipe", judul: "Jenis / tahap", render: (b) => [b.jenis_ipo, b.tahap_ppepp].filter(Boolean).map(labelEnum).join(" / ") || "—" },
    { kunci: "bobot", judul: "Bobot", num: true, render: (b) => (b.bobot !== null ? angka(b.bobot, 2) : "—") },
  ];
  return (
    <>
      <Muat q={q}>{(d) => <Tabel kolom={kolom} baris={d} id={(b) => b.id} onKlik={(b) => setLihat(b.id)} kosong="Belum ada butir." />}</Muat>
      {lihat && <ButirModal id={lihat} versi={versi} onTutup={() => setLihat(null)} />}
    </>
  );
}

function ButirModal({ id, versi, onTutup }: { id: string; versi: Rec; onTutup: () => void }) {
  const { punya } = useAuth();
  const q = useApi<Rec>(`/butir-instrumen/${id}`);
  const [elemen, setElemen] = useState<string | null>(null);
  const [panduan, setPanduan] = useState<string | null>(null);
  const bisa = punya("staf_fakultas") && versi.status === "draf";
  const simpan = useAksi(() => api.patch(`/butir-instrumen/${id}`, { ...(elemen !== null ? { elemen } : {}), ...(panduan !== null ? { panduan } : {}) }), { sukses: "Butir diperbarui", invalidate: INV });
  return (
    <Modal judul="Butir instrumen" onTutup={onTutup} lebar footer={<><Button variant="ghost" onClick={onTutup}>Tutup</Button>{bisa && <Button onClick={() => simpan.mutate()} disabled={simpan.isPending || (elemen === null && panduan === null)}>Simpan</Button>}</>}>
      <Muat q={q}>
        {(b) => (
          <div className="stack">
            <Field label={`Elemen penilaian (${b.kode})`}><textarea style={{ minHeight: 90 }} defaultValue={b.elemen} disabled={!bisa} onChange={(e) => setElemen(e.target.value)} /></Field>
            <Field label="Panduan pengisian"><textarea style={{ minHeight: 70 }} defaultValue={b.panduan ?? ""} disabled={!bisa} onChange={(e) => setPanduan(e.target.value)} /></Field>
            <strong>Rubrik</strong>
            {b.rubrik.length ? <div className="rubrik">{b.rubrik.map((r: Rec) => <div key={r.skor} className="rubrik__item"><div className="rubrik__skor">{r.skor}</div><div><strong>{r.label}</strong><div className="muted">{r.deskriptor}</div></div></div>)}</div> : <div className="muted">Belum ada rubrik.</div>}
            {b.ambang.length > 0 && <div className="chips">{b.ambang.map((a: Rec) => <Pill key={a.peringkat} warna={a.is_syarat_perlu ? "red" : "blue"}>{labelEnum(a.peringkat)} ≥ {a.skor_min}{a.is_syarat_perlu ? " · syarat perlu" : ""}</Pill>)}</div>}
            {simpan.error && <ErrorBox error={simpan.error} />}
          </div>
        )}
      </Muat>
    </Modal>
  );
}

function Peringkat({ versi }: { versi: Rec }) {
  return (
    <div className="grid grid--2">
      {versi.peringkat.map((p: Rec) => (
        <Card key={p.kode} judul={p.nama} sub={p.masa_berlaku_tahun ? `Berlaku ${p.masa_berlaku_tahun} tahun` : undefined}>
          <dl className="kv">
            <dt>Rentang nilai akhir</dt><dd>{p.nilai_akhir_min !== null || p.nilai_akhir_maks !== null ? `${p.nilai_akhir_min ?? "…"} ≤ nilai < ${p.nilai_akhir_maks ?? "…"}` : "Ditentukan ambang per butir"}</dd>
            <dt>Syarat tambahan</dt><dd>{Object.keys(p.syarat ?? {}).length ? <span className="mono">{JSON.stringify(p.syarat)}</span> : "—"}</dd>
          </dl>
        </Card>
      ))}
    </div>
  );
}

function Pemetaan({ versi }: { versi: Rec }) {
  const { punya } = useAuth();
  const q = useApi<Rec[]>(`/instrumen/${versi.id}/pemetaan`, undefined, { enabled: punya("dekan", "kaprodi", "staf_fakultas") });
  const butir = useApi<Rec[]>(`/instrumen/${versi.id}/butir`);
  const [edit, setEdit] = useState<string | null>(null);
  const setujui = useAksi((id: string) => api.post(`/pemetaan/${id}/setujui`), { sukses: "Aturan pemetaan disetujui dan berlaku", invalidate: INV });
  const kolom: Kolom<Rec>[] = [
    { kunci: "butir", judul: "Butir", render: (p) => <span className="butir-code">{p.butir_kode}</span> },
    { kunci: "sumber", judul: "Sumber data inti", render: (p) => SUMBER[p.sumber]?.label ?? labelEnum(p.sumber) },
    { kunci: "aturan", judul: "Aturan", render: (p) => <span className="mono">{JSON.stringify(p.aturan)}</span> },
    { kunci: "status", judul: "Status", render: (p) => <StatusPill status={p.status} /> },
    { kunci: "aksi", judul: "", render: (p) => (
      <div className="row" style={{ justifyContent: "flex-end" }} onClick={(e) => e.stopPropagation()}>
        {punya("dekan") && p.status === "draf" && <Button size="sm" variant="lime" onClick={() => setujui.mutate(p.id)}>Setujui</Button>}
        {punya("staf_fakultas") && <Button size="sm" variant="ghost" onClick={() => setEdit(p.butir_id)}>Ubah</Button>}
      </div>
    ) },
  ];
  return (
    <div className="stack">
      <Alert jenis="info">Aturan menghubungkan butir ke data inti tanpa menyalin data. Perubahan tersimpan sebagai <strong>draf</strong>; aturan lama tetap berlaku sampai Dekan menyetujui perubahan (EC-31).</Alert>
      {punya("staf_fakultas") && <div><select className="input" style={{ maxWidth: 380 }} value="" onChange={(e) => e.target.value && setEdit(e.target.value)}><option value="">+ Susun aturan untuk butir…</option>{butir.data?.map((b) => <option key={b.id} value={b.id}>{b.kode} — {b.elemen.slice(0, 60)}</option>)}</select></div>}
      <Muat q={q}>{(d) => <Tabel kolom={kolom} baris={d} id={(p) => p.id} kosong="Belum ada aturan pemetaan." />}</Muat>
      {setujui.error && <ErrorBox error={setujui.error} />}
      {edit && <PemetaanModal butirId={edit} aturan={(q.data ?? []).filter((p) => p.butir_id === edit && p.status !== "digantikan")} onTutup={() => setEdit(null)} />}
    </div>
  );
}

function PemetaanModal({ butirId, aturan, onTutup }: { butirId: string; aturan: Rec[]; onTutup: () => void }) {
  const [item, setItem] = useState<{ sumber: string; aturan: string; keterangan: string }[]>(
    aturan.length ? aturan.map((a) => ({ sumber: a.sumber, aturan: JSON.stringify(a.aturan ?? {}), keterangan: a.keterangan ?? "" })) : [{ sumber: "publikasi", aturan: "{}", keterangan: "" }],
  );
  const [galat, setGalat] = useState<string | null>(null);
  const simpan = useAksi(() => {
    const badan = item.map((i) => ({ sumber: i.sumber, aturan: JSON.parse(i.aturan || "{}"), keterangan: i.keterangan || null }));
    return api.put(`/butir-instrumen/${butirId}/pemetaan`, badan);
  }, { sukses: "Tersimpan sebagai draf; menunggu persetujuan Dekan", invalidate: INV, onSuccess: onTutup });
  const upd = (i: number, k: string, v: string) => setItem(item.map((x, j) => (j === i ? { ...x, [k]: v } : x)));
  const kirim = () => {
    try { item.forEach((i) => JSON.parse(i.aturan || "{}")); setGalat(null); simpan.mutate(); } catch { setGalat("Aturan harus berupa JSON yang valid."); }
  };
  return (
    <Modal judul="Susun aturan pemetaan" onTutup={onTutup} lebar footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button onClick={kirim} disabled={simpan.isPending}>Simpan draf</Button></>}>
      <Alert jenis="info"><span className="mono">{`{"filter": {"jenis": "jurnal"}, "agregasi": "daftar|hitung|jumlah|rata_rata", "kolom": "jumlah_dana", "batasi_tahun": true}`}</span></Alert>
      <div className="stack" style={{ marginTop: "1rem" }}>
        {item.map((it, i) => (
          <div key={i} className="card" style={{ padding: "0.8rem" }}>
            <div className="form-grid">
              <Field label="Sumber"><select value={it.sumber} onChange={(e) => upd(i, "sumber", e.target.value)}>{Object.entries(SUMBER).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}</select></Field>
              <Field label="Keterangan"><input value={it.keterangan} onChange={(e) => upd(i, "keterangan", e.target.value)} /></Field>
              <Field label="Aturan (JSON)" span2><textarea className="mono" style={{ minHeight: 70 }} value={it.aturan} onChange={(e) => upd(i, "aturan", e.target.value)} /></Field>
            </div>
            <Button size="sm" variant="danger" onClick={() => setItem(item.filter((_, j) => j !== i))}><Icon name="trash" size={13} /> Hapus aturan</Button>
          </div>
        ))}
        <Button variant="ghost" size="sm" onClick={() => setItem([...item, { sumber: "dosen", aturan: "{}", keterangan: "" }])}><Icon name="plus" size={14} /> Tambah sumber</Button>
      </div>
      {galat && <div style={{ marginTop: "1rem" }}><Alert jenis="danger">{galat}</Alert></div>}
      {simpan.error && <ErrorBox error={simpan.error} />}
    </Modal>
  );
}

