import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "@/shared/api/client";
import type { Halaman, Rec } from "@/shared/api/types";
import { useAuth } from "@/shared/auth/AuthProvider";
import { useAksi, useApi } from "@/shared/lib/hooks";
import { angka, labelEnum, tanggal } from "@/shared/lib/format";
import { Alert, Button, Card, Empty, ErrorBox, Field, FormFields, Icon, keMuatan, Modal, Muat, PageHead, Pill, Progress, StatusPill, Tabel, Tabs, validasiWajib, type DefField, type Kolom } from "@/shared/ui";

const INV = ["/siklus-ppepp", "/penetapan", "/standar-spm", "/butir-standar", "/dasbor"];
type Tab = "penetapan" | "katalog" | "rekap";

export function PpeppPage() {
  const { punya } = useAuth();
  const [tab, setTab] = useState<Tab>("penetapan");
  return (
    <div className="stack">
      <PageHead judul="Penjaminan mutu (PPEPP)" sub="Dekan menetapkan butir sasaran dari katalog Standar SPM (P1); prodi mendokumentasikan Pelaksanaan, Evaluasi, Pengendalian, dan Peningkatan dengan kerangka yang seragam." />
      <Tabs aktif={tab} onGanti={setTab} tabs={[{ kunci: "penetapan", label: "Butir sasaran & tahapan" }, { kunci: "katalog", label: "Katalog standar SPM" }, ...(punya("dekan") ? [{ kunci: "rekap" as const, label: "Rekap kemajuan" }] : [])]} />
      {tab === "penetapan" && <PenetapanTab />}
      {tab === "katalog" && <KatalogTab />}
      {tab === "rekap" && <RekapTab />}
    </div>
  );
}

function usePilihSiklus() {
  const q = useApi<Rec[]>("/siklus-ppepp");
  const [id, setId] = useState("");
  useEffect(() => { if (!id && q.data?.length) setId(q.data[0].id); }, [q.data, id]);
  return { q, id, setId, siklus: q.data?.find((s) => s.id === id) };
}

function PilihSiklusPpepp({ s }: { s: ReturnType<typeof usePilihSiklus> }) {
  return (
    <select className="input" value={s.id} onChange={(e) => s.setId(e.target.value)} style={{ maxWidth: 360 }} aria-label="Siklus PPEPP">
      {s.q.data?.map((x) => <option key={x.id} value={x.id}>{x.nama} — {labelEnum(x.status)}</option>)}
    </select>
  );
}

