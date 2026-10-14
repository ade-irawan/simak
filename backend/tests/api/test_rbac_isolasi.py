"""Matriks hak akses SKPL §3.2 dan isolasi data §3.3 — dijalankan terhadap endpoint nyata."""

import pytest
from sqlalchemy import select

from app.core.audit import log_audit
from app.core.database import get_session_factory
from tests.fabrik import buka_siklus, instrumen_infokom, instrumen_lamsama, tahun_akademik

pytestmark = pytest.mark.db


@pytest.fixture
async def dua_siklus(dunia):
    ta = await tahun_akademik()
    await instrumen_infokom(dekan_id=dunia.id["dekan"])
    await instrumen_lamsama(dekan_id=dunia.id["dekan"])
    return {"ILKOM": await buka_siklus(dunia, "ILKOM", ta[-1]), "KIMIA": await buka_siklus(dunia, "KIMIA", ta[-1]), "ta": ta}


async def audit_penolakan() -> list[dict]:
    async with get_session_factory()() as s:
        return [dict(r._mapping) for r in (await s.execute(select(log_audit).where(log_audit.c.aksi == "akses.ditolak"))).all()]


async def test_kaprodi_tidak_dapat_membuka_prodi_lain_ec11_us_a2(dunia, dua_siklus):
    sid_ilkom = dua_siklus["ILKOM"]["id"]
    for path in (
        f"/siklus/{sid_ilkom}",
        f"/siklus/{sid_ilkom}/butir",
        f"/siklus/{sid_ilkom}/laporan",
        f"/dasbor/prodi/{dua_siklus['ILKOM']['prodi']['id']}",
    ):
        r = await dunia.get("k_kimia", path)
        assert r.status_code == 403, path
        assert r.json()["error"]["code"] == "AKSES_DITOLAK" and "message" in r.json()["error"]
        assert "ILKOM" not in r.text  # isi data tidak bocor
    log = await audit_penolakan()
    assert len(log) >= 4 and all(l["alasan"] if False else l["detail"]["alasan"] == "di_luar_cakupan_prodi" for l in log)


async def test_daftar_hanya_memuat_prodi_sendiri(dunia, dua_siklus):
    daftar = (await dunia.get("k_kimia", "/siklus")).json()
    assert [s["prodi"]["kode"] for s in daftar] == ["KIMIA"]
    assert {s["prodi"]["kode"] for s in (await dunia.get("dekan", "/siklus")).json()} == {"ILKOM", "KIMIA"}
    assert (await dunia.get("sp_kimia", "/siklus")).json()[0]["prodi"]["kode"] == "KIMIA"


async def test_butir_prodi_lain_ditolak_lewat_id_langsung(dunia, dua_siklus):
    butir_ilkom = (await dunia.get("dekan", f"/siklus/{dua_siklus['ILKOM']['id']}/butir")).json()["data"][0]["id"]
    assert (await dunia.get("k_kimia", f"/butir-siklus/{butir_ilkom}")).status_code == 403
    assert (await dunia.patch("k_kimia", f"/butir-siklus/{butir_ilkom}", json={"row_version": 1, "catatan": "x"})).status_code == 403
    assert (await dunia.put("k_kimia", f"/butir-siklus/{butir_ilkom}/narasi/utama", json={"isi": "x"})).status_code == 403


async def test_data_inti_terisolasi_antarprodi(dunia, dua_siklus, prodi_id):
    pid_ilkom, pid_kimia = str(await prodi_id("ILKOM")), str(await prodi_id("KIMIA"))
    ta = str(dua_siklus["ta"][-1])
    sebuah = {"statistik-mahasiswa": {"prodi_id": pid_ilkom, "tahun_akademik_id": ta, "daya_tampung": 80}}
    r = await dunia.post("k_ilkom", "/statistik-mahasiswa", json=sebuah["statistik-mahasiswa"])
    assert r.status_code == 201
    obj = r.json()["id"]
    assert (await dunia.get("k_kimia", f"/statistik-mahasiswa/{obj}")).status_code == 403
    assert (await dunia.get("k_kimia", "/statistik-mahasiswa")).json()["data"] == []
    assert (await dunia.get("k_kimia", f"/statistik-mahasiswa?prodi_id={pid_ilkom}")).status_code == 403
    # menulis ke prodi lain lewat payload
    r = await dunia.post("k_kimia", "/statistik-mahasiswa", json={**sebuah["statistik-mahasiswa"], "prodi_id": pid_ilkom})
    assert r.status_code == 403
    assert (await dunia.get("sp_kimia", f"/statistik-mahasiswa/{obj}")).status_code == 403
    assert (await dunia.get("dekan", f"/statistik-mahasiswa/{obj}")).status_code == 200
    _ = pid_kimia


async def test_admin_it_tanpa_akses_konten_pemisahan_tugas(dunia, dua_siklus):
    for path in (
        "/siklus",
        "/dosen",
        "/publikasi",
        "/bukti",
        "/dasbor/fakultas",
        f"/siklus/{dua_siklus['KIMIA']['id']}/butir",
        "/standar-spm",
        "/dokumen-eksternal",
    ):
        assert (await dunia.get("it", path)).status_code == 403, path
    # tetapi ia memang mengelola akun, pengaturan, dan melihat log audit sistem
    assert (await dunia.get("it", "/pengguna")).status_code == 200
    assert (await dunia.get("it", "/pengaturan")).status_code == 200
    assert (await dunia.get("it", "/log-audit")).status_code == 200


