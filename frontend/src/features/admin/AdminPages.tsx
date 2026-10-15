import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/shared/api/client";
import type { Halaman, Rec } from "@/shared/api/types";
import { NAMA_PERAN } from "@/shared/api/types";
import { useAuth } from "@/shared/auth/AuthProvider";
import { useAksi, useApi, useDebounced } from "@/shared/lib/hooks";
import { labelEnum, namaLam, tanggal, waktu } from "@/shared/lib/format";
import { Alert, Button, Card, Empty, ErrorBox, Field, Icon, Konfirmasi, Modal, Muat, PageHead, Pager, Pill, StatusPill, Tabel, Tabs, type Kolom } from "@/shared/ui";

const INV = ["/pengguna", "/penugasan-peran", "/pengaturan", "/konfigurasi-llm"];
const PERAN = Object.keys(NAMA_PERAN);

/* ------------------------------------------------------------------ akun & penugasan */
export function PenggunaPage() {
  const { punya } = useAuth();
  const [sp, setSp] = useSearchParams();
  const tab = (sp.get("tab") as "akun" | "penugasan") ?? "akun";
  return (
    <div className="stack">
      <PageHead judul="Akun & penugasan" sub={punya("dekan") ? "Dekan menetapkan siapa berperan apa, cakupan prodi, dan mengaktifkan akses asesor (terbatas waktu, per prodi)." : "Administrator Sistem/IT membuat akun, mengatur peran dan sandi, serta membuka kunci — tanpa akses ke isi data akreditasi. Peran Dekan dan aktivasi asesor tetap wewenang Dekan."} />
      <Tabs aktif={tab} onGanti={(t) => setSp({ tab: t })} tabs={[{ kunci: "akun", label: "Akun" }, { kunci: "penugasan", label: "Penugasan peran & asesor" }]} />
      {tab === "penugasan" ? <PenugasanTab /> : <AkunTab />}
    </div>
  );
}

function AkunTab() {
  const { punya } = useAuth();
  const [q, setQ] = useState("");
  const [peran, setPeran] = useState("");
  const [terkunci, setTerkunci] = useState("");
  const [page, setPage] = useState(1);
  const [baru, setBaru] = useState(false);
  const [aksi, setAksi] = useState<{ jenis: "buka" | "reset" | "nonaktif"; akun: Rec } | null>(null);
  const [sandi, setSandi] = useState<Rec | null>(null);
  const [surel, setSurel] = useState<Rec | null>(null);
  const { profil } = useAuth();
  const cari = useDebounced(q);
  const data = useApi<Halaman<Rec>>("/pengguna", { q: cari, peran, terkunci, page, per_page: 15 }, { keep: true });
  const kolom: Kolom<Rec>[] = [
    { kunci: "nama", judul: "Pengguna", render: (a) => <div><div className="cell-title">{a.nama}</div><div className="cell-sub">{a.email}</div></div> },
    { kunci: "peran", judul: "Peran", render: (a) => <div className="chips">{a.peran.filter((p: Rec) => p.status !== "dicabut").map((p: Rec) => <Pill key={p.id} warna={p.status === "diusulkan" ? "amber" : "blue"}>{NAMA_PERAN[p.peran as keyof typeof NAMA_PERAN]}{p.prodi ? ` · ${p.prodi.kode}` : ""}{p.status === "diusulkan" ? " (usulan)" : ""}</Pill>)}</div> },
    { kunci: "status", judul: "Status", render: (a) => <div><StatusPill status={a.status} />{a.terkunci_sampai && new Date(a.terkunci_sampai) > new Date() && <div className="cell-sub" style={{ color: "var(--red)" }}><Icon name="lock" size={12} /> terkunci sampai {waktu(a.terkunci_sampai)}</div>}</div> },
    { kunci: "login", judul: "Login terakhir", render: (a) => waktu(a.login_terakhir) },
    { kunci: "aksi", judul: "", render: (a) => (
      <div className="row" style={{ justifyContent: "flex-end", gap: "0.3rem" }}>
        {punya("admin_it") && <Button size="icon" variant="ghost" title="Buka kunci" onClick={() => setAksi({ jenis: "buka", akun: a })}><Icon name="unlock" size={15} /></Button>}
        {punya("admin_it") && a.id !== profil?.id && <Button size="icon" variant="ghost" title="Atur sandi sementara" onClick={() => setSandi(a)}><Icon name="edit" size={15} /></Button>}
        {punya("admin_it") && <Button size="icon" variant="ghost" title="Ganti alamat surel" onClick={() => setSurel(a)}><Icon name="inbox" size={15} /></Button>}
        {punya("admin_it") && <Button size="icon" variant="ghost" title="Kirim tautan reset sandi" onClick={() => setAksi({ jenis: "reset", akun: a })}><Icon name="refresh" size={15} /></Button>}
        {a.status === "aktif" && <Button size="icon" variant="danger" title="Nonaktifkan" onClick={() => setAksi({ jenis: "nonaktif", akun: a })}><Icon name="x" size={15} /></Button>}
      </div>
    ) },
  ];
  return (
    <div className="stack">
      <div className="toolbar">
        <input className="input" placeholder="Cari nama atau surel…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        <select className="input" value={peran} onChange={(e) => { setPeran(e.target.value); setPage(1); }}><option value="">Semua peran</option>{PERAN.map((p) => <option key={p} value={p}>{NAMA_PERAN[p as keyof typeof NAMA_PERAN]}</option>)}</select>
        <select className="input" value={terkunci} onChange={(e) => { setTerkunci(e.target.value); setPage(1); }}><option value="">Semua status kunci</option><option value="true">Sedang terkunci</option><option value="false">Tidak terkunci</option></select>
        <span className="spacer" />
        {(punya("dekan") || punya("admin_it")) && <Button onClick={() => setBaru(true)}><Icon name="plus" size={15} /> Akun baru</Button>}
      </div>
      <Muat q={data}>{(d) => (<><Tabel kolom={kolom} baris={d.data} id={(a) => a.id} /><Pager page={d.meta.page} perPage={d.meta.per_page} total={d.meta.total} onGanti={setPage} /></>)}</Muat>
      {baru && <AkunBaruModal onTutup={() => setBaru(false)} />}
      {aksi && <AksiAkunModal {...aksi} onTutup={() => setAksi(null)} />}
      {sandi && <AturSandiModal akun={sandi} onTutup={() => setSandi(null)} />}
      {surel && <AturEmailModal akun={surel} onTutup={() => setSurel(null)} />}
    </div>
  );
}

