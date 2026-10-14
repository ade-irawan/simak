import { useEffect, useState } from "react";
import type { Rec } from "@/shared/api/types";
import { useApi } from "@/shared/lib/hooks";
import { angka } from "@/shared/lib/format";
import { Alert, Card, Empty, Muat, PageHead, Pill, Tabel, Tabs, type Kolom } from "@/shared/ui";

export function AnalisisPage() {
  const [tab, setTab] = useState<"gap" | "ppepp" | "benchmark">("benchmark");
  return (
    <div className="stack">
      <PageHead judul="Gap analysis & benchmarking" sub="Bandingkan antarprodi hanya pada indikator inti yang setara — skor mentah LAMSAMA dan LAM INFOKOM tidak pernah dibandingkan langsung." />
      <Tabs aktif={tab} onGanti={setTab} tabs={[{ kunci: "benchmark", label: "Benchmarking antarprodi" }, { kunci: "gap", label: "Kesenjangan skor" }, { kunci: "ppepp", label: "Kesenjangan target PPEPP" }]} />
      {tab === "benchmark" && <Benchmark />}
      {tab === "gap" && <GapSiklus />}
      {tab === "ppepp" && <GapPpepp />}
    </div>
  );
}

function Benchmark() {
  const ind = useApi<Rec[]>("/analisis/indikator");
  const ta = useApi<Rec[]>("/tahun-akademik");
  const [kode, setKode] = useState("");
  const [tahun, setTahun] = useState("");
  useEffect(() => { if (!kode && ind.data?.length) setKode(ind.data[0].kode); }, [ind.data, kode]);
  useEffect(() => { if (!tahun && ta.data?.length) setTahun(ta.data.find((t) => t.is_aktif)?.id ?? ta.data[0].id); }, [ta.data, tahun]);
  const q = useApi<Rec>(kode && tahun ? "/analisis/benchmark" : null, { indikator: kode, tahun_akademik_id: tahun });
  return (
    <div className="stack">
      <div className="toolbar">
        <select className="input" style={{ maxWidth: 380 }} value={kode} onChange={(e) => setKode(e.target.value)}>{ind.data?.map((i) => <option key={i.kode} value={i.kode}>{i.nama}</option>)}</select>
        <select className="input" value={tahun} onChange={(e) => setTahun(e.target.value)}>{ta.data?.map((t) => <option key={t.id} value={t.id}>{t.kode}</option>)}</select>
      </div>
      <Muat q={q}>
        {(d) => {
          const maks = Math.max(...d.data.map((x: Rec) => Number(x.nilai ?? 0)), 0.0001);
          return (
            <Card judul={d.indikator.nama} sub={`${d.tahun_akademik} · satuan ${d.indikator.satuan ?? "—"} · ${d.indikator.makin_tinggi_makin_baik ? "makin tinggi makin baik" : "makin rendah makin baik"}`}>
              {d.data.length === 0 ? <Empty judul="Belum ada nilai" /> : (
                <div className="stack">
                  {d.data.map((r: Rec) => (
                    <div key={r.prodi}>
                      <div className="row row--between" style={{ marginBottom: "0.3rem" }}><strong>{r.prodi_nama}</strong><span className="score">{r.nilai !== null ? angka(r.nilai, 2) : <span className="faint">tidak ada data</span>}</span></div>
                      <div className="progress"><div className="progress__bar" style={{ width: `${r.nilai !== null ? (Number(r.nilai) / maks) * 100 : 0}%` }} /></div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          );
        }}
      </Muat>
    </div>
  );
}

function GapSiklus() {
  const sk = useApi<Rec[]>("/siklus");
  const [id, setId] = useState("");
  useEffect(() => { if (!id && sk.data?.length) setId(sk.data[0].id); }, [sk.data, id]);
  const q = useApi<Rec>(id ? "/analisis/gap" : null, { siklus_id: id });
  const kolom: Kolom<Rec>[] = [
    { kunci: "kode", judul: "Butir", render: (b) => <span className="butir-code">{b.kode}</span> },
    { kunci: "kr", judul: "Kriteria", render: (b) => b.kriteria },
    { kunci: "skor", judul: "Skor estimasi", num: true, render: (b) => (b.skor_estimasi !== null ? angka(b.skor_estimasi, 1) : "—") },
    { kunci: "target", judul: "Skor target", num: true, render: (b) => angka(b.skor_target, 1) },
    { kunci: "selisih", judul: "Selisih", num: true, render: (b) => (b.selisih === null ? <Pill warna="amber">belum dinilai</Pill> : <Pill warna={Number(b.selisih) < 0 ? "red" : "lime"}>{Number(b.selisih) > 0 ? "+" : ""}{angka(b.selisih, 1)}</Pill>) },
    { kunci: "sp", judul: "", render: (b) => (b.is_syarat_perlu ? <Pill warna="red">syarat perlu</Pill> : null) },
  ];
  return (
    <div className="stack">
      <div className="toolbar"><select className="input" style={{ maxWidth: 380 }} value={id} onChange={(e) => setId(e.target.value)}>{sk.data?.map((s) => <option key={s.id} value={s.id}>{s.nama}</option>)}</select></div>
      <Muat q={q}>{(d) => (<><Alert jenis="warn">Estimasi internal terhadap target {d.target_peringkat ?? "(belum ditetapkan)"}. {d.butir_di_bawah_target} butir di bawah target.</Alert><Tabel kolom={kolom} baris={d.butir} id={(b) => b.butir_siklus_id} /></>)}</Muat>
    </div>
  );
}

function GapPpepp() {
  const sk = useApi<Rec[]>("/siklus-ppepp");
  const [id, setId] = useState("");
  useEffect(() => { if (!id && sk.data?.length) setId(sk.data[0].id); }, [sk.data, id]);
  const q = useApi<Rec>(id ? "/analisis/gap" : null, { siklus_ppepp_id: id });
  return (
    <div className="stack">
      <div className="toolbar"><select className="input" style={{ maxWidth: 380 }} value={id} onChange={(e) => setId(e.target.value)}>{sk.data?.map((s) => <option key={s.id} value={s.id}>{s.nama}</option>)}</select></div>
      {!sk.data?.length ? <Card><Empty judul="Belum ada siklus PPEPP" /></Card> : (
        <Muat q={q}>{(d) => (
          <div className="grid grid--3">{d.prodi.map((p: Rec) => (
            <Card key={p.prodi.id} judul={p.prodi.nama}>
              {p.butir.length === 0 ? <div className="muted">Tidak ada butir sasaran.</div> : p.butir.map((b: Rec) => (
                <div key={b.penetapan_id} className="row row--between" style={{ padding: "0.3rem 0" }}>
                  <span className="butir-code">{b.nomor_butir}</span>
                  <span>{b.capaian_nilai !== null ? <><span>{angka(b.capaian_nilai, 2)} / {angka(b.target_nilai, 2)}</span> <Pill warna={Number(b.selisih_target) >= 0 ? "lime" : "red"}>{angka(b.selisih_target, 2)}</Pill></> : <span className="faint">belum ada capaian</span>}</span>
                </div>
              ))}
            </Card>
          ))}</div>
        )}</Muat>
      )}
    </div>
  );
}
