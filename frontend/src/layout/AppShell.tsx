import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/shared/auth/AuthProvider";
import { NAMA_PERAN, type Halaman, type Rec } from "@/shared/api/types";
import { api } from "@/shared/api/client";
import { useAksi, useApi } from "@/shared/lib/hooks";
import { inisial, namaLam, waktu } from "@/shared/lib/format";
import { Button, Icon, Logo } from "@/shared/ui";
import { NAVIGASI } from "./navigasi";

function Notifikasi() {
  const [buka, setBuka] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const q = useApi<Halaman<Rec>>("/notifikasi", { per_page: 8 }, { refetchInterval: 60_000 });
  const baca = useAksi((id: string) => api.post(`/notifikasi/${id}/baca`), { invalidate: ["/notifikasi"], diam: true });
  const nav = useNavigate();
  useEffect(() => {
    const h = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setBuka(false);
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);
  const belum = q.data?.meta.belum_dibaca ?? 0;
  return (
    <div className="relative" ref={ref}>
      <Button variant="ghost" size="icon" className="bell" onClick={() => setBuka(!buka)} aria-label={`Notifikasi, ${belum} belum dibaca`}>
        <Icon name="bell" />
        {belum > 0 && <span className="bell__count">{belum > 9 ? "9+" : belum}</span>}
      </Button>
      {buka && (
        <div className="menu" style={{ width: 360 }}>
          <div className="menu__title">Notifikasi</div>
          {q.data?.data.length === 0 && <div className="empty" style={{ padding: "1.2rem" }}>Tidak ada notifikasi</div>}
          {q.data?.data.map((n) => (
            <button
              key={n.id}
              className="menu__item"
              onClick={() => {
                if (!n.dibaca_pada) baca.mutate(n.id);
                setBuka(false);
                if (n.tautan) nav(n.tautan);
              }}
            >
              <div className="row" style={{ gap: "0.5rem" }}>
                {!n.dibaca_pada && <span className="dot dot--hijau" />}
                <strong style={{ fontSize: "0.86rem" }}>{n.judul}</strong>
              </div>
              {n.isi && <div className="muted" style={{ fontSize: "0.8rem" }}>{n.isi}</div>}
              <div className="faint" style={{ fontSize: "0.72rem" }}>{waktu(n.created_at)}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function MenuPengguna() {
  const { profil, aktif, setAktif, keluar } = useAuth();
  const [buka, setBuka] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const h = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setBuka(false);
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);
  if (!profil || !aktif) return null;
  return (
    <div className="relative" ref={ref}>
      <button className="user-chip" onClick={() => setBuka(!buka)} aria-haspopup="menu" aria-expanded={buka}>
        <span className="user-chip__name">
          {profil.nama}
          <span className="user-chip__role">
            {NAMA_PERAN[aktif.peran]}
            {aktif.prodi ? ` · ${aktif.prodi.nama}` : ""}
          </span>
        </span>
        <span className="avatar">{inisial(profil.nama)}</span>
      </button>
      {buka && (
        <div className="menu" role="menu" style={{ minWidth: 300 }}>
          <div className="menu__title">{profil.email}</div>
          {profil.peran.length > 1 && (
            <>
              <div className="menu__title">Bertugas sebagai</div>
              {profil.peran.map((p) => (
                <button key={p.penugasan_id} className="menu__item" onClick={() => { setAktif(p.penugasan_id); setBuka(false); }}>
                  {p.penugasan_id === aktif.penugasan_id ? "✓ " : ""}
                  {NAMA_PERAN[p.peran]}
                  {p.prodi ? ` — ${p.prodi.nama}` : ""}
                </button>
              ))}
              <hr className="divider" style={{ margin: "0.3rem 0" }} />
            </>
          )}
          <Link to="/profil" className="menu__item" onClick={() => setBuka(false)}>Ganti kata sandi</Link>
          <button className="menu__item" onClick={() => keluar()}>Keluar</button>
        </div>
      )}
    </div>
  );
}

export function AppShell() {
  const { aktif } = useAuth();
  const [terbuka, setTerbuka] = useState(false);
  const loc = useLocation();
  useEffect(() => setTerbuka(false), [loc.pathname]);
  if (!aktif) return null;
  return (
    <div className="shell">
      <aside className={`sidebar${terbuka ? " is-open" : ""}`} aria-label="Navigasi utama">
        <Link to="/" className="brand">
          <Logo />
          <span className="brand__text">
            <strong>SIMAK</strong>
            <small>Manajemen Akreditasi</small>
          </span>
        </Link>
        {NAVIGASI.map((g) => {
          const item = g.item.filter((i) => i.peran.includes(aktif.peran));
          if (!item.length) return null;
          return (
            <div className="nav-group" key={g.judul}>
              <div className="nav-group__title">{g.judul}</div>
              {item.map((i) => (
                <NavLink key={i.to} to={i.to} end={!i.awalan} className={({ isActive }) => `nav-link${isActive ? " is-active" : ""}`}>
                  <Icon name={i.ikon} />
                  {i.label}
                </NavLink>
              ))}
            </div>
          );
        })}
        <div className="sidebar__foot">
          {aktif.instrumen ? (
            <>
              Instrumen aktif: <strong>{namaLam(aktif.instrumen.lam)}</strong> {aktif.instrumen.kode_versi ?? "(belum aktif)"}
            </>
          ) : (
            "UPPS — lintas program studi"
          )}
        </div>
      </aside>
      {terbuka && <div className="scrim" onClick={() => setTerbuka(false)} />}
      <div className="main">
        <header className="topbar">
          <Button variant="ghost" size="icon" className="topbar__menu" onClick={() => setTerbuka(true)} aria-label="Buka menu">
            <Icon name="menu" />
          </Button>
          <div className="topbar__ctx">
            <strong>{aktif.prodi ? `Program Studi ${aktif.prodi.nama}` : "Fakultas"}</strong>
            <span>{aktif.instrumen ? `${namaLam(aktif.instrumen.lam)} · versi ${aktif.instrumen.kode_versi ?? "—"}` : NAMA_PERAN[aktif.peran]}</span>
          </div>
          <span className="spacer" />
          <Notifikasi />
          <MenuPengguna />
        </header>
        <main className="page" key={loc.pathname}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
