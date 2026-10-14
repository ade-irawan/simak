"""Penilai peringkat — angka ambang mengikuti SKPL US-F4."""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.instrumen.domain.entities import (
    AmbangButir,
    ButirRingkas,
    DefinisiInstrumen,
    JenisPenilaian,
    PeringkatDef,
)
from app.modules.penilaian.domain.penilai import (
    MasukanButir,
    PenilaiAmbangButir,
    PenilaiBerbobot,
    pilih_penilai,
)

D = Decimal


def peringkat_infokom() -> list[PeringkatDef]:
    syarat = {"kriteria": ["1", "2", "3"], "rerata_kriteria_min": 3.2, "skor_butir_min": 3.0}
    return [
        PeringkatDef(uuid4(), "tidak_terakreditasi", "Tidak Terakreditasi", 0, None, None, D(200), {}),
        PeringkatDef(uuid4(), "terakreditasi", "Terakreditasi", 1, None, D(200), None, {}),
        PeringkatDef(uuid4(), "unggul_3", "Unggul 3", 2, 3, D(321), D(361), syarat),
        PeringkatDef(uuid4(), "unggul_5", "Unggul 5", 3, 5, D(361), None, syarat),
    ]


def definisi_infokom(bobot: dict[str, int]) -> tuple[DefinisiInstrumen, list[MasukanButir]]:
    """Tiga butir (kriteria 1,2,3) dengan bobot yang diberikan; skor diisi per uji."""
    butir = [
        ButirRingkas(uuid4(), k, i, f"e{k}", k.split(".")[0], "n", i, None, None, JenisPenilaian.KUALITATIF, D(b))
        for i, (k, b) in enumerate(bobot.items(), start=1)
    ]
    d = DefinisiInstrumen(uuid4(), "LAM_INFOKOM", "2.1", 4, D(400), butir, peringkat_infokom(), [], {"1": D(40), "2": D(120), "3": D(72)})
    return d, []


def masukan(d: DefinisiInstrumen, skor: dict[str, float | None]) -> list[MasukanButir]:
    return [
        MasukanButir(b.id, uuid4(), b.kode, b.kriteria_kode, b.bobot, None if skor[b.kode] is None else D(str(skor[b.kode])))
        for b in d.butir
    ]


def test_berbobot_nilai_akhir_dan_peringkat_dasar():
    # Σ bobot = 100 → maksimum 400. Semua skor 3 → 300 → Terakreditasi (200 ≤ 300 < 321).
    d, _ = definisi_infokom({"1.1": 30, "2.1": 40, "3.1": 30})
    h = PilihBerbobot().hitung(d, masukan(d, {"1.1": 3, "2.1": 3, "3.1": 3}), None)
    assert h.nilai_akhir == D("300.00") and h.peringkat.kode == "terakreditasi"


def PilihBerbobot() -> PenilaiBerbobot:
    return PenilaiBerbobot()


@pytest.mark.parametrize(
    "skor, kode",
    [
        (1.9, "tidak_terakreditasi"),  # 1.9 × 100 = 190 < 200
        (2.0, "terakreditasi"),  # 200 = batas bawah, inklusif
        (3.2, "terakreditasi"),  # 320 < 321
    ],
)
def test_berbobot_batas_rentang(skor, kode):
    d, _ = definisi_infokom({"1.1": 30, "2.1": 40, "3.1": 30})
    h = PenilaiBerbobot().hitung(d, masukan(d, {"1.1": skor, "2.1": skor, "3.1": skor}), None)
    assert h.peringkat.kode == kode


def test_berbobot_unggul_3_lolos_syarat():
    d, _ = definisi_infokom({"1.1": 30, "2.1": 40, "3.1": 30})
    # 3.3 × 100 = 330 ∈ [321, 361); rerata tiap kriteria 3.3 ≥ 3.2; tiap butir ≥ 3.0
    h = PenilaiBerbobot().hitung(d, masukan(d, {"1.1": 3.3, "2.1": 3.3, "3.1": 3.3}), None)
    assert h.nilai_akhir == D("330.00") and h.peringkat.kode == "unggul_3" and h.syarat_terpenuhi


def test_berbobot_unggul_5_dari_361():
    d, _ = definisi_infokom({"1.1": 30, "2.1": 40, "3.1": 30})
    h = PenilaiBerbobot().hitung(d, masukan(d, {"1.1": 3.7, "2.1": 3.7, "3.1": 3.7}), None)
    assert h.nilai_akhir == D("370.00") and h.peringkat.kode == "unggul_5"


def test_berbobot_syarat_gagal_turun_ke_terakreditasi():
    """Nilai akhir tinggi (≥321) tetapi satu kriteria di bawah rerata 3.20 → prediksi Terakreditasi, bukan Unggul."""
    d, _ = definisi_infokom({"1.1": 30, "2.1": 40, "3.1": 30})
    # 1.1=3.0 (rerata kriteria 1 = 3.0 < 3.2) ; lainnya 3.7 → nilai = 90+148+111 = 349
    h = PenilaiBerbobot().hitung(d, masukan(d, {"1.1": 3.0, "2.1": 3.7, "3.1": 3.7}), None)
    assert h.nilai_akhir == D("349.00")
    assert h.peringkat.kode == "terakreditasi"
    assert not h.syarat_terpenuhi
    assert any(s["syarat"] == "rerata_kriteria_min" and s["kriteria"] == "1" for s in h.rincian["syarat_gagal"])


