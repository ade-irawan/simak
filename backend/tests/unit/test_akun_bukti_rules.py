from datetime import UTC, datetime, timedelta

import pytest

from app.core.permissions import Peran
from app.modules.bukti.domain import rules as br
from app.modules.bukti.domain.entities import AksesTautan, HasilProbe, JenisBukti, StatusCekBukti
from app.modules.pengguna.domain import rules as pr

SEKARANG = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


# ---------------- kunci akun (US-A1) ----------------
def test_kunci_setelah_lima_gagal():
    sisa = 5
    n = 0
    for i in range(1, 5):
        h = pr.hitung_gagal_login(n, maks_gagal=5, menit_kunci=15, sekarang=SEKARANG)
        n = h.jumlah_gagal
        assert h.terkunci_sampai is None and h.sisa_percobaan == sisa - i
    h = pr.hitung_gagal_login(n, maks_gagal=5, menit_kunci=15, sekarang=SEKARANG)
    assert h.terkunci_sampai == SEKARANG + timedelta(minutes=15) and h.sisa_percobaan == 0


def test_kunci_terbuka_otomatis_setelah_masa_tunggu():
    sampai = SEKARANG + timedelta(minutes=15)
    assert pr.sedang_terkunci(sampai, SEKARANG)
    assert not pr.sedang_terkunci(sampai, sampai + timedelta(seconds=1))
    assert not pr.sedang_terkunci(None, SEKARANG)


def test_jendela_penugasan_asesor_berakhir_otomatis():
    mulai, sampai = SEKARANG - timedelta(days=1), SEKARANG + timedelta(days=3)
    assert pr.penugasan_berlaku(mulai, sampai, SEKARANG)
    assert not pr.penugasan_berlaku(mulai, sampai, sampai + timedelta(seconds=1))
    assert not pr.penugasan_berlaku(mulai, sampai, mulai - timedelta(seconds=1))
    assert pr.penugasan_berlaku(None, None, SEKARANG)  # Dekan: tanpa batas


@pytest.mark.parametrize(
    "peran, ada, galat",
    [
        (Peran.KAPRODI, True, False),
        (Peran.KAPRODI, False, True),
        (Peran.ASESOR, False, True),
        (Peran.DEKAN, False, False),
        (Peran.DEKAN, True, True),
        (Peran.ADMIN_IT, True, True),
    ],
)
def test_cakupan_penugasan(peran, ada, galat):
    assert (pr.periksa_cakupan(peran, ada) is not None) is galat


# ---------------- bukti ----------------
def test_validasi_berkas_ec18():
    assert br.periksa_berkas("SK.pdf", "application/pdf", 1000, 25) == []
    assert br.periksa_berkas("virus.exe", "application/octet-stream", 1000, 25)
    assert br.periksa_berkas("a.pdf", "image/png", 1000, 25)  # MIME tidak sesuai ekstensi
    assert br.periksa_berkas("a.pdf", "application/pdf", 26 * 1024 * 1024, 25)  # melebihi batas
    assert br.periksa_berkas("a.pdf", "application/pdf", 0, 25)


def test_isi_berkas_harus_sesuai_ekstensi():
    assert br.isi_sesuai_ekstensi("a.pdf", b"%PDF-1.7 ...")
    assert not br.isi_sesuai_ekstensi("a.pdf", b"MZ\x90\x00")
    assert br.isi_sesuai_ekstensi("a.png", b"\x89PNG\r\n")
    assert br.isi_sesuai_ekstensi("data.csv", b"apa saja")


def test_nama_aman_dan_url():
    assert br.nama_aman("../../etc/pass wd.pdf") == "pass-wd.pdf"
    assert br.periksa_url("https://drive.kampus.ac.id/s/x") is None
    assert (
        br.periksa_url("javascript:alert(1)") and br.periksa_url("ftp://x") and br.periksa_url("http://") and br.periksa_url("https://a b")
    )


def cek(jenis, akses, probe, gagal=0, batas=3):
    return br.tentukan_status(jenis, akses, probe, gagal, gagal_sebelum_merah=batas)


def test_link_checker_tautan_publik_perlu_gagal_beruntun_ec23():
    p404 = HasilProbe(ada=False, kode_http=404)
    h1 = cek(JenisBukti.TAUTAN, AksesTautan.PUBLIK, p404, 0)
    h2 = cek(JenisBukti.TAUTAN, AksesTautan.PUBLIK, p404, h1.gagal_beruntun)
    h3 = cek(JenisBukti.TAUTAN, AksesTautan.PUBLIK, p404, h2.gagal_beruntun)
    assert [h1.status, h2.status, h3.status] == [StatusCekBukti.BELUM_DICEK, StatusCekBukti.BELUM_DICEK, StatusCekBukti.TIDAK_TERJANGKAU]


def test_link_checker_pulih_menghapus_hitungan_gagal():
    h = cek(JenisBukti.TAUTAN, AksesTautan.PUBLIK, HasilProbe(ada=True, kode_http=200), 2)
    assert h.status == StatusCekBukti.OK and h.gagal_beruntun == 0


def test_tautan_terbatas_401_403_tidak_dihitung_rusak():
    for kode in (401, 403):
        h = cek(JenisBukti.TAUTAN, AksesTautan.TERBATAS, HasilProbe(ada=False, kode_http=kode), 5)
        assert h.status == StatusCekBukti.OK
    # tautan publik dengan jawaban yang sama ditandai tidak terjangkau
    h = cek(JenisBukti.TAUTAN, AksesTautan.PUBLIK, HasilProbe(ada=False, kode_http=403), 2)
    assert h.status == StatusCekBukti.TIDAK_TERJANGKAU
    # tautan terbatas yang 404 tetap rusak
    assert cek(JenisBukti.TAUTAN, AksesTautan.TERBATAS, HasilProbe(ada=False, kode_http=404), 2).status == StatusCekBukti.TIDAK_TERJANGKAU


def test_berkas_hilang_langsung_tidak_terjangkau():
    assert cek(JenisBukti.BERKAS, None, HasilProbe(ada=False), 0).status == StatusCekBukti.TIDAK_TERJANGKAU
    assert cek(JenisBukti.BERKAS, None, HasilProbe(ada=True), 3).status == StatusCekBukti.OK


def test_galat_jaringan_dihitung_gagal():
    h = cek(JenisBukti.TAUTAN, AksesTautan.PUBLIK, HasilProbe(ada=False, kode_http=None, galat="ConnectTimeout"), 2)
    assert h.status == StatusCekBukti.TIDAK_TERJANGKAU
