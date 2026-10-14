import { api } from "@/shared/api/client";
import type { Rec } from "@/shared/api/types";
import { useAksi, useApi } from "@/shared/lib/hooks";
import { angka, labelEnum, waktu } from "@/shared/lib/format";
import { Alert, Button, Card, ErrorBox, Icon, Muat, Pill, Tabel, type Kolom } from "@/shared/ui";
import { Link } from "react-router-dom";

export function SimulasiTab({ siklus }: { siklus: Rec }) {
  const q = useApi<Rec>(`/siklus/${siklus.id}/simulasi-skor`);
  const hitung = useAksi(() => api.post(`/siklus/${siklus.id}/simulasi-skor`), { sukses: "Simulasi dihitung ulang", invalidate: [`/siklus/${siklus.id}/simulasi`, "/dasbor"] });
  return (
    <Muat q={q}>
      {(d) => {
        const r = hitung.data ?? d;
        const rin = r.rincian ?? {};
        return (
          <div className="stack">
            <Alert jenis="warn" judul="Estimasi internal — bukan penilaian resmi asesor">
              {r.peringatan} Dihitung {waktu(r.dihitung_pada)}. Simulasi tidak membandingkan skor mentah LAMSAMA dengan LAM INFOKOM.
            </Alert>
            <div className="grid grid--3">
              <Card aksen={r.di_bawah_target ? "amber" : "lime"}>
                <div className="metric__label">Prediksi peringkat</div>
                <div className="metric__value" style={{ fontSize: "1.5rem", margin: "0.25rem 0" }}>{r.prediksi_peringkat?.nama ?? "—"}</div>
                <div className="faint" style={{ fontSize: "0.82rem" }}>Target: {r.target_peringkat?.nama ?? "belum ditetapkan"}</div>
                {r.di_bawah_target && <Pill warna="amber" dot>Di bawah target</Pill>}
              </Card>
              <Card>
                <div className="metric__label">Nilai akhir berbobot</div>
                <div className="metric__value" style={{ margin: "0.25rem 0" }}>{r.nilai_akhir !== null ? angka(r.nilai_akhir, 1) : "—"}</div>
                <div className="faint" style={{ fontSize: "0.82rem" }}>{r.nilai_akhir !== null ? `dari ${angka(r.nilai_akhir_maks)}` : "Instrumen ini tidak memakai nilai akhir (ambang per indikator)."}</div>
              </Card>
              <Card>
                <div className="metric__label">Butir belum dinilai</div>
                <div className="metric__value" style={{ margin: "0.25rem 0", color: r.butir_belum_dinilai ? "var(--amber)" : undefined }}>{r.butir_belum_dinilai}</div>
                <Button size="sm" variant="primary" onClick={() => hitung.mutate()} disabled={hitung.isPending}>{hitung.isPending ? <span className="spinner" /> : <Icon name="refresh" size={14} />} Hitung ulang</Button>
              </Card>
            </div>
            {hitung.error && <ErrorBox error={hitung.error} />}
            {rin.kriteria && <RincianBerbobot rin={rin} />}
            {rin.per_peringkat && <RincianAmbang rin={rin} />}
            {rin.prioritas_perbaikan?.length > 0 && (
              <Card judul="Prioritas perbaikan" sub="Butir yang paling menekan peringkat target.">
                <div className="stack stack--sm">
                  {rin.prioritas_perbaikan.map((p: Rec) => (
                    <div key={p.butir_siklus_id ?? p.kode} className="row row--between card" style={{ padding: "0.6rem 0.9rem" }}>
                      <div><Link className="butir-code" to={`/butir/${p.butir_siklus_id}`}>{p.kode}</Link> <span className="muted"> skor {p.skor_estimasi ?? "—"}{p.skor_min !== undefined ? ` / min ${p.skor_min}` : ""}</span></div>
                      <Pill warna={p.alasan === "syarat_perlu" || p.alasan === "di_bawah_skor_minimum" ? "red" : "amber"}>{labelEnum(p.alasan)}</Pill>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        );
      }}
    </Muat>
  );
}

function RincianBerbobot({ rin }: { rin: Rec }) {
  const kolom: Kolom<Rec>[] = [
    { kunci: "kode", judul: "Kriteria", render: (k) => <strong>{k.kode}</strong> },
    { kunci: "bobot", judul: "Bobot", num: true, render: (k) => angka(k.bobot) },
    { kunci: "rerata", judul: "Rerata skor", num: true, render: (k) => <span className="score">{angka(k.rerata, 2)}</span> },
    { kunci: "syarat", judul: "Syarat Unggul", render: (k) => (k.memenuhi_syarat === null ? <span className="faint">—</span> : <Pill warna={k.memenuhi_syarat ? "lime" : "red"} dot>{k.memenuhi_syarat ? "Memenuhi" : "Belum"}</Pill>) },
  ];
  return (
    <Card judul="Rincian per kriteria" flush>
      <Tabel kolom={kolom} baris={rin.kriteria} id={(k) => k.kode} />
      {rin.syarat_gagal?.length > 0 && (
        <div style={{ padding: "1rem 1.4rem" }}>
          <Alert jenis="danger" judul="Syarat peringkat Unggul belum terpenuhi">
            <ul>{rin.syarat_gagal.map((s: Rec, i: number) => <li key={i}>{s.syarat === "rerata_kriteria_min" ? `Kriteria ${s.kriteria}: rerata ${s.nilai} < ${s.ambang}` : `Butir ${s.butir}: skor ${s.nilai} < ${s.ambang}`}</li>)}</ul>
          </Alert>
        </div>
      )}
    </Card>
  );
}

function RincianAmbang({ rin }: { rin: Rec }) {
  return (
    <Card judul="Pemenuhan ambang per peringkat" sub="Peringkat tercapai bila semua ambang indikatornya terpenuhi (syarat perlu wajib).">
      <div className="stack">
        {rin.per_peringkat.map((p: Rec) => (
          <div key={p.kode} className="source-card">
            <div className="row row--between"><strong>{p.nama}</strong><Pill warna={p.tercapai ? "lime" : "red"} dot>{p.tercapai ? "Tercapai" : `${p.butir_di_bawah_ambang.length} indikator di bawah ambang`}</Pill></div>
            {p.butir_di_bawah_ambang.length > 0 && (
              <ul>{p.butir_di_bawah_ambang.map((b: Rec) => <li key={b.kode}>Indikator <strong>{b.kode}</strong>: skor {b.skor_estimasi ?? "belum dinilai"} (min {b.skor_min}){b.is_syarat_perlu && <> · <span style={{ color: "var(--red)" }}>syarat perlu</span></>}</li>)}</ul>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}
