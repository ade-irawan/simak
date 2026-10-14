import { useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "@/shared/api/client";
import type { Halaman, Rec } from "@/shared/api/types";
import { useAuth } from "@/shared/auth/AuthProvider";
import { useAksi, useApi } from "@/shared/lib/hooks";
import { angka, labelEnum, namaLam, tanggal } from "@/shared/lib/format";
import { Alert, Button, Card, Empty, ErrorBox, Field, Icon, LinkButton, Modal, Muat, PageHead, Pager, Pill, Progress, StatusPill, Tabel, Tabs, type Kolom } from "@/shared/ui";
import { LaporanTab } from "../laporan/LaporanTab";
import { SimulasiTab } from "../laporan/SimulasiTab";
import { PilihPenanggungJawab } from "./PilihPenanggungJawab";

/* ------------------------------------------------------------------ daftar siklus */
export function SiklusListPage() {
  const { punya } = useAuth();
  const nav = useNavigate();
  const [baru, setBaru] = useState(false);
  const q = useApi<Rec[]>("/siklus");
  const kolom: Kolom<Rec>[] = [
    { kunci: "nama", judul: "Siklus", render: (s) => <div><div className="cell-title">{s.nama}</div><div className="cell-sub">Prodi {s.prodi.nama}</div></div> },
    { kunci: "instrumen", judul: "Instrumen", render: (s) => <span>{namaLam(s.instrumen.lam)} <span className="muted">{s.instrumen.kode_versi}</span></span> },
    { kunci: "status", judul: "Status", render: (s) => <StatusPill status={s.status} /> },
    { kunci: "laporan", judul: "Laporan", render: (s) => <StatusPill status={s.laporan} /> },
    { kunci: "target", judul: "Target peringkat", render: (s) => s.target_peringkat?.nama ?? <span className="faint">—</span> },
    { kunci: "tenggat", judul: "Tenggat", render: (s) => tanggal(s.tenggat) },
  ];
  return (
    <div className="stack">
      <PageHead judul="Siklus akreditasi" sub="Satu siklus berjalan per program studi, terkunci pada satu versi instrumen." aksi={punya("dekan") && <Button onClick={() => setBaru(true)}><Icon name="plus" size={16} /> Buka siklus</Button>} />
      <Muat q={q}>
        {(d) => <Tabel kolom={kolom} baris={d} id={(s) => s.id} onKlik={(s) => nav(`/siklus/${s.id}`)} kosong={punya("dekan") ? "Belum ada siklus. Klik “Buka siklus” untuk memulai." : "Belum ada siklus untuk prodi Anda."} />}
      </Muat>
      {baru && <BukaSiklusModal onTutup={() => setBaru(false)} onSelesai={(s) => { setBaru(false); nav(`/siklus/${s.id}`); }} />}
    </div>
  );
}

function BukaSiklusModal({ onTutup, onSelesai }: { onTutup: () => void; onSelesai: (s: Rec) => void }) {
  const prodi = useApi<Rec[]>("/prodi");
  const tahun = useApi<Rec[]>("/tahun-akademik");
  const instrumen = useApi<Rec[]>("/instrumen");
  const [f, setF] = useState({ prodi_id: "", nama: "", ts: "", jumlah: "3", mulai: new Date().toISOString().slice(0, 10), tenggat: "", target: "" });
  const set = (k: string, v: string) => setF((x) => ({ ...x, [k]: v }));
  const p = prodi.data?.find((x) => x.id === f.prodi_id);
  const ins = instrumen.data?.find((i) => i.lam.kode === p?.lam && i.status === "aktif");
  const detail = useApi<Rec>(ins ? `/instrumen/${ins.id}` : null);
  const simpan = useAksi(
    () => api.post("/siklus", { prodi_id: f.prodi_id, nama: f.nama, ts_tahun_akademik_id: f.ts, jumlah_tahun_data: Number(f.jumlah), tanggal_mulai: f.mulai, tenggat: f.tenggat || null, target_peringkat_kode: f.target || null }),
    { sukses: "Siklus dibuka; lembar kerja tiap butir dibuat otomatis", invalidate: ["/siklus", "/dasbor"], onSuccess: onSelesai },
  );
  return (
    <Modal judul="Buka siklus akreditasi" onTutup={onTutup} footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button disabled={!f.prodi_id || !f.nama || !f.ts || !ins || simpan.isPending} onClick={() => simpan.mutate()}>{simpan.isPending && <span className="spinner" />} Buka siklus</Button></>}>
      <div className="form-grid">
        <Field label="Program studi" wajib><select value={f.prodi_id} onChange={(e) => set("prodi_id", e.target.value)}><option value="">— pilih —</option>{prodi.data?.map((x) => <option key={x.id} value={x.id}>{x.nama} ({namaLam(x.lam)})</option>)}</select></Field>
        <Field label="Tahun akademik TS" wajib bantuan="Data dihitung TS-n … TS."><select value={f.ts} onChange={(e) => set("ts", e.target.value)}><option value="">— pilih —</option>{tahun.data?.map((x) => <option key={x.id} value={x.id}>{x.kode}</option>)}</select></Field>
        <Field label="Nama siklus" wajib span2><input value={f.nama} onChange={(e) => set("nama", e.target.value)} placeholder={p ? `Akreditasi ${p.nama} ${tahun.data?.find((t) => t.id === f.ts)?.kode ?? ""}` : ""} /></Field>
        <Field label="Jumlah tahun data"><input type="number" min={1} max={7} value={f.jumlah} onChange={(e) => set("jumlah", e.target.value)} /></Field>
        <Field label="Target peringkat">
          <select value={f.target} onChange={(e) => set("target", e.target.value)} disabled={!detail.data}><option value="">— belum ditetapkan —</option>{detail.data?.peringkat.map((x: Rec) => <option key={x.kode} value={x.kode}>{x.nama}</option>)}</select>
        </Field>
        <Field label="Tanggal mulai" wajib><input type="date" value={f.mulai} onChange={(e) => set("mulai", e.target.value)} /></Field>
        <Field label="Tenggat"><input type="date" value={f.tenggat} onChange={(e) => set("tenggat", e.target.value)} /></Field>
      </div>
      {f.prodi_id && !ins && !instrumen.isLoading && <Alert jenis="warn" judul="Belum ada instrumen aktif">Staf Admin Fakultas perlu menyusun instrumen {namaLam(p?.lam)} dan Dekan mengaktifkannya (menu Instrumen &amp; pemetaan).</Alert>}
      {ins && <Alert jenis="info">Instrumen otomatis mengikuti prodi: <strong>{ins.nama}</strong>.</Alert>}
      {simpan.error && <ErrorBox error={simpan.error} />}
    </Modal>
  );
}

