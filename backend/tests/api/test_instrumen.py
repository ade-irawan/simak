import io

import pytest
from openpyxl import Workbook

from tests.fabrik import buka_siklus, instrumen_infokom, instrumen_lamsama, tahun_akademik

pytestmark = pytest.mark.db


def xlsx_instrumen(butir_ekstra: bool = False) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("kriteria")
    ws.append(["kode", "nama", "bobot", "urutan"])
    ws.append(["A", "Tata Kelola", None, 1])
    ws.append(["B", "Pendidikan", None, 2])
    ws = wb.create_sheet("butir")
    ws.append(
        [
            "kriteria",
            "kode",
            "nomor_urut",
            "elemen",
            "deskriptor",
            "jenis_ipo",
            "tahap_ppepp",
            "jenis_penilaian",
            "bobot",
            "panduan",
            "skema_narasi",
        ]
    )
    ws.append(
        ["A", "1", 1, "Indikator impor satu", None, None, None, "kualitatif", None, "Panduan", '[{"bagian":"utama","judul":"Uraian"}]']
    )
    ws.append(["B", "2", 2, "Indikator impor dua", None, None, None, "kualitatif", None, None, None])
    if butir_ekstra:
        ws.append(["Z", "9", 3, "Kriteria tak dikenal", None, None, None, None, None, None, None])
    ws = wb.create_sheet("rubrik")
    ws.append(["butir", "skor", "deskriptor"])
    ws.append(["1", 4, "Sangat baik"])
    ws = wb.create_sheet("peringkat")
    ws.append(["kode", "nama", "tingkat", "masa_berlaku_tahun", "nilai_akhir_min", "nilai_akhir_maks", "syarat"])
    ws.append(["tidak_terakreditasi", "Tidak Terakreditasi", 0, None, None, None, "{}"])
    ws.append(["terakreditasi", "Terakreditasi", 1, None, None, None, "{}"])
    ws = wb.create_sheet("ambang")
    ws.append(["butir", "peringkat", "skor_min", "is_syarat_perlu"])
    ws.append(["1", "terakreditasi", 3, "TRUE"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


FORM = {"lam_kode": "LAMSAMA", "kode_versi": "3.2", "nama": "IAPS 3.2 impor", "skor_maks": "4", "label_skor": '{"4":"Baik Sekali"}'}


async def test_impor_instrumen_sebagai_draf_lalu_aktif_setelah_disetujui_dekan_us_g5(dunia):
    assert (await dunia.post("k_kimia", "/instrumen/impor", data=FORM, files={"berkas": ("i.xlsx", xlsx_instrumen())})).status_code == 403
    assert (
        await dunia.post("dekan", "/instrumen/impor", data=FORM, files={"berkas": ("i.xlsx", xlsx_instrumen())})
    ).status_code == 403  # Dekan menyetujui, bukan menyusun
    r = await dunia.post("sf", "/instrumen/impor", data=FORM, files={"berkas": ("i.xlsx", xlsx_instrumen())})
    assert r.status_code == 202 and r.json()["butir"] == 2 and r.json()["rubrik"] == 1 and r.json()["ambang"] == 1
    vid = r.json()["id"]
    # draf tidak terlihat oleh Kaprodi dan tidak dipakai sistem
    assert all(v["id"] != vid for v in (await dunia.get("k_kimia", "/instrumen")).json())
    assert (await dunia.get("k_kimia", f"/instrumen/{vid}")).status_code == 404
    assert (await dunia.get("sf", f"/instrumen/{vid}")).json()["status"] == "draf"
    # Staf Fakultas dapat menyunting butir draf; Dekan mengaktifkan
    butir = (await dunia.get("sf", f"/instrumen/{vid}/butir")).json()
    r = await dunia.patch(
        "sf",
        f"/butir-instrumen/{butir[0]['id']}",
        json={"elemen": "Indikator satu (diperbaiki)", "rubrik": [{"skor": 4, "deskriptor": "Sangat baik sekali"}]},
    )
    assert (
        r.status_code == 200 and r.json()["elemen"].endswith("(diperbaiki)") and r.json()["rubrik"][0]["deskriptor"] == "Sangat baik sekali"
    )
    assert (await dunia.post("sf", f"/instrumen/{vid}/aktifkan")).status_code == 403
    r = await dunia.post("dekan", f"/instrumen/{vid}/aktifkan")
    assert r.status_code == 200 and r.json()["status"] == "aktif"
    # setelah aktif tidak dapat disunting lagi dan kini terlihat oleh Kaprodi
    assert (await dunia.patch("sf", f"/butir-instrumen/{butir[0]['id']}", json={"elemen": "ubah lagi"})).status_code == 409
    assert any(v["id"] == vid for v in (await dunia.get("k_kimia", "/instrumen")).json())


async def test_impor_instrumen_menolak_baris_bermasalah_seluruhnya(dunia):
    r = await dunia.post("sf", "/instrumen/impor", data=FORM, files={"berkas": ("i.xlsx", xlsx_instrumen(butir_ekstra=True))})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["lembar"] == "butir" and r.json()["error"]["details"][0]["baris"] == 4
    assert all(
        v["kode_versi"] != "3.2" for v in (await dunia.get("sf", "/instrumen")).json()
    )  # tidak ada setengah-instrumen yang tersimpan
    assert (await dunia.post("sf", "/instrumen/impor", data=FORM, files={"berkas": ("x.xlsx", b"bukan xlsx")})).status_code == 422
    assert (await dunia.get("sf", "/instrumen/impor/templat")).status_code == 200


async def test_instrumen_baru_mengarsipkan_versi_aktif_sebelumnya_dan_tidak_aktif_tanpa_butir(dunia):
    a = await instrumen_lamsama(kode="3.1-a", dekan_id=dunia.id["dekan"])
    assert (await dunia.get("sf", "/instrumen")).json()[0]["status"] == "aktif"
    b = await instrumen_lamsama(aktif=False, kode="3.1-b", dekan_id=dunia.id["dekan"])
    assert (await dunia.post("dekan", f"/instrumen/{b['versi']}/aktifkan")).status_code == 200
    status = {v["kode_versi"]: v["status"] for v in (await dunia.get("sf", "/instrumen")).json()}
    assert status["3.1-a"] == "arsip" and status["3.1-b"] == "aktif"
    _ = a
    # versi kosong (hanya hasil seed.sql: satu butir contoh) — instrumen tanpa butir tidak dapat diaktifkan
    kosong = await dunia.post(
        "sf", "/instrumen/impor", data={**FORM, "kode_versi": "kosong"}, files={"berkas": ("i.xlsx", xlsx_instrumen())}
    )
    assert kosong.status_code == 202


async def test_aturan_pemetaan_draf_tidak_berlaku_sampai_disetujui_ec31(dunia):
    ta = await tahun_akademik()
    ins = await instrumen_lamsama(dekan_id=dunia.id["dekan"])
    sk = await buka_siklus(dunia, "KIMIA", ta[-1])
    butir2 = next(b for b in (await dunia.get("k_kimia", f"/siklus/{sk['id']}/butir")).json()["data"] if b["butir"]["kode"] == "2")["id"]
    pub = {"judul": "Judul A", "jenis": "jurnal", "tahun_terbit": 2025, "tahun_akademik_id": str(ta[-1])}
    (await dunia.post("k_kimia", "/publikasi", json=pub)).raise_for_status()
    (await dunia.post("k_kimia", "/publikasi", json={**pub, "judul": "Prosiding B", "jenis": "prosiding"})).raise_for_status()

    async def jumlah() -> int:
        return (await dunia.get("k_kimia", f"/butir-siklus/{butir2}/data")).json()["sumber"][0]["jumlah"]

    assert await jumlah() == 1  # aturan lama: hanya jurnal
    # Staf Fakultas mengubah aturan → draf; aturan lama tetap dipakai
    r = await dunia.put(
        "sf",
        f"/butir-instrumen/{ins['2']}/pemetaan",
        json=[{"sumber": "publikasi", "aturan": {"filter": {"jenis": ["jurnal", "prosiding"]}}}],
    )
    draf = [x for x in r.json() if x["status"] == "draf"]
    assert r.status_code == 200 and len(draf) == 1 and draf[0]["menggantikan_id"]
    assert await jumlah() == 1
    pid = draf[0]["id"]
    assert (await dunia.post("sf", f"/pemetaan/{pid}/setujui")).status_code == 403  # penyusun ≠ penyetuju
    assert (await dunia.post("dekan", f"/pemetaan/{pid}/setujui")).status_code == 200
    assert await jumlah() == 2  # baru berlaku setelah disetujui Dekan
    # aturan tidak sah ditolak
    r = await dunia.put("sf", f"/butir-instrumen/{ins['2']}/pemetaan", json=[{"sumber": "publikasi", "aturan": {"agregasi": "jumlah"}}])
    assert r.status_code == 422
    daftar = (await dunia.get("dekan", f"/instrumen/{ins['versi']}/pemetaan")).json()
    assert sorted(d["status"] for d in daftar if d["butir_kode"] == "2") == ["digantikan", "disetujui"]  # riwayat aturan lama tersimpan


async def test_migrasi_instrumen_memindahkan_narasi_tanpa_menghapus_ec14(dunia):
    ta = await tahun_akademik()
    v1 = await instrumen_lamsama(kode="3.1-lama", dekan_id=dunia.id["dekan"])
    sk = await buka_siklus(dunia, "KIMIA", ta[-1])
    butir = {b["butir"]["kode"]: b for b in (await dunia.get("k_kimia", f"/siklus/{sk['id']}/butir")).json()["data"]}
    (
        await dunia.put("k_kimia", f"/butir-siklus/{butir['1']['id']}/narasi/utama", json={"isi": "Narasi yang tidak boleh hilang."})
    ).raise_for_status()
    (
        await dunia.patch(
            "k_kimia", f"/butir-siklus/{butir['1']['id']}", json={"row_version": 2, "status_kelengkapan": "lengkap", "skor_estimasi": 4}
        )
    ).raise_for_status()
    v2 = await instrumen_lamsama(kode="3.2-baru", dekan_id=dunia.id["dekan"])  # aktif; butir berkode sama 1,2,3 → dipadankan
    assert v1["versi"] != v2["versi"]
    assert (
        await dunia.post("k_kimia", f"/siklus/{sk['id']}/migrasi-instrumen", json={"instrumen_versi_id": str(v2["versi"])})
    ).status_code == 403
    r = await dunia.post("dekan", f"/siklus/{sk['id']}/migrasi-instrumen", json={"instrumen_versi_id": str(v2["versi"])})
    assert r.status_code == 200 and r.json()["butir_dipetakan"] == 3 and r.json()["butir_baru"] == 0
    baru = {b["butir"]["kode"]: b for b in (await dunia.get("k_kimia", f"/siklus/{sk['id']}/butir")).json()["data"]}
    assert baru["1"]["id"] != butir["1"]["id"] and baru["1"]["status_kelengkapan"] == "lengkap"
    detail = (await dunia.get("k_kimia", f"/butir-siklus/{baru['1']['id']}")).json()
    assert detail["narasi"][0]["isi"] == "Narasi yang tidak boleh hilang."
    assert (await dunia.get("k_kimia", f"/siklus/{sk['id']}")).json()["instrumen"]["versi_id"] == str(v2["versi"])
    assert (
        await dunia.post("dekan", f"/siklus/{sk['id']}/migrasi-instrumen", json={"instrumen_versi_id": str(v2["versi"])})
    ).status_code == 422


async def test_siklus_memakai_instrumen_sesuai_lam_prodi_dan_satu_siklus_berjalan(dunia, prodi_id):
    ta = await tahun_akademik()
    await instrumen_lamsama(dekan_id=dunia.id["dekan"])
    inf = await instrumen_infokom(dekan_id=dunia.id["dekan"])
    # prodi LAMSAMA tidak boleh dipaksa memakai instrumen LAM INFOKOM
    body = {
        "prodi_id": str(await prodi_id("KIMIA")),
        "nama": "x salah",
        "ts_tahun_akademik_id": str(ta[-1]),
        "tanggal_mulai": "2026-09-01",
        "instrumen_versi_id": str(inf["versi"]),
    }
    assert (await dunia.post("dekan", "/siklus", json=body)).status_code == 422
    await buka_siklus(dunia, "KIMIA", ta[-1])
    body.pop("instrumen_versi_id")
    assert (await dunia.post("dekan", "/siklus", json=body)).status_code == 409  # satu siklus berjalan per prodi
    body["target_peringkat_kode"] = "peringkat_ngawur"
    body["prodi_id"] = str(await prodi_id("AKTUARIA"))
    assert (await dunia.post("dekan", "/siklus", json=body)).status_code == 422


async def test_penugasan_butir_dan_papan_kerja_staf_us_g3_ec27(dunia):
    ta = await tahun_akademik()
    await instrumen_lamsama(dekan_id=dunia.id["dekan"])
    sk = await buka_siklus(dunia, "KIMIA", ta[-1])
    butir = {b["butir"]["kode"]: b["id"] for b in (await dunia.get("dekan", f"/siklus/{sk['id']}/butir")).json()["data"]}
    # EC-27: semua butir mulai "belum ditugaskan", hanya Dekan yang melihat antreannya
    assert len((await dunia.get("dekan", f"/siklus/{sk['id']}/butir-belum-ditugaskan")).json()) == 3
    assert (await dunia.get("sp_kimia", f"/siklus/{sk['id']}/butir-belum-ditugaskan")).status_code == 403
    assert (await dunia.get("dekan", f"/siklus/{sk['id']}/butir?belum_ditugaskan=true")).json()["meta"]["total"] == 3
    # butir di luar kendali prodi → Staf Fakultas; Staf Prodi tidak boleh jadi penanggung jawabnya
    r = await dunia.put(
        "dekan", f"/butir-siklus/{butir['3']}/penugasan", json={"pengelola": "fakultas", "penanggung_jawab_id": str(dunia.id["sp_kimia"])}
    )
    assert r.status_code == 422
    (
        await dunia.put(
            "dekan", f"/butir-siklus/{butir['3']}/penugasan", json={"pengelola": "fakultas", "penanggung_jawab_id": str(dunia.id["sf"])}
        )
    ).raise_for_status()
    (
        await dunia.post(
            "dekan",
            f"/siklus/{sk['id']}/penugasan-massal",
            json={"butir_siklus_ids": [butir["1"], butir["2"]], "pengelola": "prodi", "penanggung_jawab_id": str(dunia.id["sp_kimia"])},
        )
    ).raise_for_status()
    papan_sp = (await dunia.get("sp_kimia", "/saya/butir")).json()
    assert {b["kode"] for b in papan_sp["ditugaskan"]} == {"1", "2"}
    papan_sf = (await dunia.get("sf", "/saya/butir")).json()
    assert {b["kode"] for b in papan_sf["ditugaskan"]} == {"3"}
    assert (await dunia.get("dekan", f"/siklus/{sk['id']}/butir-belum-ditugaskan")).json() == []
    # penugasan memberi hak tulis ¹: SF kini dapat menyunting butir 3, tetapi tidak butir 1
    b3 = (await dunia.get("sf", f"/butir-siklus/{butir['3']}")).json()
    assert b3["dapat_disunting"] is True
    assert (
        await dunia.patch("sf", f"/butir-siklus/{butir['3']}", json={"row_version": b3["row_version"], "status_kelengkapan": "draft"})
    ).status_code == 200
    b1 = (await dunia.get("sf", f"/butir-siklus/{butir['1']}")).json()
    assert (
        b1["dapat_disunting"] is False
        and (await dunia.patch("sf", f"/butir-siklus/{butir['1']}", json={"row_version": b1["row_version"], "catatan": "x"})).status_code
        == 403
    )
    # Staf Prodi tidak dapat menyunting butir milik fakultas
    assert (await dunia.patch("sp_kimia", f"/butir-siklus/{butir['3']}", json={"row_version": 99, "catatan": "x"})).status_code == 403
    # perubahan penugasan tercatat di log audit dan notifikasi dikirim ke penanggung jawab baru
    audit = (await dunia.get("dekan", "/log-audit?aksi=butir_siklus.penugasan")).json()["meta"]["total"]
    assert audit == 3
    assert any(n["jenis"] == "butir.ditugaskan" for n in (await dunia.get("sf", "/notifikasi")).json()["data"])