/** Peran yang boleh ditetapkan pemanggil: Admin IT tidak menetapkan Dekan; asesor lewat tab Penugasan. */
function usePeranDapatDitetapkan(termasukAsesor: boolean) {
  const { punya } = useAuth();
  return PERAN.filter((p) => (termasukAsesor || p !== "asesor") && (p !== "dekan" || punya("dekan")));
}

const PERLU_PRODI = ["kaprodi", "staf_prodi", "asesor"];

function sandiAcak(): string {
  const huruf = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789";
  const b = crypto.getRandomValues(new Uint32Array(14));
  return Array.from(b, (n) => huruf[n % huruf.length]).join("") + "-7";
}

function AturSandiModal({ akun, onTutup }: { akun: Rec; onTutup: () => void }) {
  const [sandi, setSandi] = useState("");
  const simpan = useAksi(() => api.post(`/pengguna/${akun.id}/atur-sandi`, { sandi_baru: sandi }), { sukses: "Sandi sementara ditetapkan (tercatat di audit)", invalidate: INV, onSuccess: onTutup });
  return (
    <Modal judul="Atur sandi sementara" onTutup={onTutup} footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button disabled={sandi.length < 8 || simpan.isPending} onClick={() => simpan.mutate()}>Tetapkan sandi</Button></>}>
      <p className="muted" style={{ marginBottom: "1rem" }}>{akun.nama} ({akun.email}). Pengguna wajib menggantinya saat masuk; semua sesi lamanya dicabut dan kunci akun dibuka. Sampaikan sandi lewat saluran yang aman.</p>
      <Field label="Sandi sementara" wajib bantuan="Minimal 8 karakter, gabungan huruf dan angka/simbol.">
        <div className="row" style={{ gap: "0.5rem" }}>
          <input type="text" style={{ flex: 1 }} value={sandi} onChange={(e) => setSandi(e.target.value)} autoComplete="off" spellCheck={false} />
          <Button variant="ghost" onClick={() => setSandi(sandiAcak())}>Buat acak</Button>
        </div>
      </Field>
      {simpan.error && <ErrorBox error={simpan.error} />}
    </Modal>
  );
}

