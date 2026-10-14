import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "@/shared/api/client";
import type { Rec } from "@/shared/api/types";
import { useAuth } from "@/shared/auth/AuthProvider";
import { useAksi, useApi, useAutosave, useInvalidate } from "@/shared/lib/hooks";
import { angka, labelEnum, waktu } from "@/shared/lib/format";
import { Alert, Button, Card, Empty, ErrorBox, Field, Icon, Modal, Muat, PageHead, Pill, StatusPill, Tabs, useToast } from "@/shared/ui";
import { PilihBuktiModal } from "../bukti/BuktiPage";
import { PilihPenanggungJawab } from "./PilihPenanggungJawab";
import { SUMBER } from "./konstanta";

type TabButir = "narasi" | "data" | "bukti" | "rubrik";

export function ButirPage() {
  const { id } = useParams();
  const { punya } = useAuth();
  const [tab, setTab] = useState<TabButir>("narasi");
  const q = useApi<Rec>(`/butir-siklus/${id}`);
  return (
    <div className="stack">
      <Muat q={q}>
        {(b) => {
          const butir = b.butir;
          return (
            <>
              <PageHead
                crumbs={[{ label: "Siklus", to: "/siklus" }, { label: "Daftar butir", to: `/siklus/${b.siklus_id}` }, { label: `Butir ${butir.kode}` }]}
                judul={<><span className="butir-code" style={{ fontSize: "1rem", display: "block", marginBottom: "0.3rem" }}>{butir.kriteria.kode} · {butir.kriteria.nama} — Butir {butir.kode}</span><span style={{ fontSize: "1.25rem", fontWeight: 600, fontFamily: "var(--font-body)", letterSpacing: 0 }}>{butir.elemen}</span></>}
                aksi={<><StatusPill status={b.status_kelengkapan} /><Pill>{labelEnum(b.pengelola)}</Pill></>}
              />
              {b.terkunci && <Alert jenis="warn" judul="Perubahan dikunci">Laporan prodi sedang menunggu validasi atau sudah disetujui. Data, narasi, dan bukti tidak dapat diubah sampai Dekan memutuskan atau membuka kembali.</Alert>}
              {b.menunggu_dokumen_eksternal && <Alert jenis="warn" judul="Menunggu dokumen dari Direktorat Kemahasiswaan">Butir ini dipasok hasil tracer/kepuasan. Staf Fakultas akan mengunggahnya; butir lain tidak terblokir.</Alert>}
              {b.catatan_validasi.some((c: Rec) => c.status === "terbuka") && (
                <Alert jenis="danger" judul="Catatan Dekan pada butir ini">
                  <ul>{b.catatan_validasi.filter((c: Rec) => c.status === "terbuka").map((c: Rec) => <li key={c.id}>{c.isi}</li>)}</ul>
                </Alert>
              )}
              <div className="grid" style={{ gridTemplateColumns: "minmax(0,1fr) 340px", alignItems: "start" }}>
                <div className="stack" style={{ minWidth: 0 }}>
                  <Tabs aktif={tab} onGanti={setTab} tabs={[
                    { kunci: "narasi", label: "Narasi" },
                    { kunci: "data", label: "Data pendukung" },
                    { kunci: "bukti", label: "Bukti", jumlah: b.bukti.length },
                    { kunci: "rubrik", label: "Rubrik & panduan" },
                  ]} />
                  {tab === "narasi" && <NarasiTab b={b} />}
                  {tab === "data" && <DataTab b={b} />}
                  {tab === "bukti" && <BuktiTab b={b} />}
                  {tab === "rubrik" && <RubrikTab b={b} />}
                </div>
                <div className="stack" style={{ minWidth: 0 }}>
                  <PenilaianCard b={b} />
                  {punya("dekan") && <PenugasanCard b={b} />}
                </div>
              </div>
            </>
          );
        }}
      </Muat>
    </div>
  );
}

