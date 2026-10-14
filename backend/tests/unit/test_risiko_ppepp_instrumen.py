from datetime import date
from decimal import Decimal

from app.modules.instrumen.domain import rules as ir
from app.modules.penilaian.domain.risiko import SinyalRisiko, tingkat_risiko
from app.modules.ppepp.domain import rules as pp
from app.modules.ppepp.domain.entities import StatusTahapan, Tahap

HARI_INI = date(2026, 10, 4)


def sinyal(**kw):
    dasar = dict(
        persen_siap=80.0,
        bukti_bermasalah=0,
        belum_ditugaskan=0,
        menunggu_eksternal=0,
        tenggat=date(2027, 3, 1),
        skor_di_bawah_target=False,
        hari_ini=HARI_INI,
    )
    return SinyalRisiko(**(dasar | kw))


def test_risiko_hijau_kuning_merah():
    assert tingkat_risiko(sinyal())[0] == "hijau"
    assert tingkat_risiko(sinyal(persen_siap=50))[0] == "kuning"
    assert tingkat_risiko(sinyal(skor_di_bawah_target=True))[0] == "kuning"
    assert tingkat_risiko(sinyal(belum_ditugaskan=2))[0] == "kuning"
    assert tingkat_risiko(sinyal(bukti_bermasalah=1))[0] == "merah"
    assert tingkat_risiko(sinyal(persen_siap=60, tenggat=date(2026, 10, 20)))[0] == "merah"  # ≤30 hari & <70%
    assert tingkat_risiko(sinyal(persen_siap=90, tenggat=date(2026, 10, 20)))[0] == "hijau"
    assert tingkat_risiko(sinyal(persen_siap=90, tenggat=date(2026, 10, 1)))[0] == "merah"  # terlewat


def test_aturan_pemetaan_valid_dan_tidak():
    assert ir.validasi_aturan({}) == []
    assert ir.validasi_aturan({"filter": {"jenis": "jurnal"}, "agregasi": "hitung"}) == []
    assert ir.validasi_aturan({"agregasi": "jumlah", "kolom": "jumlah_dana"}) == []
    assert ir.validasi_aturan({"agregasi": "jumlah"})  # kolom wajib
    assert ir.validasi_aturan({"agregasi": "rata-rata-ngawur"})
    assert ir.validasi_aturan({"sembarang": 1})
    assert ir.validasi_aturan({"filter": "bukan-objek"})


def test_instrumen_siap_aktif():
    galat, _ = ir.periksa_siap_aktif(jumlah_butir=0, jumlah_peringkat=1, bobot_kriteria=[], nilai_akhir_maks=None, jumlah_kriteria_kosong=0)
    assert len(galat) == 2
    galat, peringatan = ir.periksa_siap_aktif(
        jumlah_butir=5,
        jumlah_peringkat=3,
        bobot_kriteria=[Decimal(40), Decimal(20)],
        nilai_akhir_maks=Decimal(400),
        jumlah_kriteria_kosong=2,
    )
    assert galat == [] and len(peringatan) == 2


def test_ppepp_selisih_dan_saran():
    assert pp.selisih_target(Decimal("0.8"), Decimal("1.0")) == Decimal("-0.2")
    assert pp.selisih_target(None, Decimal(1)) is None
    s = pp.saran_berikutnya(Tahap.EVALUASI, StatusTahapan.SELESAI, "Empat dosen belum", None, Decimal("-0.2"))
    assert s and s.tahap == "pengendalian"
    assert pp.saran_berikutnya(Tahap.EVALUASI, StatusTahapan.SELESAI, None, None, Decimal("0.1")).tahap == "peningkatan"
    assert pp.saran_berikutnya(Tahap.EVALUASI, StatusTahapan.BERJALAN, "x", None, None) is None
    assert pp.saran_berikutnya(Tahap.PENINGKATAN, StatusTahapan.SELESAI, None, None, None).tahap == "arsip"
    assert pp.tahap_valid("penetapan") is None and pp.tahap_valid("evaluasi") == Tahap.EVALUASI