/* ------------------------------------------------------------------ P1 + daftar butir sasaran */
function PenetapanTab() {
  const { punya } = useAuth();
  const nav = useNavigate();
  const s = usePilihSiklus();
  const [baru, setBaru] = useState(false);
  const [tambah, setTambah] = useState(false);
  const [ubah, setUbah] = useState<Rec | null>(null);
  const list = useApi<Rec[]>(s.id ? `/siklus-ppepp/${s.id}/penetapan` : null);
  const tetapkan = useAksi(() => api.post(`/siklus-ppepp/${s.id}/tetapkan`), { sukses: (r) => `${r.butir_ditetapkan} butir ditetapkan; ${r.tahapan_dibuat} tahapan dibuat`, invalidate: INV });
  const selesai = useAksi(() => api.post(`/siklus-ppepp/${s.id}/selesai`), { sukses: "Siklus PPEPP diselesaikan; hasil Peningkatan menjadi baseline siklus berikutnya", invalidate: INV });
  const dekan = punya("dekan");
  const kolom: Kolom<Rec>[] = [
    { kunci: "no", judul: "Butir sasaran", render: (p) => <div><span className="butir-code">{p.nomor_butir}</span><div className="cell-sub" style={{ maxWidth: 420 }}>{p.isi}</div></div> },
    { kunci: "ind", judul: "Indikator & target", render: (p) => <div>{p.indikator}<div className="cell-sub">Target {angka(p.target_nilai, 2)} {p.target_satuan ?? ""}</div></div> },
    { kunci: "cakupan", judul: "Cakupan", render: (p) => (p.prodi_id ? <Pill>Satu prodi</Pill> : <Pill warna="blue">Semua prodi</Pill>) },
    { kunci: "base", judul: "Baseline", num: true, render: (p) => (p.baseline_nilai !== null ? <span title={p.baseline_dari?.siklus}>{angka(p.baseline_nilai, 2)}</span> : <span className="faint">—</span>) },
    { kunci: "st", judul: "Status", render: (p) => <StatusPill status={p.status} /> },
    { kunci: "aksi", judul: "", render: (p) => (
      <div className="row" style={{ justifyContent: "flex-end" }} onClick={(e) => e.stopPropagation()}>
        {dekan && <Button variant="ghost" size="icon" title="Ubah" onClick={() => setUbah(p)}><Icon name="edit" size={15} /></Button>}
        {p.status === "ditetapkan" && <Link className="btn btn--ghost btn--sm" to={`/ppepp/penetapan/${p.id}`}>Tahapan <Icon name="chevronRight" size={13} /></Link>}
      </div>
    ) },
  ];
  return (
    <div className="stack">
      <div className="toolbar">
        <PilihSiklusPpepp s={s} />
        <span className="spacer" />
        {dekan && <Button variant="ghost" onClick={() => setBaru(true)}><Icon name="plus" size={15} /> Siklus PPEPP baru</Button>}
        {dekan && s.id && <Button variant="primary" onClick={() => setTambah(true)}><Icon name="plus" size={15} /> Butir sasaran</Button>}
        {dekan && s.siklus && list.data?.some((p) => p.status === "draf") && <Button variant="lime" onClick={() => tetapkan.mutate()} disabled={tetapkan.isPending}>Tetapkan resmi (P1)</Button>}
        {dekan && s.siklus && s.siklus.status !== "selesai" && s.siklus.status !== "draf" && <Button variant="ghost" onClick={() => selesai.mutate()}>Selesaikan siklus</Button>}
      </div>
      {s.q.isLoading ? null : !s.q.data?.length ? (
        <Card><Empty judul="Belum ada siklus PPEPP" ikon="target">{dekan ? "Buat siklus PPEPP, lalu pilih butir sasaran dari katalog Standar SPM yang sudah divalidasi." : "Menunggu Dekan menetapkan butir sasaran."}</Empty></Card>
      ) : (
        <Muat q={list}>{(d) => (d.length ? <Tabel kolom={kolom} baris={d} id={(p) => p.id} onKlik={(p) => p.status === "ditetapkan" && nav(`/ppepp/penetapan/${p.id}`)} /> : <Card><Empty judul="Belum ada butir sasaran" ikon="target" /></Card>)}</Muat>
      )}
      {tetapkan.error && <ErrorBox error={tetapkan.error} />}
      {baru && <SiklusPpeppModal onTutup={() => setBaru(false)} onSelesai={(x) => { setBaru(false); s.setId(x.id); }} />}
      {tambah && s.id && <PenetapanModal siklusId={s.id} onTutup={() => setTambah(false)} />}
      {ubah && <PenetapanModal siklusId={s.id} awal={ubah} onTutup={() => setUbah(null)} />}
    </div>
  );
}

function SiklusPpeppModal({ onTutup, onSelesai }: { onTutup: () => void; onSelesai: (x: Rec) => void }) {
  const ta = useApi<Rec[]>("/tahun-akademik");
  const [f, setF] = useState({ nama: "", tahun_akademik_id: "", tanggal_mulai: "", tanggal_selesai: "" });
  const simpan = useAksi(() => api.post("/siklus-ppepp", { ...f, tanggal_selesai: f.tanggal_selesai || null }), { sukses: "Siklus PPEPP dibuat", invalidate: INV, onSuccess: onSelesai });
  const set = (k: string, v: string) => setF({ ...f, [k]: v });
  return (
    <Modal judul="Siklus PPEPP baru" onTutup={onTutup} footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button disabled={!f.nama || !f.tahun_akademik_id || !f.tanggal_mulai || simpan.isPending} onClick={() => simpan.mutate()}>Buat</Button></>}>
      <Alert jenis="info">Hasil Peningkatan siklus sebelumnya otomatis menjadi baseline Penetapan siklus baru (EC-22).</Alert>
      <div className="form-grid" style={{ marginTop: "1rem" }}>
        <Field label="Nama" wajib span2><input value={f.nama} onChange={(e) => set("nama", e.target.value)} placeholder="PPEPP 2026/2027" /></Field>
        <Field label="Tahun akademik" wajib><select value={f.tahun_akademik_id} onChange={(e) => set("tahun_akademik_id", e.target.value)}><option value="">— pilih —</option>{ta.data?.map((t) => <option key={t.id} value={t.id}>{t.kode}</option>)}</select></Field>
        <span />
        <Field label="Mulai" wajib><input type="date" value={f.tanggal_mulai} onChange={(e) => set("tanggal_mulai", e.target.value)} /></Field>
        <Field label="Selesai"><input type="date" value={f.tanggal_selesai} onChange={(e) => set("tanggal_selesai", e.target.value)} /></Field>
      </div>
      {simpan.error && <ErrorBox error={simpan.error} />}
    </Modal>
  );
}

