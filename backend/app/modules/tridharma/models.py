"""Model data inti Tridharma (netral terhadap instrumen). Memetakan tabel di db/schema.sql §7."""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.core.database import Base, Berversi, PkUuid, Stempel, pg_enum


class StatusData(enum.StrEnum):
    DRAFT = "draft"
    TERVERIFIKASI = "terverifikasi"


class JejakData(Berversi):
    """Kolom bersama data inti: status verifikasi, penguncian optimistik, dan jejak pembuat."""

    @declared_attr.directive
    def status_data(cls) -> Mapped[StatusData]:  # noqa: N805
        return mapped_column(pg_enum(StatusData, "status_data"), server_default="draft")

    @declared_attr.directive
    def created_by(cls) -> Mapped[UUID | None]:  # noqa: N805
        return mapped_column(ForeignKey("pengguna.id"))

    @declared_attr.directive
    def updated_by(cls) -> Mapped[UUID | None]:  # noqa: N805
        return mapped_column(ForeignKey("pengguna.id"))


class HapusLunak:
    deleted_at: Mapped[datetime | None] = mapped_column()


class Dosen(PkUuid, Stempel, JejakData, HapusLunak, Base):
    __tablename__ = "dosen"
    nidn: Mapped[str | None] = mapped_column(Text)
    nuptk: Mapped[str | None] = mapped_column(Text)
    nama: Mapped[str] = mapped_column(Text)
    gelar_depan: Mapped[str | None] = mapped_column(Text)
    gelar_belakang: Mapped[str | None] = mapped_column(Text)
    jabatan_akademik: Mapped[str | None] = mapped_column(Text)
    pendidikan_tertinggi: Mapped[str] = mapped_column(Text)
    bidang_keahlian: Mapped[str | None] = mapped_column(Text)
    status_kepegawaian: Mapped[str] = mapped_column(Text)
    punya_sertifikat_pendidik: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    email: Mapped[str | None] = mapped_column(CITEXT)
    is_aktif: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class DosenProdi(PkUuid, Base):
    __tablename__ = "dosen_prodi"
    dosen_id: Mapped[UUID] = mapped_column(ForeignKey("dosen.id", ondelete="CASCADE"))
    prodi_id: Mapped[UUID] = mapped_column(ForeignKey("prodi.id"))
    tahun_akademik_id: Mapped[UUID] = mapped_column(ForeignKey("tahun_akademik.id"))
    jenis: Mapped[str] = mapped_column(Text)
    proporsi_beban: Mapped[Decimal] = mapped_column(Numeric(4, 3), server_default=text("1"))
    sks_diampu: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))


class MahasiswaStatistik(PkUuid, Stempel, JejakData, Base):
    __tablename__ = "mahasiswa_statistik"
    prodi_id: Mapped[UUID] = mapped_column(ForeignKey("prodi.id"))
    tahun_akademik_id: Mapped[UUID] = mapped_column(ForeignKey("tahun_akademik.id"))
    daya_tampung: Mapped[int | None] = mapped_column(Integer)
    pendaftar: Mapped[int | None] = mapped_column(Integer)
    lulus_seleksi: Mapped[int | None] = mapped_column(Integer)
    maba_reguler: Mapped[int | None] = mapped_column(Integer)
    maba_transfer: Mapped[int | None] = mapped_column(Integer)
    aktif_reguler: Mapped[int | None] = mapped_column(Integer)
    aktif_transfer: Mapped[int | None] = mapped_column(Integer)
    mahasiswa_asing: Mapped[int | None] = mapped_column(Integer)


class LulusanStatistik(PkUuid, Stempel, JejakData, Base):
    __tablename__ = "lulusan_statistik"
    prodi_id: Mapped[UUID] = mapped_column(ForeignKey("prodi.id"))
    tahun_akademik_id: Mapped[UUID] = mapped_column(ForeignKey("tahun_akademik.id"))
    jumlah_lulusan: Mapped[int | None] = mapped_column(Integer)
    ipk_min: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    ipk_rata: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    ipk_maks: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    masa_studi_rata_tahun: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    lulus_tepat_waktu: Mapped[int | None] = mapped_column(Integer)


class Kurikulum(PkUuid, Stempel, JejakData, HapusLunak, Base):
    __tablename__ = "kurikulum"
    prodi_id: Mapped[UUID] = mapped_column(ForeignKey("prodi.id"))
    nama: Mapped[str] = mapped_column(Text)
    tahun_berlaku: Mapped[int] = mapped_column(SmallInteger)
    is_aktif: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class MataKuliah(PkUuid, Stempel, Base):
    __tablename__ = "mata_kuliah"
    kurikulum_id: Mapped[UUID] = mapped_column(ForeignKey("kurikulum.id", ondelete="CASCADE"))
    kode: Mapped[str] = mapped_column(Text)
    nama: Mapped[str] = mapped_column(Text)
    sks: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    semester: Mapped[int | None] = mapped_column(SmallInteger)
    jenis: Mapped[str] = mapped_column(Text, server_default="wajib")
    ada_rps: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class KegiatanTridharma(PkUuid, Stempel, JejakData, HapusLunak, Base):
    __tablename__ = "kegiatan_tridharma"
    jenis: Mapped[str] = mapped_column(Text)
    judul: Mapped[str] = mapped_column(Text)
    tahun_akademik_id: Mapped[UUID] = mapped_column(ForeignKey("tahun_akademik.id"))
    sumber_dana: Mapped[str] = mapped_column(Text)
    nama_pemberi_dana: Mapped[str | None] = mapped_column(Text)
    nomor_kontrak: Mapped[str | None] = mapped_column(Text)
    jumlah_dana: Mapped[Decimal] = mapped_column(Numeric(16, 2), server_default=text("0"))
    jumlah_mahasiswa: Mapped[int] = mapped_column(Integer, server_default=text("0"))


