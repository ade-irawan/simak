import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api, ApiError } from "@/shared/api/client";
import type { Halaman as HalamanApi, Rec } from "@/shared/api/types";
import { useAuth } from "@/shared/auth/AuthProvider";
import { useAksi, useApi, useDebounced } from "@/shared/lib/hooks";
import {
  Alert, Button, Empty, ErrorBox, Field, FormFields, Icon, Konfirmasi, ListEditor, Modal, Muat, PageHead, Pager, Pill, StatusPill, Tabel, TombolTemplat, keMuatan, validasiWajib,
  type Kolom,
} from "@/shared/ui";
import { PilihBuktiModal } from "../bukti/BuktiPage";
import { SUMBER_DATA, type Opsi, type SumberCfg } from "./konfigurasi";

const INV = ["/dosen", "/statistik", "/kurikulum", "/penelitian", "/pkm", "/publikasi", "/kerja-sama", "/sarana", "/keuangan", "/dasbor", "/butir-siklus", "/siklus"];

export function DataIntiPage() {
  const { sumber } = useParams();
  const cfg = SUMBER_DATA[sumber ?? ""];
  if (!cfg) return <Empty judul="Sumber data tidak dikenal" />;
  return <HalamanData key={cfg.path} cfg={cfg} />;
}

function useOpsi(): Opsi {
  const tahun = useApi<Rec[]>("/tahun-akademik");
  const prodi = useApi<Rec[]>("/prodi");
  const dosen = useApi<HalamanApi<Rec>>("/dosen", { per_page: 100, sort: "nama" });
  return useMemo<Opsi>(
    () => ({
      tahun: (tahun.data ?? []).map((t) => ({ nilai: t.id, label: t.kode })),
      prodi: (prodi.data ?? []).map((p) => ({ nilai: p.id, label: p.nama })),
      dosen: (dosen.data?.data ?? []).map((d) => ({ nilai: d.id, label: `${d.nama}${d.nidn ? ` (${d.nidn})` : ""}` })),
    }),
    [tahun.data, prodi.data, dosen.data],
  );
}

