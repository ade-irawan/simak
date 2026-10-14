import { useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { useAuth } from "@/shared/auth/AuthProvider";
import type { Rec } from "@/shared/api/types";
import { useApi } from "@/shared/lib/hooks";
import { angka, labelEnum, tanggal } from "@/shared/lib/format";
import { Alert, Card, Empty, Icon, LinkButton, Muat, PageHead, Pill, Progress, Risiko, StatusPill, Tabel, type Kolom } from "@/shared/ui";

function warnaProgres(p: Rec): "red" | "amber" | "lime" | undefined {
  if (p.tingkat_risiko === "merah") return "red";
  if (p.tingkat_risiko === "kuning") return "amber";
  if (p.tingkat_risiko === "hijau") return "lime";
  return undefined;
}

function KartuProdi({ p }: { p: Rec }) {
  const b = p.butir;
  const sim = p.simulasi;
  return (
    <Card className="prodi-card card--hover" aksen={p.tingkat_risiko === "merah" ? "red" : p.tingkat_risiko === "kuning" ? "amber" : undefined}>
      <div className="prodi-card__top">
        <div>
          <div className="prodi-card__name">{p.prodi.nama}</div>
          <div className="muted" style={{ fontSize: "0.82rem" }}>{p.instrumen ?? "Belum ada siklus akreditasi"}</div>
        </div>
        <Risiko tingkat={p.tingkat_risiko} />
      </div>

      <div>
        <div className="row row--between" style={{ marginBottom: "0.4rem" }}>
          <span className="metric__label">Kesiapan dokumen</span>
          <strong className="score">{angka(p.persen_siap, 1)}%</strong>
        </div>
        <Progress nilai={p.persen_siap} warna={warnaProgres(p)} />
      </div>

      {b ? (
        <div className="stat-row">
          <div className="stat-cell"><b style={{ color: "var(--lime)" }}>{b.lengkap}</b><span>Lengkap</span></div>
          <div className="stat-cell"><b style={{ color: "var(--amber)" }}>{b.draft}</b><span>Draf</span></div>
          <div className="stat-cell"><b>{b.belum_mulai}</b><span>Belum mulai</span></div>
          <div className="stat-cell"><b>{b.jumlah}</b><span>Total butir</span></div>
        </div>
      ) : (
        <Alert jenis="info">Dekan belum membuka siklus akreditasi untuk prodi ini.</Alert>
      )}

      {b && (
        <div className="chips">
          {b.bukti_bermasalah > 0 && <Pill warna="red" dot>{b.bukti_bermasalah} bukti bermasalah</Pill>}
          {b.belum_ditugaskan > 0 && <Pill warna="amber" dot>{b.belum_ditugaskan} belum ditugaskan</Pill>}
          {b.menunggu_dokumen_eksternal > 0 && <Pill warna="amber" dot>{b.menunggu_dokumen_eksternal} menunggu Direktorat</Pill>}
          <Pill warna="blue">PPEPP {p.ppepp.tahap_selesai}/{p.ppepp.tahap_total} tahap</Pill>
          {p.laporan && <StatusPill status={p.laporan} />}
        </div>
      )}

      {sim && p.siklus_id && (
        <div className="card" style={{ padding: "0.8rem 1rem", background: "rgba(255,255,255,0.02)" }}>
          <div className="metric__label">Simulasi skor · estimasi internal</div>
          <div className="row row--between" style={{ marginTop: "0.25rem" }}>
            <strong className="score">{sim.prediksi_peringkat ?? "Belum dihitung"}</strong>
            {sim.nilai_akhir !== null && <span className="muted">nilai {angka(sim.nilai_akhir, 1)}</span>}
          </div>
          {sim.target_peringkat && <div className="faint" style={{ fontSize: "0.78rem" }}>Target: {sim.target_peringkat}</div>}
        </div>
      )}

      {p.alasan_risiko?.length > 0 && (
        <ul className="reasons">
          {p.alasan_risiko.map((a: string) => <li key={a}>{a}</li>)}
        </ul>
      )}

      <div className="row" style={{ marginTop: "auto" }}>
        {p.siklus_id && <LinkButton to={`/siklus/${p.siklus_id}`} variant="primary" size="sm">Buka siklus <Icon name="chevronRight" size={14} /></LinkButton>}
        <LinkButton to={`/dasbor/prodi/${p.prodi.id}`} size="sm">Rincian prodi</LinkButton>
      </div>
    </Card>
  );
}

export function DasborFakultas() {
  const [tahun, setTahun] = useState("");
  const ta = useApi<Rec[]>("/tahun-akademik");
  const q = useApi<Rec>("/dasbor/fakultas", { tahun_akademik_id: tahun });
  const prodi: Rec[] = q.data?.prodi ?? [];
  const merah = prodi.filter((p) => p.tingkat_risiko === "merah").length;
  return (
    <div className="stack">
      <PageHead
        judul="Dasbor Fakultas"
        sub="Kemajuan, risiko, dan prediksi peringkat seluruh program studi dalam satu tampilan."
        aksi={
          <select className="input" value={tahun} onChange={(e) => setTahun(e.target.value)} aria-label="Tahun akademik">
            <option value="">Tahun akademik aktif{q.data?.tahun_akademik ? ` (${q.data.tahun_akademik})` : ""}</option>
            {ta.data?.map((t) => <option key={t.id} value={t.id}>{t.kode}</option>)}
          </select>
        }
      />
      <Muat q={q}>
        {() => (
          <>
            {merah > 0 && <Alert jenis="danger" judul={`${merah} program studi berisiko tinggi`}>Periksa tenggat, bukti yang tidak terjangkau, dan butir yang belum ditugaskan.</Alert>}
            <div className="grid grid--auto" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))" }}>
              {prodi.map((p) => <KartuProdi key={p.prodi.id} p={p} />)}
            </div>
          </>
        )}
      </Muat>
    </div>
  );
}

