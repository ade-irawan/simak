from uuid import UUID

import pytest
from sqlalchemy import select

from app.core.database import get_session_factory
from app.core.unit_of_work import UnitOfWork
from app.modules.bukti.application.layanan import LayananBukti
from app.modules.bukti.infrastructure.models import Bukti
from tests.fabrik import buka_siklus, instrumen_lamsama, tahun_akademik

pytestmark = pytest.mark.db


async def test_alur_unggah_berkas_url_sementara_lalu_daftarkan_us_b3(dunia, storage, prodi_id):
    kimia = str(await prodi_id("KIMIA"))
    r = await dunia.post(
        "sp_kimia", "/bukti/unggahan", json={"nama_berkas": "SK GPM 2025.pdf", "mime_type": "application/pdf", "ukuran_byte": 1000}
    )
    assert r.status_code == 200
    key = r.json()["objek_key"]
    assert key.startswith("bukti/") and key.endswith("SK-GPM-2025.pdf") and r.json()["url_unggah"].startswith("http")
    # berkas belum diunggah klien → pendaftaran ditolak
    body = {"jenis": "berkas", "judul": "SK Pembentukan GPM", "objek_key": key, "berlaku_untuk": [kimia], "sumber": "Fakultas"}
    assert (await dunia.post("sp_kimia", "/bukti", json=body)).status_code == 422
    storage.objek[key] = b"%PDF-1.7 isi berkas"  # klien PUT ke URL sementara
    r = await dunia.post("sp_kimia", "/bukti", json=body)
    assert r.status_code == 201 and r.json()["jenis"] == "berkas" and r.json()["ukuran_byte"] == len(storage.objek[key])
    assert r.json()["status_cek"] == "ok" and r.json()["berlaku_untuk"][0]["kode"] == "KIMIA"
    unduh = (await dunia.get("k_kimia", f"/bukti/{r.json()['id']}/unduh")).json()
    assert unduh["jenis"] == "berkas" and unduh["url"].startswith("http://storage.test/unduh/")
    # prodi lain tidak melihat bukti ini
    assert (await dunia.get("k_ilkom", f"/bukti/{r.json()['id']}")).status_code == 403
    assert (await dunia.get("k_ilkom", "/bukti")).json()["data"] == []


async def test_penolakan_unggahan_ec18(dunia, storage):
    for nama, mime, ukuran in (
        ("virus.exe", "application/x-msdownload", 100),
        ("a.pdf", "application/pdf", 26 * 1024 * 1024),
        ("a.pdf", "image/png", 100),
        ("kosong.pdf", "application/pdf", 0),
    ):
        r = await dunia.post("sp_kimia", "/bukti/unggahan", json={"nama_berkas": nama, "mime_type": mime, "ukuran_byte": ukuran})
        assert r.status_code == 422, (nama, r.text)
    # isi berkas tidak sesuai ekstensi → ditolak dan berkas dihapus dari penyimpanan
    r = await dunia.post(
        "sp_kimia", "/bukti/unggahan", json={"nama_berkas": "palsu.pdf", "mime_type": "application/pdf", "ukuran_byte": 20}
    )
    key = r.json()["objek_key"]
    storage.objek[key] = b"MZ\x90\x00 bukan pdf sebenarnya"
    r = await dunia.post("sp_kimia", "/bukti", json={"jenis": "berkas", "judul": "Berkas palsu", "objek_key": key})
    assert r.status_code == 422 and key not in storage.objek