function HalamanData({ cfg }: { cfg: SumberCfg }) {
  const { punya, aktif } = useAuth();
  const opsi = useOpsi();
  const [q, setQ] = useState("");
  const [tahun, setTahun] = useState("");
  const [status, setStatus] = useState("");
  const [prodi, setProdi] = useState("");
  const [extra, setExtra] = useState<Record<string, string>>({});
  const [page, setPage] = useState(1);
  const [form, setForm] = useState<{ awal: Rec | null } | null>(null);
  const [impor, setImpor] = useState(false);
  const [bukti, setBukti] = useState<Rec | null>(null);
  const [hapus, setHapus] = useState<Rec | null>(null);
  const cari = useDebounced(q);
  const tulis = punya("kaprodi", "staf_prodi", "staf_fakultas");
  const data = useApi<HalamanApi<Rec>>(`/${cfg.path}`, { q: cari, tahun_akademik_id: tahun, status_data: status, prodi_id: prodi, page, per_page: 15, ...extra }, { keep: true });
  const verifikasi = useAksi((id: string) => api.post(`/${cfg.path}/${id}/verifikasi`), { sukses: "Data diverifikasi", invalidate: INV });

  const baris = useMemo(() => (data.data?.data ?? []).map((r): Rec => ({ ...r, _tahun: opsi.tahun.find((t) => t.nilai === (r.tahun_akademik_id ?? ""))?.label ?? "—" })), [data.data, opsi.tahun]);
  const kolom: Kolom<Rec>[] = [
    ...cfg.kolom,
    {
      kunci: "aksi", judul: "", render: (r) => (
        <div className="row" style={{ justifyContent: "flex-end", gap: "0.25rem" }} onClick={(e) => e.stopPropagation()}>
          <Button variant="ghost" size="icon" title="Bukti" onClick={() => setBukti(r)}><Icon name="paperclip" size={15} /></Button>
          {tulis && <Button variant="ghost" size="icon" title="Ubah" onClick={() => setForm({ awal: r })}><Icon name="edit" size={15} /></Button>}
          {punya("kaprodi") && r.status_data === "draft" && <Button variant="ghost" size="icon" title="Verifikasi" onClick={() => verifikasi.mutate(r.id)}><Icon name="checkCircle" size={15} /></Button>}
          {punya("kaprodi") && <Button variant="danger" size="icon" title="Hapus" onClick={() => setHapus(r)}><Icon name="trash" size={15} /></Button>}
        </div>
      ),
    },
  ];

  return (
    <div className="stack">
      <PageHead
        judul={cfg.judul}
        sub={cfg.sub}
        aksi={tulis && (
          <>
            {punya("staf_prodi", "staf_fakultas") && <Button variant="ghost" onClick={() => setImpor(true)}><Icon name="upload" size={15} /> Impor CSV/XLSX</Button>}
            <Button onClick={() => setForm({ awal: null })}><Icon name="plus" size={16} /> Tambah</Button>
          </>
        )}
      />
      <div className="toolbar">
        <input className="input" placeholder="Cari…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        {cfg.tahun && <select className="input" value={tahun} onChange={(e) => { setTahun(e.target.value); setPage(1); }}><option value="">Semua tahun</option>{opsi.tahun.map((t) => <option key={t.nilai} value={t.nilai}>{t.label}</option>)}</select>}
        {punya("dekan", "staf_fakultas") && <select className="input" value={prodi} onChange={(e) => { setProdi(e.target.value); setPage(1); }}><option value="">Semua prodi</option>{opsi.prodi.map((p) => <option key={p.nilai} value={p.nilai}>{p.label}</option>)}</select>}
        <select className="input" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}><option value="">Semua status</option><option value="draft">Draf</option><option value="terverifikasi">Terverifikasi</option></select>
        {cfg.filter?.map((f) => (
          <select key={f.nama} className="input" value={extra[f.nama] ?? ""} onChange={(e) => { setExtra({ ...extra, [f.nama]: e.target.value }); setPage(1); }}>
            <option value="">{f.label}: semua</option>{f.pilihan.map((p) => <option key={p.nilai} value={p.nilai}>{p.label}</option>)}
          </select>
        ))}
      </div>
      <Muat q={data}>
        {(d) => (
          <>
            <Tabel kolom={kolom} baris={baris} id={(r) => r.id} onKlik={tulis ? (r) => setForm({ awal: r }) : undefined} kosong={tulis ? "Belum ada data. Klik “Tambah” untuk memulai." : "Belum ada data."} />
            <Pager page={d.meta.page} perPage={d.meta.per_page} total={d.meta.total} onGanti={setPage} />
          </>
        )}
      </Muat>
      {form && <FormModal cfg={cfg} opsi={opsi} awal={form.awal} onTutup={() => setForm(null)} sendiri={{ prodiId: aktif?.prodi?.id, fakultas: punya("staf_fakultas", "dekan") }} />}
      {impor && <ImporModal cfg={cfg} onTutup={() => setImpor(false)} />}
      {bukti && <BuktiDataModal cfg={cfg} item={bukti} tulis={tulis} onTutup={() => setBukti(null)} />}
      {hapus && <HapusModal cfg={cfg} item={hapus} onTutup={() => setHapus(null)} />}
    </div>
  );
}

