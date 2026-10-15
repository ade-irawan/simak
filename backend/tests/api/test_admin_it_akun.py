"""Admin IT mengelola akun: membuat pengguna beserta peran, mengatur sandi, mengelola penugasan — dengan pagar pemisahan tugas."""

import pytest
from sqlalchemy import select

from app.core.database import get_session_factory
from app.modules.referensi.models import Prodi
from tests.conftest import SANDI

pytestmark = pytest.mark.db

SANDI_BARU = "Sementara-2026!"


async def _prodi_id(kode: str) -> str:
    async with get_session_factory()() as s:
        return str((await s.execute(select(Prodi.id).where(Prodi.kode == kode))).scalar_one())


async def test_admin_it_membuat_pengguna_dengan_peran_dan_prodi(dunia, klien):
    kimia = await _prodi_id("KIMIA")
    r = await dunia.post(
        "it",
        "/pengguna",
        json={
            "nama": "Staf Baru Kimia",
            "email": "staf.baru@uji.test",
            "password_awal": SANDI_BARU,
            "penugasan": [{"peran": "staf_prodi", "prodi_id": kimia}],
        },
    )
    assert r.status_code == 201, r.text
    akun = r.json()
    assert akun["wajib_ganti_sandi"] is True
    assert [(p["peran"], p["prodi"]["kode"], p["status"]) for p in akun["peran"]] == [("staf_prodi", "KIMIA", "aktif")]
    # akun langsung dapat masuk dengan sandi awal
    assert (await klien.post("/api/v1/auth/login", json={"email": "staf.baru@uji.test", "password": SANDI_BARU})).status_code == 200
    # cakupan tetap divalidasi: staf prodi tanpa prodi ditolak; peran Dekan tidak boleh ditetapkan Admin IT
    assert (
        await dunia.post("it", "/pengguna", json={"nama": "Tanpa Prodi", "email": "x1@uji.test", "penugasan": [{"peran": "staf_prodi"}]})
    ).status_code == 422
    r = await dunia.post("it", "/pengguna", json={"nama": "Calon Dekan", "email": "x2@uji.test", "penugasan": [{"peran": "dekan"}]})
    assert r.status_code == 403
    # peran lain tetap tidak boleh membuat akun
    assert (await dunia.post("k_kimia", "/pengguna", json={"nama": "Orang Lain", "email": "x3@uji.test"})).status_code == 403


async def test_admin_it_mengelola_penugasan_tetapi_asesor_menunggu_dekan(dunia):
    kimia = await _prodi_id("KIMIA")
    akun = (await dunia.post("it", "/pengguna", json={"nama": "Dosen Tamu", "email": "tamu@uji.test", "penugasan": []})).json()
    # peran biasa langsung aktif
    r = await dunia.post("it", "/penugasan-peran", json={"pengguna_id": akun["id"], "peran": "staf_prodi", "prodi_id": kimia})
    assert r.status_code == 201 and r.json()["status"] == "aktif"
    # asesor hanya berstatus usulan; Admin IT tidak dapat menyetujuinya, Dekan yang menyetujui
    r = await dunia.post("it", "/penugasan-peran", json={"pengguna_id": akun["id"], "peran": "asesor", "prodi_id": kimia})
    assert r.status_code == 201 and r.json()["status"] == "diusulkan"
    usulan = r.json()["id"]
    assert (await dunia.post("it", f"/penugasan-peran/{usulan}/setujui", json={})).status_code == 403
    # Dekan tidak dapat ditetapkan Admin IT; daftar penugasan terbuka bagi Admin IT
    assert (await dunia.post("it", "/penugasan-peran", json={"pengguna_id": akun["id"], "peran": "dekan"})).status_code == 403
    assert (await dunia.get("it", "/penugasan-peran")).status_code == 200
    # mencabut penugasan biasa diizinkan; mencabut penugasan Dekan atau milik sendiri tidak
    aktif = next(p for p in (await dunia.get("it", f"/pengguna/{akun['id']}")).json()["peran"] if p["peran"] == "staf_prodi")
    assert (await dunia.post("it", f"/penugasan-peran/{aktif['id']}/cabut")).json()["status"] == "dicabut"
    semua = (await dunia.get("dekan", "/penugasan-peran")).json()["data"]
    punya_dekan = next(p for p in semua if p["peran"] == "dekan")
    assert (await dunia.post("it", f"/penugasan-peran/{punya_dekan['id']}/cabut")).status_code == 403
    punya_it = next(p for p in semua if p["peran"] == "admin_it")
    assert (await dunia.post("it", f"/penugasan-peran/{punya_it['id']}/cabut")).status_code == 422