function AturEmailModal({ akun, onTutup }: { akun: Rec; onTutup: () => void }) {
  const { profil } = useAuth();
  const [email, setEmail] = useState(akun.email);
  const sendiri = akun.id === profil?.id;
  const simpan = useAksi(() => api.post(`/pengguna/${akun.id}/atur-email`, { email }), { sukses: "Alamat surel diganti (tercatat di audit)", invalidate: INV, onSuccess: onTutup });
  const valid = /^\S+@\S+\.\S+$/.test(email) && email.trim().toLowerCase() !== akun.email.toLowerCase();
  return (
    <Modal judul="Ganti alamat surel" onTutup={onTutup} footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button disabled={!valid || simpan.isPending} onClick={() => simpan.mutate()}>Simpan surel</Button></>}>
      <p className="muted" style={{ marginBottom: "1rem" }}>{akun.nama}. Surel dipakai untuk masuk, sehingga pengguna harus masuk dengan alamat baru. Tautan reset/buka kunci yang belum dipakai dihanguskan{sendiri ? "." : " dan semua sesi pengguna dicabut."}</p>
      <Field label="Alamat surel baru" wajib>
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="off" spellCheck={false} />
      </Field>
      {simpan.error && <ErrorBox error={simpan.error} />}
    </Modal>
  );
}

function AkunBaruModal({ onTutup }: { onTutup: () => void }) {
  const prodi = useApi<Rec[]>("/prodi");
  const opsiPeran = usePeranDapatDitetapkan(false);
  const [f, setF] = useState({ nama: "", email: "", password_awal: "" });
  const [peran, setPeran] = useState<{ peran: string; prodi_id: string }[]>([{ peran: "kaprodi", prodi_id: "" }]);
  const ubahPeran = (i: number, k: "peran" | "prodi_id", v: string) => setPeran(peran.map((r, j) => (j === i ? { ...r, [k]: v, ...(k === "peran" ? { prodi_id: "" } : {}) } : r)));
  const lengkap = peran.every((r) => !PERLU_PRODI.includes(r.peran) || r.prodi_id);
  const simpan = useAksi(() => api.post("/pengguna", { nama: f.nama, email: f.email, password_awal: f.password_awal || null, penugasan: peran.map((r) => ({ peran: r.peran, prodi_id: PERLU_PRODI.includes(r.peran) ? r.prodi_id : null })) }),
    { sukses: "Akun dibuat", invalidate: INV, onSuccess: onTutup });
  const set = (k: string, v: string) => setF({ ...f, [k]: v });
  return (
    <Modal judul="Akun baru" onTutup={onTutup} footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button disabled={!f.nama || !f.email || !lengkap || simpan.isPending} onClick={() => simpan.mutate()}>Buat akun</Button></>}>
      <div className="form-grid">
        <Field label="Nama" wajib><input value={f.nama} onChange={(e) => set("nama", e.target.value)} /></Field>
        <Field label="Surel" wajib><input type="email" value={f.email} onChange={(e) => set("email", e.target.value)} /></Field>
        <Field label="Peran" span2 bantuan="Satu akun dapat memegang beberapa peran. Peran asesor ditambahkan lewat tab Penugasan setelah akun ada.">
          <div className="stack" style={{ gap: "0.5rem" }}>
            {peran.map((r, i) => (
              <div className="row" key={i} style={{ gap: "0.5rem" }}>
                <select style={{ flex: 1 }} value={r.peran} onChange={(e) => ubahPeran(i, "peran", e.target.value)}>{opsiPeran.map((p) => <option key={p} value={p}>{NAMA_PERAN[p as keyof typeof NAMA_PERAN]}</option>)}</select>
                {PERLU_PRODI.includes(r.peran) && <select style={{ flex: 1 }} value={r.prodi_id} onChange={(e) => ubahPeran(i, "prodi_id", e.target.value)}><option value="">— prodi —</option>{prodi.data?.map((p) => <option key={p.id} value={p.id}>{p.nama} ({namaLam(p.lam)})</option>)}</select>}
                {peran.length > 1 && <Button size="icon" variant="ghost" title="Hapus peran" onClick={() => setPeran(peran.filter((_, j) => j !== i))}><Icon name="x" size={15} /></Button>}
              </div>
            ))}
            <div><Button size="sm" variant="ghost" onClick={() => setPeran([...peran, { peran: "staf_prodi", prodi_id: "" }])}><Icon name="plus" size={14} /> Tambah peran</Button></div>
          </div>
        </Field>
        <Field label="Sandi awal (opsional)" span2 bantuan="Kosong = pengguna menetapkan sandi sendiri lewat tautan surel. Bila diisi, pengguna wajib menggantinya saat masuk pertama."><div className="row" style={{ gap: "0.5rem" }}><input style={{ flex: 1 }} type="text" value={f.password_awal} onChange={(e) => set("password_awal", e.target.value)} autoComplete="off" spellCheck={false} /><Button variant="ghost" onClick={() => set("password_awal", sandiAcak())}>Buat acak</Button></div></Field>
      </div>
      {simpan.error && <ErrorBox error={simpan.error} />}
    </Modal>
  );
}

