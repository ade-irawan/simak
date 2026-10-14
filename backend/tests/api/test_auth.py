import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from app.core.audit import log_audit
from app.core.database import get_session_factory
from app.modules.pengguna.infrastructure.models import Pengguna
from tests.conftest import SANDI
from tests.fabrik import instrumen_infokom, instrumen_lamsama

pytestmark = pytest.mark.db


async def aksi_audit(aksi: str) -> int:
    async with get_session_factory()() as s:
        return len((await s.execute(select(log_audit.c.id).where(log_audit.c.aksi == aksi))).all())


async def test_login_menampilkan_peran_dan_instrumen_otomatis_sesuai_prodi(dunia):
    """US-A1: instrumen mengikuti prodi (ILKOM → LAM INFOKOM; KIMIA → LAMSAMA), bukan pilihan manual."""
    await instrumen_infokom(dekan_id=dunia.id["dekan"])
    await instrumen_lamsama(dekan_id=dunia.id["dekan"])
    r = await dunia.get("k_ilkom", "/auth/me")
    assert r.status_code == 200
    peran = r.json()["peran"][0]
    assert peran["peran"] == "kaprodi" and peran["prodi"]["kode"] == "ILKOM"
    assert peran["instrumen"] == {"lam": "LAM_INFOKOM", "kode_versi": "uji"}
    kimia = (await dunia.get("k_kimia", "/auth/me")).json()["peran"][0]
    assert kimia["instrumen"]["lam"] == "LAMSAMA"


async def test_endpoint_butuh_token(klien, db):
    r = await klien.get("/api/v1/auth/me")
    assert r.status_code == 401 and r.json()["error"]["code"] == "TIDAK_TERAUTENTIKASI"
    r = await klien.get("/api/v1/siklus", headers={"Authorization": "Bearer bukan-token"})
    assert r.status_code == 401


async def test_lima_gagal_mengunci_akun_lalu_admin_it_membuka_ec_us_a1(dunia, klien):
    for sisa in (4, 3, 2, 1):
        r = await klien.post("/api/v1/auth/login", json={"email": "k_ilkom@uji.test", "password": "salah-salah"})
        assert r.status_code == 401 and r.json()["error"]["details"][0]["sisa_percobaan"] == sisa
    r = await klien.post("/api/v1/auth/login", json={"email": "k_ilkom@uji.test", "password": "salah-salah"})
    assert r.status_code == 423 and r.json()["error"]["code"] == "AKUN_TERKUNCI"
    assert "terkunci_sampai" in r.json()["error"]["details"][0]
    # sandi benar pun ditolak selama terkunci
    r = await klien.post("/api/v1/auth/login", json={"email": "k_ilkom@uji.test", "password": SANDI})
    assert r.status_code == 423
    assert await aksi_audit("login.gagal") == 5 and await aksi_audit("akun.terkunci") == 1

    # Admin IT membuka kunci dan tindakan tercatat beserta alasan
    r = await dunia.post("it", f"/pengguna/{dunia.id['k_ilkom']}/buka-kunci", json={"alasan": "Identitas diverifikasi lewat telepon"})
    assert r.status_code == 200 and r.json()["jumlah_gagal_login"] == 0
    assert (await klien.post("/api/v1/auth/login", json={"email": "k_ilkom@uji.test", "password": SANDI})).status_code == 200
    assert await aksi_audit("pengguna.buka_kunci") == 1
    # Dekan tidak punya wewenang teknis ini (pemisahan Dekan vs Admin IT)
    assert (await dunia.post("dekan", f"/pengguna/{dunia.id['k_ilkom']}/buka-kunci", json={"alasan": "coba coba aja"})).status_code == 403


