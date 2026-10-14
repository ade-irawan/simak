import pytest

from app.core.exceptions import BuktiBermasalah, KonflikStatus, LaporanBelumLengkap
from app.modules.laporan.domain.entities import FormatEkspor, JenisEkspor, StatusLaporan
from app.modules.laporan.domain.rules import StatusLaporanState, periksa_ekspor, terkunci


def test_alur_normal_ajukan_setujui():
    s = StatusLaporanState(StatusLaporan.DRAFT)
    assert s.ajukan([]) == 1 and s.status == StatusLaporan.MENUNGGU_VALIDASI
    s.setujui([])
    assert s.status == StatusLaporan.DISETUJUI


def test_ajukan_diblokir_bila_ada_masalah_ec06():
    s = StatusLaporanState(StatusLaporan.DRAFT)
    with pytest.raises(LaporanBelumLengkap) as e:
        s.ajukan([{"kode": "3", "masalah": ["status_draft"]}])
    assert e.value.details[0]["kode"] == "3" and s.status == StatusLaporan.DRAFT and s.nomor_terakhir == 0


def test_setujui_diblokir_bukti_bermasalah_ec23():
    s = StatusLaporanState(StatusLaporan.MENUNGGU_VALIDASI, 1)
    with pytest.raises(BuktiBermasalah):
        s.setujui([{"kode": "3"}])
    assert s.status == StatusLaporan.MENUNGGU_VALIDASI


def test_kembalikan_kembali_ke_draft_dan_nomor_bertambah_saat_ajukan_ulang_ec08():
    s = StatusLaporanState(StatusLaporan.DRAFT)
    s.ajukan([])
    s.kembalikan()
    assert s.status == StatusLaporan.DRAFT
    assert s.ajukan([]) == 2


@pytest.mark.parametrize(
    "awal, aksi",
    [
        (StatusLaporan.DRAFT, "setujui"),
        (StatusLaporan.DRAFT, "kembalikan"),
        (StatusLaporan.DRAFT, "buka_kembali"),
        (StatusLaporan.MENUNGGU_VALIDASI, "ajukan"),
        (StatusLaporan.MENUNGGU_VALIDASI, "buka_kembali"),
        (StatusLaporan.DISETUJUI, "ajukan"),
        (StatusLaporan.DISETUJUI, "setujui"),
        (StatusLaporan.DISETUJUI, "kembalikan"),
    ],
)
def test_transisi_ilegal_ditolak(awal, aksi):
    s = StatusLaporanState(awal)
    with pytest.raises(KonflikStatus):
        {"ajukan": lambda: s.ajukan([]), "setujui": lambda: s.setujui([]), "kembalikan": s.kembalikan, "buka_kembali": s.buka_kembali}[
            aksi
        ]()


def test_buka_kembali_dari_disetujui_ec09():
    s = StatusLaporanState(StatusLaporan.DISETUJUI, 2)
    s.buka_kembali()
    assert s.status == StatusLaporan.DRAFT


def test_penguncian():
    assert not terkunci(StatusLaporan.DRAFT)
    assert terkunci(StatusLaporan.MENUNGGU_VALIDASI) and terkunci(StatusLaporan.DISETUJUI)


def test_ekspor_final_hanya_dari_laporan_disetujui():
    periksa_ekspor(JenisEkspor.LED, FormatEkspor.DOCX, False, StatusLaporan.DRAFT)
    periksa_ekspor(JenisEkspor.LED, FormatEkspor.PDF, True, StatusLaporan.DISETUJUI)
    with pytest.raises(KonflikStatus):
        periksa_ekspor(JenisEkspor.LED, FormatEkspor.PDF, True, StatusLaporan.MENUNGGU_VALIDASI)
    with pytest.raises(KonflikStatus):
        periksa_ekspor(JenisEkspor.LED, FormatEkspor.XLSX, False, StatusLaporan.DRAFT)