function AksiAkunModal({ jenis, akun, onTutup }: { jenis: "buka" | "reset" | "nonaktif"; akun: Rec; onTutup: () => void }) {
  const [alasan, setAlasan] = useState("");
  const aksi = useAksi(() => {
    if (jenis === "buka") return api.post(`/pengguna/${akun.id}/buka-kunci`, { alasan });
    if (jenis === "reset") return api.post(`/pengguna/${akun.id}/reset-sandi`);
    return api.post(`/pengguna/${akun.id}/nonaktifkan`);
  }, { sukses: jenis === "buka" ? "Kunci akun dibuka (tercatat di audit)" : jenis === "reset" ? "Tautan reset sandi dikirim" : "Akun dinonaktifkan", invalidate: INV, onSuccess: onTutup });
  const judul = { buka: "Buka kunci akun", reset: "Kirim tautan reset sandi", nonaktif: "Nonaktifkan akun" }[jenis];
  if (jenis !== "buka") return <Konfirmasi judul={judul} bahaya={jenis === "nonaktif"} labelYa="Lanjutkan" memproses={aksi.isPending} onBatal={onTutup} onYa={() => aksi.mutate()} pesan={<>{akun.nama} ({akun.email}). {jenis === "nonaktif" && "Semua sesi dicabut."}</>} />;
  return (
    <Modal judul={judul} onTutup={onTutup} footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button disabled={alasan.trim().length < 5 || aksi.isPending} onClick={() => aksi.mutate()}>Buka kunci</Button></>}>
      <p className="muted" style={{ marginBottom: "1rem" }}>{akun.nama} ({akun.email}). Catat alasan — termasuk cara identitas pemilik diverifikasi.</p>
      <Field label="Alasan" wajib><textarea style={{ minHeight: 80 }} value={alasan} onChange={(e) => setAlasan(e.target.value)} /></Field>
      {aksi.error && <ErrorBox error={aksi.error} />}
    </Modal>
  );
}

