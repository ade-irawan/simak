import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "@/shared/api/client";
import { useAuth } from "@/shared/auth/AuthProvider";
import { useToast } from "@/shared/ui";
import { Alert, Button, ErrorBox, Eyebrow, Field, Icon, Logo } from "@/shared/ui";

function KerangkaAuth({ judul, sub, children }: { judul: string; sub?: string; children: React.ReactNode }) {
  return (
    <div className="auth">
      <div className="auth__grid" />
      <div className="auth__glow" />
      <div className="auth__wrap">
        <div>
          <div className="brand" style={{ padding: 0, marginBottom: "2rem" }}>
            <Logo size={46} />
            <span className="brand__text">
              <strong style={{ fontSize: "1.3rem" }}>SIMAK</strong>
              <small>Sistem Informasi Manajemen Akreditasi</small>
            </span>
          </div>
          <Eyebrow>Fakultas · LAMSAMA &amp; LAM INFOKOM</Eyebrow>
          <h1 className="auth__title">
            Satu data, <span className="grad grad--blue">dua instrumen</span> akreditasi.
          </h1>
          <p className="auth__lead">
            Input Tridharma sekali, dipetakan otomatis ke IAPS 3.1 LAMSAMA dan IAPS 2.1 LAM INFOKOM — dengan siklus PPEPP, validasi Dekan, dan telaah bukti
            asesor yang terkendali.
          </p>
          <dl className="auth__stats">
            <div className="metric"><div className="metric__value grad grad--lime">1</div><div className="metric__label">Basis data tunggal</div></div>
            <div className="metric"><div className="metric__value grad grad--blue">2</div><div className="metric__label">Instrumen LAM</div></div>
            <div className="metric"><div className="metric__value">5</div><div className="metric__label">Tahap PPEPP</div></div>
          </dl>
        </div>
        <div className="auth__card">
          <h2>{judul}</h2>
          {sub && <p className="muted" style={{ marginBottom: "1.4rem" }}>{sub}</p>}
          {children}
        </div>
      </div>
    </div>
  );
}

export function MasukPage() {
  const { masuk, profil, memuat } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState("");
  const [sandi, setSandi] = useState("");
  const [galat, setGalat] = useState<unknown>(null);
  const [proses, setProses] = useState(false);
  const [terkunci, setTerkunci] = useState(false);
  const asal = (loc.state as { dari?: string } | null)?.dari ?? "/";
  if (!memuat && profil) return <Navigate to={asal} replace />;

  const kirim = async (e: FormEvent) => {
    e.preventDefault();
    setProses(true);
    setGalat(null);
    try {
      const p = await masuk(email.trim(), sandi);
      nav(p.wajib_ganti_sandi ? "/profil" : asal, { replace: true });
    } catch (err) {
      setGalat(err);
      setTerkunci(err instanceof ApiError && err.code === "AKUN_TERKUNCI");
    } finally {
      setProses(false);
    }
  };

  return (
    <KerangkaAuth judul="Masuk" sub="Gunakan akun yang diberikan Dekan atau Administrator.">
      <form onSubmit={kirim} noValidate>
        <Field label="Surel">
          <input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nama@kampus.ac.id" required autoFocus />
        </Field>
        <Field label="Kata sandi">
          <input type="password" autoComplete="current-password" value={sandi} onChange={(e) => setSandi(e.target.value)} required />
        </Field>
        {galat != null && (
          <div style={{ marginBottom: "1rem" }}>
            <ErrorBox error={galat} />
          </div>
        )}
        {terkunci && (
          <div style={{ marginBottom: "1rem" }}>
            <Alert jenis="info">
              Akun akan terbuka otomatis setelah masa tunggu, atau <Link className="link" to={`/buka-kunci?surel=${encodeURIComponent(email)}`}>kirim tautan buka kunci ke surel</Link>.
            </Alert>
          </div>
        )}
        <Button type="submit" blok disabled={proses || !email || !sandi}>
          {proses ? <span className="spinner" /> : <Icon name="lock" size={16} />} Masuk
        </Button>
        <div className="row row--between" style={{ marginTop: "1.1rem", fontSize: "0.85rem" }}>
          <Link className="link" to="/lupa-sandi">Lupa kata sandi?</Link>
          <Link className="link" to="/buka-kunci">Akun terkunci?</Link>
        </div>
      </form>
    </KerangkaAuth>
  );
}

export function LupaSandiPage() {
  const [email, setEmail] = useState("");
  const [selesai, setSelesai] = useState(false);
  const [proses, setProses] = useState(false);
  const kirim = async (e: FormEvent) => {
    e.preventDefault();
    setProses(true);
    try {
      await api.post("/auth/lupa-sandi", { email });
    } finally {
      setProses(false);
      setSelesai(true);
    }
  };
  return (
    <KerangkaAuth judul="Atur ulang kata sandi" sub="Kami akan mengirim tautan atur ulang ke surel akun Anda.">
      {selesai ? (
        <Alert jenis="ok" judul="Permintaan diterima">Bila surel terdaftar, tautan atur ulang telah dikirim. Periksa kotak masuk Anda.</Alert>
      ) : (
        <form onSubmit={kirim}>
          <Field label="Surel"><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus /></Field>
          <Button type="submit" blok disabled={proses || !email}>Kirim tautan</Button>
        </form>
      )}
      <p style={{ marginTop: "1.1rem", fontSize: "0.85rem" }}><Link className="link" to="/masuk">← Kembali ke halaman masuk</Link></p>
    </KerangkaAuth>
  );
}