/* ------------------------------------------------------------------ detail siklus */
type TabSiklus = "butir" | "laporan" | "simulasi" | "pengaturan";

export function SiklusDetailPage({ tabAwal }: { tabAwal?: TabSiklus }) {
  const { id } = useParams();
  const { punya } = useAuth();
  const [sp, setSp] = useSearchParams();
  const tab = (sp.get("tab") as TabSiklus) ?? tabAwal ?? "butir";
  const q = useApi<Rec>(`/siklus/${id}`);
  const ganti = (t: TabSiklus) => setSp({ tab: t });
  return (
    <div className="stack">
      <Muat q={q}>
        {(s) => {
          const k = s.kesiapan;
          return (
            <>
              <PageHead
                crumbs={[{ label: "Siklus", to: "/siklus" }, { label: s.prodi.nama }]}
                judul={s.nama}
                sub={<>Prodi {s.prodi.nama} · {namaLam(s.instrumen.lam)} {s.instrumen.kode_versi} · tenggat {tanggal(s.tenggat)}</>}
                aksi={<><StatusPill status={s.status} /><StatusPill status={s.laporan} /></>}
              />
              {k && (
                <Card>
                  <div className="row row--between" style={{ marginBottom: "0.5rem" }}>
                    <span className="metric__label">Kesiapan dokumen</span>
                    <strong className="score">{angka(k.persen_siap, 1)}% · {k.butir_lengkap}/{k.jumlah_butir} butir lengkap</strong>
                  </div>
                  <Progress nilai={Number(k.persen_siap)} />
                </Card>
              )}
              <Tabs
                aktif={tab}
                onGanti={ganti}
                tabs={[
                  { kunci: "butir", label: "Butir" },
                  { kunci: "laporan", label: "Laporan & validasi" },
                  ...(punya("dekan", "kaprodi") ? [{ kunci: "simulasi" as const, label: "Simulasi skor" }] : []),
                  ...(punya("dekan") ? [{ kunci: "pengaturan" as const, label: "Pengaturan" }] : []),
                ]}
              />
              {tab === "butir" && <ButirTab siklus={s} />}
              {tab === "laporan" && <LaporanTab siklus={s} />}
              {tab === "simulasi" && <SimulasiTab siklus={s} />}
              {tab === "pengaturan" && <PengaturanTab siklus={s} />}
            </>
          );
        }}
      </Muat>
    </div>
  );
}