/* ------------------------------------------------------------------ formulir */
function FormModal({ cfg, opsi, awal, onTutup, sendiri }: { cfg: SumberCfg; opsi: Opsi; awal: Rec | null; onTutup: () => void; sendiri: { prodiId?: string; fakultas: boolean } }) {
  const { punya } = useAuth();
  const def = cfg.def(opsi, sendiri);
  const edit = !!awal;
  const [nilai, setNilai] = useState<Rec>(() => {
    if (!awal) return { ...cfg.awal(opsi), ...(!sendiri.fakultas && sendiri.prodiId && def.some((d) => d.nama === "prodi_id") ? { prodi_id: sendiri.prodiId } : {}) };
    const n: Rec = { ...awal };
    if (awal.atribusi_prodi) n.atribusi_prodi = awal.atribusi_prodi.map((a: Rec) => ({ prodi_id: a.prodi_id, proporsi: a.proporsi }));
    if (cfg.bersarang?.includes("prodi_ids")) n.prodi_ids = (awal.prodi ?? []).map((p: Rec) => p.id);
    return n;
  });
  const [galat, setGalat] = useState<Record<string, string>>({});
  const [duplikat, setDuplikat] = useState<Rec[] | null>(null);
  const [konflik, setKonflik] = useState<Rec | null>(null);
  const [abaikan, setAbaikan] = useState(false);
  const set = (n: string, v: any) => setNilai((x) => ({ ...x, [n]: v }));

  const simpan = useAksi(
    async () => {
      const muatan = keMuatan(def, nilai);
      const q = abaikan ? "?abaikan_kemiripan=true" : "";
      if (edit) {
        const { id, row_version, ...badan } = muatan;
        void id;
        const { afiliasi, ...tanpaAfiliasi } = badan;
        const kolomBoleh = new Set([...def.map((d) => d.nama), ...(cfg.bersarang ?? []).filter((x) => x !== "afiliasi")]);
        const kirim = Object.fromEntries(Object.entries(tanpaAfiliasi).filter(([k]) => kolomBoleh.has(k)));
        const hasil = await api.patch(`/${cfg.path}/${awal!.id}${q}`, { ...kirim, row_version });
        if (afiliasi && cfg.bersarang?.includes("afiliasi")) await api.put(`/dosen/${awal!.id}/afiliasi`, afiliasi);
        return hasil;
      }
      const badan = Object.fromEntries(Object.entries(muatan).filter(([, v]) => v !== null || def.some((d) => d.nama === "prodi_id")));
      return api.post(`/${cfg.path}${q}`, badan);
    },
    { sukses: edit ? "Perubahan disimpan" : "Data ditambahkan", invalidate: INV, onSuccess: onTutup, diam: true },
  );
  const kirim = () => {
    const g = validasiWajib(def, nilai);
    setGalat(g);
    if (Object.keys(g).length) return;
    setDuplikat(null);
    simpan.mutate(undefined, {
      onError: (e) => {
        if (e instanceof ApiError && e.code === "DUPLIKAT") setDuplikat(e.details);
        if (e instanceof ApiError && e.code === "KONFLIK_VERSI") setKonflik(e.details[0] as Rec);
        if (e instanceof ApiError && e.code === "VALIDASI_GAGAL") {
          const peta: Record<string, string> = {};
          e.details.forEach((d) => d.kolom && (peta[String(d.kolom).split(".")[0]] = String(d.pesan)));
          setGalat(peta);
        }
      },
    });
  };
  const bolehTetapSimpan = !!duplikat && duplikat.every((d) => d.alasan === "judul_mirip" || d.alasan === "kerja_sama_sama");

  return (
    <Modal judul={`${edit ? "Ubah" : "Tambah"} — ${cfg.judul}`} onTutup={onTutup} lebar footer={
      <><Button variant="ghost" onClick={onTutup}>Batal</Button><Button onClick={kirim} disabled={simpan.isPending}>{simpan.isPending && <span className="spinner" />} Simpan</Button></>
    }>
      {edit && awal!.status_data === "terverifikasi" && <div style={{ marginBottom: "1rem" }}><Alert jenis="warn">Data ini sudah terverifikasi. Mengubahnya mengembalikan status ke draf.</Alert></div>}
      <FormFields def={def} nilai={nilai} onUbah={set} galat={galat} />
      {cfg.bersarang?.includes("afiliasi") && (
        <ListEditor judul="Afiliasi prodi (EC-01)" item={nilai.afiliasi ?? []} onUbah={(x) => set("afiliasi", x)} kosong={{ jenis: "homebase", proporsi_beban: 1, tahun_akademik_id: opsi.tahun[0]?.nilai ?? "", prodi_id: sendiri.prodiId ?? "" }} def={[
          { nama: "prodi_id", label: "Prodi", jenis: "pilihan", wajib: true, pilihan: sendiri.fakultas ? opsi.prodi : opsi.prodi.filter((p) => p.nilai === sendiri.prodiId) },
          { nama: "tahun_akademik_id", label: "Tahun", jenis: "pilihan", wajib: true, pilihan: opsi.tahun },
          { nama: "jenis", label: "Jenis", jenis: "pilihan", pilihan: [{ nilai: "homebase", label: "Homebase" }, { nilai: "pengampu", label: "Pengampu lintas prodi" }] },
          { nama: "proporsi_beban", label: "Proporsi beban (0–1)", jenis: "angka", min: 0, max: 1, langkah: "0.05" }, { nama: "sks_diampu", label: "SKS diampu", jenis: "angka", min: 0 },
        ]} />
      )}
      {cfg.bersarang?.includes("dosen") && (
        <ListEditor judul="Dosen pelaksana" item={nilai.dosen ?? []} onUbah={(x) => set("dosen", x)} kosong={{ peran: "anggota", dosen_id: "" }} def={[
          { nama: "dosen_id", label: "Dosen", jenis: "pilihan", wajib: true, pilihan: opsi.dosen }, { nama: "peran", label: "Peran", jenis: "pilihan", pilihan: [{ nilai: "ketua", label: "Ketua" }, { nilai: "anggota", label: "Anggota" }] },
        ]} />
      )}
      {cfg.bersarang?.includes("penulis") && (
        <ListEditor judul="Penulis (dosen)" item={nilai.penulis ?? []} onUbah={(x) => set("penulis", x)} kosong={{ urutan_penulis: (nilai.penulis?.length ?? 0) + 1, is_korespondensi: false, dosen_id: "" }} def={[
          { nama: "dosen_id", label: "Dosen", jenis: "pilihan", wajib: true, pilihan: opsi.dosen }, { nama: "urutan_penulis", label: "Urutan", jenis: "angka", langkah: "1", min: 1 }, { nama: "is_korespondensi", label: "Penulis korespondensi", jenis: "centang" },
        ]} />
      )}
      {cfg.bersarang?.includes("atribusi_prodi") && punya("kaprodi", "staf_prodi", "staf_fakultas") && (
        <ListEditor judul="Atribusi prodi (opsional)" item={nilai.atribusi_prodi ?? []} onUbah={(x) => set("atribusi_prodi", x)} kosong={{ proporsi: 1, prodi_id: "" }} def={[
          { nama: "prodi_id", label: "Prodi", jenis: "pilihan", wajib: true, pilihan: opsi.prodi }, { nama: "proporsi", label: "Proporsi (jumlah ≤ 1)", jenis: "angka", min: 0.01, max: 1, langkah: "0.05" },
        ]} />
      )}
      {cfg.bersarang?.includes("prodi_ids") && (
        <Field label="Berlaku untuk prodi" bantuan="Kosong = prodi Anda.">
          <div className="chips">{opsi.prodi.map((p) => (
            <label key={p.nilai} className="check"><input type="checkbox" checked={(nilai.prodi_ids ?? []).includes(p.nilai)} onChange={(e) => set("prodi_ids", e.target.checked ? [...(nilai.prodi_ids ?? []), p.nilai] : (nilai.prodi_ids ?? []).filter((x: string) => x !== p.nilai))} />{p.label}</label>
          ))}</div>
        </Field>
      )}
      {duplikat && (
        <Alert jenis="warn" judul="Data serupa sudah tercatat">
          <ul>{duplikat.map((d) => <li key={d.id}>{d.judul ?? "(tanpa judul)"}{d.doi ? ` — DOI ${d.doi}` : ""} <Pill warna="amber">{String(d.alasan).replace(/_/g, " ")}</Pill></li>)}</ul>
          <div className="row" style={{ marginTop: "0.6rem" }}>
            <Button variant="ghost" size="sm" onClick={onTutup}>Batal — pakai catatan yang ada</Button>
            {bolehTetapSimpan ? <Button size="sm" onClick={() => { setAbaikan(true); setTimeout(kirim, 0); }}>Tetap simpan sebagai catatan baru</Button> : <span className="faint">Identitas yang sama (DOI/NIDN) tidak dapat disimpan ganda.</span>}
          </div>
        </Alert>
      )}
      {konflik && (
        <Alert jenis="danger" judul="Data diubah pengguna lain">
          Versi {String((konflik as Rec).row_version)} sudah tersimpan. <Button size="sm" variant="ghost" onClick={() => { setNilai((konflik as Rec).data); setKonflik(null); }}>Muat versi terbaru</Button> sebelum menyimpan agar tidak saling menimpa.
        </Alert>
      )}
      {simpan.error && !duplikat && !konflik && <div style={{ marginTop: "1rem" }}><ErrorBox error={simpan.error} /></div>}
    </Modal>
  );
}