/* ------------------------------------------------------------------ penilaian mandiri */
function PenilaianCard({ b }: { b: Rec }) {
  const [status, setStatus] = useState<string>(b.status_kelengkapan);
  const [skor, setSkor] = useState<number | null>(b.skor_estimasi !== null ? Number(b.skor_estimasi) : null);
  const [catatan, setCatatan] = useState<string>(b.catatan ?? "");
  const skorTersedia = b.butir.rubrik.length ? b.butir.rubrik.map((r: Rec) => r.skor).sort() : [1, 2, 3, 4];
  const simpan = useAksi(() => api.patch(`/butir-siklus/${b.id}`, { row_version: b.row_version, status_kelengkapan: status, skor_estimasi: skor, catatan }), {
    sukses: "Penilaian disimpan", invalidate: ["/butir-siklus", "/siklus", "/dasbor", "/saya"],
  });
  const bisa = b.dapat_disunting;
  return (
    <Card judul="Penilaian mandiri" sub="Skor estimasi internal — bukan penilaian resmi asesor.">
      <Field label="Status kelengkapan" bantuan="Draf boleh kapan saja; kelengkapan penuh hanya diperiksa saat pengajuan.">
        <select value={status} onChange={(e) => setStatus(e.target.value)} disabled={!bisa}>
          <option value="belum_mulai">Belum mulai</option><option value="draft">Draf</option><option value="lengkap">Lengkap</option>
        </select>
      </Field>
      <Field label="Skor estimasi">
        <div className="score-picker">
          {skorTersedia.map((s: number) => (
            <button key={s} className={skor === s ? "is-on" : ""} disabled={!bisa} onClick={() => setSkor(skor === s ? null : s)} aria-pressed={skor === s}>{s}</button>
          ))}
        </div>
        {b.butir.rubrik.find((r: Rec) => r.skor === skor)?.label && <div className="field__help">{b.butir.rubrik.find((r: Rec) => r.skor === skor).label}</div>}
      </Field>
      <Field label="Catatan"><textarea style={{ minHeight: 84 }} value={catatan} onChange={(e) => setCatatan(e.target.value)} disabled={!bisa} placeholder="mis. menunggu laporan benchmarking" /></Field>
      <Button blok onClick={() => simpan.mutate()} disabled={!bisa || simpan.isPending}>{simpan.isPending && <span className="spinner" />} Simpan penilaian</Button>
      {!bisa && !b.terkunci && <p className="field__help" style={{ marginTop: "0.6rem" }}>Anda bukan pengelola butir ini. Penugasan ditentukan Dekan.</p>}
      {simpan.error && <div style={{ marginTop: "0.8rem" }}><ErrorBox error={simpan.error} /></div>}
      <hr className="divider" />
      <dl className="kv">
        <dt>Penanggung jawab</dt><dd>{b.penanggung_jawab?.nama ?? <span style={{ color: "var(--amber)" }}>Belum ditugaskan</span>}</dd>
        <dt>Jenis / tahap</dt><dd>{[b.butir.jenis_ipo, b.butir.tahap_ppepp].filter(Boolean).map(labelEnum).join(" / ") || "—"}</dd>
        {b.butir.bobot !== null && <><dt>Bobot</dt><dd>{angka(b.butir.bobot, 2)}</dd></>}
      </dl>
    </Card>
  );
}

function PenugasanCard({ b }: { b: Rec }) {
  const [pengelola, setPengelola] = useState<string>(b.pengelola);
  const [pj, setPj] = useState<string>(b.penanggung_jawab?.id ?? "");
  const prodi = useApi<Rec>(`/siklus/${b.siklus_id}`);
  const simpan = useAksi(() => api.put(`/butir-siklus/${b.id}/penugasan`, { pengelola, penanggung_jawab_id: pj || null }), {
    sukses: "Penugasan diperbarui; antrean kerja staf ikut berubah", invalidate: ["/butir-siklus", "/siklus", "/saya"],
  });
  return (
    <Card judul="Penugasan (Dekan)" aksen="lime">
      <Field label="Dikelola oleh">
        <select value={pengelola} onChange={(e) => { setPengelola(e.target.value); setPj(""); }}><option value="prodi">Prodi</option><option value="fakultas">Fakultas (di luar kendali prodi)</option></select>
      </Field>
      <Field label="Penanggung jawab">{prodi.data && <PilihPenanggungJawab prodiId={prodi.data.prodi.id} pengelola={pengelola} nilai={pj} onUbah={setPj} />}</Field>
      <Button variant="lime" blok onClick={() => simpan.mutate()} disabled={simpan.isPending}>Tetapkan penugasan</Button>
      {simpan.error && <div style={{ marginTop: "0.8rem" }}><ErrorBox error={simpan.error} /></div>}
    </Card>
  );
}

