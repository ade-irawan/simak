import io

import pytest
from openpyxl import Workbook

from tests.fabrik import tahun_akademik

pytestmark = pytest.mark.db


@pytest.fixture
async def ta(dunia):
    return str((await tahun_akademik())[-1])


def pub(ta, **kw):
    return {
        "judul": "Sintesis Katalis Heterogen Berbasis Zeolit",
        "jenis": "jurnal",
        "tahun_terbit": 2025,
        "tahun_akademik_id": ta,
        "doi": "10.1000/jcr.2025.0142",
        **kw,
    }


async def test_doi_sama_selalu_ditolak_dan_judul_mirip_dapat_dilewati_ec03(dunia, ta):
    r = await dunia.post("k_kimia", "/publikasi", json=pub(ta))
    assert r.status_code == 201 and r.json()["status_data"] == "draft" and r.json()["row_version"] == 1
    asli = r.json()["id"]
    # DOI sama (beda huruf besar/kecil) → 409 DUPLIKAT dengan kandidat
    r = await dunia.post("k_kimia", "/publikasi", json=pub(ta, doi="10.1000/JCR.2025.0142", judul="Judul berbeda sama sekali"))
    assert r.status_code == 409 and r.json()["error"]["code"] == "DUPLIKAT"
    assert r.json()["error"]["details"][0]["alasan"] == "doi_sama" and r.json()["error"]["details"][0]["id"] == asli
    assert (
        await dunia.post("k_kimia", "/publikasi?abaikan_kemiripan=true", json=pub(ta, doi="10.1000/JCR.2025.0142", judul="Lain"))
    ).status_code == 409  # DOI tak bisa dilewati
    # judul sama tetapi DOI berbeda → peringatan kemiripan, dapat dilewati
    r = await dunia.post("k_kimia", "/publikasi", json=pub(ta, doi="10.1000/lain"))
    assert r.status_code == 409 and r.json()["error"]["details"][0]["alasan"] == "judul_mirip"
    assert (await dunia.post("k_kimia", "/publikasi?abaikan_kemiripan=true", json=pub(ta, doi="10.1000/lain"))).status_code == 201


async def test_gabung_publikasi_menyatukan_catatan_ec03(dunia, ta):
    a = (await dunia.post("k_kimia", "/publikasi", json=pub(ta))).json()["id"]
    b = (
        await dunia.post(
            "k_kimia", "/publikasi?abaikan_kemiripan=true", json=pub(ta, doi=None, nama_media="Jurnal Penyatu", jumlah_sitasi=9)
        )
    ).json()["id"]
    r = await dunia.post("k_kimia", f"/publikasi/{a}/gabung", json={"sumber_id": b})
    assert r.status_code == 200 and r.json()["nama_media"] == "Jurnal Penyatu" and r.json()["jumlah_sitasi"] == 9
    assert (
        await dunia.get("k_kimia", f"/publikasi/{b}")
    ).status_code == 404  # catatan sumber hilang → tidak ada dua record untuk satu objek
    assert (await dunia.get("k_kimia", "/publikasi")).json()["meta"]["total"] == 1
    assert (await dunia.post("sp_kimia", f"/publikasi/{a}/gabung", json={"sumber_id": b})).status_code == 403  # hanya Kaprodi


async def test_penguncian_optimistik_ec10(dunia, ta):
    obj = (await dunia.post("k_kimia", "/publikasi", json=pub(ta))).json()
    r = await dunia.patch("sp_kimia", f"/publikasi/{obj['id']}", json={"row_version": 1, "jumlah_sitasi": 3})
    assert r.status_code == 200 and r.json()["row_version"] == 2
    r = await dunia.patch("k_kimia", f"/publikasi/{obj['id']}", json={"row_version": 1, "jumlah_sitasi": 99})
    assert r.status_code == 409 and r.json()["error"]["code"] == "KONFLIK_VERSI"
    assert r.json()["error"]["details"][0]["row_version"] == 2 and r.json()["error"]["details"][0]["data"]["jumlah_sitasi"] == 3
    assert (await dunia.get("k_kimia", f"/publikasi/{obj['id']}")).json()["jumlah_sitasi"] == 3
    # perubahan membatalkan verifikasi sebelumnya
    (await dunia.post("k_kimia", f"/publikasi/{obj['id']}/verifikasi")).raise_for_status()
    assert (await dunia.get("k_kimia", f"/publikasi/{obj['id']}")).json()["status_data"] == "terverifikasi"
    r = await dunia.patch("k_kimia", f"/publikasi/{obj['id']}", json={"row_version": 3, "jumlah_sitasi": 4})
    assert r.status_code == 200 and r.json()["status_data"] == "draft"


