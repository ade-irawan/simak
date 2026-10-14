import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "@/shared/api/client";
import type { Rec } from "@/shared/api/types";
import { useAksi, useApi } from "@/shared/lib/hooks";
import { angka, labelEnum, namaLam, tanggal, waktu } from "@/shared/lib/format";
import { Alert, Button, Card, Empty, Icon, Muat, PageHead, Pill, StatusPill, Tabel, type Kolom } from "@/shared/ui";
import { SUMBER } from "../siklus/konstanta";

/** Tampilan telaah asesor: hanya baca, per butir, dari versi laporan yang disetujui Dekan. */
export function AsesmenDaftar() {
  const nav = useNavigate();
  const q = useApi<Rec>("/asesmen/siklus");
  const kolom: Kolom<Rec>[] = [
    { kunci: "prodi", judul: "Program studi", render: (s) => <div><div className="cell-title">{s.prodi.nama}</div><div className="cell-sub">{s.instrumen}</div></div> },
    { kunci: "versi", judul: "Versi laporan", render: (s) => <span>Pengajuan #{s.versi_laporan.nomor}<div className="cell-sub">disetujui {waktu(s.versi_laporan.disetujui_pada)}</div></span> },
    { kunci: "jendela", judul: "Jendela asesmen", render: (s) => `${tanggal(s.jendela_asesmen.mulai)} – ${tanggal(s.jendela_asesmen.sampai)}` },
    { kunci: "progres", judul: "Telaah", render: (s) => <Pill warna="blue">{s.butir.sudah_ditelaah}/{s.butir.jumlah} butir</Pill> },
  ];
  return (
    <div className="stack">
      <PageHead judul="Telaah asesmen" sub="Akses baca-saja, terbatas pada prodi yang ditugaskan dan jendela asesmen. Setiap tindakan baca tercatat di log audit." />
      <Alert jenis="ok" judul="Anda melihat versi yang sudah disetujui Dekan">Narasi, skor estimasi, dan bukti ditampilkan sebagaimana saat disetujui — bukan data yang sedang dikerjakan prodi.</Alert>
      <Muat q={q}>{(d) => <Tabel kolom={kolom} baris={d.data} id={(s) => s.siklus_id} onKlik={(s) => nav(`/asesmen/${s.siklus_id}`)} kosong="Belum ada laporan yang disetujui untuk prodi yang ditugaskan." />}</Muat>
    </div>
  );
}

export function AsesmenButirDaftar() {
  const { siklusId } = useParams();
  const q = useApi<Rec[]>(`/asesmen/siklus/${siklusId}/butir`);
  return (
    <div className="stack">
      <PageHead crumbs={[{ label: "Telaah asesmen", to: "/asesmen" }, { label: "Butir" }]} judul="Butir per kriteria" sub="Pilih butir untuk membaca narasi, skor estimasi, dan membuka bukti." />
      <Muat q={q}>
        {(d) => (
          <div className="stack">
            {d.map((k) => (
              <Card key={k.kode} judul={`Kriteria ${k.kode} — ${k.nama}`} flush>
                <div className="table-wrap" style={{ border: 0 }}>
                  <table className="table"><tbody>
                    {k.butir.map((b: Rec) => (
                      <tr key={b.butir_siklus_id}>
                        <td style={{ width: 90 }}><Link className="butir-code" to={`/asesmen/butir/${b.butir_siklus_id}`}>{b.kode}</Link></td>
                        <td>{b.elemen}</td>
                        <td className="num">skor {b.skor_estimasi ?? "—"}</td>
                        <td><Pill>{b.jumlah_bukti} bukti</Pill></td>
                        <td>{b.sudah_ditelaah ? <Pill warna="lime" dot>Ditelaah</Pill> : <Pill>Belum</Pill>}</td>
                      </tr>
                    ))}
                  </tbody></table>
                </div>
              </Card>
            ))}
          </div>
        )}
      </Muat>
    </div>
  );
}

export function AsesmenButir() {
  const { id } = useParams();
  const q = useApi<Rec>(`/asesmen/butir/${id}`);
  const [catatan, setCatatan] = useState<string | null>(null);
  const telaah = useAksi((sudah: boolean) => api.put(`/asesmen/butir/${id}/telaah`, { sudah_ditelaah: sudah, catatan: catatan ?? q.data?.telaah.catatan ?? null }), { sukses: "Tanda telaah disimpan", invalidate: ["/asesmen"] });
  const buka = useAksi(async (bid: string) => { const r = await api.get(`/bukti/${bid}/unduh`); window.open(r.url, "_blank", "noopener"); });
  return (
    <div className="stack">
      <Muat q={q}>
        {(d) => (
          <>
            <PageHead crumbs={[{ label: "Telaah asesmen", to: "/asesmen" }, { label: `Butir ${d.butir.kode}` }]}
              judul={<><span className="butir-code" style={{ display: "block", fontSize: "1rem" }}>{d.kriteria.kode} · {d.kriteria.nama} — Butir {d.butir.kode}</span><span style={{ fontFamily: "var(--font-body)", fontWeight: 600, fontSize: "1.2rem", letterSpacing: 0 }}>{d.butir.elemen}</span></>}
              aksi={<Pill warna="lime" dot>Hanya baca · versi #{d.versi_laporan.nomor}</Pill>} />
            <div className="grid" style={{ gridTemplateColumns: "minmax(0,1fr) 320px", alignItems: "start" }}>
              <div className="stack" style={{ minWidth: 0 }}>
                <Card judul="Narasi evaluasi diri">
                  {d.narasi.length === 0 ? <Empty judul="Tidak ada narasi" /> : d.narasi.map((n: Rec) => (
                    <div key={n.bagian} style={{ marginBottom: "1rem" }}>
                      <div className="metric__label">{d.butir.skema_narasi.find((s: Rec) => s.bagian === n.bagian)?.judul ?? n.bagian}</div>
                      <div style={{ whiteSpace: "pre-wrap", marginTop: "0.3rem" }}>{n.isi || <span className="faint">(kosong)</span>}</div>
                    </div>
                  ))}
                </Card>
                <Card judul="Bukti" sub="Hanya bukti yang tercantum pada versi ini yang dapat dibuka.">
                  {d.bukti.length === 0 ? <Empty judul="Tidak ada bukti" ikon="paperclip" /> : <div className="stack stack--sm">{d.bukti.map((b: Rec) => (
                    <div key={b.id} className="card row row--between" style={{ padding: "0.65rem 0.9rem" }}>
                      <div><div className="cell-title"><Icon name={b.jenis === "berkas" ? "file" : "link"} size={14} /> {b.judul}</div><div className="cell-sub">{b.sumber ?? "—"}</div></div>
                      <div className="row"><StatusPill status={b.status_cek} /><Button size="sm" onClick={() => buka.mutate(b.id)}><Icon name="external" size={14} /> Buka</Button></div>
                    </div>
                  ))}</div>}
                </Card>
                <Card judul="Data pendukung">
                  {d.data_terpetakan.length === 0 ? <div className="muted">Butir kualitatif tanpa data terpetakan.</div> : d.data_terpetakan.map((s: Rec) => (
                    <div key={s.aturan_id} className={`source-card${s.kosong ? " source-card--empty" : ""}`} style={{ marginBottom: "0.6rem" }}>
                      <div className="row row--between"><strong>{SUMBER[s.sumber]?.label ?? s.sumber}</strong><Pill warna={s.kosong ? "amber" : "lime"}>{s.jumlah} catatan</Pill></div>
                      {!s.kosong && <ul>{s.contoh.slice(0, 6).map((c: Rec) => <li key={c.id}>{c.label}</li>)}</ul>}
                    </div>
                  ))}
                </Card>
              </div>
              <div className="stack">
                <Card judul="Skor estimasi" sub="Bukan penilaian resmi.">
                  <div className="metric__value">{d.skor_estimasi !== null ? angka(d.skor_estimasi, 1) : "—"}</div>
                  {d.butir.rubrik.map((r: Rec) => <div key={r.skor} className="rubrik__item" style={{ marginTop: "0.5rem", ...(Number(d.skor_estimasi) === r.skor ? { borderColor: "var(--blue)" } : {}) }}><div className="rubrik__skor">{r.skor}</div><div><strong>{r.label}</strong><div className="muted" style={{ fontSize: "0.82rem" }}>{r.deskriptor}</div></div></div>)}
                  {d.butir.ambang.length > 0 && <div className="chips" style={{ marginTop: "0.8rem" }}>{d.butir.ambang.map((a: Rec) => <Pill key={a.peringkat} warna={a.is_syarat_perlu ? "red" : "blue"}>{labelEnum(a.peringkat)} ≥ {a.skor_min}</Pill>)}</div>}
                </Card>
                <Card judul="Catatan baca saya" sub="Tidak mengubah data sumber.">
                  <textarea className="input" style={{ minHeight: 100 }} defaultValue={d.telaah.catatan ?? ""} onChange={(e) => setCatatan(e.target.value)} placeholder="mis. konfirmasi saat asesmen lapangan" />
                  <div className="row" style={{ marginTop: "0.7rem" }}>
                    <Button variant={d.telaah.sudah_ditelaah ? "ghost" : "lime"} onClick={() => telaah.mutate(!d.telaah.sudah_ditelaah)} disabled={telaah.isPending}>{d.telaah.sudah_ditelaah ? "Batalkan tanda" : "Tandai sudah ditelaah"}</Button>
                    {catatan !== null && <Button variant="ghost" onClick={() => telaah.mutate(d.telaah.sudah_ditelaah)}>Simpan catatan</Button>}
                  </div>
                </Card>
              </div>
            </div>
          </>
        )}
      </Muat>
    </div>
  );
}
export { namaLam };