def test_berbobot_skor_butir_di_bawah_minimum_menggagalkan_unggul():
    d, _ = definisi_infokom({"1.1": 15, "1.2": 15, "2.1": 40, "3.1": 30})
    # kriteria 1: rerata (2.9×15 + 3.7×15)/30 = 3.3 ≥ 3.2 namun butir 1.1 = 2.9 < 3.0
    h = PenilaiBerbobot().hitung(d, masukan(d, {"1.1": 2.9, "1.2": 3.7, "2.1": 3.7, "3.1": 3.7}), None)
    assert h.peringkat.kode == "terakreditasi"
    assert any(s["syarat"] == "skor_butir_min" and s["butir"] == "1.1" for s in h.rincian["syarat_gagal"])


def test_berbobot_butir_belum_dinilai_dihitung_nol_dan_dilaporkan():
    d, _ = definisi_infokom({"1.1": 30, "2.1": 40, "3.1": 30})
    h = PenilaiBerbobot().hitung(d, masukan(d, {"1.1": 4, "2.1": None, "3.1": 4}), None)
    assert h.butir_belum_dinilai == 1 and h.nilai_akhir == D("240.00")


# ---------------------------------------------------------------- LAMSAMA
def definisi_lamsama(toleransi: int = 0) -> DefinisiInstrumen:
    b = [ButirRingkas(uuid4(), str(i), i, f"e{i}", "A", "n", 1, None, None, JenisPenilaian.KUALITATIF, None) for i in (1, 2, 3)]
    pr = [
        PeringkatDef(uuid4(), "tidak_terakreditasi", "TT", 0, None, None, None, {}),
        PeringkatDef(uuid4(), "terakreditasi", "Terakreditasi", 1, None, None, None, {}),
        PeringkatDef(uuid4(), "unggul_2", "Unggul 2", 2, 2, None, None, {"toleransi": toleransi}),
        PeringkatDef(uuid4(), "unggul_5", "Unggul 5", 3, 5, None, None, {}),
    ]
    by = {p.kode: p for p in pr}
    ambang = []
    for butir in b:
        syarat = butir.kode == "1"
        ambang += [
            AmbangButir(butir.id, by["terakreditasi"].id, D(2), syarat),
            AmbangButir(butir.id, by["unggul_2"].id, D(3), syarat),
            AmbangButir(butir.id, by["unggul_5"].id, D(4), syarat),
        ]
    return DefinisiInstrumen(uuid4(), "LAMSAMA", "3.1", 4, None, b, pr, ambang, {"A": None})


def m_lamsama(d: DefinisiInstrumen, skor: list[float | None]) -> list[MasukanButir]:
    return [MasukanButir(b.id, uuid4(), b.kode, "A", None, None if s is None else D(str(s))) for b, s in zip(d.butir, skor, strict=True)]


def test_lamsama_dipilih_untuk_instrumen_tanpa_nilai_akhir():
    assert isinstance(pilih_penilai(definisi_lamsama()), PenilaiAmbangButir)
    d, _ = definisi_infokom({"1.1": 30})
    assert isinstance(pilih_penilai(d), PenilaiBerbobot)


@pytest.mark.parametrize(
    "skor, kode", [([4, 4, 4], "unggul_5"), ([3, 3, 3], "unggul_2"), ([2, 2, 2], "terakreditasi"), ([1, 4, 4], "tidak_terakreditasi")]
)
def test_lamsama_peringkat_menurut_ambang(skor, kode):
    d = definisi_lamsama()
    h = PenilaiAmbangButir().hitung(d, m_lamsama(d, skor), None)
    assert h.nilai_akhir is None and h.peringkat.kode == kode


def test_lamsama_syarat_perlu_menggagalkan_walau_lainnya_tinggi():
    d = definisi_lamsama()
    h = PenilaiAmbangButir().hitung(d, m_lamsama(d, [2, 4, 4]), None)  # indikator 1 (syarat perlu) hanya 2
    assert h.peringkat.kode == "terakreditasi"
    u5 = next(x for x in h.rincian["per_peringkat"] if x["kode"] == "unggul_5")
    assert not u5["tercapai"] and u5["butir_di_bawah_ambang"][0]["is_syarat_perlu"] is True


def test_lamsama_butir_belum_dinilai_dianggap_belum_memenuhi():
    d = definisi_lamsama()
    h = PenilaiAmbangButir().hitung(d, m_lamsama(d, [4, None, 4]), None)
    assert h.butir_belum_dinilai == 1 and h.peringkat.kode == "tidak_terakreditasi"


def test_lamsama_toleransi_butir_bukan_syarat_perlu():
    d = definisi_lamsama(toleransi=1)
    h = PenilaiAmbangButir().hitung(d, m_lamsama(d, [3, 2, 3]), None)  # satu butir non-syarat-perlu di bawah ambang unggul_2
    assert h.peringkat.kode == "unggul_2"
