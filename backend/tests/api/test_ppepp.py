import pytest

from tests.fabrik import tahun_akademik

pytestmark = pytest.mark.db


@pytest.fixture
async def katalog(dunia):
    ta = await tahun_akademik()
    st = (await dunia.post("sf", "/standar-spm", json={"kode": "STD-PEN", "nama": "Standar Penelitian", "kategori": "penelitian"})).json()
    b = (
        await dunia.post(
            "sf",
            f"/standar-spm/{st['id']}/butir",
            json={
                "nomor": "STD-PEN-03",
                "pernyataan": "Setiap dosen tetap menghasilkan publikasi ilmiah.",
                "indikator": "Publikasi jurnal per dosen tetap per tahun",
                "satuan": "publikasi/dosen/tahun",
            },
        )
    ).json()
    return {"ta": ta, "standar": st["id"], "butir": b["id"]}


def penetapan(katalog, **kw):
    return {
        "butir_standar_id": katalog["butir"],
        "nomor_butir": "STD-PEN-03",
        "isi": "Setiap dosen tetap menghasilkan publikasi ilmiah.",
        "indikator": "Publikasi per dosen per tahun",
        "target_nilai": 1.0,
        "target_satuan": "publikasi/dosen/tahun",
        **kw,
    }


async def siklus(dunia, katalog, nama="PPEPP 2025/2026"):
    r = await dunia.post(
        "dekan",
        "/siklus-ppepp",
        json={"nama": nama, "tahun_akademik_id": str(katalog["ta"][-1]), "tanggal_mulai": "2025-08-01", "tanggal_selesai": "2026-07-31"},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_katalog_dikelola_staf_fakultas_dan_divalidasi_dekan_us_c1(dunia, katalog):
    assert (await dunia.post("k_kimia", "/standar-spm", json={"kode": "X", "nama": "Standar X"})).status_code == 403
    sk = await siklus(dunia, katalog)
    # standar yang belum divalidasi Dekan tidak dapat dipakai pada Penetapan
    r = await dunia.post("dekan", f"/siklus-ppepp/{sk['id']}/penetapan", json=penetapan(katalog))
    assert r.status_code == 422
    assert (await dunia.post("sf", f"/standar-spm/{katalog['standar']}/validasi")).status_code == 403
    assert (await dunia.post("dekan", f"/standar-spm/{katalog['standar']}/validasi")).status_code == 200
    assert (await dunia.post("dekan", f"/siklus-ppepp/{sk['id']}/penetapan", json=penetapan(katalog))).status_code == 201
    # mengubah katalog membuat validasi dicabut
    (await dunia.patch("sf", f"/butir-standar/{katalog['butir']}", json={"indikator": "Indikator baru"})).raise_for_status()
    cat = next(s for s in (await dunia.get("dekan", "/standar-spm")).json() if s["id"] == katalog["standar"])
    assert cat["divalidasi_pada"] is None


async def test_penetapan_oleh_dekan_lalu_prodi_mengisi_tahapan_p2_p5_us_c2(dunia, katalog, prodi_id):
    (await dunia.post("dekan", f"/standar-spm/{katalog['standar']}/validasi")).raise_for_status()
    sk = await siklus(dunia, katalog)
    r = await dunia.post("dekan", f"/siklus-ppepp/{sk['id']}/penetapan", json=penetapan(katalog))
    pid = r.json()["id"]
    assert r.json()["status"] == "draf" and r.json()["baseline_nilai"] is None
    # prodi hanya melihat butir yang sudah ditetapkan Dekan
    assert (await dunia.get("k_kimia", f"/siklus-ppepp/{sk['id']}/penetapan")).json() == []
    assert (await dunia.post("k_kimia", f"/siklus-ppepp/{sk['id']}/tetapkan")).status_code == 403
    r = await dunia.post("dekan", f"/siklus-ppepp/{sk['id']}/tetapkan")
    assert (
        r.status_code == 200 and r.json()["butir_ditetapkan"] == 1 and r.json()["tahapan_dibuat"] == 12
    )  # 4 tahap × 3 prodi (butir berlaku untuk semua prodi)
    assert (await dunia.post("dekan", f"/siklus-ppepp/{sk['id']}/tetapkan")).status_code == 422  # tidak ada lagi draf
    assert len((await dunia.get("k_kimia", f"/siklus-ppepp/{sk['id']}/penetapan")).json()) == 1
    t = (await dunia.get("k_kimia", f"/penetapan/{pid}/tahapan")).json()
    assert t["penetapan"]["dapat_disunting"] is False and all(x["prodi_id"] for x in t["tahapan"])
    kimia = str(await prodi_id("KIMIA"))
    ev = next(x for x in t["tahapan"] if x["tahap"] == "evaluasi")
    # P1 tidak dapat diisi lewat endpoint tahapan
    assert (
        await dunia.put("k_kimia", f"/penetapan/{pid}/tahapan/penetapan?prodi_id={kimia}", json={"row_version": 1, "status": "selesai"})
    ).status_code == 422
    body = {
        "row_version": ev["row_version"],
        "status": "selesai",
        "uraian": "Evaluasi semester genap",
        "capaian_nilai": 0.8,
        "temuan": "Empat dosen belum memiliki publikasi bereputasi.",
    }
    r = await dunia.put("sp_kimia", f"/penetapan/{pid}/tahapan/evaluasi?prodi_id={kimia}", json=body)
    assert (
        r.status_code == 200
        and r.json()["selisih_target"] == pytest.approx(-0.2)
        and r.json()["saran_berikutnya"]["tahap"] == "pengendalian"
    )
    # versi usang → konflik
    assert (await dunia.put("sp_kimia", f"/penetapan/{pid}/tahapan/evaluasi?prodi_id={kimia}", json=body)).status_code == 409
    # prodi lain tidak boleh menulis tahapan KIMIA
    assert (
        await dunia.put("k_ilkom", f"/penetapan/{pid}/tahapan/evaluasi?prodi_id={kimia}", json={**body, "row_version": 2})
    ).status_code == 403
    assert (await dunia.get("k_ilkom", f"/penetapan/{pid}/tahapan?prodi_id={kimia}")).status_code == 403
    rekap = (await dunia.get("dekan", f"/siklus-ppepp/{sk['id']}/rekap")).json()
    k = next(p for p in rekap["prodi"] if p["prodi"]["kode"] == "KIMIA")
    assert k["tahap_selesai"] == 1 and k["tahap_total"] == 4 and k["butir"][0]["selisih_target"] == pytest.approx(-0.2)
    assert (await dunia.get("k_kimia", f"/siklus-ppepp/{sk['id']}/rekap")).status_code == 403


async def test_baseline_siklus_baru_dari_peningkatan_siklus_lama_ec22(dunia, katalog, prodi_id):
    (await dunia.post("dekan", f"/standar-spm/{katalog['standar']}/validasi")).raise_for_status()
    kimia = str(await prodi_id("KIMIA"))
    lama = await siklus(dunia, katalog, "PPEPP 2024/2025")
    pid = (await dunia.post("dekan", f"/siklus-ppepp/{lama['id']}/penetapan", json=penetapan(katalog, prodi_id=kimia))).json()["id"]
    (await dunia.post("dekan", f"/siklus-ppepp/{lama['id']}/tetapkan")).raise_for_status()
    t = (await dunia.get("k_kimia", f"/penetapan/{pid}/tahapan")).json()["tahapan"]
    pen = next(x for x in t if x["tahap"] == "peningkatan")
    r = await dunia.put(
        "sp_kimia",
        f"/penetapan/{pid}/tahapan/peningkatan?prodi_id={kimia}",
        json={"row_version": pen["row_version"], "status": "selesai", "capaian_nilai": 0.7},
    )
    assert r.status_code == 200
    (await dunia.post("dekan", f"/siklus-ppepp/{lama['id']}/selesai")).raise_for_status()
    assert (
        await dunia.put(
            "sp_kimia",
            f"/penetapan/{pid}/tahapan/peningkatan?prodi_id={kimia}",
            json={"row_version": 2, "status": "selesai", "capaian_nilai": 0.9},
        )
    ).status_code == 409  # siklus selesai
    baru = await siklus(dunia, katalog, "PPEPP 2025/2026")
    assert baru["siklus_sebelumnya_id"] == lama["id"]
    r = await dunia.post("dekan", f"/siklus-ppepp/{baru['id']}/penetapan", json=penetapan(katalog, prodi_id=kimia))
    assert (
        r.status_code == 201
        and float(r.json()["baseline_nilai"]) == pytest.approx(0.7)
        and r.json()["baseline_dari"]["siklus"] == "PPEPP 2024/2025"
    )


async def test_perubahan_butir_sasaran_tercatat_berversi_di_audit(dunia, katalog):
    (await dunia.post("dekan", f"/standar-spm/{katalog['standar']}/validasi")).raise_for_status()
    sk = await siklus(dunia, katalog)
    p = (await dunia.post("dekan", f"/siklus-ppepp/{sk['id']}/penetapan", json=penetapan(katalog))).json()
    r = await dunia.patch("dekan", f"/penetapan/{p['id']}", json={"row_version": 1, "target_nilai": 1.5})
    assert r.status_code == 200 and r.json()["row_version"] == 2
    assert (await dunia.patch("dekan", f"/penetapan/{p['id']}", json={"row_version": 1, "target_nilai": 2})).status_code == 409
    log = (await dunia.get("dekan", "/log-audit?aksi=penetapan.ubah")).json()["data"][0]["detail"]
    assert log["lama"]["target_nilai"] == "1.0000" or float(log["lama"]["target_nilai"]) == 1.0
    assert float(log["baru"]["target_nilai"]) == 1.5
    assert (await dunia.patch("k_kimia", f"/penetapan/{p['id']}", json={"row_version": 2, "target_nilai": 0})).status_code == 403


async def test_tahapan_terkunci_saat_laporan_menunggu_validasi(dunia, katalog, prodi_id):
    from tests.fabrik import buka_siklus, instrumen_lamsama

    (await dunia.post("dekan", f"/standar-spm/{katalog['standar']}/validasi")).raise_for_status()
    sk = await siklus(dunia, katalog)
    pid = (await dunia.post("dekan", f"/siklus-ppepp/{sk['id']}/penetapan", json=penetapan(katalog))).json()["id"]
    (await dunia.post("dekan", f"/siklus-ppepp/{sk['id']}/tetapkan")).raise_for_status()
    await instrumen_lamsama(dekan_id=dunia.id["dekan"])
    siklus_akreditasi = await buka_siklus(dunia, "KIMIA", katalog["ta"][-1])
    # kuncikan laporan secara langsung di basis data (alur ajukan sudah diuji di test_alur_laporan)
    from sqlalchemy import update

    from app.core.database import get_session_factory
    from app.modules.laporan.domain.entities import StatusLaporan
    from app.modules.laporan.infrastructure.models import Laporan

    async with get_session_factory()() as s:
        await s.execute(update(Laporan).values(status=StatusLaporan.MENUNGGU_VALIDASI))
        await s.commit()
    kimia = str(await prodi_id("KIMIA"))
    t = (await dunia.get("k_kimia", f"/penetapan/{pid}/tahapan")).json()["tahapan"]
    pel = next(x for x in t if x["tahap"] == "pelaksanaan")
    r = await dunia.put(
        "sp_kimia", f"/penetapan/{pid}/tahapan/pelaksanaan?prodi_id={kimia}", json={"row_version": pel["row_version"], "status": "berjalan"}
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "LAPORAN_TERKUNCI"
    _ = siklus_akreditasi
