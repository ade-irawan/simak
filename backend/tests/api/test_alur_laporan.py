"""Alur akreditasi end-to-end: SKPL §5 (alur besar), EC-06..09, EC-15, EC-23, EC-28/29 dan US-F3, US-H1."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select, update

from app.core.database import get_session_factory
from app.modules.bukti.domain.entities import StatusCekBukti
from app.modules.bukti.infrastructure.models import Bukti
from tests.fabrik import buka_siklus, instrumen_lamsama, tahun_akademik

pytestmark = pytest.mark.db


@pytest.fixture
async def kimia(dunia, prodi_id):
    """Siklus KIMIA (LAMSAMA kecil, 3 butir) + id prodi/tahun/butir."""
    ta = await tahun_akademik()
    ins = await instrumen_lamsama(dekan_id=dunia.id["dekan"])
    sk = await buka_siklus(dunia, "KIMIA", ta[-1], target_peringkat_kode="unggul_2")
    butir = {b["butir"]["kode"]: b for b in (await dunia.get("k_kimia", f"/siklus/{sk['id']}/butir")).json()["data"]}
    return {"sk": sk, "sid": sk["id"], "ta": ta, "ins": ins, "butir": butir, "pid": str(await prodi_id("KIMIA"))}


async def lengkapi(dunia, k, skor: dict[str, float] | None = None, who="k_kimia") -> None:
    skor = skor or {"1": 4, "2": 3, "3": 3}
    for kode, b in k["butir"].items():
        d = (await dunia.get(who, f"/butir-siklus/{b['id']}")).json()
        r = await dunia.patch(
            who,
            f"/butir-siklus/{b['id']}",
            json={"row_version": d["row_version"], "status_kelengkapan": "lengkap", "skor_estimasi": skor[kode]},
        )
        assert r.status_code == 200, r.text


async def siapkan_data_dan_dokumen(dunia, k, storage_bukti=True) -> None:
    """Memenuhi pemetaan: 1 publikasi (butir 2) + dokumen tracer dari Direktorat (butir 3)."""
    r = await dunia.post(
        "k_kimia",
        "/publikasi",
        json={
            "judul": "Sintesis katalis heterogen",
            "jenis": "jurnal",
            "tingkat": "internasional",
            "tahun_terbit": 2025,
            "tahun_akademik_id": str(k["ta"][-1]),
            "doi": "10.1000/uji.1",
        },
    )
    assert r.status_code == 201, r.text
    bk = await dunia.post(
        "sf",
        "/bukti",
        json={
            "jenis": "tautan",
            "judul": "Laporan tracer study 2025",
            "url": "https://dir.kampus.ac.id/tracer",
            "akses_tautan": "publik",
            "berlaku_untuk": [k["pid"]],
        },
    )
    assert bk.status_code == 201, bk.text
    d = await dunia.post(
        "sf",
        "/dokumen-eksternal",
        json={
            "jenis": "tracer_study",
            "judul": "Tracer 2025",
            "tahun_akademik_id": str(k["ta"][-1]),
            "populasi": 300,
            "jumlah_responden": 200,
            "bukti_id": bk.json()["id"],
            "prodi_id": [k["pid"]],
        },
    )
    assert d.status_code == 201, d.text
    r = await dunia.put(
        "sf",
        f"/dokumen-eksternal/{d.json()['id']}/indikator",
        json=[{"prodi_id": k["pid"], "kode": "masa_tunggu_bulan", "nama": "Masa tunggu", "nilai": "4.5", "satuan": "bulan"}],
    )
    assert r.status_code == 200 and r.json()["butir_dibebaskan"] == 1, r.text
    # bukti untuk butir 1
    b1 = await dunia.put("k_kimia", f"/butir-siklus/{k['butir']['1']['id']}/bukti/{bk.json()['id']}")
    assert b1.status_code == 200, b1.text


async def ajukan(dunia, k) -> Any:
    return await dunia.post("k_kimia", f"/siklus/{k['sid']}/laporan/ajukan", json={"catatan": "Pengajuan pertama."})


async def test_pra_cek_dan_ajukan_diblokir_bila_belum_lengkap_ec06_ec15(dunia, kimia):
    r = await ajukan(dunia, kimia)
    assert r.status_code == 422 and r.json()["error"]["code"] == "LAPORAN_BELUM_LENGKAP"
    masalah = {d["kode"]: d["masalah"] for d in r.json()["error"]["details"]}
    assert set(masalah) == {"1", "2", "3"}
    assert "belum_mulai" in masalah["1"]
    assert "menunggu_dokumen_eksternal" in masalah["3"]  # EC-15: menunggu dokumen Direktorat
    assert "data_kurang" in masalah["2"]  # butir 2 dipasok publikasi, belum ada data
    pra = (await dunia.get("k_kimia", f"/siklus/{kimia['sid']}/laporan/pra-cek")).json()
    assert pra["siap_diajukan"] is False and pra["jumlah_masalah"] == 3
    assert (await dunia.get("dekan", f"/siklus/{kimia['sid']}/laporan")).json()["status"] == "draft"


async def test_simpan_draf_tidak_mensyaratkan_kelengkapan_us_b4(dunia, kimia):
    b = kimia["butir"]["1"]
    r = await dunia.patch(
        "k_kimia", f"/butir-siklus/{b['id']}", json={"row_version": 1, "status_kelengkapan": "draft", "catatan": "Menunggu laporan"}
    )
    assert r.status_code == 200 and r.json()["status_kelengkapan"] == "draft" and r.json()["row_version"] == 2
    # penyimpan kedua dengan versi usang → konflik, bukan menimpa (EC-10)
    r = await dunia.patch("sp_kimia", f"/butir-siklus/{b['id']}", json={"row_version": 1, "catatan": "usang"})
    assert r.status_code in (403, 409)
    r = await dunia.patch("k_kimia", f"/butir-siklus/{b['id']}", json={"row_version": 1, "catatan": "usang"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "KONFLIK_VERSI"


async def test_data_terpetakan_satu_data_banyak_butir_us_b1(dunia, kimia):
    """Satu publikasi yang diinput sekali otomatis terpasok ke butir 2 tanpa input tambahan."""
    sebelum = (await dunia.get("k_kimia", f"/butir-siklus/{kimia['butir']['2']['id']}/data")).json()
    assert sebelum["belum_lengkap"] is True and sebelum["sumber"][0]["jumlah"] == 0
    r = await dunia.post(
        "k_kimia",
        "/publikasi",
        json={"judul": "Judul A", "jenis": "jurnal", "tahun_terbit": 2025, "tahun_akademik_id": str(kimia["ta"][-1])},
    )
    assert r.status_code == 201
    assert r.json()["butir_terkait"][0]["kode"] == "2"  # respons menyebut butir yang terpasok
    sesudah = (await dunia.get("k_kimia", f"/butir-siklus/{kimia['butir']['2']['id']}/data")).json()
    assert sesudah["sumber"][0]["jumlah"] == 1 and sesudah["belum_lengkap"] is False
    # publikasi jenis lain tidak memenuhi filter aturan (jenis = jurnal)
    await dunia.post(
        "k_kimia",
        "/publikasi",
        json={"judul": "Prosiding B", "jenis": "prosiding", "tahun_terbit": 2025, "tahun_akademik_id": str(kimia["ta"][-1])},
    )
    assert (await dunia.get("k_kimia", f"/butir-siklus/{kimia['butir']['2']['id']}/data")).json()["sumber"][0]["jumlah"] == 1
    # publikasi di luar rentang TS-2..TS tidak ikut (EC-04): tambahkan tahun baru
    async with get_session_factory()() as s:
        from datetime import date

        from app.modules.referensi.models import TahunAkademik

        lama = TahunAkademik(kode="2015/2016", tanggal_mulai=date(2015, 8, 1), tanggal_selesai=date(2016, 7, 31))
        s.add(lama)
        await s.commit()
        lama_id = lama.id
    await dunia.post(
        "k_kimia", "/publikasi", json={"judul": "Judul Lama", "jenis": "jurnal", "tahun_terbit": 2015, "tahun_akademik_id": str(lama_id)}
    )
    assert (await dunia.get("k_kimia", f"/butir-siklus/{kimia['butir']['2']['id']}/data")).json()["sumber"][0]["jumlah"] == 1


async def test_alur_lengkap_ajukan_kunci_kembalikan_setujui(dunia, kimia):
    k = kimia
    await siapkan_data_dan_dokumen(dunia, k)
    (
        await dunia.put("k_kimia", f"/butir-siklus/{k['butir']['1']['id']}/narasi/utama", json={"isi": "Narasi versi satu."})
    ).raise_for_status()
    await lengkapi(dunia, k)

    r = await ajukan(dunia, k)
    assert r.status_code == 201, r.text
    lap_id = r.json()["laporan_id"]
    assert r.json()["status"] == "menunggu_validasi" and r.json()["pengajuan"]["nomor"] == 1

    # --- EC-07: data terkunci selama menunggu validasi
    b1 = k["butir"]["1"]["id"]
    for r2 in (
        await dunia.patch("k_kimia", f"/butir-siklus/{b1}", json={"row_version": 3, "catatan": "ubah diam-diam"}),
        await dunia.put("k_kimia", f"/butir-siklus/{b1}/narasi/utama", json={"row_version": 1, "isi": "ubah diam-diam"}),
        await dunia.post(
            "k_kimia", "/publikasi", json={"judul": "Baru", "jenis": "jurnal", "tahun_terbit": 2025, "tahun_akademik_id": str(k["ta"][-1])}
        ),
    ):
        assert r2.status_code == 409 and r2.json()["error"]["code"] == "LAPORAN_TERKUNCI"
    assert (await ajukan(dunia, k)).status_code == 409  # tidak bisa mengajukan ganda
    # prodi lain tidak terdampak
    assert (
        await dunia.post(
            "k_ilkom",
            "/kerja-sama",
            json={"nama_mitra": "Mitra", "tingkat": "lokal", "judul_kegiatan": "Judul", "bidang_pkm": True, "tanggal_mulai": "2026-01-01"},
        )
    ).status_code == 201

    # --- Dekan mengembalikan dengan catatan per butir (EC-08)
    r = await dunia.post(
        "dekan",
        f"/laporan/{lap_id}/kembalikan",
        json={"catatan_umum": "Lengkapi bukti.", "catatan_butir": [{"butir_siklus_id": b1, "isi": "Bukti benchmarking belum ada."}]},
    )
    assert r.status_code == 200 and r.json()["status"] == "draft"
    catatan = (await dunia.get("k_kimia", f"/siklus/{k['sid']}/laporan/catatan")).json()
    assert {c["isi"] for c in catatan} == {"Lengkapi bukti.", "Bukti benchmarking belum ada."}
    assert (await dunia.get("k_kimia", f"/butir-siklus/{b1}")).json()["catatan_validasi"][0]["isi"] == "Bukti benchmarking belum ada."
    (
        await dunia.put("k_kimia", f"/butir-siklus/{b1}/narasi/utama", json={"row_version": 1, "isi": "Narasi versi dua (diperbaiki)."})
    ).raise_for_status()
    # riwayat pengajuan 1 tersimpan lengkap dengan cuplikan
    riwayat = (await dunia.get("k_kimia", f"/laporan/{lap_id}/pengajuan")).json()
    assert [(p["nomor"], p["keputusan"]) for p in riwayat] == [(1, "dikembalikan")]
    cup1 = (await dunia.get("k_kimia", f"/pengajuan/{riwayat[0]['id']}")).json()["cuplikan"]
    assert cup1["kriteria"][0]["butir"][0]["narasi"][0]["isi"] == "Narasi versi satu."

    # --- pengajuan ulang → nomor 2 → disetujui
    r = await ajukan(dunia, k)
    assert r.status_code == 201 and r.json()["pengajuan"]["nomor"] == 2
    r = await dunia.post("dekan", f"/laporan/{lap_id}/setujui", json={"catatan_umum": "Disetujui."})
    assert r.status_code == 200 and r.json()["status"] == "disetujui"
    # EC-09: data yang sudah disetujui tidak dapat diubah/dihapus
    assert (await dunia.patch("k_kimia", f"/butir-siklus/{b1}", json={"row_version": 5, "catatan": "x"})).status_code == 409
    assert (await dunia.post("dekan", f"/laporan/{lap_id}/setujui", json={})).status_code == 409


async def test_validasi_diblokir_bukti_tidak_terjangkau_ec23(dunia, kimia):
    k = kimia
    await siapkan_data_dan_dokumen(dunia, k)
    await lengkapi(dunia, k)
    lap_id = (await ajukan(dunia, k)).json()["laporan_id"]
    async with get_session_factory()() as s:  # link-checker menandai bukti rusak
        await s.execute(update(Bukti).values(status_cek=StatusCekBukti.TIDAK_TERJANGKAU))
        await s.commit()
    r = await dunia.post("dekan", f"/laporan/{lap_id}/setujui", json={})
    assert r.status_code == 409 and r.json()["error"]["code"] == "BUKTI_BERMASALAH"
    assert r.json()["error"]["details"][0]["kode"] == "1" and r.json()["error"]["details"][0]["bukti"]
    async with get_session_factory()() as s:
        await s.execute(update(Bukti).values(status_cek=StatusCekBukti.OK))
        await s.commit()
    assert (await dunia.post("dekan", f"/laporan/{lap_id}/setujui", json={})).status_code == 200


async def test_pengajuan_diblokir_bila_bukti_butir_bermasalah(dunia, kimia):
    k = kimia
    await siapkan_data_dan_dokumen(dunia, k)
    await lengkapi(dunia, k)
    async with get_session_factory()() as s:
        await s.execute(update(Bukti).values(status_cek=StatusCekBukti.TIDAK_TERJANGKAU))
        await s.commit()
    r = await ajukan(dunia, k)
    assert r.status_code == 422 and "bukti_tidak_terjangkau" in r.json()["error"]["details"][0]["masalah"]
    assert (await dunia.get("sf", "/siklus/" + k["sid"] + "/butir?bukti_bermasalah=true")).json()["meta"]["total"] == 1


async def laporan_disetujui(dunia, k) -> str:
    await siapkan_data_dan_dokumen(dunia, k)
    (
        await dunia.put("k_kimia", f"/butir-siklus/{k['butir']['1']['id']}/narasi/utama", json={"isi": "Narasi yang disetujui."})
    ).raise_for_status()
    await lengkapi(dunia, k)
    lap_id = (await ajukan(dunia, k)).json()["laporan_id"]
    (await dunia.post("dekan", f"/laporan/{lap_id}/setujui", json={})).raise_for_status()
    return lap_id


async def test_aktivasi_asesor_butuh_laporan_disetujui_ec28(dunia, kimia):
    await dunia.akun("asesor", "asesor_belum") if False else None
    from app.core.security import hash_sandi
    from app.modules.pengguna.infrastructure.models import Pengguna
    from tests.conftest import SANDI

    async with get_session_factory()() as s:
        p = Pengguna(email="asesor@uji.test", nama="Asesor", password_hash=hash_sandi(SANDI), wajib_ganti_sandi=False)
        s.add(p)
        await s.commit()
        asesor_id = str(p.id)
    mulai, sampai = datetime.now(UTC) - timedelta(hours=1), datetime.now(UTC) + timedelta(days=4)
    body = {
        "pengguna_id": asesor_id,
        "peran": "asesor",
        "prodi_id": kimia["pid"],
        "berlaku_mulai": mulai.isoformat(),
        "berlaku_sampai": sampai.isoformat(),
    }
    r = await dunia.post("dekan", "/penugasan-peran", json=body)
    assert r.status_code == 409 and r.json()["error"]["code"] == "LAPORAN_BELUM_DISETUJUI"
    # usulan tetap tersimpan
    usulan = (await dunia.get("dekan", "/penugasan-peran?status=diusulkan")).json()["data"]
    assert len(usulan) == 1 and usulan[0]["peran"] == "asesor"
    # Kaprodi hanya dapat mengusulkan untuk prodinya sendiri; ILKOM ditolak
    r = await dunia.post(
        "k_kimia", "/penugasan-peran", json={"pengguna_id": asesor_id, "peran": "asesor", "prodi_id": str(dunia.id["k_ilkom"])}
    )
    assert r.status_code in (403, 422)
    # setelah laporan disetujui, usulan dapat disetujui Dekan
    await laporan_disetujui(dunia, kimia)
    r = await dunia.post(
        "dekan",
        f"/penugasan-peran/{usulan[0]['id']}/setujui",
        json={"berlaku_mulai": mulai.isoformat(), "berlaku_sampai": sampai.isoformat()},
    )
    assert r.status_code == 200 and r.json()["status"] == "aktif"


async def test_asesor_membaca_versi_disetujui_readonly_dan_terisolasi(dunia, kimia):
    from app.core.security import hash_sandi
    from app.modules.pengguna.infrastructure.models import Pengguna
    from tests.conftest import SANDI

    lap_id = await laporan_disetujui(dunia, kimia)
    k = kimia
    mulai, sampai = datetime.now(UTC) - timedelta(hours=1), datetime.now(UTC) + timedelta(days=4)
    async with get_session_factory()() as s:
        p = Pengguna(email="asesor@uji.test", nama="Asesor", password_hash=hash_sandi(SANDI), wajib_ganti_sandi=False)
        s.add(p)
        await s.commit()
        dunia.id["asesor"] = p.id
    r = await dunia.post(
        "dekan",
        "/penugasan-peran",
        json={
            "pengguna_id": str(dunia.id["asesor"]),
            "peran": "asesor",
            "prodi_id": k["pid"],
            "berlaku_mulai": mulai.isoformat(),
            "berlaku_sampai": sampai.isoformat(),
        },
    )
    assert r.status_code == 201 and r.json()["status"] == "aktif"
    await dunia.masuk("asesor")

    daftar = (await dunia.get("asesor", "/asesmen/siklus")).json()["data"]
    assert len(daftar) == 1 and daftar[0]["versi_laporan"]["nomor"] == 1 and daftar[0]["butir"] == {"jumlah": 3, "sudah_ditelaah": 0}
    butir = (await dunia.get("asesor", f"/asesmen/siklus/{k['sid']}/butir")).json()
    assert [b["kode"] for kr in butir for b in kr["butir"]] == ["1", "2", "3"]
    b1 = k["butir"]["1"]["id"]
    d = (await dunia.get("asesor", f"/asesmen/butir/{b1}")).json()
    assert (
        d["narasi"][0]["isi"] == "Narasi yang disetujui."
        and d["hanya_baca"] is True
        and d["bukti"][0]["judul"] == "Laporan tracer study 2025"
    )
    r = await dunia.put("asesor", f"/asesmen/butir/{b1}/telaah", json={"sudah_ditelaah": True, "catatan": "Konfirmasi saat lapangan."})
    assert r.status_code == 200 and r.json()["sudah_ditelaah"] is True
    assert (await dunia.get("asesor", "/asesmen/siklus")).json()["data"][0]["butir"]["sudah_ditelaah"] == 1

    # --- tidak ada jalur tulis, dan tidak ada akses ke lembar kerja berjalan / modul lain (US-H1)
    for metode, path in (
        ("PATCH", f"/butir-siklus/{b1}"),
        ("PUT", f"/butir-siklus/{b1}/narasi/utama"),
        ("GET", f"/butir-siklus/{b1}"),
        ("GET", f"/siklus/{k['sid']}"),
        ("GET", "/dosen"),
        ("GET", "/publikasi"),
        ("POST", f"/siklus/{k['sid']}/laporan/ajukan"),
        ("POST", f"/laporan/{lap_id}/setujui"),
        ("GET", "/dasbor/fakultas"),
        ("GET", "/log-audit"),
        ("POST", "/siklus"),
    ):
        r = await dunia.req("asesor", metode, path, json={})
        assert r.status_code == 403, (metode, path, r.status_code)
    # --- prodi lain: tak terlihat sama sekali (EC-26)
    ta = k["ta"]
    from tests.fabrik import instrumen_infokom

    await instrumen_infokom(dekan_id=dunia.id["dekan"])
    ilkom = await buka_siklus(dunia, "ILKOM", ta[-1])
    assert (await dunia.get("asesor", f"/asesmen/siklus/{ilkom['id']}/butir")).status_code == 403
    ilkom_butir = (await dunia.get("dekan", f"/siklus/{ilkom['id']}/butir")).json()["data"][0]["id"]
    assert (await dunia.get("asesor", f"/asesmen/butir/{ilkom_butir}")).status_code == 403
    async with get_session_factory()() as s:
        from app.core.audit import log_audit

        n = len(
            (
                await s.execute(
                    select(log_audit.c.id).where(log_audit.c.aksi == "akses.ditolak", log_audit.c.pengguna_id == dunia.id["asesor"])
                )
            ).all()
        )
        baca = len((await s.execute(select(log_audit.c.id).where(log_audit.c.aksi.like("asesmen.%")))).all())
    assert n >= 10 and baca >= 3  # penolakan dan semua tindakan baca asesor tercatat

    # --- unduh bukti: hanya yang tercantum pada versi disetujui
    bukti_id = d["bukti"][0]["id"]
    assert (await dunia.get("asesor", f"/bukti/{bukti_id}/unduh")).status_code == 200
    bukti_lain = (
        await dunia.post(
            "sf",
            "/bukti",
            json={
                "jenis": "tautan",
                "judul": "Dokumen lain",
                "url": "https://x.kampus.ac.id/a",
                "akses_tautan": "publik",
                "berlaku_untuk": [],
            },
        )
    ).json()["id"]
    assert (await dunia.get("asesor", f"/bukti/{bukti_lain}/unduh")).status_code == 403

    # --- laporan dibuka kembali: peringatan asesor aktif; asesor tetap melihat versi disetujui terakhir (EC-29)
    r = await dunia.post("dekan", f"/laporan/{lap_id}/buka-kembali", json={"alasan": "Koreksi data"})
    assert r.status_code == 200 and r.json()["status"] == "draft" and "asesor aktif" in r.json()["peringatan"]
    cur = (await dunia.get("k_kimia", f"/butir-siklus/{b1}")).json()
    (
        await dunia.put(
            "k_kimia",
            f"/butir-siklus/{b1}/narasi/utama",
            json={"row_version": cur["narasi"][0]["row_version"], "isi": "Narasi BARU belum disetujui."},
        )
    ).raise_for_status()
    d2 = (await dunia.get("asesor", f"/asesmen/butir/{b1}")).json()
    assert d2["narasi"][0]["isi"] == "Narasi yang disetujui."  # perubahan baru tidak tampil ke asesor

    # --- jendela asesmen berakhir → akses otomatis hilang tanpa hapus manual (US-A2)
    async with get_session_factory()() as s:
        from app.modules.pengguna.infrastructure.models import PenugasanPeran

        t = (await s.execute(select(PenugasanPeran).where(PenugasanPeran.pengguna_id == dunia.id["asesor"]))).scalar_one()
        t.berlaku_sampai = datetime.now(UTC) - timedelta(seconds=1)
        t.berlaku_mulai = datetime.now(UTC) - timedelta(days=1)
        await s.commit()
    r = await dunia.get("asesor", "/asesmen/siklus")
    assert r.status_code == 403 and r.json()["error"]["code"] == "AKSES_DITOLAK"


async def test_ekspor_final_hanya_setelah_disetujui_us_f3_d2(dunia, kimia, antrean, storage):
    k = kimia
    r = await dunia.post("k_kimia", f"/siklus/{k['sid']}/ekspor", json={"jenis": "led", "format": "docx", "final": True})
    assert r.status_code == 409
    # draf (ber-watermark) boleh kapan saja → tugas masuk antrean 'dokumen'
    r = await dunia.post("k_kimia", f"/siklus/{k['sid']}/ekspor", json={"jenis": "led", "format": "docx", "final": False})
    assert r.status_code == 202 and r.json()["status"] == "antre"
    assert antrean[-1][0] == "simak.ekspor_dokumen" and antrean[-1][1][0] == r.json()["id"]
    # data_kuantitatif hanya xlsx
    assert (
        await dunia.post("k_kimia", f"/siklus/{k['sid']}/ekspor", json={"jenis": "data_kuantitatif", "format": "pdf"})
    ).status_code == 409
    # staf prodi lain tidak dapat meminta ekspor siklus ini
    assert (await dunia.post("sp_ilkom", f"/siklus/{k['sid']}/ekspor", json={"jenis": "led", "format": "docx"})).status_code == 403
    # hanya pemohon atau Dekan dapat melihat statusnya
    eid = r.json()["id"]
    assert (await dunia.get("k_kimia", f"/ekspor/{eid}")).status_code == 200
    assert (await dunia.get("dekan", f"/ekspor/{eid}")).status_code == 200
    assert (await dunia.get("sp_kimia", f"/ekspor/{eid}")).status_code == 403
    assert (await dunia.get("k_kimia", f"/ekspor/{eid}/unduh")).status_code == 409  # belum selesai


async def test_kaprodi_mengusulkan_asesor_untuk_prodinya_saja(dunia, kimia):
    """§3.4: Kaprodi mengusulkan, Dekan menyetujui; pencarian calon dibatasi dan usulan prodi lain tak terlihat."""
    from app.core.security import hash_sandi
    from app.modules.pengguna.infrastructure.models import Pengguna
    from tests.conftest import SANDI

    async with get_session_factory()() as s:
        calon = Pengguna(email="prof.calon@uji.test", nama="Prof. Calon Asesor", password_hash=hash_sandi(SANDI), wajib_ganti_sandi=False)
        s.add(calon)
        await s.commit()
        calon_id = str(calon.id)
    # pencarian: minimal 3 huruf; staf/pimpinan (pemegang peran lain) tidak muncul sebagai calon
    assert (await dunia.get("k_kimia", "/pengguna/calon-asesor", params={"q": "pr"})).status_code == 422
    hasil = (await dunia.get("k_kimia", "/pengguna/calon-asesor", params={"q": "uji.test"})).json()
    assert [h["email"] for h in hasil] == ["prof.calon@uji.test"]
    assert (await dunia.get("sp_kimia", "/pengguna/calon-asesor", params={"q": "calon"})).status_code == 403
    assert (await dunia.get("it", "/pengguna/calon-asesor", params={"q": "calon"})).status_code == 403

    r = await dunia.post(
        "k_kimia",
        "/penugasan-peran",
        json={"pengguna_id": calon_id, "peran": "asesor", "prodi_id": kimia["pid"], "catatan": "Asesor lapangan"},
    )
    assert r.status_code == 201 and r.json()["status"] == "diusulkan"
    assert (
        await dunia.post("k_kimia", "/penugasan-peran", json={"pengguna_id": calon_id, "peran": "asesor", "prodi_id": kimia["pid"]})
    ).status_code == 422  # tidak ganda
    ilkom = str(await _prodi_id("ILKOM"))
    assert (
        await dunia.post("k_kimia", "/penugasan-peran", json={"pengguna_id": calon_id, "peran": "asesor", "prodi_id": ilkom})
    ).status_code == 403
    # Kaprodi melihat usulan prodinya; prodi lain tidak melihatnya
    daftar = (await dunia.get("k_kimia", "/penugasan-peran")).json()["data"]
    assert [(d["peran"], d["status"]) for d in daftar] == [("asesor", "diusulkan")]
    assert (await dunia.get("k_ilkom", "/penugasan-peran")).json()["data"] == []
    assert (await dunia.get("k_kimia", "/penugasan-peran", params={"prodi_id": ilkom})).status_code == 403
    assert (await dunia.get("k_kimia", "/penugasan-peran", params={"peran": "dekan"})).status_code == 403
    assert (await dunia.get("sp_kimia", "/penugasan-peran")).status_code == 403
    # setelah diusulkan ia tidak lagi... namun tetap calon (belum memegang peran non-asesor); Dekan melihat usulannya
    assert len((await dunia.get("dekan", "/penugasan-peran", params={"status": "diusulkan"})).json()["data"]) == 1
    # Kaprodi tidak dapat menyetujui sendiri
    assert (await dunia.post("k_kimia", f"/penugasan-peran/{r.json()['id']}/setujui", json={})).status_code == 403


async def _prodi_id(kode: str):
    from app.modules.referensi.models import Prodi

    async with get_session_factory()() as s:
        return (await s.execute(select(Prodi.id).where(Prodi.kode == kode))).scalar_one()