function PenetapanModal({ siklusId, awal, onTutup }: { siklusId: string; awal?: Rec; onTutup: () => void }) {
  const katalog = useApi<Rec[]>("/standar-spm");
  const prodi = useApi<Rec[]>("/prodi");
  const [butirId, setButirId] = useState<string>(awal?.butir_standar_id ?? "");
  const [f, setF] = useState<Rec>(awal ? { ...awal } : { prodi_id: "", nomor_butir: "", isi: "", indikator: "", target_nilai: "", target_satuan: "", target_deskripsi: "" });
  const set = (k: string, v: any) => setF((x) => ({ ...x, [k]: v }));
  const semuaButir = (katalog.data ?? []).filter((s) => s.divalidasi_pada && s.is_aktif).flatMap((s) => s.butir.filter((b: Rec) => b.is_aktif).map((b: Rec) => ({ ...b, standar: s.nama })));
  const pilih = (id: string) => {
    setButirId(id);
    const b = semuaButir.find((x) => x.id === id);
    if (b) setF((x) => ({ ...x, nomor_butir: b.nomor, isi: b.pernyataan, indikator: b.indikator ?? "", target_satuan: b.satuan ?? "", target_nilai: x.target_nilai || (b.target_default && !isNaN(Number(b.target_default)) ? b.target_default : "") }));
  };
  const simpan = useAksi(() => {
    const badan = { nomor_butir: f.nomor_butir, isi: f.isi, indikator: f.indikator, target_nilai: f.target_nilai === "" || f.target_nilai === null ? null : Number(f.target_nilai), target_satuan: f.target_satuan || null, target_deskripsi: f.target_deskripsi || null };
    return awal ? api.patch(`/penetapan/${awal.id}`, { ...badan, row_version: awal.row_version }) : api.post(`/siklus-ppepp/${siklusId}/penetapan`, { ...badan, butir_standar_id: butirId, prodi_id: f.prodi_id || null });
  }, { sukses: awal ? "Butir sasaran diubah (tercatat di audit)" : "Butir sasaran ditambahkan (draf)", invalidate: INV, onSuccess: onTutup });
  return (
    <Modal judul={awal ? "Ubah butir sasaran" : "Tambah butir sasaran (P1)"} onTutup={onTutup} lebar footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button disabled={(!awal && !butirId) || !f.nomor_butir || !f.isi || !f.indikator || simpan.isPending} onClick={() => simpan.mutate()}>Simpan</Button></>}>
      {!awal && (
        <>
          <Field label="Butir standar dari katalog SPM" wajib bantuan="Hanya standar yang sudah divalidasi Dekan yang dapat dipilih.">
            <select value={butirId} onChange={(e) => pilih(e.target.value)}><option value="">— pilih butir standar —</option>{semuaButir.map((b) => <option key={b.id} value={b.id}>{b.nomor} — {b.pernyataan.slice(0, 80)} ({b.standar})</option>)}</select>
          </Field>
          <Field label="Berlaku untuk"><select value={f.prodi_id} onChange={(e) => set("prodi_id", e.target.value)}><option value="">Semua prodi (kerangka seragam)</option>{prodi.data?.map((p) => <option key={p.id} value={p.id}>{p.nama} saja</option>)}</select></Field>
        </>
      )}
      <div className="form-grid">
        <Field label="Nomor butir" wajib><input value={f.nomor_butir} onChange={(e) => set("nomor_butir", e.target.value)} /></Field>
        <Field label="Satuan target"><input value={f.target_satuan ?? ""} onChange={(e) => set("target_satuan", e.target.value)} /></Field>
        <Field label="Isi / pernyataan standar" wajib span2><textarea style={{ minHeight: 70 }} value={f.isi} onChange={(e) => set("isi", e.target.value)} /></Field>
        <Field label="Indikator capaian" wajib span2><input value={f.indikator} onChange={(e) => set("indikator", e.target.value)} /></Field>
        <Field label="Target (angka)"><input type="number" step="any" value={f.target_nilai ?? ""} onChange={(e) => set("target_nilai", e.target.value)} /></Field>
        <Field label="Deskripsi target"><input value={f.target_deskripsi ?? ""} onChange={(e) => set("target_deskripsi", e.target.value)} /></Field>
      </div>
      {simpan.error && <ErrorBox error={simpan.error} />}
    </Modal>
  );
}