async def test_log_audit_untuk_it_menyamarkan_detail_konten(dunia, dua_siklus):
    await dunia.get("k_kimia", f"/siklus/{dua_siklus['ILKOM']['id']}")  # menghasilkan akses.ditolak dengan detail path
    it = (await dunia.get("it", "/log-audit?aksi=akses")).json()["data"]
    dekan = (await dunia.get("dekan", "/log-audit?aksi=akses")).json()["data"]
    assert it and dekan
    assert "path" in dekan[0]["detail"] and "path" not in it[0]["detail"]


async def test_staf_admin_tidak_dapat_menyunting_narasi_ec30(dunia, dua_siklus):
    butir = (await dunia.get("dekan", f"/siklus/{dua_siklus['KIMIA']['id']}/butir")).json()["data"][0]["id"]
    for who in ("sp_kimia", "sf", "dekan", "it"):
        r = await dunia.put(who, f"/butir-siklus/{butir}/narasi/utama", json={"isi": "coba"})
        assert r.status_code == 403, who
    # termasuk bila staf adalah penanggung jawab butir tersebut
    (
        await dunia.put(
            "dekan", f"/butir-siklus/{butir}/penugasan", json={"pengelola": "prodi", "penanggung_jawab_id": str(dunia.id["sp_kimia"])}
        )
    ).raise_for_status()
    assert (await dunia.put("sp_kimia", f"/butir-siklus/{butir}/narasi/utama", json={"isi": "coba"})).status_code == 403
    r = await dunia.put("k_kimia", f"/butir-siklus/{butir}/narasi/utama", json={"isi": "Uraian oleh Kaprodi."})
    assert r.status_code == 200 and r.json()["sumber"] == "manual" and r.json()["row_version"] == 1
    detail = (await dunia.get("sp_kimia", f"/butir-siklus/{butir}")).json()
    assert (
        detail["narasi"][0]["isi"] == "Uraian oleh Kaprodi."
        and detail["narasi_dapat_disunting"] is False
        and detail["dapat_disunting"] is True
    )
    assert (await dunia.get("k_kimia", f"/butir-siklus/{butir}")).json()["narasi_dapat_disunting"] is True


async def test_staf_tidak_dapat_submit_atau_approve_ec12(dunia, dua_siklus):
    sid = dua_siklus["KIMIA"]["id"]
    assert (await dunia.post("sp_kimia", f"/siklus/{sid}/laporan/ajukan", json={})).status_code == 403
    assert (await dunia.post("sf", f"/siklus/{sid}/laporan/ajukan", json={})).status_code == 403
    assert (await dunia.post("dekan", f"/siklus/{sid}/laporan/ajukan", json={})).status_code == 403  # SoD: Dekan bukan pengaju
    laporan_id = (await dunia.get("dekan", f"/siklus/{sid}/laporan")).json()["laporan_id"]
    for who in ("k_kimia", "sp_kimia", "sf"):
        assert (await dunia.post(who, f"/laporan/{laporan_id}/setujui", json={})).status_code == 403, who


async def test_hanya_dekan_membuka_siklus_dan_menugaskan_butir(dunia, dua_siklus, prodi_id):
    body = {
        "prodi_id": str(await prodi_id("AKTUARIA")),
        "nama": "x",
        "ts_tahun_akademik_id": str(dua_siklus["ta"][-1]),
        "tanggal_mulai": "2026-09-01",
    }
    for who in ("k_kimia", "sf", "sp_kimia", "it"):
        assert (await dunia.post(who, "/siklus", json=body)).status_code == 403, who
    butir = (await dunia.get("dekan", f"/siklus/{dua_siklus['KIMIA']['id']}/butir")).json()["data"][0]["id"]
    for who in ("k_kimia", "sf", "sp_kimia"):
        assert (await dunia.put(who, f"/butir-siklus/{butir}/penugasan", json={"pengelola": "prodi"})).status_code == 403, who


async def test_hapus_data_hanya_kaprodi_dan_hanya_draft_ec09(dunia, dua_siklus, prodi_id):
    pid = str(await prodi_id("KIMIA"))
    r = await dunia.post(
        "sp_kimia",
        "/kerja-sama",
        json={
            "nama_mitra": "Mitra A",
            "tingkat": "nasional",
            "judul_kegiatan": "Magang",
            "bidang_pendidikan": True,
            "tanggal_mulai": "2026-01-01",
            "prodi_ids": [pid],
        },
    )
    assert r.status_code == 201
    kid = r.json()["id"]
    assert (await dunia.delete("sp_kimia", f"/kerja-sama/{kid}")).status_code == 403  # staf tidak boleh menghapus
    assert (await dunia.delete("k_ilkom", f"/kerja-sama/{kid}")).status_code == 403
    (await dunia.post("k_kimia", f"/kerja-sama/{kid}/verifikasi")).raise_for_status()
    assert (await dunia.delete("k_kimia", f"/kerja-sama/{kid}")).status_code == 409  # sudah terverifikasi
    r2 = await dunia.post(
        "k_kimia",
        "/kerja-sama",
        json={
            "nama_mitra": "Mitra B",
            "tingkat": "lokal",
            "judul_kegiatan": "Riset",
            "bidang_penelitian": True,
            "tanggal_mulai": "2026-02-01",
        },
    )
    assert r2.status_code == 201
    assert (await dunia.delete("k_kimia", f"/kerja-sama/{r2.json()['id']}")).status_code == 204
    assert (await dunia.get("k_kimia", f"/kerja-sama/{r2.json()['id']}")).status_code == 404