async def test_tautan_validasi_dan_akses_terbatas_us_b3(dunia):
    for url in ("javascript:alert(1)", "ftp://server/x", "bukan url", "http://"):
        assert (await dunia.post("sp_kimia", "/bukti", json={"jenis": "tautan", "judul": "Tautan", "url": url})).status_code == 422, url
    r = await dunia.post(
        "sp_kimia",
        "/bukti",
        json={
            "jenis": "tautan",
            "judul": "Laporan AMI 2025",
            "url": "https://drive.kampus.ac.id/s/ami",
            "akses_tautan": "terbatas",
            "sumber": "SPM",
            "tanggal_dokumen": "2025-12-01",
        },
    )
    assert r.status_code == 201 and r.json()["akses_tautan"] == "terbatas" and r.json()["status_cek"] == "belum_dicek"
    assert [p["kode"] for p in r.json()["berlaku_untuk"]] == ["KIMIA"]  # bawaan: prodi pembuat
    assert (await dunia.post("sp_kimia", "/bukti", json={"jenis": "berkas", "judul": "Tanpa objek"})).status_code == 422


async def test_satu_bukti_berlaku_untuk_banyak_prodi_dan_penyuntingan(dunia, prodi_id):
    kimia, ilkom = str(await prodi_id("KIMIA")), str(await prodi_id("ILKOM"))
    r = await dunia.post(
        "sf",
        "/bukti",
        json={
            "jenis": "tautan",
            "judul": "Fasilitas laboratorium dasar",
            "url": "https://x.kampus.ac.id/lab",
            "akses_tautan": "publik",
            "berlaku_untuk": [kimia, ilkom],
        },
    )
    bid = r.json()["id"]
    assert {p["kode"] for p in r.json()["berlaku_untuk"]} == {"KIMIA", "ILKOM"}
    assert (await dunia.get("k_kimia", f"/bukti/{bid}")).status_code == 200 and (
        await dunia.get("k_ilkom", f"/bukti/{bid}")
    ).status_code == 200
    # Kaprodi tidak boleh membuat bukti atas nama prodi lain
    assert (
        await dunia.post(
            "k_kimia", "/bukti", json={"jenis": "tautan", "judul": "Bukti curang", "url": "https://a.b/c", "berlaku_untuk": [ilkom]}
        )
    ).status_code == 403
    # mengubah URL mereset status cek; versi usang ditolak
    r = await dunia.patch("sf", f"/bukti/{bid}", json={"row_version": 1, "url": "https://x.kampus.ac.id/lab-baru"})
    assert r.status_code == 200 and r.json()["status_cek"] == "belum_dicek" and r.json()["row_version"] == 2
    assert (await dunia.patch("sf", f"/bukti/{bid}", json={"row_version": 1, "judul": "usang"})).status_code == 409


async def test_link_checker_manual_dan_terjadwal_ec23(dunia, probe, antrean, prodi_id):
    kimia = str(await prodi_id("KIMIA"))
    mati = (
        await dunia.post(
            "sp_kimia",
            "/bukti",
            json={"jenis": "tautan", "judul": "Tautan mati", "url": "https://mati.kampus.ac.id/x", "akses_tautan": "publik"},
        )
    ).json()["id"]
    hidup = (
        await dunia.post(
            "sp_kimia",
            "/bukti",
            json={"jenis": "tautan", "judul": "Tautan hidup", "url": "https://hidup.kampus.ac.id/x", "akses_tautan": "publik"},
        )
    ).json()["id"]
    terbatas = (
        await dunia.post(
            "sp_kimia",
            "/bukti",
            json={"jenis": "tautan", "judul": "Tautan privat", "url": "https://privat.kampus.ac.id/x", "akses_tautan": "terbatas"},
        )
    ).json()["id"]
    probe.hasil["https://mati.kampus.ac.id/x"] = (False, 404)
    probe.hasil["https://privat.kampus.ac.id/x"] = (False, 403)
    # pemeriksaan manual: satu kegagalan langsung dilaporkan
    r = await dunia.post("sp_kimia", f"/bukti/{mati}/cek")
    assert r.json()["status_cek"] == "tidak_terjangkau" and r.json()["kode_http"] == 404
    assert (await dunia.post("sp_kimia", f"/bukti/{hidup}/cek")).json()["status_cek"] == "ok"
    assert (await dunia.post("sp_kimia", f"/bukti/{terbatas}/cek")).json()["status_cek"] == "ok"  # 403 pada tautan terbatas bukan kerusakan
    # peringatan dikirim ke Kaprodi/Staf prodi dan Staf Fakultas
    judul = [n["judul"] for n in (await dunia.get("k_kimia", "/notifikasi")).json()["data"]]
    assert "Bukti tidak terjangkau" in judul and (await dunia.get("sf", "/notifikasi")).json()["data"]
    assert (await dunia.get("k_ilkom", "/notifikasi")).json()["data"] == []
    # pemeriksaan terjadwal: butuh 3 gagal beruntun sebelum merah (hindari alarm palsu)
    probe.hasil["https://hidup.kampus.ac.id/x"] = (False, 500)
    async with get_session_factory()() as s:
        svc = LayananBukti(UnitOfWork(s), None, probe)  # type: ignore[arg-type]
        for putaran in range(3):
            row = await s.get(Bukti, UUID(hidup))
            row.dicek_pada = None
            await s.commit()
            await svc.periksa_terjadwal()
            await s.refresh(row)
            if putaran < 2:
                assert row.status_cek.value != "tidak_terjangkau", f"belum boleh merah pada kegagalan ke-{putaran + 1}"
        assert row.status_cek.value == "tidak_terjangkau" and row.gagal_beruntun == 3
    _ = kimia