/* ------------------------------------------------------------------ narasi (hanya Kaprodi) */
function NarasiTab({ b }: { b: Rec }) {
  const bagian: { bagian: string; judul: string }[] = b.butir.skema_narasi.length ? b.butir.skema_narasi : [{ bagian: "utama", judul: "Uraian" }];
  return (
    <div className="stack">
      {!b.narasi_dapat_disunting && !b.terkunci && (
        <Alert jenis="info" judul="Narasi hanya disunting Kaprodi">Staf Admin mengelola data dan bukti; narasi dapat dibaca di sini tetapi tidak dapat diubah, termasuk pada butir yang Anda tangani.</Alert>
      )}
      {b.butir.panduan && <Alert jenis="info" judul="Panduan pengisian">{b.butir.panduan}</Alert>}
      {bagian.map((x) => <NarasiEditor key={x.bagian} b={b} bagian={x.bagian} judul={x.judul} />)}
    </div>
  );
}

function NarasiEditor({ b, bagian, judul }: { b: Rec; bagian: string; judul: string }) {
  const ada = b.narasi.find((n: Rec) => n.bagian === bagian);
  const [isi, setIsi] = useState<string>(ada?.isi ?? "");
  const [rv, setRv] = useState<number | null>(ada?.row_version ?? null);
  const [sumber, setSumber] = useState<string>(ada?.sumber ?? "manual");
  const [konflik, setKonflik] = useState(false);
  const [llm, setLlm] = useState<string | null>(null);
  const [draf, setDraf] = useState(false);
  const bisa: boolean = b.narasi_dapat_disunting;
  const invalidate = useInvalidate();
  const rvRef = useRef(rv);
  rvRef.current = rv;
  const llmRef = useRef(llm);
  llmRef.current = llm;

  const kirim = async (teks: string, status: "draft" | "final" = "draft") => {
    try {
      const r = await api.put(`/butir-siklus/${b.id}/narasi/${bagian}`, { row_version: rvRef.current, isi: teks, status, permintaan_llm_id: llmRef.current });
      setRv(r.row_version);
      setSumber(r.sumber);
      setLlm(null);
      setKonflik(false);
    } catch (e) {
      if (e instanceof ApiError && e.code === "KONFLIK_VERSI") setKonflik(true);
      throw e;
    }
  };
  const auto = useAutosave(isi, (v) => kirim(v), bisa && !konflik);
  const manual = useAksi((status: "draft" | "final") => kirim(isi, status), { sukses: "Narasi disimpan", diam: false, onSuccess: () => invalidate("/butir-siklus", "/siklus") });
  useEffect(() => { auto.setAwal(ada?.isi ?? ""); /* eslint-disable-next-line */ }, []);

  const label = { diam: "", menyimpan: "Menyimpan…", tersimpan: "Tersimpan otomatis", gagal: "Gagal menyimpan — tulisan Anda masih aman di layar" }[auto.status];
  return (
    <Card judul={judul} sub={ada ? `Terakhir disimpan ${waktu(ada.updated_at)}` : "Belum ditulis"} aksi={
      <>
        {sumber !== "manual" && <Pill warna="blue">{sumber === "llm" ? "Draf LLM" : "Draf LLM disunting"}</Pill>}
        {bisa && <Button variant="ghost" size="sm" onClick={() => setDraf(true)}><Icon name="sparkles" size={14} /> Susun draf (LLM)</Button>}
      </>
    }>
      {konflik && (
        <Alert jenis="danger" judul="Narasi diubah pengguna lain">
          Muat versi terbaru sebelum menyimpan agar perubahan tidak saling menimpa. <Button size="sm" variant="ghost" onClick={() => invalidate("/butir-siklus")}>Muat ulang</Button>
        </Alert>
      )}
      <div className="field"><textarea value={isi} onChange={(e) => setIsi(e.target.value)} disabled={!bisa} style={{ minHeight: 220 }} placeholder={bisa ? "Tulis narasi evaluasi diri untuk bagian ini…" : "(belum diisi)"} aria-label={judul} /></div>
      {bisa && (
        <div className="row row--between">
          <span className={`autosave${auto.status === "tersimpan" ? " autosave--ok" : auto.status === "gagal" ? " autosave--err" : ""}`}>{auto.status === "menyimpan" && <span className="spinner" />}{label}</span>
          <div className="row">
            <Button variant="ghost" size="sm" onClick={() => manual.mutate("draft")} disabled={manual.isPending}>Simpan draf</Button>
            <Button size="sm" onClick={() => manual.mutate("final")} disabled={manual.isPending || !isi.trim()}>Tandai final</Button>
          </div>
        </div>
      )}
      {draf && <DrafLlmModal butirId={b.id} bagian={bagian} onTutup={() => setDraf(false)} onPakai={(teks, id) => { setIsi(teks); setLlm(id); setDraf(false); }} />}
    </Card>
  );
}