function ButirTab({ siklus }: { siklus: Rec }) {
  const { punya } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ status_kelengkapan: "", pengelola: "", q: "", flag: "" });
  const [page, setPage] = useState(1);
  const [pilih, setPilih] = useState<string[]>([]);
  const [tugas, setTugas] = useState(false);
  const query = {
    status_kelengkapan: f.status_kelengkapan, pengelola: f.pengelola, q: f.q, page, per_page: 50,
    belum_ditugaskan: f.flag === "belum_ditugaskan" || undefined,
    bukti_bermasalah: f.flag === "bukti_bermasalah" || undefined,
    menunggu_dokumen_eksternal: f.flag === "menunggu" || undefined,
  };
  const q = useApi<Halaman<Rec>>(`/siklus/${siklus.id}/butir`, query, { keep: true });
  const dekan = punya("dekan");
  const kolom: Kolom<Rec>[] = useMemo(() => [
    ...(dekan ? [{ kunci: "pilih", judul: "", lebar: "34px", render: (b: Rec) => <input type="checkbox" checked={pilih.includes(b.id)} onClick={(e) => e.stopPropagation()} onChange={(e) => setPilih(e.target.checked ? [...pilih, b.id] : pilih.filter((x) => x !== b.id))} aria-label={`Pilih butir ${b.butir.kode}`} /> }] : []),
    { kunci: "kode", judul: "Butir", render: (b: Rec) => <div><span className="butir-code">{b.butir.kode}</span><div className="cell-sub">{b.butir.kriteria.kode} · {b.butir.kriteria.nama}</div></div> },
    { kunci: "elemen", judul: "Elemen penilaian", render: (b: Rec) => <span style={{ display: "block", maxWidth: 480 }}>{b.butir.elemen}</span> },
    { kunci: "status", judul: "Status", render: (b: Rec) => <StatusPill status={b.status_kelengkapan} /> },
    { kunci: "skor", judul: "Skor", num: true, render: (b: Rec) => (b.skor_estimasi !== null ? <span className="score">{angka(b.skor_estimasi, 1)}</span> : <span className="faint">—</span>) },
    { kunci: "pj", judul: "Penanggung jawab", render: (b: Rec) => <div>{b.penanggung_jawab?.nama ?? <span style={{ color: "var(--amber)" }}>Belum ditugaskan</span>}<div className="cell-sub">{labelEnum(b.pengelola)}</div></div> },
    { kunci: "bukti", judul: "Bukti", render: (b: Rec) => <div className="chips"><Pill>{b.jumlah_bukti}</Pill>{b.jumlah_bukti_bermasalah > 0 && <Pill warna="red" dot>{b.jumlah_bukti_bermasalah} rusak</Pill>}{b.menunggu_dokumen_eksternal && <Pill warna="amber">Direktorat</Pill>}{b.catatan_validasi_terbuka > 0 && <Pill warna="red">{b.catatan_validasi_terbuka} catatan</Pill>}</div> },
  ], [dekan, pilih]);
  return (
    <div className="stack">
      <div className="toolbar">
        <input className="input" placeholder="Cari kode atau elemen…" value={f.q} onChange={(e) => { setF({ ...f, q: e.target.value }); setPage(1); }} />
        <select className="input" value={f.status_kelengkapan} onChange={(e) => { setF({ ...f, status_kelengkapan: e.target.value }); setPage(1); }}><option value="">Semua status</option><option value="belum_mulai">Belum mulai</option><option value="draft">Draf</option><option value="lengkap">Lengkap</option></select>
        <select className="input" value={f.pengelola} onChange={(e) => { setF({ ...f, pengelola: e.target.value }); setPage(1); }}><option value="">Semua pengelola</option><option value="prodi">Dikelola prodi</option><option value="fakultas">Dikelola fakultas</option></select>
        <select className="input" value={f.flag} onChange={(e) => { setF({ ...f, flag: e.target.value }); setPage(1); }}><option value="">Semua tanda</option><option value="belum_ditugaskan">Belum ditugaskan</option><option value="bukti_bermasalah">Bukti bermasalah</option><option value="menunggu">Menunggu dokumen Direktorat</option></select>
        <span className="spacer" />
        {dekan && pilih.length > 0 && <Button variant="lime" size="sm" onClick={() => setTugas(true)}><Icon name="users" size={14} /> Tugaskan {pilih.length} butir</Button>}
      </div>
      <Muat q={q}>
        {(d) => (
          <>
            <Tabel kolom={kolom} baris={d.data} id={(b) => b.id} onKlik={(b) => nav(`/butir/${b.id}`)} kosong="Tidak ada butir yang cocok dengan penyaring." />
            <Pager page={d.meta.page} perPage={d.meta.per_page} total={d.meta.total} onGanti={setPage} />
          </>
        )}
      </Muat>
      {tugas && <TugaskanModal siklus={siklus} ids={pilih} onTutup={() => setTugas(false)} onSelesai={() => { setTugas(false); setPilih([]); }} />}
    </div>
  );
}