/* ------------------------------------------------------------------ bukti, hapus, impor */
function BuktiDataModal({ cfg, item, tulis, onTutup }: { cfg: SumberCfg; item: Rec; tulis: boolean; onTutup: () => void }) {
  const [pilih, setPilih] = useState(false);
  const daftar = useApi<Rec[]>(`/${cfg.path}/${item.id}/bukti`);
  const butir = useApi<Rec[]>(`/${cfg.path}/${item.id}/butir`);
  const lampir = useAksi((b: Rec) => api.put(`/${cfg.path}/${item.id}/bukti/${b.id}`), { sukses: "Bukti dilampirkan", invalidate: [`/${cfg.path}`], onSuccess: () => { setPilih(false); daftar.refetch(); } });
  const lepas = useAksi((id: string) => api.del(`/${cfg.path}/${item.id}/bukti/${id}`), { sukses: "Bukti dilepas", invalidate: [`/${cfg.path}`], onSuccess: () => daftar.refetch() });
  return (
    <Modal judul="Bukti & dampak data" onTutup={onTutup} lebar footer={<Button variant="ghost" onClick={onTutup}>Tutup</Button>}>
      <div className="stack">
        <div className="row row--between"><strong>Bukti terlampir</strong>{tulis && <Button size="sm" onClick={() => setPilih(true)}><Icon name="plus" size={14} /> Lampirkan bukti</Button>}</div>
        <Muat q={daftar}>{(d) => (d.length === 0 ? <div className="muted">Belum ada bukti.</div> : <div className="stack stack--sm">{d.map((b) => (
          <div key={b.id} className="card row row--between" style={{ padding: "0.6rem 0.9rem" }}><span>{b.judul}</span><div className="row"><StatusPill status={b.status_cek} />{tulis && <Button size="icon" variant="danger" onClick={() => lepas.mutate(b.id)}><Icon name="x" size={14} /></Button>}</div></div>
        ))}</div>)}</Muat>
        <hr className="divider" />
        <strong>Butir instrumen yang dipasok data ini</strong>
        <Muat q={butir}>{(d) => (d.length === 0 ? <div className="muted">Belum ada aturan pemetaan aktif untuk jenis data ini.</div> : <ul className="reasons">{d.map((b, i) => <li key={i}><span className="butir-code">{b.kode}</span> ({b.instrumen}) — {b.elemen}</li>)}</ul>)}</Muat>
      </div>
      {pilih && <PilihBuktiModal sudah={daftar.data?.map((b) => b.id) ?? []} onTutup={() => setPilih(false)} onPilih={(b) => lampir.mutate(b)} />}
    </Modal>
  );
}