async def test_admin_it_mengatur_sandi_sementara(dunia, klien):
    target = dunia.id["k_kimia"]
    r = await dunia.post("it", f"/pengguna/{target}/atur-sandi", json={"sandi_baru": "lemah"})
    assert r.status_code == 422  # kebijakan sandi tetap berlaku
    # akun dikunci dulu agar terbukti kunci ikut dibuka
    for _ in range(5):
        await klien.post("/api/v1/auth/login", json={"email": "k_kimia@uji.test", "password": "salah-salah"})
    assert (await klien.post("/api/v1/auth/login", json={"email": "k_kimia@uji.test", "password": SANDI})).status_code == 423
    assert (await dunia.post("it", f"/pengguna/{target}/atur-sandi", json={"sandi_baru": SANDI_BARU})).status_code == 204
    assert (await klien.post("/api/v1/auth/login", json={"email": "k_kimia@uji.test", "password": SANDI})).status_code == 401
    masuk = await klien.post("/api/v1/auth/login", json={"email": "k_kimia@uji.test", "password": SANDI_BARU})
    assert masuk.status_code == 200 and masuk.json()["pengguna"]["wajib_ganti_sandi"] is True
    # Dekan yang lupa sandi dapat dibantu Admin IT; ia wajib menggantinya saat masuk
    assert (await dunia.post("it", f"/pengguna/{dunia.id['dekan']}/atur-sandi", json={"sandi_baru": SANDI_BARU})).status_code == 204
    masuk = await klien.post("/api/v1/auth/login", json={"email": "dekan@uji.test", "password": SANDI_BARU})
    assert masuk.status_code == 200 and masuk.json()["pengguna"]["wajib_ganti_sandi"] is True
    # pagar: bukan untuk akun sendiri atau peran selain Admin IT
    assert (await dunia.post("it", f"/pengguna/{dunia.id['it']}/atur-sandi", json={"sandi_baru": SANDI_BARU})).status_code == 422
    assert (await dunia.post("dekan", f"/pengguna/{target}/atur-sandi", json={"sandi_baru": SANDI_BARU})).status_code == 403
    # tercatat di log audit
    from tests.api.test_auth import aksi_audit

    assert await aksi_audit("pengguna.atur_sandi") == 2


async def test_admin_it_mengganti_email_akun_mana_pun(dunia, klien):
    target = dunia.id["k_kimia"]
    # selain Admin IT ditolak; email ganda dan email yang sama ditolak
    assert (await dunia.post("dekan", f"/pengguna/{target}/atur-email", json={"email": "baru@uji.test"})).status_code == 403
    assert (await dunia.post("it", f"/pengguna/{target}/atur-email", json={"email": "dekan@uji.test"})).status_code == 422
    assert (await dunia.post("it", f"/pengguna/{target}/atur-email", json={"email": "k_kimia@uji.test"})).status_code == 422
    assert (await dunia.post("it", f"/pengguna/{target}/atur-email", json={"email": "bukan-email"})).status_code == 422
    # akun biasa, akun Dekan, dan akun sendiri semuanya boleh
    r = await dunia.post("it", f"/pengguna/{target}/atur-email", json={"email": "Baru.Kimia@Uji.test"})
    assert r.status_code == 200 and r.json()["email"] == "baru.kimia@uji.test"
    assert (await dunia.post("it", f"/pengguna/{dunia.id['dekan']}/atur-email", json={"email": "dekan.baru@uji.test"})).status_code == 200
    assert (await dunia.post("it", f"/pengguna/{dunia.id['it']}/atur-email", json={"email": "it.baru@uji.test"})).status_code == 200
    # surel lama tidak lagi bisa dipakai masuk; surel baru bisa
    assert (await klien.post("/api/v1/auth/login", json={"email": "k_kimia@uji.test", "password": SANDI})).status_code == 401
    assert (await klien.post("/api/v1/auth/login", json={"email": "baru.kimia@uji.test", "password": SANDI})).status_code == 200
    from tests.api.test_auth import aksi_audit

    assert await aksi_audit("pengguna.atur_email") == 3