function TugaskanModal({ siklus, ids, onTutup, onSelesai }: { siklus: Rec; ids: string[]; onTutup: () => void; onSelesai: () => void }) {
  const [pengelola, setPengelola] = useState("prodi");
  const [pj, setPj] = useState("");
  const simpan = useAksi(() => api.post(`/siklus/${siklus.id}/penugasan-massal`, { butir_siklus_ids: ids, pengelola, penanggung_jawab_id: pj || null }), {
    sukses: (r) => `${r.jumlah} butir ditugaskan`, invalidate: ["/siklus", "/butir-siklus", "/saya", "/dasbor"], onSuccess: onSelesai,
  });
  return (
    <Modal judul={`Tugaskan ${ids.length} butir`} onTutup={onTutup} footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button onClick={() => simpan.mutate()} disabled={simpan.isPending}>Tetapkan</Button></>}>
      <Field label="Dikelola oleh" bantuan="Butir di luar kendali prodi (SK fakultas, keuangan, kerja sama, tracer) masuk antrean Staf Fakultas.">
        <select value={pengelola} onChange={(e) => { setPengelola(e.target.value); setPj(""); }}><option value="prodi">Prodi (Staf Admin Prodi)</option><option value="fakultas">Fakultas (Staf Admin Fakultas)</option></select>
      </Field>
      <Field label="Penanggung jawab"><PilihPenanggungJawab prodiId={siklus.prodi.id} pengelola={pengelola} nilai={pj} onUbah={setPj} /></Field>
      {simpan.error && <ErrorBox error={simpan.error} />}
    </Modal>
  );
}