class KegiatanDosen(Base):
    __tablename__ = "kegiatan_dosen"
    kegiatan_id: Mapped[UUID] = mapped_column(ForeignKey("kegiatan_tridharma.id", ondelete="CASCADE"), primary_key=True)
    dosen_id: Mapped[UUID] = mapped_column(ForeignKey("dosen.id"), primary_key=True)
    peran: Mapped[str] = mapped_column(Text, server_default="anggota")


class KegiatanProdi(Base):
    __tablename__ = "kegiatan_prodi"
    kegiatan_id: Mapped[UUID] = mapped_column(ForeignKey("kegiatan_tridharma.id", ondelete="CASCADE"), primary_key=True)
    prodi_id: Mapped[UUID] = mapped_column(ForeignKey("prodi.id"), primary_key=True)
    proporsi: Mapped[Decimal] = mapped_column(Numeric(4, 3), server_default=text("1"))


class Publikasi(PkUuid, Stempel, JejakData, HapusLunak, Base):
    __tablename__ = "publikasi"
    judul: Mapped[str] = mapped_column(Text)
    jenis: Mapped[str] = mapped_column(Text)
    tingkat: Mapped[str | None] = mapped_column(Text)
    nama_media: Mapped[str | None] = mapped_column(Text)
    tahun_terbit: Mapped[int] = mapped_column(SmallInteger)
    tahun_akademik_id: Mapped[UUID] = mapped_column(ForeignKey("tahun_akademik.id"))
    doi: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    jumlah_sitasi: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    kegiatan_id: Mapped[UUID | None] = mapped_column(ForeignKey("kegiatan_tridharma.id", ondelete="SET NULL"))
    jumlah_mahasiswa: Mapped[int] = mapped_column(Integer, server_default=text("0"))


class PublikasiDosen(Base):
    __tablename__ = "publikasi_dosen"
    publikasi_id: Mapped[UUID] = mapped_column(ForeignKey("publikasi.id", ondelete="CASCADE"), primary_key=True)
    dosen_id: Mapped[UUID] = mapped_column(ForeignKey("dosen.id"), primary_key=True)
    urutan_penulis: Mapped[int] = mapped_column(SmallInteger)
    is_korespondensi: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class PublikasiProdi(Base):
    __tablename__ = "publikasi_prodi"
    publikasi_id: Mapped[UUID] = mapped_column(ForeignKey("publikasi.id", ondelete="CASCADE"), primary_key=True)
    prodi_id: Mapped[UUID] = mapped_column(ForeignKey("prodi.id"), primary_key=True)
    proporsi: Mapped[Decimal] = mapped_column(Numeric(4, 3), server_default=text("1"))


class KerjaSama(PkUuid, Stempel, JejakData, HapusLunak, Base):
    __tablename__ = "kerja_sama"
    nama_mitra: Mapped[str] = mapped_column(Text)
    tingkat: Mapped[str] = mapped_column(Text)
    judul_kegiatan: Mapped[str] = mapped_column(Text)
    nomor_dokumen: Mapped[str | None] = mapped_column(Text)
    bidang_pendidikan: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    bidang_penelitian: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    bidang_pkm: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    tanggal_mulai: Mapped[date] = mapped_column(Date)
    tanggal_selesai: Mapped[date | None] = mapped_column(Date)
    manfaat: Mapped[str | None] = mapped_column(Text)


class KerjaSamaProdi(Base):
    __tablename__ = "kerja_sama_prodi"
    kerja_sama_id: Mapped[UUID] = mapped_column(ForeignKey("kerja_sama.id", ondelete="CASCADE"), primary_key=True)
    prodi_id: Mapped[UUID] = mapped_column(ForeignKey("prodi.id"), primary_key=True)


class SaranaPrasarana(PkUuid, Stempel, JejakData, HapusLunak, Base):
    __tablename__ = "sarana_prasarana"
    nama: Mapped[str] = mapped_column(Text)
    jenis: Mapped[str] = mapped_column(Text)
    lokasi: Mapped[str | None] = mapped_column(Text)
    kapasitas: Mapped[int | None] = mapped_column(Integer)
    jumlah: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    kepemilikan: Mapped[str] = mapped_column(Text, server_default="milik_sendiri")
    kondisi: Mapped[str] = mapped_column(Text, server_default="baik")
    is_bersama: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class SaranaProdi(Base):
    __tablename__ = "sarana_prodi"
    sarana_id: Mapped[UUID] = mapped_column(ForeignKey("sarana_prasarana.id", ondelete="CASCADE"), primary_key=True)
    prodi_id: Mapped[UUID] = mapped_column(ForeignKey("prodi.id"), primary_key=True)


class Keuangan(PkUuid, Stempel, JejakData, HapusLunak, Base):
    __tablename__ = "keuangan"
    prodi_id: Mapped[UUID | None] = mapped_column(ForeignKey("prodi.id"))
    tahun_akademik_id: Mapped[UUID] = mapped_column(ForeignKey("tahun_akademik.id"))
    arah: Mapped[str] = mapped_column(Text)
    kategori: Mapped[str] = mapped_column(Text)
    jumlah: Mapped[Decimal] = mapped_column(Numeric(18, 2))