async def test_validasi_isian_dan_proporsi_atribusi_ec02(dunia, ta, prodi_id):
    assert (await dunia.post("k_kimia", "/publikasi", json={"judul": "x"})).status_code == 422
    r = await dunia.post("k_kimia", "/publikasi", json={"judul": ""})
    assert r.status_code == 422 and {d["kolom"] for d in r.json()["error"]["details"]} >= {
        "judul",
        "jenis",
        "tahun_terbit",
        "tahun_akademik_id",
    }
    kimia, ilkom = str(await prodi_id("KIMIA")), str(await prodi_id("ILKOM"))
    r = await dunia.post(
        "k_kimia", "/publikasi", json=pub(ta, atribusi_prodi=[{"prodi_id": kimia, "proporsi": 0.7}, {"prodi_id": ilkom, "proporsi": 0.6}])
    )
    assert r.status_code == 422
    # publikasi lintas prodi: atribusi dibagi, tercatat di kedua prodi, tanpa hitung ganda
    r = await dunia.post(
        "k_kimia", "/publikasi", json=pub(ta, atribusi_prodi=[{"prodi_id": kimia, "proporsi": 0.5}, {"prodi_id": ilkom, "proporsi": 0.5}])
    )
    assert r.status_code == 201
    assert {p["kode"] for p in r.json()["prodi"]} == {"KIMIA", "ILKOM"}
    assert (await dunia.get("k_ilkom", f"/publikasi/{r.json()['id']}")).status_code == 200  # prodi mitra ikut dapat membaca


async def test_dosen_lintas_prodi_dan_afiliasi_ec01(dunia, ta, prodi_id):
    kimia, ilkom = str(await prodi_id("KIMIA")), str(await prodi_id("ILKOM"))
    body = {
        "nama": "Dr. Lintas Prodi",
        "pendidikan_tertinggi": "s3",
        "status_kepegawaian": "tetap",
        "nidn": "0011223344",
        "afiliasi": [
            {"prodi_id": kimia, "tahun_akademik_id": ta, "jenis": "homebase", "proporsi_beban": 0.6},
            {"prodi_id": ilkom, "tahun_akademik_id": ta, "jenis": "pengampu", "proporsi_beban": 0.4},
        ],
    }
    assert (
        await dunia.post("k_kimia", "/dosen", json={k: v for k, v in body.items() if k != "afiliasi"})
    ).status_code == 422  # K/SP wajib beri afiliasi
    r = await dunia.post("k_kimia", "/dosen", json=body)
    assert r.status_code == 201
    did = r.json()["id"]
    assert len(r.json()["afiliasi"]) == 2 and {p["kode"] for p in r.json()["prodi"]} == {"KIMIA", "ILKOM"}
    assert (await dunia.post("k_kimia", "/dosen", json={**body, "nama": "Duplikat"})).status_code == 409  # NIDN sama
    assert (await dunia.get("k_ilkom", "/dosen")).json()["meta"]["total"] == 1  # tampil di kedua prodi
    # satu homebase per tahun: menambah homebase kedua ditolak
    r = await dunia.put(
        "k_ilkom", f"/dosen/{did}/afiliasi", json=[{"prodi_id": ilkom, "tahun_akademik_id": ta, "jenis": "homebase", "proporsi_beban": 0.4}]
    )
    assert r.status_code == 422
    # Staf Fakultas dapat mengelola data bersama tanpa afiliasi
    assert (
        await dunia.post("sf", "/dosen", json={"nama": "Dosen Bersama", "pendidikan_tertinggi": "s2", "status_kepegawaian": "tetap"})
    ).status_code == 201


async def test_data_bersama_sarana_hanya_staf_fakultas(dunia, ta, prodi_id):
    kimia = str(await prodi_id("KIMIA"))
    body = {"nama": "Perpustakaan Fakultas", "jenis": "perpustakaan", "is_bersama": True, "prodi_ids": [kimia]}
    assert (await dunia.post("k_kimia", "/sarana", json=body)).status_code == 403
    r = await dunia.post("sf", "/sarana", json=body)
    assert r.status_code == 201
    assert (await dunia.patch("k_kimia", f"/sarana/{r.json()['id']}", json={"row_version": 1, "jumlah": 5})).status_code == 403
    assert (await dunia.patch("sf", f"/sarana/{r.json()['id']}", json={"row_version": 1, "jumlah": 5})).status_code == 200
    # sarana milik prodi biasa boleh oleh Kaprodi
    assert (await dunia.post("k_kimia", "/sarana", json={"nama": "Lab Kimia Dasar", "jenis": "laboratorium"})).status_code == 201


