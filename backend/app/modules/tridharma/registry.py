"""Registri sumber daya data inti. Menambah sumber baru = menambah satu ``Spec`` di sini
(model, skema, cara terikat ke prodi, kolom cari) — tanpa menyentuh router maupun layanan."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from app.modules.instrumen.public import JenisEntitas
from app.modules.tridharma import models as m
from app.modules.tridharma import schemas as s
from app.modules.tridharma.relasi import Afiliasi, Langsung, Penangan, Penghubung


@dataclass(frozen=True)
class Spec:
    path: str  # segmen URL, mis. "publikasi"
    entitas: JenisEntitas  # kunci pada pemetaan_butir & bukti_data_inti
    model: type
    skema: type[BaseModel]
    penangan: Penangan
    kolom_cari: tuple[str, ...] = ()
    kolom_tahun: str | None = "tahun_akademik_id"
    filter_boleh: tuple[str, ...] = ()
    #: saringan tetap pada tabel bersama (mis. kegiatan_tridharma.jenis)
    tetap: dict[str, Any] = field(default_factory=dict)
    soft_delete: bool = True
    #: hanya Staf Fakultas yang boleh menulis bila kondisi ini benar pada baris (mis. sarana bersama)
    kolom_hanya_sf: str | None = None
    #: Staf Fakultas boleh menulis ke prodi mana pun (data bersama / tingkat UPPS), bukan hanya prodi yang ditugaskan
    sf_bebas: bool = False
    nama: str = ""


SPEC_LIST: tuple[Spec, ...] = (
    Spec(
        "dosen",
        JenisEntitas.DOSEN,
        m.Dosen,
        s.DosenIn,
        Afiliasi(),
        ("nama", "nidn", "nuptk", "email"),
        kolom_tahun=None,
        filter_boleh=("status_kepegawaian", "jabatan_akademik", "is_aktif", "pendidikan_tertinggi"),
        sf_bebas=True,
        nama="Dosen",
    ),
    Spec(
        "statistik-mahasiswa",
        JenisEntitas.MAHASISWA_STATISTIK,
        m.MahasiswaStatistik,
        s.MahasiswaStatistikIn,
        Langsung(),
        soft_delete=False,
        nama="Statistik mahasiswa",
    ),
    Spec(
        "statistik-lulusan",
        JenisEntitas.LULUSAN_STATISTIK,
        m.LulusanStatistik,
        s.LulusanStatistikIn,
        Langsung(),
        soft_delete=False,
        nama="Statistik lulusan",
    ),
    Spec(
        "kurikulum",
        JenisEntitas.KURIKULUM,
        m.Kurikulum,
        s.KurikulumIn,
        Langsung(),
        ("nama",),
        kolom_tahun=None,
        filter_boleh=("is_aktif",),
        nama="Kurikulum",
    ),
    Spec(
        "penelitian",
        JenisEntitas.PENELITIAN,
        m.KegiatanTridharma,
        s.KegiatanIn,
        Penghubung(m.KegiatanProdi, "kegiatan_id", bidang_input="atribusi_prodi", proporsi=True),
        ("judul", "nomor_kontrak"),
        filter_boleh=("sumber_dana",),
        tetap={"jenis": "penelitian"},
        nama="Penelitian",
    ),
    Spec(
        "pkm",
        JenisEntitas.PKM,
        m.KegiatanTridharma,
        s.KegiatanIn,
        Penghubung(m.KegiatanProdi, "kegiatan_id", bidang_input="atribusi_prodi", proporsi=True),
        ("judul", "nomor_kontrak"),
        filter_boleh=("sumber_dana",),
        tetap={"jenis": "pkm"},
        nama="Pengabdian kepada masyarakat",
    ),
    Spec(
        "publikasi",
        JenisEntitas.PUBLIKASI,
        m.Publikasi,
        s.PublikasiIn,
        Penghubung(m.PublikasiProdi, "publikasi_id", bidang_input="atribusi_prodi", proporsi=True),
        ("judul", "doi", "nama_media"),
        filter_boleh=("jenis", "tingkat", "tahun_terbit"),
        nama="Publikasi dan luaran",
    ),
    Spec(
        "kerja-sama",
        JenisEntitas.KERJA_SAMA,
        m.KerjaSama,
        s.KerjaSamaIn,
        Penghubung(m.KerjaSamaProdi, "kerja_sama_id", bidang_input="prodi_ids"),
        ("nama_mitra", "judul_kegiatan"),
        kolom_tahun=None,
        filter_boleh=("tingkat",),
        sf_bebas=True,
        nama="Kerja sama",
    ),
    Spec(
        "sarana",
        JenisEntitas.SARANA_PRASARANA,
        m.SaranaPrasarana,
        s.SaranaIn,
        Penghubung(m.SaranaProdi, "sarana_id", bidang_input="prodi_ids"),
        ("nama", "lokasi"),
        kolom_tahun=None,
        filter_boleh=("jenis", "kondisi", "is_bersama"),
        kolom_hanya_sf="is_bersama",
        sf_bebas=True,
        nama="Sarana dan prasarana",
    ),
    Spec(
        "keuangan",
        JenisEntitas.KEUANGAN,
        m.Keuangan,
        s.KeuanganIn,
        Langsung(boleh_kosong=True),
        ("kategori",),
        filter_boleh=("arah", "kategori"),
        sf_bebas=True,
        nama="Keuangan",
    ),
)

SPEC: dict[str, Spec] = {sp.path: sp for sp in SPEC_LIST}
SPEC_ENTITAS: dict[JenisEntitas, Spec] = {sp.entitas: sp for sp in SPEC_LIST}