/* ------------------------------------------------------------------ katalog SPM */
function KatalogTab() {
  const { punya } = useAuth();
  const q = useApi<Rec[]>("/standar-spm");
  const [standar, setStandar] = useState(false);
  const [butir, setButir] = useState<Rec | null>(null);
  const validasi = useAksi((id: string) => api.post(`/standar-spm/${id}/validasi`), { sukses: "Standar divalidasi", invalidate: INV });
  return (
    <div className="stack">
      <div className="toolbar"><span className="spacer" />{punya("staf_fakultas") && <Button onClick={() => setStandar(true)}><Icon name="plus" size={15} /> Standar baru</Button>}</div>
      <Alert jenis="info">Katalog dikelola Staf Admin Fakultas dari dokumen Satuan Penjaminan Mutu dan divalidasi Dekan. Mengubah katalog mencabut validasinya.</Alert>
      <Muat q={q}>
        {(d) => d.length === 0 ? <Card><Empty judul="Katalog masih kosong" ikon="book" /></Card> : (
          <div className="stack">
            {d.map((s) => (
              <Card key={s.id} judul={<>{s.kode} — {s.nama}</>} sub={`${s.kategori ?? "—"} · ${s.dokumen_sumber ?? "dokumen sumber belum dicatat"}`} aksi={
                <>
                  {s.divalidasi_pada ? <Pill warna="lime" dot>Divalidasi {tanggal(s.divalidasi_pada)}</Pill> : <Pill warna="amber" dot>Belum divalidasi</Pill>}
                  {punya("dekan") && !s.divalidasi_pada && <Button size="sm" variant="lime" onClick={() => validasi.mutate(s.id)}>Validasi</Button>}
                  {punya("staf_fakultas") && <Button size="sm" variant="ghost" onClick={() => setButir(s)}><Icon name="plus" size={14} /> Butir</Button>}
                </>
              }>
                {s.butir.length === 0 ? <div className="muted">Belum ada butir.</div> : (
                  <div className="stack stack--sm">{s.butir.map((b: Rec) => (
                    <div key={b.id} className="source-card"><span className="butir-code">{b.nomor}</span> {b.pernyataan}
                      <div className="cell-sub">Indikator: {b.indikator ?? "—"} · target bawaan {b.target_default ?? "—"} {b.satuan ?? ""}</div></div>
                  ))}</div>
                )}
              </Card>
            ))}
          </div>
        )}
      </Muat>
      {standar && <StandarModal onTutup={() => setStandar(false)} />}
      {butir && <ButirStandarModal standar={butir} onTutup={() => setButir(null)} />}
    </div>
  );
}

const DEF_STANDAR: DefField[] = [
  { nama: "kode", label: "Kode", wajib: true }, { nama: "nama", label: "Nama standar", wajib: true }, { nama: "kategori", label: "Kategori" }, { nama: "versi", label: "Versi" },
  { nama: "dokumen_sumber", label: "Dokumen sumber (SPM)", span2: true },
];
const DEF_BUTIR_STANDAR: DefField[] = [
  { nama: "nomor", label: "Nomor butir", wajib: true }, { nama: "satuan", label: "Satuan" }, { nama: "pernyataan", label: "Pernyataan standar", jenis: "teksArea", wajib: true },
  { nama: "indikator", label: "Indikator", span2: true }, { nama: "target_default", label: "Target bawaan" },
];

function StandarModal({ onTutup }: { onTutup: () => void }) {
  const [n, setN] = useState<Rec>({});
  const [g, setG] = useState<Record<string, string>>({});
  const simpan = useAksi(() => api.post("/standar-spm", keMuatan(DEF_STANDAR, n)), { sukses: "Standar dibuat", invalidate: INV, onSuccess: onTutup });
  return (
    <Modal judul="Standar SPM baru" onTutup={onTutup} footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button onClick={() => { const e = validasiWajib(DEF_STANDAR, n); setG(e); if (!Object.keys(e).length) simpan.mutate(); }}>Simpan</Button></>}>
      <FormFields def={DEF_STANDAR} nilai={n} onUbah={(k, v) => setN({ ...n, [k]: v })} galat={g} />
      {simpan.error && <ErrorBox error={simpan.error} />}
    </Modal>
  );
}

