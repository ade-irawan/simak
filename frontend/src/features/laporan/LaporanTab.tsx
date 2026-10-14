import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/shared/api/client";
import type { Rec } from "@/shared/api/types";
import { useAuth } from "@/shared/auth/AuthProvider";
import { useAksi, useApi } from "@/shared/lib/hooks";
import { labelEnum, tanggal, ukuranBerkas, waktu } from "@/shared/lib/format";
import { Alert, Button, Card, Empty, ErrorBox, Field, Icon, Konfirmasi, Modal, Muat, Pill, StatusPill, Tabel, useToast, type Kolom } from "@/shared/ui";
import { MASALAH } from "../siklus/konstanta";

const INV = ["/siklus", "/laporan", "/pengajuan", "/dasbor", "/butir-siklus", "/penugasan", "/notifikasi"];

export function LaporanTab({ siklus }: { siklus: Rec }) {
  const { punya } = useAuth();
  const q = useApi<Rec>(`/siklus/${siklus.id}/laporan`);
  return (
    <Muat q={q}>
      {(l) => (
        <div className="stack">
          <Alur status={l.status} />
          {l.status === "disetujui" && (
            <Alert jenis="ok" judul="Laporan disetujui Dekan">
              Dokumen final dapat diekspor. Asesor hanya melihat versi yang disetujui ini; perubahan setelah laporan dibuka kembali tidak tampil sampai disetujui lagi.
              {punya("kaprodi") && <> <Link className="link" to="/usulan-asesor">Usulkan asesor →</Link></>}
            </Alert>
          )}
          {l.status === "menunggu_validasi" && <Alert jenis="info" judul="Menunggu validasi Dekan">Lembar kerja, narasi, bukti, dan data prodi dikunci agar tidak berubah di belakang validator.</Alert>}
          {punya("kaprodi") && l.status === "draft" && <PraCek siklusId={siklus.id} onAjukan={() => undefined} laporan={l} />}
          {l.catatan_validasi_terbuka > 0 && <CatatanDekan siklusId={siklus.id} />}
          {punya("dekan") && <KeputusanDekan laporan={l} siklus={siklus} />}
          <div className="grid grid--2" style={{ alignItems: "start" }}>
            <Riwayat laporanId={l.laporan_id} />
            <Ekspor siklus={siklus} laporan={l} />
          </div>
        </div>
      )}
    </Muat>
  );
}

function Alur({ status }: { status: string }) {
  const urutan = ["draft", "menunggu_validasi", "disetujui"];
  const idx = urutan.indexOf(status);
  const nama = { draft: ["Draf", "Kaprodi menyusun & melengkapi"], menunggu_validasi: ["Menunggu validasi", "Dekan meninjau; data terkunci"], disetujui: ["Disetujui", "Final; dapat diekspor & ditelaah asesor"] } as Record<string, string[]>;
  return (
    <div className="phases" style={{ gridTemplateColumns: "repeat(3,1fr)" }}>
      {urutan.map((s, i) => (
        <div key={s} className={`phase ${i < idx ? "phase--done" : i === idx ? "phase--run" : "phase--lock"}`}>
          <b>{i + 1}. {nama[s][0]}</b>
          <span className="muted">{nama[s][1]}</span>
        </div>
      ))}
    </div>
  );
}