async def test_hapus_bukti_hanya_kaprodi_dan_ditolak_bila_masih_dipakai(dunia):
    ta = await tahun_akademik()
    await instrumen_lamsama(dekan_id=dunia.id["dekan"])
    sk = await buka_siklus(dunia, "KIMIA", ta[-1])
    butir = (await dunia.get("k_kimia", f"/siklus/{sk['id']}/butir")).json()["data"][0]["id"]
    bid = (await dunia.post("sp_kimia", "/bukti", json={"jenis": "tautan", "judul": "Bukti A", "url": "https://a.kampus.ac.id/x"})).json()[
        "id"
    ]
    (await dunia.put("k_kimia", f"/butir-siklus/{butir}/bukti/{bid}")).raise_for_status()
    assert (await dunia.delete("sp_kimia", f"/bukti/{bid}")).status_code == 403
    assert (await dunia.delete("k_kimia", f"/bukti/{bid}")).status_code == 409  # masih ditautkan ke butir
    (await dunia.delete("k_kimia", f"/butir-siklus/{butir}/bukti/{bid}")).raise_for_status()
    assert (await dunia.delete("k_kimia", f"/bukti/{bid}")).status_code == 204
    assert (await dunia.get("k_kimia", f"/bukti/{bid}")).status_code == 404
    async with get_session_factory()() as s:
        assert (await s.execute(select(Bukti.deleted_at).where(Bukti.id == UUID(bid)))).scalar_one() is not None  # hapus lunak


async def test_bukti_tidak_boleh_ditautkan_ke_butir_prodi_yang_tidak_berlaku(dunia, prodi_id):
    ta = await tahun_akademik()
    await instrumen_lamsama(dekan_id=dunia.id["dekan"])
    sk = await buka_siklus(dunia, "KIMIA", ta[-1])
    butir = (await dunia.get("k_kimia", f"/siklus/{sk['id']}/butir")).json()["data"][0]["id"]
    ilkom = str(await prodi_id("ILKOM"))
    bid = (
        await dunia.post(
            "k_ilkom",
            "/bukti",
            json={"jenis": "tautan", "judul": "Bukti ILKOM", "url": "https://i.kampus.ac.id/x", "berlaku_untuk": [ilkom]},
        )
    ).json()["id"]
    assert (await dunia.put("k_kimia", f"/butir-siklus/{butir}/bukti/{bid}")).status_code == 403  # bukti tak terlihat oleh Kaprodi KIMIA
    assert (await dunia.put("sf", f"/butir-siklus/{butir}/bukti/{bid}")).status_code == 403  # SF belum ditugaskan pada butir ini