function PenugasanTab() {
  const { punya, profil } = useAuth();
  const [status, setStatus] = useState("");
  const [peran, setPeran] = useState("");
  const [baru, setBaru] = useState(false);
  const [setuju, setSetuju] = useState<Rec | null>(null);
  const q = useApi<Halaman<Rec>>("/penugasan-peran", { status, peran, per_page: 50 });
  const cabut = useAksi((id: string) => api.post(`/penugasan-peran/${id}/cabut`), { sukses: "Penugasan dicabut", invalidate: INV });
  const kolom: Kolom<Rec>[] = [
    { kunci: "p", judul: "Pengguna", render: (t) => t.pengguna.nama },
    { kunci: "peran", judul: "Peran", render: (t) => NAMA_PERAN[t.peran as keyof typeof NAMA_PERAN] },
    { kunci: "prodi", judul: "Prodi", render: (t) => t.prodi?.nama ?? <span className="faint">—</span> },
    { kunci: "jendela", judul: "Jendela asesmen", render: (t) => (t.berlaku_mulai ? `${tanggal(t.berlaku_mulai)} – ${tanggal(t.berlaku_sampai)}` : <span className="faint">tanpa batas</span>) },
    { kunci: "status", judul: "Status", render: (t) => <StatusPill status={t.status} /> },
    { kunci: "aksi", judul: "", render: (t) => (
      <div className="row" style={{ justifyContent: "flex-end" }}>
        {t.status === "diusulkan" && punya("dekan") && <Button size="sm" variant="lime" onClick={() => setSetuju(t)}>Setujui</Button>}
        {t.status !== "dicabut" && (punya("dekan") || (t.peran !== "dekan" && t.pengguna.id !== profil?.id)) && <Button size="sm" variant="danger" onClick={() => cabut.mutate(t.id)}>Cabut</Button>}
      </div>
    ) },
  ];
  return (
    <div className="stack">
      <Alert jenis="info" judul="Aturan akses asesor">{!punya("dekan") && "Penugasan asesor yang Anda tambahkan berstatus usulan sampai Dekan menyetujuinya. "}Hanya Dekan yang mengaktifkan asesor; akses terikat satu prodi, hanya-baca, otomatis berakhir di akhir jendela asesmen, dan hanya setelah laporan prodi berstatus <strong>Disetujui</strong>. Bila belum, usulan tetap tersimpan dan dapat diaktifkan kemudian (EC-28).</Alert>
      <div className="toolbar">
        <select className="input" value={peran} onChange={(e) => setPeran(e.target.value)}><option value="">Semua peran</option>{PERAN.map((p) => <option key={p} value={p}>{NAMA_PERAN[p as keyof typeof NAMA_PERAN]}</option>)}</select>
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Semua status</option><option value="aktif">Aktif</option><option value="diusulkan">Diusulkan</option><option value="dicabut">Dicabut</option></select>
        <span className="spacer" /><Button onClick={() => setBaru(true)}><Icon name="plus" size={15} /> Tambah penugasan</Button>
      </div>
      <Muat q={q}>{(d) => <Tabel kolom={kolom} baris={d.data} id={(t) => t.id} kosong="Belum ada penugasan." />}</Muat>
      {baru && <PenugasanModal onTutup={() => setBaru(false)} />}
      {setuju && <SetujuiPenugasanModal t={setuju} onTutup={() => setSetuju(null)} />}
    </div>
  );
}

const lokal = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);

function PenugasanModal({ onTutup }: { onTutup: () => void }) {
  const users = useApi<Halaman<Rec>>("/pengguna", { per_page: 100 });
  const opsiPeran = usePeranDapatDitetapkan(true);
  const prodi = useApi<Rec[]>("/prodi");
  const [f, setF] = useState({ pengguna_id: "", peran: "asesor", prodi_id: "", mulai: lokal(new Date()), sampai: lokal(new Date(Date.now() + 4 * 86400000)), catatan: "" });
  const set = (k: string, v: string) => setF({ ...f, [k]: v });
  const perluProdi = ["kaprodi", "staf_prodi", "asesor"].includes(f.peran);
  const simpan = useAksi(() => api.post("/penugasan-peran", {
    pengguna_id: f.pengguna_id, peran: f.peran, prodi_id: perluProdi ? f.prodi_id : null, catatan: f.catatan || null,
    ...(f.peran === "asesor" ? { berlaku_mulai: new Date(f.mulai).toISOString(), berlaku_sampai: new Date(f.sampai).toISOString() } : {}),
  }), { sukses: "Penugasan ditambahkan", invalidate: INV, onSuccess: onTutup });
  return (
    <Modal judul="Tambah penugasan peran" onTutup={onTutup} footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button disabled={!f.pengguna_id || (perluProdi && !f.prodi_id) || simpan.isPending} onClick={() => simpan.mutate()}>Tambah</Button></>}>
      <div className="form-grid">
        <Field label="Pengguna" wajib span2><select value={f.pengguna_id} onChange={(e) => set("pengguna_id", e.target.value)}><option value="">— pilih —</option>{users.data?.data.map((u) => <option key={u.id} value={u.id}>{u.nama} — {u.email}</option>)}</select></Field>
        <Field label="Peran" wajib><select value={f.peran} onChange={(e) => set("peran", e.target.value)}>{opsiPeran.map((p) => <option key={p} value={p}>{NAMA_PERAN[p as keyof typeof NAMA_PERAN]}</option>)}</select></Field>
        {perluProdi && <Field label="Program studi" wajib><select value={f.prodi_id} onChange={(e) => set("prodi_id", e.target.value)}><option value="">— pilih —</option>{prodi.data?.map((p) => <option key={p.id} value={p.id}>{p.nama}</option>)}</select></Field>}
        {f.peran === "asesor" && <><Field label="Jendela mulai" wajib><input type="datetime-local" value={f.mulai} onChange={(e) => set("mulai", e.target.value)} /></Field><Field label="Jendela berakhir" wajib><input type="datetime-local" value={f.sampai} onChange={(e) => set("sampai", e.target.value)} /></Field></>}
        <Field label="Catatan" span2><input value={f.catatan} onChange={(e) => set("catatan", e.target.value)} placeholder="mis. Asesmen lapangan Prodi Kimia" /></Field>
      </div>
      {simpan.error && <ErrorBox error={simpan.error} />}
    </Modal>
  );
}