function DrafLlmModal({ butirId, bagian, onTutup, onPakai }: { butirId: string; bagian: string; onTutup: () => void; onPakai: (teks: string, id: string) => void }) {
  const toast = useToast();
  const [arahan, setArahan] = useState("");
  const [permintaan, setPermintaan] = useState<string | null>(null);
  const [galat, setGalat] = useState<unknown>(null);
  const q = useApi<Rec>(permintaan ? `/permintaan-llm/${permintaan}` : null, undefined, { refetchInterval: permintaan ? 2000 : undefined });
  const mulai = async () => {
    setGalat(null);
    try {
      const r = await api.post(`/butir-siklus/${butirId}/narasi/${bagian}/draf-llm`, { arahan: arahan || null, sertakan_data_terpetakan: true });
      setPermintaan(r.id);
    } catch (e) {
      setGalat(e);
      if (e instanceof ApiError && e.code === "LLM_TIDAK_TERSEDIA") toast.info("Generator LLM tidak tersedia. Anda tetap dapat menulis narasi secara manual.");
    }
  };
  const selesai = q.data?.status === "selesai";
  const gagal = q.data?.status === "gagal";
  return (
    <Modal judul="Susun draf narasi dengan LLM" onTutup={onTutup} lebar footer={
      <>
        <Button variant="ghost" onClick={onTutup}>Tutup</Button>
        {!permintaan && <Button onClick={mulai}><Icon name="sparkles" size={15} /> Susun draf</Button>}
        {selesai && <Button variant="lime" onClick={() => onPakai(q.data!.hasil, permintaan!)}>Pakai sebagai titik awal</Button>}
      </>
    }>
      <Alert jenis="info" judul="Selalu ditinjau manusia">Draf dibuat dari data inti, bukti, dan hasil evaluasi yang sudah terpetakan. Draf tidak otomatis masuk ke LED; Anda wajib meninjau dan menyuntingnya. Fitur ini opsional.</Alert>
      {!permintaan && (
        <div style={{ marginTop: "1rem" }}><Field label="Arahan tambahan (opsional)"><textarea style={{ minHeight: 80 }} value={arahan} onChange={(e) => setArahan(e.target.value)} placeholder="mis. Tekankan capaian tiga tahun terakhir." /></Field></div>
      )}
      {permintaan && !selesai && !gagal && <div className="loading"><span className="spinner" /><span>Model sedang menyusun draf…</span></div>}
      {gagal && <Alert jenis="danger" judul="Draf gagal dibuat">{q.data?.galat} — tulisan manual Anda tidak terpengaruh.</Alert>}
      {selesai && <div className="field" style={{ marginTop: "1rem" }}><label>Hasil draf ({q.data!.mode}, {q.data!.model})</label><div className="json" style={{ whiteSpace: "pre-wrap", fontFamily: "var(--font-body)", fontSize: "0.9rem", color: "var(--text)" }}>{q.data!.hasil}</div></div>}
      {galat != null && <div style={{ marginTop: "1rem" }}><ErrorBox error={galat} /></div>}
    </Modal>
  );
}

/* ------------------------------------------------------------------ data terpetakan */
function DataTab({ b }: { b: Rec }) {
  const q = useApi<Rec>(`/butir-siklus/${b.id}/data`);
  return (
    <Muat q={q}>
      {(d) => (
        <div className="stack">
          <Alert jenis="info">Data di bawah dibaca langsung dari data inti sesuai aturan pemetaan yang disetujui Dekan (rentang TS-{d.tahun_akademik_ids.length - 1}…TS). Mengubah data inti otomatis memperbarui semua butir yang merujuknya.</Alert>
          {d.sumber.length === 0 && <Empty judul="Butir ini tidak dipasok data inti" ikon="database">Penilaian bersifat kualitatif; gunakan narasi dan bukti.</Empty>}
          {d.belum_lengkap && <Alert jenis="warn" judul="Butir Belum Lengkap">Seluruh sumber data pendukung masih kosong: {d.data_kurang.map((s: string) => SUMBER[s]?.label ?? s).join(", ")}.</Alert>}
          {d.sumber.map((s: Rec) => (
            <div key={s.aturan_id} className={`source-card${s.kosong ? " source-card--empty" : ""}`}>
              <div className="row row--between">
                <strong>{SUMBER[s.sumber]?.label ?? s.sumber}</strong>
                <div className="row">
                  <Pill warna={s.kosong ? "amber" : "lime"}>{s.jumlah} catatan</Pill>
                  {s.nilai !== null && <Pill warna="blue">{s.agregasi} = {angka(s.nilai, 2)}</Pill>}
                  {SUMBER[s.sumber] && <Link className="link" to={SUMBER[s.sumber].to} style={{ fontSize: "0.82rem" }}>Kelola data →</Link>}
                </div>
              </div>
              {s.keterangan && <div className="muted" style={{ fontSize: "0.82rem" }}>{s.keterangan}</div>}
              {s.kosong ? <div className="muted" style={{ marginTop: "0.4rem" }}>Belum ada data pada rentang ini.</div> : (
                <ul>{s.contoh.slice(0, 8).map((c: Rec) => <li key={c.id}>{c.label}</li>)}{s.jumlah > 8 && <li className="faint">… dan {s.jumlah - 8} lainnya</li>}</ul>
              )}
            </div>
          ))}
        </div>
      )}
    </Muat>
  );
}