async def test_kunci_terbuka_otomatis_setelah_masa_tunggu(dunia, klien):
    for _ in range(5):
        await klien.post("/api/v1/auth/login", json={"email": "k_kimia@uji.test", "password": "salah-salah"})
    async with get_session_factory()() as s:
        await s.execute(
            update(Pengguna).where(Pengguna.id == dunia.id["k_kimia"]).values(terkunci_sampai=datetime.now(UTC) - timedelta(seconds=1))
        )
        await s.commit()
    assert (await klien.post("/api/v1/auth/login", json={"email": "k_kimia@uji.test", "password": SANDI})).status_code == 200


async def test_buka_kunci_mandiri_lewat_tautan_surel(dunia, klien, antrean):
    for _ in range(5):
        await klien.post("/api/v1/auth/login", json={"email": "k_kimia@uji.test", "password": "x" * 11})
    # selalu 202 — tidak membocorkan apakah email terdaftar
    assert (await klien.post("/api/v1/auth/buka-kunci/minta", json={"email": "tidak.ada@uji.test"})).status_code == 202
    assert (await klien.post("/api/v1/auth/buka-kunci/minta", json={"email": "k_kimia@uji.test"})).status_code == 202
    surel = [a for n, a in antrean if n == "simak.kirim_surel"]
    assert len(surel) == 1 and surel[0][0] == "k_kimia@uji.test"
    token = re.search(r"token=([\w-]+)", surel[0][2]).group(1)
    assert (await klien.post("/api/v1/auth/buka-kunci", json={"token": token})).status_code == 204
    assert (await klien.post("/api/v1/auth/login", json={"email": "k_kimia@uji.test", "password": SANDI})).status_code == 200
    # token sekali pakai
    assert (await klien.post("/api/v1/auth/buka-kunci", json={"token": token})).status_code == 400


async def test_refresh_dirotasi_dan_pemakaian_ulang_dicabut(dunia, klien):
    r = await klien.post("/api/v1/auth/login", json={"email": "k_ilkom@uji.test", "password": SANDI})
    set_cookie = r.headers["set-cookie"]
    assert "HttpOnly" in set_cookie and "SameSite=strict" in set_cookie.replace("Strict", "strict")
    lama = klien.cookies.get("simak_refresh")
    r2 = await klien.post("/api/v1/auth/refresh")
    assert r2.status_code == 200 and r2.json()["access_token"]
    baru = klien.cookies.get("simak_refresh")
    assert baru and baru != lama
    # memakai token lama lagi = pencurian → seluruh sesi dicabut
    klien.cookies.set("simak_refresh", lama, path="/api/v1/auth")
    assert (await klien.post("/api/v1/auth/refresh")).status_code == 401
    klien.cookies.set("simak_refresh", baru, path="/api/v1/auth")
    assert (await klien.post("/api/v1/auth/refresh")).status_code == 401


async def test_ganti_sandi_dan_reset(dunia, klien):
    r = await dunia.put("k_ilkom", "/auth/sandi", json={"sandi_lama": "salah", "sandi_baru": "Baru-Sekali-9"})
    assert r.status_code == 422
    r = await dunia.put("k_ilkom", "/auth/sandi", json={"sandi_lama": SANDI, "sandi_baru": "pendek"})
    assert r.status_code == 422
    assert (await dunia.put("k_ilkom", "/auth/sandi", json={"sandi_lama": SANDI, "sandi_baru": "Baru-Sekali-9"})).status_code == 204
    assert (await klien.post("/api/v1/auth/login", json={"email": "k_ilkom@uji.test", "password": "Baru-Sekali-9"})).status_code == 200


async def test_asesor_di_luar_jendela_ditolak_dan_dicatat_ec26(dunia, klien):
    sekarang = datetime.now(UTC)
    await dunia.akun("asesor", "asesor", "KIMIA", berlaku=(sekarang - timedelta(days=5), sekarang - timedelta(days=1)))
    r = await klien.post("/api/v1/auth/login", json={"email": "asesor@uji.test", "password": SANDI})
    assert r.status_code == 403 and r.json()["error"]["code"] == "AKSES_DITOLAK"
    assert await aksi_audit("akses.ditolak") == 1  # dicatat sekali (tidak ganda)