function SetujuiPenugasanModal({ t, onTutup }: { t: Rec; onTutup: () => void }) {
  const [mulai, setMulai] = useState(lokal(t.berlaku_mulai ? new Date(t.berlaku_mulai) : new Date()));
  const [sampai, setSampai] = useState(lokal(t.berlaku_sampai ? new Date(t.berlaku_sampai) : new Date(Date.now() + 4 * 86400000)));
  const aksi = useAksi(() => api.post(`/penugasan-peran/${t.id}/setujui`, { berlaku_mulai: new Date(mulai).toISOString(), berlaku_sampai: new Date(sampai).toISOString() }), { sukses: "Penugasan disetujui dan aktif", invalidate: INV, onSuccess: onTutup });
  return (
    <Modal judul={`Setujui ${NAMA_PERAN[t.peran as keyof typeof NAMA_PERAN]}: ${t.pengguna.nama}`} onTutup={onTutup} footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button variant="lime" disabled={aksi.isPending} onClick={() => aksi.mutate()}>Setujui &amp; aktifkan</Button></>}>
      <div className="form-grid"><Field label="Jendela mulai"><input type="datetime-local" value={mulai} onChange={(e) => setMulai(e.target.value)} /></Field><Field label="Jendela berakhir"><input type="datetime-local" value={sampai} onChange={(e) => setSampai(e.target.value)} /></Field></div>
      {aksi.error && <ErrorBox error={aksi.error} />}
    </Modal>
  );
}

/* ------------------------------------------------------------------ log audit */
export function AuditPage() {
  const { punya } = useAuth();
  const [aksi, setAksi] = useState("");
  const [dari, setDari] = useState("");
  const [page, setPage] = useState(1);
  const [lihat, setLihat] = useState<Rec | null>(null);
  const cari = useDebounced(aksi);
  const q = useApi<Halaman<Rec>>("/log-audit", { aksi: cari, dari: dari ? new Date(dari).toISOString() : undefined, page, per_page: 25 }, { keep: true });
  const kolom: Kolom<Rec>[] = [
    { kunci: "w", judul: "Waktu", render: (l) => <span className="nowrap">{waktu(l.waktu)}</span> },
    { kunci: "u", judul: "Pengguna", render: (l) => <div>{l.pengguna?.nama ?? <span className="faint">—</span>}<div className="cell-sub">{l.peran ? labelEnum(l.peran) : ""}</div></div> },
    { kunci: "a", judul: "Aksi", render: (l) => <Pill warna={l.aksi.startsWith("akses.") || l.aksi.startsWith("login.gagal") ? "red" : l.aksi.startsWith("laporan.") ? "blue" : ""}>{l.aksi}</Pill> },
    { kunci: "e", judul: "Entitas", render: (l) => (l.entitas ? <span>{l.entitas}{l.prodi ? ` · ${l.prodi}` : ""}</span> : <span className="faint">—</span>) },
    { kunci: "ip", judul: "IP", render: (l) => <span className="mono">{l.ip ?? "—"}</span> },
  ];
  return (
    <div className="stack">
      <PageHead judul="Log audit" sub={punya("dekan") ? "Seluruh aksi sensitif: login, penolakan akses, perubahan penugasan, persetujuan, ekspor, dan tindakan asesor." : "Lapisan akun dan sistem. Detail yang memuat isi data akreditasi disamarkan untuk peran ini."} />
      <div className="toolbar"><input className="input" placeholder="Awalan aksi, mis. login. / akses. / laporan." value={aksi} onChange={(e) => { setAksi(e.target.value); setPage(1); }} /><input className="input" type="date" value={dari} onChange={(e) => { setDari(e.target.value); setPage(1); }} aria-label="Dari tanggal" /></div>
      <Muat q={q}>{(d) => (<><Tabel kolom={kolom} baris={d.data} id={(l) => String(l.id)} onKlik={setLihat} kosong="Tidak ada catatan." /><Pager page={d.meta.page} perPage={d.meta.per_page} total={d.meta.total} onGanti={setPage} /></>)}</Muat>
      {lihat && <Modal judul={lihat.aksi} onTutup={() => setLihat(null)} footer={<Button variant="ghost" onClick={() => setLihat(null)}>Tutup</Button>}><pre className="json">{JSON.stringify(lihat.detail, null, 2)}</pre><p className="faint" style={{ marginTop: "0.6rem", fontSize: "0.78rem" }}>{waktu(lihat.waktu)} · {lihat.ip ?? "tanpa IP"} · entitas {lihat.entitas ?? "—"} {lihat.entitas_id ?? ""}</p></Modal>}
    </div>
  );
}