function PraCek({ siklusId, laporan }: { siklusId: string; onAjukan: () => void; laporan: Rec }) {
  const q = useApi<Rec>(`/siklus/${siklusId}/laporan/pra-cek`);
  const [catatan, setCatatan] = useState("");
  const [konfirmasi, setKonfirmasi] = useState(false);
  const ajukan = useAksi(() => api.post(`/siklus/${siklusId}/laporan/ajukan`, { catatan: catatan || null }), {
    sukses: "Laporan diajukan; Dekan menerima notifikasi", invalidate: INV, onSuccess: () => setKonfirmasi(false),
  });
  return (
    <Card judul="Kesiapan pengajuan" sub="Pemantauan harian tidak mensyaratkan kelengkapan, tetapi pengajuan memeriksa semua butir." aksen={q.data?.siap_diajukan ? "lime" : "amber"}>
      <Muat q={q}>
        {(p) => (
          <div className="stack">
            {p.siap_diajukan ? <Alert jenis="ok" judul="Semua butir siap">Tidak ada butir yang menghalangi pengajuan. Penggunaan generator LLM tidak disyaratkan.</Alert> : (
              <>
                <Alert jenis="warn" judul={`${p.jumlah_masalah} butir menghalangi pengajuan`}>Lengkapi butir berikut lalu periksa ulang.</Alert>
                <div className="stack stack--sm">
                  {p.butir.map((b: Rec) => (
                    <div key={b.butir_siklus_id} className="card row row--between" style={{ padding: "0.6rem 0.9rem" }}>
                      <Link className="butir-code" to={`/butir/${b.butir_siklus_id}`}>Butir {b.kode}</Link>
                      <div className="chips">{b.masalah.map((m: string) => <Pill key={m} warna={m === "bukti_tidak_terjangkau" ? "red" : "amber"}>{MASALAH[m] ?? m}</Pill>)}</div>
                    </div>
                  ))}
                </div>
              </>
            )}
            <Field label="Catatan pengajuan (opsional)"><textarea style={{ minHeight: 70 }} value={catatan} onChange={(e) => setCatatan(e.target.value)} /></Field>
            <div className="row"><Button disabled={!p.siap_diajukan || ajukan.isPending} onClick={() => setKonfirmasi(true)}><Icon name="send" size={15} /> Ajukan untuk validasi</Button><Button variant="ghost" onClick={() => q.refetch()}><Icon name="refresh" size={15} /> Periksa ulang</Button></div>
            {ajukan.error && <ErrorBox error={ajukan.error} />}
            {laporan.pengajuan_terakhir && <div className="faint" style={{ fontSize: "0.8rem" }}>Pengajuan terakhir: #{laporan.pengajuan_terakhir.nomor} — {labelEnum(laporan.pengajuan_terakhir.keputusan)}</div>}
          </div>
        )}
      </Muat>
      {konfirmasi && <Konfirmasi judul="Ajukan laporan?" pesan="Setelah diajukan, data prodi dikunci sampai Dekan menyetujui atau mengembalikan laporan." labelYa="Ya, ajukan" memproses={ajukan.isPending} onBatal={() => setKonfirmasi(false)} onYa={() => ajukan.mutate()} />}
    </Card>
  );
}

function CatatanDekan({ siklusId }: { siklusId: string }) {
  const { punya } = useAuth();
  const q = useApi<Rec[]>(`/siklus/${siklusId}/laporan/catatan`);
  const selesai = useAksi((id: string) => api.patch(`/catatan-validasi/${id}`), { sukses: "Catatan ditandai selesai", invalidate: INV });
  return (
    <Card judul="Catatan Dekan dari pengembalian terakhir" aksen="red">
      <div className="stack stack--sm">
        {q.data?.map((c) => (
          <div key={c.id} className="card row row--between" style={{ padding: "0.6rem 0.9rem" }}>
            <div>
              {c.butir_siklus_id ? <Link className="butir-code" to={`/butir/${c.butir_siklus_id}`}>Butir</Link> : <Pill>Umum</Pill>} <span style={{ marginLeft: "0.4rem" }}>{c.isi}</span>
            </div>
            <div className="row"><StatusPill status={c.status} />{punya("kaprodi") && c.status === "terbuka" && <Button size="sm" variant="ghost" onClick={() => selesai.mutate(c.id)}>Tandai selesai</Button>}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ keputusan Dekan */
function KeputusanDekan({ laporan, siklus }: { laporan: Rec; siklus: Rec }) {
  const [dialog, setDialog] = useState<"setujui" | "kembalikan" | "buka" | null>(null);
  if (laporan.status === "draft") return null;
  return (
    <Card judul="Keputusan Dekan" aksen="blue" sub={laporan.pengajuan_terakhir ? `Pengajuan #${laporan.pengajuan_terakhir.nomor} · ${waktu(laporan.pengajuan_terakhir.diajukan_pada)}` : undefined}>
      {laporan.status === "menunggu_validasi" ? (
        <div className="row">
          <Button variant="lime" onClick={() => setDialog("setujui")}><Icon name="checkCircle" size={16} /> Setujui</Button>
          <Button variant="danger" onClick={() => setDialog("kembalikan")}>Kembalikan dengan catatan</Button>
          {laporan.pengajuan_terakhir && <PeninjauanCuplikan pengajuanId={laporan.pengajuan_terakhir.id} />}
        </div>
      ) : (
        <div className="row">
          <Button variant="ghost" onClick={() => setDialog("buka")}><Icon name="unlock" size={15} /> Buka kembali laporan</Button>
          <Link className="btn btn--primary" to="/pengguna?tab=penugasan"><Icon name="users" size={15} /> Aktifkan akses asesor</Link>
        </div>
      )}
      {dialog === "setujui" && <SetujuiModal laporan={laporan} onTutup={() => setDialog(null)} />}
      {dialog === "kembalikan" && <KembalikanModal laporan={laporan} siklus={siklus} onTutup={() => setDialog(null)} />}
      {dialog === "buka" && <BukaKembaliModal laporan={laporan} onTutup={() => setDialog(null)} />}
    </Card>
  );
}

function SetujuiModal({ laporan, onTutup }: { laporan: Rec; onTutup: () => void }) {
  const [catatan, setCatatan] = useState("");
  const aksi = useAksi(() => api.post(`/laporan/${laporan.laporan_id}/setujui`, { catatan_umum: catatan || null }), { sukses: "Laporan disetujui", invalidate: INV, onSuccess: onTutup });
  return (
    <Modal judul="Setujui laporan" onTutup={onTutup} footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button variant="lime" onClick={() => aksi.mutate()} disabled={aksi.isPending}>Setujui</Button></>}>
      <p className="muted" style={{ marginBottom: "1rem" }}>Persetujuan diblokir bila masih ada bukti yang tidak terjangkau (berkas hilang atau tautan mati).</p>
      <Field label="Catatan (opsional)"><textarea style={{ minHeight: 80 }} value={catatan} onChange={(e) => setCatatan(e.target.value)} /></Field>
      {aksi.error && <ErrorBox error={aksi.error} />}
    </Modal>
  );
}

function KembalikanModal({ laporan, siklus, onTutup }: { laporan: Rec; siklus: Rec; onTutup: () => void }) {
  const butir = useApi<Rec>(`/siklus/${siklus.id}/butir`, { per_page: 100 });
  const [umum, setUmum] = useState("");
  const [per, setPer] = useState<{ butir_siklus_id: string; isi: string }[]>([]);
  const aksi = useAksi(() => api.post(`/laporan/${laporan.laporan_id}/kembalikan`, { catatan_umum: umum || null, catatan_butir: per.filter((p) => p.butir_siklus_id && p.isi.trim().length >= 3) }), {
    sukses: "Laporan dikembalikan ke Kaprodi", invalidate: INV, onSuccess: onTutup,
  });
  return (
    <Modal judul="Kembalikan laporan" onTutup={onTutup} lebar footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button variant="danger" onClick={() => aksi.mutate()} disabled={aksi.isPending || (!umum.trim() && per.length === 0)}>Kembalikan</Button></>}>
      <Field label="Catatan umum"><textarea style={{ minHeight: 80 }} value={umum} onChange={(e) => setUmum(e.target.value)} placeholder="mis. Lengkapi bukti benchmarking dan perbaiki analisis kriteria C." /></Field>
      <div className="row row--between" style={{ marginBottom: "0.5rem" }}><strong style={{ fontSize: "0.9rem" }}>Catatan per butir</strong><Button size="sm" variant="ghost" onClick={() => setPer([...per, { butir_siklus_id: "", isi: "" }])}><Icon name="plus" size={14} /> Tambah</Button></div>
      {per.map((p, i) => (
        <div key={i} className="card" style={{ padding: "0.8rem", marginBottom: "0.5rem" }}>
          <select className="input" value={p.butir_siklus_id} onChange={(e) => setPer(per.map((x, j) => (j === i ? { ...x, butir_siklus_id: e.target.value } : x)))}>
            <option value="">— pilih butir —</option>{butir.data?.data.map((b: Rec) => <option key={b.id} value={b.id}>{b.butir.kode} — {b.butir.elemen.slice(0, 70)}</option>)}
          </select>
          <textarea className="input" style={{ marginTop: "0.5rem", minHeight: 60 }} value={p.isi} onChange={(e) => setPer(per.map((x, j) => (j === i ? { ...x, isi: e.target.value } : x)))} placeholder="Catatan untuk butir ini" />
        </div>
      ))}
      {aksi.error && <ErrorBox error={aksi.error} />}
    </Modal>
  );
}

function BukaKembaliModal({ laporan, onTutup }: { laporan: Rec; onTutup: () => void }) {
  const toast = useToast();
  const [alasan, setAlasan] = useState("");
  const aksi = useAksi(() => api.post(`/laporan/${laporan.laporan_id}/buka-kembali`, { alasan: alasan || null }), {
    sukses: "Laporan dibuka kembali", invalidate: INV, onSuccess: (r) => { if (r.peringatan) toast.warn(r.peringatan); onTutup(); },
  });
  return (
    <Modal judul="Buka kembali laporan" onTutup={onTutup} footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button onClick={() => aksi.mutate()} disabled={aksi.isPending}>Buka kembali</Button></>}>
      <Alert jenis="warn">Laporan kembali ke status draf dan dapat diubah. Asesor yang sedang aktif tetap melihat versi terakhir yang disetujui sampai versi baru disetujui. Tindakan tercatat di log audit.</Alert>
      <div style={{ marginTop: "1rem" }}><Field label="Alasan"><textarea style={{ minHeight: 80 }} value={alasan} onChange={(e) => setAlasan(e.target.value)} /></Field></div>
      {aksi.error && <ErrorBox error={aksi.error} />}
    </Modal>
  );
}

function PeninjauanCuplikan({ pengajuanId }: { pengajuanId: string }) {
  const [buka, setBuka] = useState(false);
  return (
    <>
      <Button variant="ghost" onClick={() => setBuka(true)}><Icon name="eye" size={15} /> Tinjau isi pengajuan</Button>
      {buka && <CuplikanModal id={pengajuanId} onTutup={() => setBuka(false)} />}
    </>
  );
}

function CuplikanModal({ id, onTutup }: { id: string; onTutup: () => void }) {
  const q = useApi<Rec>(`/pengajuan/${id}`);
  return (
    <Modal judul="Isi pengajuan (cuplikan saat diajukan)" onTutup={onTutup} lebar footer={<Button variant="ghost" onClick={onTutup}>Tutup</Button>}>
      <Muat q={q}>
        {(p) => (
          <div className="stack">
            <div className="chips"><StatusPill status={p.keputusan} /><Pill>#{p.nomor}</Pill><Pill>diajukan {waktu(p.diajukan_pada)}</Pill></div>
            {p.cuplikan?.skor?.prediksi_peringkat && <Alert jenis="info">Prediksi peringkat saat diajukan: <strong>{p.cuplikan.skor.prediksi_peringkat.nama}</strong> (estimasi internal).</Alert>}
            {p.cuplikan?.kriteria.map((k: Rec) => (
              <Card key={k.kode} judul={`Kriteria ${k.kode} — ${k.nama}`}>
                <div className="stack stack--sm">
                  {k.butir.map((b: Rec) => (
                    <div key={b.kode} className="source-card">
                      <div className="row row--between"><span><span className="butir-code">{b.kode}</span> <span className="muted">{b.elemen}</span></span><div className="chips"><StatusPill status={b.status_kelengkapan} /><Pill>skor {b.skor_estimasi ?? "—"}</Pill><Pill>{b.bukti.length} bukti</Pill></div></div>
                      {b.narasi.map((n: Rec) => <div key={n.bagian} style={{ marginTop: "0.5rem", whiteSpace: "pre-wrap", fontSize: "0.88rem" }}>{n.isi || <span className="faint">(narasi kosong)</span>}</div>)}
                    </div>
                  ))}
                </div>
              </Card>
            ))}
            {p.catatan?.length > 0 && <Card judul="Catatan validasi"><ul className="reasons">{p.catatan.map((c: Rec) => <li key={c.id}>{c.isi}</li>)}</ul></Card>}
          </div>
        )}
      </Muat>
    </Modal>
  );
}

/* ------------------------------------------------------------------ riwayat & ekspor */
function Riwayat({ laporanId }: { laporanId: string }) {
  const { punya } = useAuth();
  const bisa = punya("dekan", "kaprodi");
  const q = useApi<Rec[]>(bisa ? `/laporan/${laporanId}/pengajuan` : null);
  const [lihat, setLihat] = useState<string | null>(null);
  const kolom: Kolom<Rec>[] = [
    { kunci: "no", judul: "#", render: (p) => <strong>{p.nomor}</strong> },
    { kunci: "tgl", judul: "Diajukan", render: (p) => waktu(p.diajukan_pada) },
    { kunci: "kep", judul: "Keputusan", render: (p) => <StatusPill status={p.keputusan} /> },
    { kunci: "cat", judul: "Catatan", render: (p) => p.catatan_umum ?? <span className="faint">—</span> },
  ];
  return (
    <Card judul="Riwayat pengajuan" sub="Cuplikan tiap pengajuan tersimpan, termasuk yang dikembalikan." flush>
      {!bisa ? <Empty judul="Riwayat hanya untuk Dekan dan Kaprodi" /> : (
        <Muat q={q}>{(d) => (d.length ? <Tabel kolom={kolom} baris={d} id={(p) => p.id} onKlik={(p) => setLihat(p.id)} /> : <Empty judul="Belum pernah diajukan" ikon="history" />)}</Muat>
      )}
      {lihat && <CuplikanModal id={lihat} onTutup={() => setLihat(null)} />}
    </Card>
  );
}

function Ekspor({ siklus, laporan }: { siklus: Rec; laporan: Rec }) {
  const [jenis, setJenis] = useState("led");
  const [format, setFormat] = useState("docx");
  const [final, setFinal] = useState(false);
  const [ekspor, setEkspor] = useState<Rec[]>([]);
  const { punya } = useAuth();
  const minta = useAksi(() => api.post(`/siklus/${siklus.id}/ekspor`, { jenis, format, final }), { sukses: "Dokumen sedang disusun…", onSuccess: (r) => setEkspor([r, ...ekspor]) });
  const final_ok = laporan.status === "disetujui";
  return (
    <Card judul="Ekspor dokumen" sub="Data yang diekspor identik dengan basis data inti; dokumen draf diberi tanda air.">
      <div className="form-grid">
        <Field label="Jenis dokumen"><select value={jenis} onChange={(e) => { setJenis(e.target.value); setFormat(e.target.value === "led" ? "docx" : "xlsx"); }}><option value="led">Laporan Evaluasi Diri (LED)</option><option value="data_kuantitatif">Data kuantitatif</option>{punya("dekan") && <option value="gap_analysis">Gap analysis</option>}</select></Field>
        <Field label="Format"><select value={format} onChange={(e) => setFormat(e.target.value)}>{jenis === "led" ? <><option value="docx">DOCX</option><option value="pdf">PDF</option></> : <option value="xlsx">XLSX</option>}</select></Field>
      </div>
      <label className="check" style={{ marginBottom: "1rem" }}>
        <input type="checkbox" checked={final} disabled={!final_ok || jenis === "gap_analysis"} onChange={(e) => setFinal(e.target.checked)} />
        Dokumen final {final_ok ? "(dari versi yang disetujui Dekan)" : "— tersedia setelah laporan disetujui"}
      </label>
      <Button onClick={() => minta.mutate()} disabled={minta.isPending}><Icon name="download" size={15} /> Buat dokumen</Button>
      {minta.error && <div style={{ marginTop: "0.8rem" }}><ErrorBox error={minta.error} /></div>}
      <div className="stack stack--sm" style={{ marginTop: "1rem" }}>{ekspor.map((e) => <BarisEkspor key={e.id} awal={e} />)}</div>
    </Card>
  );
}

function BarisEkspor({ awal }: { awal: Rec }) {
  const q = useApi<Rec>(`/ekspor/${awal.id}`, undefined, { refetchInterval: awal.status === "selesai" || awal.status === "gagal" ? undefined : 2000 });
  const e = q.data ?? awal;
  const berhenti = e.status === "selesai" || e.status === "gagal";
  const unduh = useAksi(async () => { const r = await api.get(`/ekspor/${awal.id}/unduh`); window.open(r.url, "_blank", "noopener"); });
  if (berhenti && q.isFetching === false && q.refetch === undefined) return null;
  return (
    <div className="card row row--between" style={{ padding: "0.6rem 0.9rem" }}>
      <div>
        <strong>{labelEnum(e.jenis)}</strong> · {String(e.format).toUpperCase()} {e.metadata?.final ? <Pill warna="lime">Final</Pill> : <Pill>Draf</Pill>}
        <div className="cell-sub">{e.status === "selesai" ? `${ukuranBerkas(e.ukuran_byte)} · data per ${tanggal(e.metadata?.data_per)}` : e.status === "gagal" ? e.galat : "Sedang diproses…"}</div>
      </div>
      <div className="row">
        {!berhenti && <span className="spinner" />}
        <StatusPill status={e.status} />
        {e.status === "selesai" && <Button size="sm" onClick={() => unduh.mutate()}><Icon name="download" size={14} /> Unduh</Button>}
      </div>
    </div>
  );
}