async def test_keuangan_upps_hanya_staf_fakultas_dan_unik(dunia, ta, prodi_id):
    kimia = str(await prodi_id("KIMIA"))
    upps = {"tahun_akademik_id": ta, "arah": "perolehan", "kategori": "operasional", "jumlah": 1000000}
    # tanpa prodi_id: Kaprodi otomatis ke prodinya sendiri; hanya Staf Fakultas yang menghasilkan baris tingkat UPPS
    r = await dunia.post("k_kimia", "/keuangan", json=upps)
    assert r.status_code == 201 and r.json()["prodi_id"] == kimia
    assert (await dunia.post("k_kimia", "/keuangan", json={**upps, "prodi_id": str(await prodi_id("ILKOM"))})).status_code == 403
    r = await dunia.post("sf", "/keuangan", json=upps)
    assert r.status_code == 201 and r.json()["prodi_id"] is None
    assert (await dunia.post("sf", "/keuangan", json=upps)).status_code == 409  # unik per (prodi, tahun, arah, kategori)
    assert len((await dunia.get("k_kimia", "/keuangan")).json()["data"]) == 2  # Kaprodi melihat data prodi + UPPS
    assert len((await dunia.get("k_ilkom", "/keuangan")).json()["data"]) == 1  # prodi lain hanya melihat baris UPPS


async def test_impor_csv_melaporkan_baris_bermasalah_tanpa_membatalkan_yang_sah_ec17(dunia, ta, prodi_id):
    csv = (
        "tahun_akademik_id,arah,kategori,jumlah,prodi_kode\n"
        f"{ta},penggunaan,penelitian,1500000,KIMIA\n"
        f"{ta},penggunaan,pkm,bukan-angka,KIMIA\n"
        f"{ta},penggunaan,sarana,2500000,KIMIA\n"
        f"{ta},ngawur,sarana,10,KIMIA\n"
    ).encode()
    r = await dunia.post("sp_kimia", "/keuangan/impor", files={"berkas": ("keu.csv", csv, "text/csv")})
    assert r.status_code == 202
    hasil = r.json()
    assert hasil["status"] == "selesai" and hasil["baris_berhasil"] == 2
    assert {g["baris"] for g in hasil["baris_gagal"]} == {3, 5}
    assert (await dunia.get("sp_kimia", "/keuangan")).json()["meta"]["total"] == 2
    # mode atomik: satu baris salah membatalkan semuanya
    r = await dunia.post("sp_kimia", "/keuangan/impor?atomik=true", files={"berkas": ("k.csv", csv.replace(b"1500000", b"1"), "text/csv")})
    assert r.json()["status"] == "dibatalkan" and (await dunia.get("sp_kimia", "/keuangan")).json()["meta"]["total"] == 2