export function DasborProdi({ prodiId }: { prodiId?: string }) {
  const params = useParams();
  const id = prodiId ?? params.prodiId!;
  const { punya } = useAuth();
  const q = useApi<Rec>(`/dasbor/prodi/${id}`);
  const kolom: Kolom<Rec>[] = [
    { kunci: "kode", judul: "Butir", render: (b) => <Link className="butir-code" to={`/butir/${b.butir_siklus_id}`}>{b.kode}</Link> },
    { kunci: "elemen", judul: "Elemen", render: (b) => <span style={{ display: "block", maxWidth: 520 }}>{b.elemen}</span> },
    { kunci: "status", judul: "Status", render: (b) => <StatusPill status={b.status_kelengkapan} /> },
    { kunci: "pengelola", judul: "Pengelola", render: (b) => <span>{labelEnum(b.pengelola)}<div className="cell-sub">{b.penanggung_jawab ?? <span style={{ color: "var(--amber)" }}>Belum ditugaskan</span>}</div></span> },
    { kunci: "tanda", judul: "Catatan", render: (b) => b.menunggu_dokumen_eksternal ? <Pill warna="amber">Menunggu Direktorat</Pill> : null },
  ];
  return (
    <div className="stack">
      <Muat q={q}>
        {(d) => (
          <>
            <PageHead
              judul={`Prodi ${d.prodi.nama}`}
              sub={d.instrumen ? `${d.instrumen} · ${d.tingkat_risiko === "abu" ? "belum dimulai" : "pemantauan berjalan"}` : "Belum ada siklus akreditasi"}
              aksi={d.siklus_id && <LinkButton to={`/siklus/${d.siklus_id}`} variant="primary">Kelola butir</LinkButton>}
            />
            {!d.siklus_id ? (
              <Alert jenis="info" judul="Belum ada siklus akreditasi">
                {punya("dekan") ? <>Buka siklus baru dari menu <Link className="link" to="/siklus">Siklus &amp; butir</Link>.</> : "Dekan akan membuka siklus untuk prodi ini."}
              </Alert>
            ) : (
              <>
                <div className="grid grid--3">
                  <Card aksen="blue">
                    <div className="metric__label">Kesiapan dokumen</div>
                    <div className="metric__value" style={{ margin: "0.2rem 0 0.6rem" }}>{angka(d.persen_siap, 1)}%</div>
                    <Progress nilai={d.persen_siap} warna={warnaProgres(d)} />
                    <div className="faint" style={{ marginTop: "0.6rem", fontSize: "0.8rem" }}>Tenggat {tanggal(d.tenggat)}</div>
                  </Card>
                  <Card>
                    <div className="metric__label">Simulasi skor · estimasi internal</div>
                    <div className="metric__value" style={{ margin: "0.2rem 0", fontSize: "1.3rem" }}>{d.simulasi?.prediksi_peringkat ?? "Belum dihitung"}</div>
                    <div className="faint" style={{ fontSize: "0.8rem" }}>Target: {d.simulasi?.target_peringkat ?? "—"}</div>
                  </Card>
                  <Card>
                    <div className="metric__label">PPEPP &amp; laporan</div>
                    <div className="metric__value" style={{ margin: "0.2rem 0", fontSize: "1.3rem" }}>{d.ppepp.tahap_selesai}/{d.ppepp.tahap_total} tahap</div>
                    <StatusPill status={d.laporan} />
                  </Card>
                </div>
                {d.alasan_risiko?.length > 0 && <Alert jenis={d.tingkat_risiko === "merah" ? "danger" : "warn"} judul="Perlu perhatian"><ul>{d.alasan_risiko.map((a: string) => <li key={a}>{a}</li>)}</ul></Alert>}
                <Card judul="Butir belum lengkap" sub="Pemantauan progres berjalan — kelengkapan penuh tidak disyaratkan sampai pengajuan.">
                  {d.butir_belum_lengkap.length === 0 ? <Empty judul="Semua butir lengkap" ikon="checkCircle" /> : <Tabel kolom={kolom} baris={d.butir_belum_lengkap} id={(b) => b.butir_siklus_id} />}
                </Card>
              </>
            )}
          </>
        )}
      </Muat>
    </div>
  );
}

/** Beranda menyesuaikan peran (US-A1). */
export function Beranda() {
  const { aktif } = useAuth();
  if (!aktif) return null;
  switch (aktif.peran) {
    case "dekan":
    case "staf_fakultas":
      return <DasborFakultas />;
    case "kaprodi":
    case "staf_prodi":
      return aktif.prodi ? <DasborProdi prodiId={aktif.prodi.id} /> : <Empty judul="Prodi belum ditetapkan" />;
    case "asesor":
      return <Navigate to="/asesmen" replace />;
    case "admin_it":
      return <Navigate to="/pengguna" replace />;
  }
}