function HapusModal({ cfg, item, onTutup }: { cfg: SumberCfg; item: Rec; onTutup: () => void }) {
  const dampak = useApi<Rec[]>(`/${cfg.path}/${item.id}/butir`);
  const hapus = useAksi(() => api.del(`/${cfg.path}/${item.id}`), { sukses: "Data dihapus", invalidate: INV, onSuccess: onTutup });
  return (
    <Konfirmasi judul="Hapus data?" bahaya labelYa="Hapus" memproses={hapus.isPending} onBatal={onTutup} onYa={() => hapus.mutate()} pesan={
      <div className="stack stack--sm">
        <span>Hanya data berstatus <strong>draf</strong> yang dapat dihapus; data terverifikasi atau yang sudah disetujui dilindungi (EC-09).</span>
        {dampak.data && dampak.data.length > 0 && (
          <Alert jenis="warn" judul="Dampak pada butir">Butir berikut akan kembali “Belum Lengkap” bila data ini hilang: {dampak.data.map((b) => b.kode).join(", ")}.</Alert>
        )}
        {hapus.error && <ErrorBox error={hapus.error} />}
      </div>
    } />
  );
}

function ImporModal({ cfg, onTutup }: { cfg: SumberCfg; onTutup: () => void }) {
  const [berkas, setBerkas] = useState<File | null>(null);
  const [atomik, setAtomik] = useState(false);
  const unggah = useAksi(() => {
    const f = new FormData();
    f.append("berkas", berkas!);
    return api.upload(`/${cfg.path}/impor`, f, { atomik });
  }, { invalidate: INV, diam: true });
  const hasil = unggah.data;
  return (
    <Modal judul={`Impor ${cfg.judul}`} onTutup={onTutup} lebar footer={<><Button variant="ghost" onClick={onTutup}>Tutup</Button><Button disabled={!berkas || unggah.isPending} onClick={() => unggah.mutate()}>{unggah.isPending && <span className="spinner" />} Impor</Button></>}>
      <Alert jenis="info" judul="Mulai dari templat">
        Unduh templat, isi mulai baris 2, lalu unggah kembali. Templat memuat petunjuk tiap kolom serta daftar kode prodi dan tahun akademik yang sah.
        <div style={{ margin: "0.6rem 0" }}><TombolTemplat path={`/${cfg.path}/impor/templat`} namaDasar={`templat-impor-${cfg.path}`} /></div>
        Kolom berkas: <span className="mono">{cfg.kolomImpor}</span>. {cfg.petunjukImpor}
      </Alert>
      <div style={{ margin: "1rem 0" }}><Field label="Berkas"><input type="file" accept=".csv,.xlsx" onChange={(e) => setBerkas(e.target.files?.[0] ?? null)} /></Field>
        <label className="check"><input type="checkbox" checked={atomik} onChange={(e) => setAtomik(e.target.checked)} /> Batalkan semuanya bila ada baris bermasalah</label></div>
      {unggah.error && <ErrorBox error={unggah.error} />}
      {hasil && (
        <div className="stack">
          <Alert jenis={hasil.baris_gagal.length ? "warn" : "ok"} judul={hasil.status === "dibatalkan" ? "Impor dibatalkan" : `${hasil.baris_berhasil} baris berhasil`}>
            {hasil.baris_gagal.length ? `${hasil.baris_gagal.length} baris bermasalah dilaporkan dengan nomornya${hasil.status === "selesai" ? "; baris yang sah tetap tersimpan." : "."}` : "Semua baris sah."}
          </Alert>
          {hasil.baris_gagal.length > 0 && <div className="table-wrap"><table className="table"><thead><tr><th>Baris</th><th>Kolom</th><th>Masalah</th></tr></thead><tbody>{hasil.baris_gagal.map((g: Rec, i: number) => <tr key={i}><td>{g.baris}</td><td>{g.kolom}</td><td>{g.pesan}</td></tr>)}</tbody></table></div>}
        </div>
      )}
    </Modal>
  );
}