/* ------------------------------------------------------------------ pengaturan sistem (Admin IT) */
export function PengaturanPage() {
  const q = useApi<Rec[]>("/pengaturan");
  return (
    <div className="stack">
      <PageHead judul="Pengaturan sistem" sub="Parameter teknis yang tidak di-hardcode: kebijakan kunci akun, batas ukuran berkas, selang link-checker." />
      <Muat q={q}>{(d) => <div className="stack">{d.map((p) => <BarisPengaturan key={p.kunci} p={p} />)}</div>}</Muat>
    </div>
  );
}

function BarisPengaturan({ p }: { p: Rec }) {
  const [nilai, setNilai] = useState(JSON.stringify(p.nilai));
  useEffect(() => setNilai(JSON.stringify(p.nilai)), [p.nilai]);
  const simpan = useAksi(() => api.put(`/pengaturan/${p.kunci}`, { nilai: JSON.parse(nilai) }), { sukses: `${p.kunci} diperbarui`, invalidate: ["/pengaturan"] });
  return (
    <Card>
      <div className="row row--between">
        <div><div className="cell-title mono">{p.kunci}</div><div className="cell-sub">{p.deskripsi}</div></div>
        <div className="row"><input className="input" style={{ width: 120 }} value={nilai} onChange={(e) => setNilai(e.target.value)} aria-label={p.kunci} /><Button size="sm" disabled={nilai === JSON.stringify(p.nilai) || simpan.isPending} onClick={() => simpan.mutate()}>Simpan</Button></div>
      </div>
      {simpan.error && <ErrorBox error={simpan.error} />}
    </Card>
  );
}