async def test_impor_xlsx_dan_pembatasan_peran(dunia, ta):
    wb = Workbook()
    ws = wb.active
    ws.append(["tahun_akademik_id", "arah", "kategori", "jumlah", "prodi_kode"])
    ws.append([ta, "perolehan", "hibah", 5000000, "KIMIA"])
    buf = io.BytesIO()
    wb.save(buf)
    berkas = {"berkas": ("keu.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    assert (await dunia.post("k_kimia", "/keuangan/impor", files=berkas)).status_code == 403  # impor: SP, SF (bukan Kaprodi/Dekan)
    r = await dunia.post("sp_kimia", "/keuangan/impor", files=berkas)
    assert r.json()["baris_berhasil"] == 1
    # staf prodi tidak dapat mengimpor ke prodi lain
    wb2 = Workbook()
    wb2.active.append(["tahun_akademik_id", "arah", "kategori", "jumlah", "prodi_kode"])
    wb2.active.append([ta, "perolehan", "hibah", 5, "ILKOM"])
    b2 = io.BytesIO()
    wb2.save(b2)
    r = await dunia.post("sp_kimia", "/keuangan/impor", files={"berkas": ("x.xlsx", b2.getvalue(), "application/octet-stream")})
    assert r.json()["baris_berhasil"] == 0 and r.json()["baris_gagal"]


async def test_kurikulum_dan_mata_kuliah(dunia, prodi_id):
    kimia = str(await prodi_id("KIMIA"))
    kur = (await dunia.post("sp_kimia", "/kurikulum", json={"prodi_id": kimia, "nama": "Kurikulum 2024", "tahun_berlaku": 2024})).json()
    r = await dunia.post(
        "sp_kimia", f"/kurikulum/{kur['id']}/mata-kuliah", json={"kode": "KIM101", "nama": "Kimia Dasar", "sks": 3, "semester": 1}
    )
    assert r.status_code == 201
    assert (
        await dunia.post("sp_kimia", f"/kurikulum/{kur['id']}/mata-kuliah", json={"kode": "KIM101", "nama": "Duplikat", "sks": 3})
    ).status_code == 422
    assert len((await dunia.get("k_kimia", f"/kurikulum/{kur['id']}/mata-kuliah")).json()) == 1
    assert (await dunia.get("k_ilkom", f"/kurikulum/{kur['id']}/mata-kuliah")).status_code == 403
    assert (
        await dunia.post("k_ilkom", f"/kurikulum/{kur['id']}/mata-kuliah", json={"kode": "X", "nama": "Xx", "sks": 1})
    ).status_code == 403


async def test_penelitian_pkm_tersimpan_dengan_dosen_dan_ketua_tunggal(dunia, ta, prodi_id):
    kimia = str(await prodi_id("KIMIA"))
    d1 = (
        await dunia.post(
            "sp_kimia",
            "/dosen",
            json={
                "nama": "Dosen Satu",
                "pendidikan_tertinggi": "s3",
                "status_kepegawaian": "tetap",
                "afiliasi": [{"prodi_id": kimia, "tahun_akademik_id": ta}],
            },
        )
    ).json()["id"]
    d2 = (
        await dunia.post(
            "sp_kimia",
            "/dosen",
            json={
                "nama": "Dosen Dua",
                "pendidikan_tertinggi": "s3",
                "status_kepegawaian": "tetap",
                "afiliasi": [{"prodi_id": kimia, "tahun_akademik_id": ta}],
            },
        )
    ).json()["id"]
    body = {
        "judul": "Penelitian katalis hijau",
        "tahun_akademik_id": ta,
        "sumber_dana": "dalam_negeri",
        "jumlah_dana": 75000000,
        "dosen": [{"dosen_id": d1, "peran": "ketua"}, {"dosen_id": d2, "peran": "ketua"}],
    }
    assert (await dunia.post("k_kimia", "/penelitian", json=body)).status_code == 422
    body["dosen"][1]["peran"] = "anggota"
    r = await dunia.post("k_kimia", "/penelitian", json=body)
    assert r.status_code == 201 and len(r.json()["dosen"]) == 2 and r.json()["jenis"] == "penelitian"
    assert (await dunia.get("k_kimia", "/pkm")).json()["meta"]["total"] == 0  # penelitian dan PkM terpisah walau satu tabel
    assert (await dunia.get("k_kimia", "/penelitian?sumber_dana=dalam_negeri")).json()["meta"]["total"] == 1
    assert (await dunia.get("k_kimia", "/penelitian?q=katalis")).json()["meta"]["total"] == 1
    assert (await dunia.get("k_kimia", "/penelitian?q=tidakada")).json()["meta"]["total"] == 0


async def test_lampirkan_bukti_ke_data_inti_dan_peringatan_dampak_ec05(dunia, ta):
    obj = (await dunia.post("k_kimia", "/publikasi", json=pub(ta))).json()
    bukti = (
        await dunia.post(
            "sp_kimia",
            "/bukti",
            json={"jenis": "tautan", "judul": "Halaman artikel", "url": "https://doi.org/10.1000/jcr.2025.0142", "akses_tautan": "publik"},
        )
    ).json()
    r = await dunia.put("sp_kimia", f"/publikasi/{obj['id']}/bukti/{bukti['id']}")
    assert r.status_code == 200 and r.json()[0]["judul"] == "Halaman artikel"
    assert (await dunia.get("k_kimia", f"/publikasi/{obj['id']}/bukti")).json()[0]["id"] == bukti["id"]
    assert (await dunia.put("k_ilkom", f"/publikasi/{obj['id']}/bukti/{bukti['id']}")).status_code == 403
    assert (await dunia.delete("sp_kimia", f"/publikasi/{obj['id']}/bukti/{bukti['id']}")).status_code == 204
    assert (await dunia.get("k_kimia", f"/publikasi/{obj['id']}/bukti")).json() == []
    # daftar butir yang merujuk jenis data ini (kosong bila belum ada instrumen aktif dengan aturan terkait)
    assert (await dunia.get("k_kimia", f"/publikasi/{obj['id']}/butir")).status_code == 200