export function ResetSandiPage() {
  const [sp] = useSearchParams();
  const [sandi, setSandi] = useState("");
  const [ulang, setUlang] = useState("");
  const [galat, setGalat] = useState<unknown>(null);
  const [ok, setOk] = useState(false);
  const token = sp.get("token") ?? "";
  const kirim = async (e: FormEvent) => {
    e.preventDefault();
    setGalat(null);
    try {
      await api.post("/auth/reset-sandi", { token, password_baru: sandi });
      setOk(true);
    } catch (err) {
      setGalat(err);
    }
  };
  return (
    <KerangkaAuth judul="Tetapkan kata sandi baru">
      {ok ? (
        <Alert jenis="ok" judul="Kata sandi diperbarui">Silakan <Link className="link" to="/masuk">masuk</Link> dengan kata sandi baru.</Alert>
      ) : (
        <form onSubmit={kirim}>
          <Field label="Kata sandi baru" bantuan="Minimal 10 karakter, kombinasi huruf dan angka/simbol."><input type="password" value={sandi} onChange={(e) => setSandi(e.target.value)} autoComplete="new-password" required autoFocus /></Field>
          <Field label="Ulangi kata sandi" galat={ulang && ulang !== sandi ? "Tidak sama" : undefined}><input type="password" value={ulang} onChange={(e) => setUlang(e.target.value)} autoComplete="new-password" required /></Field>
          {galat != null && <div style={{ marginBottom: "1rem" }}><ErrorBox error={galat} /></div>}
          <Button type="submit" blok disabled={!token || !sandi || sandi !== ulang}>Simpan kata sandi</Button>
          {!token && <p className="field__error" style={{ marginTop: "0.6rem" }}>Tautan tidak memuat token.</p>}
        </form>
      )}
    </KerangkaAuth>
  );
}

export function BukaKunciPage() {
  const [sp] = useSearchParams();
  const token = sp.get("token");
  const [email, setEmail] = useState(sp.get("surel") ?? "");
  const [status, setStatus] = useState<"diam" | "terkirim" | "terbuka">("diam");
  const [galat, setGalat] = useState<unknown>(null);
  const toast = useToast();
  const minta = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/auth/buka-kunci/minta", { email });
      setStatus("terkirim");
    } catch (err) {
      toast.galat(err);
    }
  };
  const buka = async () => {
    try {
      await api.post("/auth/buka-kunci", { token });
      setStatus("terbuka");
    } catch (err) {
      setGalat(err);
    }
  };
  return (
    <KerangkaAuth judul="Buka kunci akun" sub="Akun terkunci sementara setelah lima kali salah sandi.">
      {token ? (
        status === "terbuka" ? (
          <Alert jenis="ok" judul="Akun terbuka">Silakan <Link className="link" to="/masuk">masuk kembali</Link>.</Alert>
        ) : (
          <>
            {galat != null && <div style={{ marginBottom: "1rem" }}><ErrorBox error={galat} /></div>}
            <Button blok onClick={buka}><Icon name="unlock" size={16} /> Buka kunci akun saya</Button>
          </>
        )
      ) : status === "terkirim" ? (
        <Alert jenis="ok" judul="Permintaan diterima">Bila surel terdaftar, tautan buka kunci (berlaku 30 menit) telah dikirim.</Alert>
      ) : (
        <form onSubmit={minta}>
          <Field label="Surel akun"><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus /></Field>
          <Button type="submit" blok disabled={!email}>Kirim tautan buka kunci</Button>
          <p className="muted" style={{ marginTop: "1rem", fontSize: "0.82rem" }}>Mendesak? Hubungi Administrator Sistem/IT untuk membuka kunci langsung.</p>
        </form>
      )}
      <p style={{ marginTop: "1.1rem", fontSize: "0.85rem" }}><Link className="link" to="/masuk">← Kembali ke halaman masuk</Link></p>
    </KerangkaAuth>
  );
}

export function ProfilPage() {
  const { profil, aktif, muatUlang } = useAuth();
  const toast = useToast();
  const [lama, setLama] = useState("");
  const [baru, setBaru] = useState("");
  const [galat, setGalat] = useState<unknown>(null);
  const simpan = async (e: FormEvent) => {
    e.preventDefault();
    setGalat(null);
    try {
      await api.put("/auth/sandi", { sandi_lama: lama, sandi_baru: baru });
      toast.ok("Kata sandi diperbarui. Sesi di perangkat lain dicabut.");
      setLama("");
      setBaru("");
      await muatUlang();
    } catch (err) {
      setGalat(err);
    }
  };
  if (!profil || !aktif) return null;
  return (
    <div className="stack" style={{ maxWidth: 560 }}>
      <h1 style={{ fontSize: "1.6rem" }}>Akun saya</h1>
      {profil.wajib_ganti_sandi && <Alert jenis="warn" judul="Ganti kata sandi">Akun Anda memakai sandi awal. Tetapkan kata sandi pribadi sebelum melanjutkan.</Alert>}
      <form className="card" onSubmit={simpan}>
        <p className="muted" style={{ marginBottom: "1rem" }}>{profil.nama} · {profil.email}</p>
        <Field label="Kata sandi saat ini"><input type="password" value={lama} onChange={(e) => setLama(e.target.value)} autoComplete="current-password" required /></Field>
        <Field label="Kata sandi baru" bantuan="Minimal 10 karakter, kombinasi huruf dan angka/simbol."><input type="password" value={baru} onChange={(e) => setBaru(e.target.value)} autoComplete="new-password" required /></Field>
        {galat != null && <div style={{ marginBottom: "1rem" }}><ErrorBox error={galat} /></div>}
        <Button type="submit" disabled={!lama || !baru}>Simpan kata sandi</Button>
      </form>
    </div>
  );
}