/* ------------------------------------------------------------------ pengaturan siklus (Dekan) */
function PengaturanTab({ siklus }: { siklus: Rec }) {
  const [tenggat, setTenggat] = useState<string>(siklus.tenggat ?? "");
  const [target, setTarget] = useState<string>(siklus.target_peringkat?.kode ?? "");
  const [status, setStatus] = useState<string>(siklus.status);
  const [migrasi, setMigrasi] = useState("");
  const instrumen = useApi<Rec[]>("/instrumen");
  const kandidat = (instrumen.data ?? []).filter((i) => i.status === "aktif" && i.lam.kode === siklus.instrumen.lam && i.id !== siklus.instrumen.versi_id);
  const simpan = useAksi(() => api.patch(`/siklus/${siklus.id}`, { tenggat: tenggat || null, target_peringkat_kode: target || null, status }), { sukses: "Pengaturan siklus disimpan", invalidate: ["/siklus", "/dasbor"] });
  const pindah = useAksi(() => api.post(`/siklus/${siklus.id}/migrasi-instrumen`, { instrumen_versi_id: migrasi }), {
    sukses: (r) => `Migrasi selesai: ${r.butir_dipetakan} butir dipetakan, narasi dipertahankan`, invalidate: ["/siklus", "/butir-siklus"],
  });
  return (
    <div className="grid grid--2">
      <Card judul="Parameter siklus">
        <Field label="Tenggat"><input type="date" value={tenggat} onChange={(e) => setTenggat(e.target.value)} /></Field>
        <Field label="Target peringkat"><select value={target} onChange={(e) => setTarget(e.target.value)}><option value="">— belum ditetapkan —</option>{siklus.peringkat_tersedia.map((p: Rec) => <option key={p.kode} value={p.kode}>{p.nama}</option>)}</select></Field>
        <Field label="Status siklus" bantuan="Status hanya dapat maju: persiapan → berjalan → selesai → arsip.">
          <select value={status} onChange={(e) => setStatus(e.target.value)}>{["persiapan", "berjalan", "selesai", "arsip"].map((s) => <option key={s} value={s}>{labelEnum(s)}</option>)}</select>
        </Field>
        <Button onClick={() => simpan.mutate()} disabled={simpan.isPending}>Simpan</Button>
        {simpan.error && <div style={{ marginTop: "1rem" }}><ErrorBox error={simpan.error} /></div>}
      </Card>
      <Card judul="Migrasi ke versi instrumen baru" sub="Butir dipadankan menurut kode/padanan; narasi dan tautan bukti dipindahkan, tidak dihapus (EC-14).">
        {kandidat.length === 0 ? <Alert jenis="info">Tidak ada versi instrumen aktif lain untuk LAM ini.</Alert> : (
          <>
            <Field label="Versi baru"><select value={migrasi} onChange={(e) => setMigrasi(e.target.value)}><option value="">— pilih —</option>{kandidat.map((i) => <option key={i.id} value={i.id}>{i.nama} ({i.kode_versi})</option>)}</select></Field>
            <Button variant="lime" disabled={!migrasi || pindah.isPending} onClick={() => pindah.mutate()}>Migrasikan siklus</Button>
          </>
        )}
        {pindah.error && <div style={{ marginTop: "1rem" }}><ErrorBox error={pindah.error} /></div>}
        {pindah.data?.butir_lama_tanpa_padanan?.length > 0 && <Alert jenis="warn" judul="Butir lama tanpa padanan">{pindah.data.butir_lama_tanpa_padanan.join(", ")} — narasinya tetap tersimpan.</Alert>}
      </Card>
    </div>
  );
}

export function PapanKerjaPage() {
  const q = useApi<Rec>("/saya/butir");
  const kolom: Kolom<Rec>[] = [
    { kunci: "kode", judul: "Butir", render: (b) => <Link to={`/butir/${b.id}`} className="butir-code">{b.kode}</Link> },
    { kunci: "prodi", judul: "Prodi", render: (b) => b.prodi },
    { kunci: "elemen", judul: "Elemen", render: (b) => <span style={{ display: "block", maxWidth: 460 }}>{b.elemen}</span> },
    { kunci: "status", judul: "Status", render: (b) => <StatusPill status={b.status_kelengkapan} /> },
    { kunci: "bukti", judul: "Bukti", render: (b) => <div className="chips"><Pill>{b.jumlah_bukti}</Pill>{b.jumlah_bukti_bermasalah > 0 && <Pill warna="red">{b.jumlah_bukti_bermasalah} rusak</Pill>}{b.menunggu_dokumen_eksternal && <Pill warna="amber">Menunggu Direktorat</Pill>}</div> },
  ];
  return (
    <div className="stack">
      <PageHead judul="Papan kerja saya" sub="Hanya butir yang ditugaskan Dekan kepada Anda, ditambah antrean butir yang belum bertuan pada bagian Anda." />
      <Muat q={q}>
        {(d) => (
          <>
            <Card judul="Ditugaskan kepada saya" flush>{d.ditugaskan.length ? <Tabel kolom={kolom} baris={d.ditugaskan} id={(b) => b.id} /> : <Empty judul="Belum ada butir yang ditugaskan" ikon="clipboard" />}</Card>
            <Card judul="Antrean belum bertuan" sub="Butir pada bagian Anda yang belum diberi penanggung jawab." flush>{d.antrean_belum_bertuan.length ? <Tabel kolom={kolom} baris={d.antrean_belum_bertuan} id={(b) => b.id} /> : <Empty judul="Antrean kosong" />}</Card>
          </>
        )}
      </Muat>
    </div>
  );
}

export { LinkButton };
