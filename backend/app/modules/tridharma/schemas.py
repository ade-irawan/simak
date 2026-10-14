"""Skema Pydantic data inti. Nama kolom mengikuti basis data (docs/arsitektur/03-spesifikasi-api.md §6)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.types import Surel


class Dasar(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- Dosen ----------
class AfiliasiIn(Dasar):
    prodi_id: UUID
    tahun_akademik_id: UUID
    jenis: Literal["homebase", "pengampu"] = "homebase"
    proporsi_beban: Decimal = Field(default=Decimal("1"), gt=0, le=1)
    sks_diampu: Decimal | None = Field(default=None, ge=0)


class DosenIn(Dasar):
    nidn: str | None = None
    nuptk: str | None = None
    nama: str = Field(min_length=2)
    gelar_depan: str | None = None
    gelar_belakang: str | None = None
    jabatan_akademik: Literal["tenaga_pengajar", "asisten_ahli", "lektor", "lektor_kepala", "guru_besar"] | None = None
    pendidikan_tertinggi: Literal["s1", "s2", "s3", "profesi", "spesialis"]
    bidang_keahlian: str | None = None
    status_kepegawaian: Literal["tetap", "tidak_tetap", "praktisi"]
    punya_sertifikat_pendidik: bool = False
    email: Surel | None = None
    is_aktif: bool = True
    afiliasi: list[AfiliasiIn] = Field(default_factory=list, description="Hanya saat membuat; kelola lanjut lewat /dosen/{id}/afiliasi")


# ---------- Statistik ----------
class MahasiswaStatistikIn(Dasar):
    prodi_id: UUID
    tahun_akademik_id: UUID
    daya_tampung: int | None = Field(default=None, ge=0)
    pendaftar: int | None = Field(default=None, ge=0)
    lulus_seleksi: int | None = Field(default=None, ge=0)
    maba_reguler: int | None = Field(default=None, ge=0)
    maba_transfer: int | None = Field(default=None, ge=0)
    aktif_reguler: int | None = Field(default=None, ge=0)
    aktif_transfer: int | None = Field(default=None, ge=0)
    mahasiswa_asing: int | None = Field(default=None, ge=0)


class LulusanStatistikIn(Dasar):
    prodi_id: UUID
    tahun_akademik_id: UUID
    jumlah_lulusan: int | None = Field(default=None, ge=0)
    ipk_min: Decimal | None = Field(default=None, ge=0, le=4)
    ipk_rata: Decimal | None = Field(default=None, ge=0, le=4)
    ipk_maks: Decimal | None = Field(default=None, ge=0, le=4)
    masa_studi_rata_tahun: Decimal | None = Field(default=None, gt=0)
    lulus_tepat_waktu: int | None = Field(default=None, ge=0)


# ---------- Kurikulum ----------
class KurikulumIn(Dasar):
    prodi_id: UUID
    nama: str = Field(min_length=2)
    tahun_berlaku: int = Field(ge=1950, le=2100)
    is_aktif: bool = True


class MataKuliahIn(Dasar):
    kode: str = Field(min_length=1)
    nama: str = Field(min_length=2)
    sks: Decimal = Field(gt=0)
    semester: int | None = Field(default=None, ge=1, le=14)
    jenis: Literal["wajib", "pilihan"] = "wajib"
    ada_rps: bool = False


# ---------- Kegiatan (penelitian / PkM) ----------
class DosenKegiatanIn(Dasar):
    dosen_id: UUID
    peran: Literal["ketua", "anggota"] = "anggota"


class AtribusiProdiIn(Dasar):
    prodi_id: UUID
    proporsi: Decimal = Field(default=Decimal("1"), gt=0, le=1)


def _periksa_proporsi(atribusi: list[AtribusiProdiIn]) -> list[AtribusiProdiIn]:
    if sum((a.proporsi for a in atribusi), Decimal(0)) > Decimal("1.0001"):
        raise ValueError("Jumlah proporsi atribusi prodi tidak boleh melebihi 1 (EC-02).")
    if len({a.prodi_id for a in atribusi}) != len(atribusi):
        raise ValueError("Prodi pada atribusi tidak boleh ganda.")
    return atribusi


class KegiatanIn(Dasar):
    judul: str = Field(min_length=3)
    tahun_akademik_id: UUID
    sumber_dana: Literal["pt_mandiri", "dalam_negeri", "luar_negeri"]
    nama_pemberi_dana: str | None = None
    nomor_kontrak: str | None = None
    jumlah_dana: Decimal = Field(default=Decimal(0), ge=0)
    jumlah_mahasiswa: int = Field(default=0, ge=0)
    dosen: list[DosenKegiatanIn] = Field(default_factory=list)
    atribusi_prodi: list[AtribusiProdiIn] = Field(default_factory=list, description="Kosong = prodi pemanggil (100%)")

    @field_validator("atribusi_prodi")
    @classmethod
    def _proporsi(cls, v: list[AtribusiProdiIn]) -> list[AtribusiProdiIn]:
        return _periksa_proporsi(v)

    @model_validator(mode="after")
    def _satu_ketua(self) -> KegiatanIn:
        if sum(1 for d in self.dosen if d.peran == "ketua") > 1:
            raise ValueError("Satu kegiatan hanya boleh memiliki satu ketua.")
        return self


# ---------- Publikasi ----------
class PenulisIn(Dasar):
    dosen_id: UUID
    urutan_penulis: int = Field(ge=1)
    is_korespondensi: bool = False


class PublikasiIn(Dasar):
    judul: str = Field(min_length=3)
    jenis: Literal[
        "jurnal",
        "prosiding",
        "buku",
        "bab_buku",
        "paten",
        "paten_sederhana",
        "hak_cipta",
        "desain_industri",
        "teknologi_tepat_guna",
        "lainnya",
    ]
    tingkat: Literal["internasional_bereputasi", "internasional", "nasional_terakreditasi", "nasional", "lokal"] | None = None
    nama_media: str | None = None
    tahun_terbit: int = Field(ge=1950, le=2100)
    tahun_akademik_id: UUID
    doi: str | None = None
    url: str | None = None
    jumlah_sitasi: int = Field(default=0, ge=0)
    kegiatan_id: UUID | None = None
    jumlah_mahasiswa: int = Field(default=0, ge=0)
    penulis: list[PenulisIn] = Field(default_factory=list)
    atribusi_prodi: list[AtribusiProdiIn] = Field(default_factory=list, description="Kosong = prodi pemanggil (100%)")

    @field_validator("atribusi_prodi")
    @classmethod
    def _proporsi(cls, v: list[AtribusiProdiIn]) -> list[AtribusiProdiIn]:
        return _periksa_proporsi(v)

    @field_validator("doi")
    @classmethod
    def _doi(cls, v: str | None) -> str | None:
        return v.strip() or None if v else None


class GabungIn(Dasar):
    sumber_id: UUID


# ---------- Kerja sama ----------
class KerjaSamaIn(Dasar):
    nama_mitra: str = Field(min_length=2)
    tingkat: Literal["internasional", "nasional", "lokal"]
    judul_kegiatan: str = Field(min_length=2)
    nomor_dokumen: str | None = None
    bidang_pendidikan: bool = False
    bidang_penelitian: bool = False
    bidang_pkm: bool = False
    tanggal_mulai: date
    tanggal_selesai: date | None = None
    manfaat: str | None = None
    prodi_ids: list[UUID] = Field(default_factory=list, description="Kosong = prodi pemanggil")

    @model_validator(mode="after")
    def _periksa(self) -> KerjaSamaIn:
        if not (self.bidang_pendidikan or self.bidang_penelitian or self.bidang_pkm):
            raise ValueError("Pilih minimal satu bidang kerja sama.")
        if self.tanggal_selesai and self.tanggal_selesai < self.tanggal_mulai:
            raise ValueError("tanggal_selesai tidak boleh sebelum tanggal_mulai.")
        return self


# ---------- Sarana ----------
class SaranaIn(Dasar):
    nama: str = Field(min_length=2)
    jenis: Literal["ruang_kuliah", "laboratorium", "perpustakaan", "peralatan", "perangkat_lunak", "lainnya"]
    lokasi: str | None = None
    kapasitas: int | None = Field(default=None, ge=0)
    jumlah: int = Field(default=1, ge=0)
    kepemilikan: Literal["milik_sendiri", "sewa", "kerja_sama"] = "milik_sendiri"
    kondisi: Literal["baik", "rusak_ringan", "rusak_berat"] = "baik"
    is_bersama: bool = False
    prodi_ids: list[UUID] = Field(default_factory=list, description="Kosong = prodi pemanggil")


# ---------- Keuangan ----------
class KeuanganIn(Dasar):
    prodi_id: UUID | None = Field(default=None, description="Kosong = tingkat UPPS/fakultas (Staf Fakultas)")
    tahun_akademik_id: UUID
    arah: Literal["perolehan", "penggunaan"]
    kategori: str = Field(min_length=2)
    jumlah: Decimal = Field(ge=0)