/* ------------------------------------------------------------------ konfigurasi LLM */
export function LlmPage() {
  const { punya } = useAuth();
  const [baru, setBaru] = useState(false);
  const [online, setOnline] = useState<Rec | null>(null);
  const q = useApi<Rec[]>("/konfigurasi-llm");
  const uji = useAksi((id: string) => api.post(`/konfigurasi-llm/${id}/uji`), { invalidate: INV, sukses: (r) => (r.berhasil ? "Koneksi berhasil" : "Koneksi gagal") });
  const aktifkan = useAksi((p: { id: string; konfirmasi: boolean }) => api.post(`/konfigurasi-llm/${p.id}/aktifkan`, { konfirmasi_online: p.konfirmasi }), { sukses: "Konfigurasi diaktifkan", invalidate: INV, onSuccess: () => setOnline(null) });
  const nonaktif = useAksi((id: string) => api.post(`/konfigurasi-llm/${id}/nonaktifkan`), { sukses: "Dinonaktifkan", invalidate: INV });
  return (
    <div className="stack">
      <PageHead judul="Generator LED (LLM)" sub="Opsional. Mode offline (model lokal) adalah bawaan demi kerahasiaan; mode online hanya aktif setelah persetujuan eksplisit Dekan. Kunci API disimpan terenkripsi dan tidak pernah ditampilkan."
        aksi={punya("staf_fakultas") && <Button onClick={() => setBaru(true)}><Icon name="plus" size={15} /> Konfigurasi baru</Button>} />
      <Alert jenis="info">Memakai generator <strong>bukan syarat</strong> pengajuan maupun validasi laporan. Draf selalu ditinjau dan disunting Kaprodi.</Alert>
      <Muat q={q}>
        {(d) => d.length === 0 ? <Card><Empty judul="Belum ada konfigurasi LLM" ikon="sparkles" /></Card> : (
          <div className="grid grid--2">
            {d.map((k) => (
              <Card key={k.id} judul={k.nama} sub={`${k.model} · ${k.base_url}`} aksen={k.is_aktif ? "lime" : undefined} aksi={<><Pill warna={k.mode === "offline" ? "lime" : "amber"}>{k.mode}</Pill>{k.is_aktif && <Pill warna="lime" dot>Aktif</Pill>}</>}>
                <dl className="kv"><dt>Kunci API</dt><dd>{k.punya_api_key ? "tersimpan (terenkripsi)" : "tidak ada"}</dd><dt>Uji koneksi</dt><dd>{k.diuji_pada ? `${waktu(k.diuji_pada)} — ${k.hasil_uji}` : "belum diuji"}</dd><dt>Disetujui</dt><dd>{k.disetujui_pada ? waktu(k.disetujui_pada) : "—"}</dd></dl>
                <div className="row" style={{ marginTop: "1rem" }}>
                  <Button size="sm" variant="ghost" onClick={() => uji.mutate(k.id)} disabled={uji.isPending}>Uji koneksi</Button>
                  {punya("dekan") && !k.is_aktif && <Button size="sm" variant="lime" onClick={() => (k.mode === "online" ? setOnline(k) : aktifkan.mutate({ id: k.id, konfirmasi: false }))}>Aktifkan</Button>}
                  {punya("dekan") && k.is_aktif && <Button size="sm" variant="danger" onClick={() => nonaktif.mutate(k.id)}>Nonaktifkan</Button>}
                </div>
              </Card>
            ))}
          </div>
        )}
      </Muat>
      {aktifkan.error && <ErrorBox error={aktifkan.error} />}
      {baru && <LlmModal onTutup={() => setBaru(false)} />}
      {online && <Konfirmasi judul="Aktifkan mode online?" bahaya labelYa="Saya setuju, aktifkan" memproses={aktifkan.isPending} onBatal={() => setOnline(null)} onYa={() => aktifkan.mutate({ id: online.id, konfirmasi: true })} pesan={<>Mode online mengirim konteks akreditasi (data inti, bukti, hasil evaluasi) ke <strong>{online.base_url}</strong>. Aktifkan hanya bila kebijakan institusi mengizinkan.</>} />}
    </div>
  );
}

function LlmModal({ onTutup }: { onTutup: () => void }) {
  const [f, setF] = useState({ nama: "", mode: "offline", base_url: "http://llm:11434/v1", model: "", api_key: "" });
  const set = (k: string, v: string) => setF({ ...f, [k]: v });
  const simpan = useAksi(() => api.post("/konfigurasi-llm", { ...f, api_key: f.api_key || null }), { sukses: "Konfigurasi disiapkan; uji lalu minta Dekan mengaktifkan", invalidate: INV, onSuccess: onTutup });
  return (
    <Modal judul="Konfigurasi LLM baru" onTutup={onTutup} footer={<><Button variant="ghost" onClick={onTutup}>Batal</Button><Button disabled={!f.nama || !f.base_url || !f.model || simpan.isPending} onClick={() => simpan.mutate()}>Simpan</Button></>}>
      <div className="form-grid">
        <Field label="Nama" wajib><input value={f.nama} onChange={(e) => set("nama", e.target.value)} /></Field>
        <Field label="Mode" wajib><select value={f.mode} onChange={(e) => set("mode", e.target.value)}><option value="offline">Offline (model lokal) — disarankan</option><option value="online">Online (API penyedia)</option></select></Field>
        <Field label="Base URL" wajib span2 bantuan="Antarmuka kompatibel OpenAI, mis. Ollama/vLLM atau penyedia daring."><input value={f.base_url} onChange={(e) => set("base_url", e.target.value)} /></Field>
        <Field label="Model" wajib><input value={f.model} onChange={(e) => set("model", e.target.value)} /></Field>
        <Field label="Kunci API (opsional)"><input type="password" value={f.api_key} onChange={(e) => set("api_key", e.target.value)} autoComplete="off" /></Field>
      </div>
      {simpan.error && <ErrorBox error={simpan.error} />}
    </Modal>
  );
}
