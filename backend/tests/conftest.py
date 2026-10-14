"""Fixture bersama. Pengujian API/integrasi memakai PostgreSQL SUNGGUHAN (bukan SQLite) karena skema memakai
ENUM, indeks parsial, jsonb, citext, dan pg_trgm.

    TEST_DATABASE_URL=postgresql+asyncpg://simak:<sandi>@localhost:5432/simak_test uv run pytest

Tanpa TEST_DATABASE_URL, uji bertanda ``db`` dilewati dan uji unit tetap jalan.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import pytest

TEST_URL = os.environ.get("TEST_DATABASE_URL")
if TEST_URL:
    # Harus diatur sebelum modul aplikasi membaca Settings (lru_cache).
    os.environ["DATABASE_URL"] = TEST_URL
    os.environ.setdefault("APP_ENV", "development")
    os.environ["JWT_SECRET"] = "pengujian-" + "x" * 40
    os.environ["SMTP_HOST"] = ""

DB_DIR = Path(__file__).resolve().parents[2] / "db"
SANDI = "Sandi-Uji-2026!"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if TEST_URL:
        return
    lewati = pytest.mark.skip(reason="TEST_DATABASE_URL tidak diatur")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(lewati)


@pytest.fixture(scope="session", autouse=True)
def _hasher_cepat() -> None:
    """Argon2 berparameter ringan agar pembuatan akun per uji tidak lambat (parameter produksi tetap default)."""
    from argon2 import PasswordHasher

    import app.core.security as sec

    sec._hasher = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)
    sec.HASH_TIRUAN = sec.hash_sandi("tiruan-agar-waktu-sama")


@pytest.fixture(scope="session")
def _skema() -> None:
    """Membuat ulang skema sekali per sesi dari db/schema.sql + migrasi data konfigurasi."""
    if not TEST_URL:
        return
    import psycopg

    dsn = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        conn.execute((DB_DIR / "schema.sql").read_text(encoding="utf-8"))
        for kode, nama, satuan, deskripsi, naik in _indikator():
            conn.execute(
                "INSERT INTO indikator_inti (kode, nama, satuan, deskripsi, makin_tinggi_makin_baik) VALUES (%s,%s,%s,%s,%s)",
                (kode, nama, satuan, deskripsi, naik),
            )
        conn.execute((DB_DIR / "seed.sql").read_text(encoding="utf-8"))
        conn.execute("UPDATE fakultas SET nama = 'Fakultas Uji'")


def _indikator() -> list[tuple[str, str, str, str, bool]]:
    import importlib.util

    spec = importlib.util.spec_from_file_location("m0002", Path(__file__).resolve().parents[1] / "alembic/versions/0002_indikator_inti.py")
    modul = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(modul)  # type: ignore[union-attr]
    return modul.INDIKATOR


TABEL_DATA = (
    "log_audit notifikasi token_refresh token_akun telaah_asesor catatan_validasi ekspor_dokumen laporan_pengajuan laporan simulasi_skor "
    "bukti_tahapan_ppepp bukti_data_inti bukti_butir bukti_prodi permintaan_llm konfigurasi_llm narasi_butir butir_siklus siklus_akreditasi "
    "tahapan_ppepp penetapan_butir siklus_ppepp butir_standar_instrumen butir_standar_spm standar_spm indikator_eksternal "
    "dokumen_eksternal_prodi dokumen_eksternal bukti nilai_indikator pemetaan_butir instrumen_butir_padanan instrumen_butir_ambang "
    "instrumen_butir_rubrik instrumen_butir instrumen_peringkat instrumen_kriteria instrumen_versi "
    "kegiatan_dosen kegiatan_prodi publikasi_dosen publikasi_prodi kerja_sama_prodi sarana_prodi dosen_prodi mata_kuliah "
    "publikasi kegiatan_tridharma kerja_sama sarana_prasarana keuangan kurikulum mahasiswa_statistik lulusan_statistik dosen "
    "penugasan_peran pengguna tahun_akademik"
)


@pytest.fixture
async def db(_skema: None) -> AsyncIterator[None]:
    """Basis data bersih berisi referensi (fakultas, LAM, prodi, kerangka instrumen resmi dari seed.sql) untuk tiap uji."""
    import psycopg

    import app.models  # noqa: F401
    from app.core.database import reset_engine

    await reset_engine()
    dsn = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")  # type: ignore[union-attr]
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(f"TRUNCATE {', '.join((TABEL_DATA + ' prodi lam fakultas pengaturan_sistem').split())} RESTART IDENTITY CASCADE")
        conn.execute((DB_DIR / "seed.sql").read_text(encoding="utf-8"))
    yield
    await reset_engine()


class FakeStorage:
    """Penyimpanan berkas dalam memori (pengganti MinIO)."""

    def __init__(self) -> None:
        self.objek: dict[str, bytes] = {}

    async def pastikan_bucket(self) -> None: ...

    def url_unggah(self, objek_key: str, kedaluwarsa: Any) -> str:
        return f"http://storage.test/unggah/{objek_key}"

    def url_unduh(self, objek_key: str, nama_berkas: str | None, kedaluwarsa: Any) -> str:
        return f"http://storage.test/unduh/{objek_key}"

    async def ada(self, objek_key: str) -> bool:
        return objek_key in self.objek

    async def ukuran(self, objek_key: str) -> int | None:
        return len(self.objek[objek_key]) if objek_key in self.objek else None

    async def baca(self, objek_key: str, maks_byte: int | None = None) -> bytes:
        return self.objek[objek_key][:maks_byte] if maks_byte else self.objek[objek_key]

    async def simpan(self, objek_key: str, data: bytes, mime: str) -> None:
        self.objek[objek_key] = data

    async def hapus(self, objek_key: str) -> None:
        self.objek.pop(objek_key, None)


class FakeProbe:
    """Probe tautan terkendali: ``hasil[url] = (ada, kode_http)``; default 200."""

    def __init__(self) -> None:
        self.hasil: dict[str, tuple[bool, int | None]] = {}

    async def periksa(self, url: str) -> Any:
        from app.modules.bukti.domain.entities import HasilProbe

        ada, kode = self.hasil.get(url, (True, 200))
        return HasilProbe(ada=ada, kode_http=kode)


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> FakeStorage:
    s = FakeStorage()
    for target in ("app.modules.bukti.api.router.dapatkan_penyimpanan", "app.modules.laporan.api.router.dapatkan_penyimpanan"):
        monkeypatch.setattr(target, lambda s=s: s)
    return s


@pytest.fixture
def probe(monkeypatch: pytest.MonkeyPatch) -> FakeProbe:
    p = FakeProbe()
    monkeypatch.setattr("app.modules.bukti.api.router.HttpLinkProbe", lambda: p)
    return p


@pytest.fixture
def antrean(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, tuple[Any, ...]]]:
    """Menangkap tugas Celery yang dikirim API alih-alih menghubungi Redis."""
    terkirim: list[tuple[str, tuple[Any, ...]]] = []

    def kirim(nama: str, *args: Any, antrean: str = "default") -> str:
        terkirim.append((nama, args))
        return f"tugas-{len(terkirim)}"

    for target in (
        "app.modules.laporan.api.router.kirim_tugas",
        "app.modules.llm.api.router.kirim_tugas",
        "app.modules.notifikasi.application.penangan.kirim_tugas",
    ):
        monkeypatch.setattr(target, kirim)
    return terkirim


@pytest.fixture
async def klien(db: None, storage: FakeStorage, probe: FakeProbe, antrean: list[Any]) -> AsyncIterator[Any]:
    import httpx

    from app.main import create_app
    from app.modules.notifikasi.application.penangan import daftarkan_penangan

    daftarkan_penangan()
    transport = httpx.ASGITransport(app=create_app(), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class Dunia:
    """Pembantu pengujian: membuat akun, masuk, dan memanggil API sebagai peran tertentu."""

    def __init__(self, klien: Any):
        self.klien = klien
        self.token: dict[str, str] = {}
        self.id: dict[str, Any] = {}

    async def akun(self, nama: str, peran: str, prodi_kode: str | None = None, berlaku: tuple[Any, Any] | None = None) -> None:
        from sqlalchemy import select

        from app.core.database import get_session_factory
        from app.core.permissions import Peran
        from app.core.security import hash_sandi
        from app.modules.pengguna.infrastructure.models import Pengguna, PenugasanPeran
        from app.modules.referensi.models import Prodi

        async with get_session_factory()() as s:
            prodi_id = (await s.execute(select(Prodi.id).where(Prodi.kode == prodi_kode))).scalar_one() if prodi_kode else None
            p = Pengguna(email=f"{nama}@uji.test", nama=nama.title(), password_hash=hash_sandi(SANDI), wajib_ganti_sandi=False)
            s.add(p)
            await s.flush()
            mulai, sampai = berlaku or (None, None)
            s.add(PenugasanPeran(pengguna_id=p.id, peran=Peran(peran), prodi_id=prodi_id, berlaku_mulai=mulai, berlaku_sampai=sampai))
            await s.commit()
            self.id[nama] = p.id

    async def masuk(self, nama: str) -> str:
        r = await self.klien.post("/api/v1/auth/login", json={"email": f"{nama}@uji.test", "password": SANDI})
        assert r.status_code == 200, r.text
        self.token[nama] = r.json()["access_token"]
        return self.token[nama]

    def h(self, nama: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token[nama]}"}

    async def req(self, nama: str, metode: str, path: str, **kw: Any) -> Any:
        return await self.klien.request(metode, f"/api/v1{path}", headers=self.h(nama), **kw)

    async def get(self, nama: str, path: str, **kw: Any) -> Any:
        return await self.req(nama, "GET", path, **kw)

    async def post(self, nama: str, path: str, **kw: Any) -> Any:
        return await self.req(nama, "POST", path, **kw)

    async def put(self, nama: str, path: str, **kw: Any) -> Any:
        return await self.req(nama, "PUT", path, **kw)

    async def patch(self, nama: str, path: str, **kw: Any) -> Any:
        return await self.req(nama, "PATCH", path, **kw)

    async def delete(self, nama: str, path: str, **kw: Any) -> Any:
        return await self.req(nama, "DELETE", path, **kw)


@pytest.fixture
async def dunia(klien: Any) -> Dunia:
    """Akun standar: dekan, sf (staf fakultas), it, dan K/SP untuk ILKOM & KIMIA; semua sudah masuk."""
    d = Dunia(klien)
    spek: list[tuple[str, str, str | None]] = [
        ("dekan", "dekan", None),
        ("sf", "staf_fakultas", None),
        ("it", "admin_it", None),
        ("k_ilkom", "kaprodi", "ILKOM"),
        ("sp_ilkom", "staf_prodi", "ILKOM"),
        ("k_kimia", "kaprodi", "KIMIA"),
        ("sp_kimia", "staf_prodi", "KIMIA"),
    ]
    for nama, peran, prodi in spek:
        await d.akun(nama, peran, prodi)
        await d.masuk(nama)
    return d


@pytest.fixture
def prodi_id() -> Callable[[str], Any]:
    """Pencari id prodi menurut kode (dipanggil di dalam uji async lewat ``await``)."""

    async def cari(kode: str) -> Any:
        from sqlalchemy import select

        from app.core.database import get_session_factory
        from app.modules.referensi.models import Prodi

        async with get_session_factory()() as s:
            return (await s.execute(select(Prodi.id).where(Prodi.kode == kode))).scalar_one()

    return cari  # type: ignore[return-value]