/* ------------------------------------------------------------------ bukti butir */
function BuktiTab({ b }: { b: Rec }) {
  const [pilih, setPilih] = useState(false);
  const bisa: boolean = b.dapat_disunting;
  const tautkan = useAksi((bukti: Rec) => api.put(`/butir-siklus/${b.id}/bukti/${bukti.id}`), { sukses: "Bukti ditautkan ke butir", invalidate: ["/butir-siklus", "/siklus", "/saya", "/bukti"], onSuccess: () => setPilih(false) });
  const lepas = useAksi((id: string) => api.del(`/butir-siklus/${b.id}/bukti/${id}`), { sukses: "Tautan bukti dilepas", invalidate: ["/butir-siklus", "/siklus", "/saya"] });
  const buka = useAksi(async (id: string) => { const r = await api.get(`/bukti/${id}/unduh`); window.open(r.url, "_blank", "noopener"); });
  return (
    <Card judul="Bukti butir" sub="Berkas atau tautan; diperiksa link-checker secara berkala." aksi={bisa && <Button size="sm" onClick={() => setPilih(true)}><Icon name="plus" size={14} /> Tautkan bukti</Button>}>
      {b.bukti.length === 0 ? <Empty judul="Belum ada bukti" ikon="paperclip" /> : (
        <div className="stack stack--sm">
          {b.bukti.map((x: Rec) => (
            <div key={x.id} className="card row row--between" style={{ padding: "0.75rem 1rem" }}>
              <div style={{ minWidth: 0 }}>
                <div className="cell-title"><Icon name={x.jenis === "berkas" ? "file" : "link"} size={14} /> {x.judul}</div>
                <div className="cell-sub" style={{ overflowWrap: "anywhere" }}>{x.jenis === "berkas" ? x.nama_berkas : x.url}</div>
              </div>
              <div className="row">
                <StatusPill status={x.status_cek} />
                <Button variant="ghost" size="icon" title="Buka" onClick={() => buka.mutate(x.id)}><Icon name="external" size={15} /></Button>
                {bisa && <Button variant="danger" size="icon" title="Lepas dari butir" onClick={() => lepas.mutate(x.id)}><Icon name="x" size={15} /></Button>}
              </div>
            </div>
          ))}
        </div>
      )}
      {pilih && <PilihBuktiModal sudah={b.bukti.map((x: Rec) => x.id)} onTutup={() => setPilih(false)} onPilih={(x) => tautkan.mutate(x)} />}
    </Card>
  );
}

/* ------------------------------------------------------------------ rubrik */
function RubrikTab({ b }: { b: Rec }) {
  const bt = b.butir;
  return (
    <div className="stack">
      {bt.deskriptor && <Alert jenis="info">{bt.deskriptor}</Alert>}
      <Card judul="Rubrik penilaian">
        {bt.rubrik.length === 0 ? <Empty judul="Rubrik belum dimuat" ikon="book">Staf Admin Fakultas dapat memuatnya lewat impor instrumen.</Empty> : (
          <div className="rubrik">{bt.rubrik.map((r: Rec) => <div key={r.skor} className="rubrik__item"><div className="rubrik__skor">{r.skor}</div><div><strong>{r.label}</strong><div className="muted">{r.deskriptor}</div></div></div>)}</div>
        )}
      </Card>
      {bt.ambang.length > 0 && (
        <Card judul="Tingkat minimum per peringkat">
          <div className="chips">{bt.ambang.map((a: Rec) => <Pill key={a.peringkat} warna={a.is_syarat_perlu ? "red" : "blue"}>{labelEnum(a.peringkat)} ≥ {a.skor_min}{a.is_syarat_perlu ? " · syarat perlu" : ""}</Pill>)}</div>
        </Card>
      )}
    </div>
  );
}