function ButirStandarModal({ standar, onTutup }: { standar: Rec; onTutup: () => void }) {
  const [n, setN] = useState<Rec>({});
  const [g, setG] = useState<Record<string, string>>({});
  const simpan = useAksi(() => api.post(`/standar-spm/${standar.id}/butir`, { ...keMuatan(DEF_BUTIR_STANDAR, n), instrumen_butir_ids: [] }), { sukses: "Butir standar ditambahkan", invalidate: INV, onSuccess: onTutup });
  return (
    <Modal judul={`Butir untuk ${standar.kode}`} onTutup={onTutup} footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button onClick={() => { const e = validasiWajib(DEF_BUTIR_STANDAR, n); setG(e); if (!Object.keys(e).length) simpan.mutate(); }}>Simpan</Button></>}>
      <FormFields def={DEF_BUTIR_STANDAR} nilai={n} onUbah={(k, v) => setN({ ...n, [k]: v })} galat={g} />
      {simpan.error && <ErrorBox error={simpan.error} />}
    </Modal>
  );
}

/* ------------------------------------------------------------------ rekap Dekan */
function RekapTab() {
  const s = usePilihSiklus();
  const q = useApi<Rec>(s.id ? `/siklus-ppepp/${s.id}/rekap` : null);
  return (
    <div className="stack">
      <div className="toolbar"><PilihSiklusPpepp s={s} /></div>
      <Muat q={q}>
        {(d) => (
          <div className="grid grid--3">
            {d.prodi.map((p: Rec) => (
              <Card key={p.prodi.id} judul={p.prodi.nama} sub={`${p.butir_sasaran} butir sasaran`}>
                <div className="row row--between" style={{ marginBottom: "0.4rem" }}><span className="metric__label">Tahapan selesai</span><strong>{p.tahap_selesai}/{p.tahap_total}</strong></div>
                <Progress nilai={p.tahap_total ? (p.tahap_selesai / p.tahap_total) * 100 : 0} />
                <div className="stack stack--sm" style={{ marginTop: "1rem" }}>
                  {p.butir.map((b: Rec) => (
                    <div key={b.penetapan_id} className="row row--between" style={{ fontSize: "0.85rem" }}>
                      <span className="butir-code">{b.nomor_butir}</span>
                      <span>{b.capaian_nilai !== null ? <>{angka(b.capaian_nilai, 2)} / {angka(b.target_nilai, 2)} <Pill warna={Number(b.selisih_target) >= 0 ? "lime" : "red"}>{Number(b.selisih_target) >= 0 ? "+" : ""}{angka(b.selisih_target, 2)}</Pill></> : <span className="faint">belum ada capaian</span>}</span>
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        )}
      </Muat>
    </div>
  );
}

/* ------------------------------------------------------------------ tahapan P2–P5 satu butir sasaran */
const URUTAN = ["pelaksanaan", "evaluasi", "pengendalian", "peningkatan"] as const;
const JUDUL: Record<string, string> = { pelaksanaan: "P2 · Pelaksanaan", evaluasi: "P3 · Evaluasi", pengendalian: "P4 · Pengendalian", peningkatan: "P5 · Peningkatan" };

export function TahapanPage() {
  const { id } = useParams();
  const { punya, aktif } = useAuth();
  const prodiList = useApi<Rec[]>("/prodi");
  const [prodi, setProdi] = useState(aktif?.prodi?.id ?? "");
  useEffect(() => { if (!prodi && prodiList.data?.length) setProdi(prodiList.data[0].id); }, [prodiList.data, prodi]);
  const q = useApi<Rec>(prodi ? `/penetapan/${id}/tahapan` : null, { prodi_id: prodi });
  return (
    <div className="stack">
      <PageHead crumbs={[{ label: "PPEPP", to: "/ppepp" }, { label: "Tahapan" }]} judul="Tahapan PPEPP" sub="P1 Penetapan ditetapkan Dekan dan hanya dapat dibaca. Prodi mengisi P2–P5." aksi={punya("dekan", "staf_fakultas") && (
        <select className="input" value={prodi} onChange={(e) => setProdi(e.target.value)}>{prodiList.data?.map((p) => <option key={p.id} value={p.id}>{p.nama}</option>)}</select>
      )} />
      <Muat q={q}>
        {(d) => {
          const p = d.penetapan;
          const per: Record<string, Rec> = Object.fromEntries(d.tahapan.filter((t: Rec) => t.prodi_id === prodi).map((t: Rec) => [t.tahap, t]));
          return (
            <>
              <Card aksen="blue" judul={<><span className="butir-code">{p.nomor_butir}</span> — P1 Penetapan</>} sub="Dibaca saja bagi prodi">
                <p style={{ marginBottom: "0.8rem" }}>{p.isi}</p>
                <div className="chips"><Pill warna="blue">Indikator: {p.indikator}</Pill><Pill warna="lime">Target {angka(p.target_nilai, 2)} {p.target_satuan ?? ""}</Pill>{p.baseline_nilai !== null && <Pill>Baseline {angka(p.baseline_nilai, 2)}</Pill>}</div>
              </Card>
              <div className="phases">{URUTAN.map((t) => <div key={t} className={`phase ${per[t]?.status === "selesai" ? "phase--done" : per[t]?.status === "berjalan" ? "phase--run" : ""}`}><b>{JUDUL[t]}</b><StatusPill status={per[t]?.status} /></div>)}<div className="phase phase--lock"><b>P1 · Penetapan</b><span className="muted">oleh Dekan</span></div></div>
              <div className="grid grid--2" style={{ alignItems: "start" }}>
                {URUTAN.map((t) => per[t] ? <FormTahap key={`${t}-${per[t].row_version}`} penetapanId={id!} prodiId={prodi} tahap={t} data={per[t]} target={p.target_nilai} bisa={punya("kaprodi", "staf_prodi", "staf_fakultas") && (aktif?.prodi?.id === prodi || punya("staf_fakultas"))} /> : null)}
              </div>
            </>
          );
        }}
      </Muat>
    </div>
  );
}

function FormTahap({ penetapanId, prodiId, tahap, data, bisa }: { penetapanId: string; prodiId: string; tahap: string; data: Rec; target: number | null; bisa: boolean }) {
  const [n, setN] = useState<Rec>({ ...data });
  const [saran, setSaran] = useState<Rec | null>(null);
  const def: DefField[] = [
    { nama: "status", label: "Status", jenis: "pilihan", wajib: true, pilihan: [{ nilai: "belum_mulai", label: "Belum mulai" }, { nilai: "berjalan", label: "Berjalan" }, { nilai: "selesai", label: "Selesai" }] },
    { nama: "tenggat", label: "Tenggat", jenis: "tanggal" },
    { nama: "uraian", label: "Uraian", jenis: "teksArea" },
    ...(tahap === "evaluasi" || tahap === "peningkatan" || tahap === "pelaksanaan" ? [{ nama: "capaian_nilai", label: "Capaian (angka)", jenis: "angka" as const }, { nama: "capaian_deskripsi", label: "Deskripsi capaian" }] : []),
    ...(tahap === "evaluasi" ? [{ nama: "temuan", label: "Temuan evaluasi", jenis: "teksArea" as const }] : []),
    ...(tahap === "pengendalian" ? [{ nama: "tindak_lanjut", label: "Tindak lanjut", jenis: "teksArea" as const }] : []),
  ];
  const simpan = useAksi(() => api.put(`/penetapan/${penetapanId}/tahapan/${tahap}`, { ...keMuatan(def, n), row_version: data.row_version, bukti_id: [] }, { prodi_id: prodiId }), {
    sukses: "Tahapan disimpan", invalidate: INV, onSuccess: (r) => setSaran(r.saran_berikutnya),
  });
  return (
    <Card judul={JUDUL[tahap]} sub={data.selisih_target !== null && data.selisih_target !== undefined ? `Selisih terhadap target: ${angka(data.selisih_target, 2)}` : undefined} aksi={<StatusPill status={data.status} />}>
      <FormFields def={def} nilai={n} onUbah={(k, v) => setN({ ...n, [k]: v })} disabled={!bisa} />
      {saran && <Alert jenis="info" judul="Saran langkah berikutnya">{saran.pesan}</Alert>}
      {bisa && <div style={{ marginTop: "0.8rem" }}><Button onClick={() => simpan.mutate()} disabled={simpan.isPending}>Simpan {JUDUL[tahap].split("· ")[1]}</Button></div>}
      {simpan.error instanceof ApiError && <div style={{ marginTop: "0.8rem" }}><ErrorBox error={simpan.error} /></div>}
    </Card>
  );
}

export type { Halaman };
