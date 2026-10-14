from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, Berversi, PkUuid, Stempel, pg_enum
from app.modules.instrumen.public import TahapPpepp
from app.modules.ppepp.domain.entities import StatusPenetapan, StatusSiklusPpepp, StatusTahapan


class StandarSpm(PkUuid, Stempel, Base):
    __tablename__ = "standar_spm"
    kode: Mapped[str] = mapped_column(Text, unique=True)
    nama: Mapped[str] = mapped_column(Text)
    kategori: Mapped[str | None] = mapped_column(Text)
    dokumen_sumber: Mapped[str | None] = mapped_column(Text)
    versi: Mapped[str | None] = mapped_column(Text)
    is_aktif: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    divalidasi_oleh: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    divalidasi_pada: Mapped[datetime | None]
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))


class ButirStandarSpm(PkUuid, Stempel, Base):
    __tablename__ = "butir_standar_spm"
    standar_id: Mapped[UUID] = mapped_column(ForeignKey("standar_spm.id", ondelete="CASCADE"))
    nomor: Mapped[str] = mapped_column(Text)
    pernyataan: Mapped[str] = mapped_column(Text)
    indikator: Mapped[str | None] = mapped_column(Text)
    target_default: Mapped[str | None] = mapped_column(Text)
    satuan: Mapped[str | None] = mapped_column(Text)
    is_aktif: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    __table_args__ = (UniqueConstraint("standar_id", "nomor"),)


class ButirStandarInstrumen(Base):
    __tablename__ = "butir_standar_instrumen"
    butir_standar_id: Mapped[UUID] = mapped_column(ForeignKey("butir_standar_spm.id", ondelete="CASCADE"), primary_key=True)
    instrumen_butir_id: Mapped[UUID] = mapped_column(ForeignKey("instrumen_butir.id", ondelete="CASCADE"), primary_key=True)


class SiklusPpepp(PkUuid, Stempel, Base):
    __tablename__ = "siklus_ppepp"
    nama: Mapped[str] = mapped_column(Text)
    tahun_akademik_id: Mapped[UUID] = mapped_column(ForeignKey("tahun_akademik.id"))
    tanggal_mulai: Mapped[date] = mapped_column(Date)
    tanggal_selesai: Mapped[date | None] = mapped_column(Date)
    status: Mapped[StatusSiklusPpepp] = mapped_column(pg_enum(StatusSiklusPpepp, "status_siklus_ppepp"), server_default="draf")
    siklus_sebelumnya_id: Mapped[UUID | None] = mapped_column(ForeignKey("siklus_ppepp.id"))
    ditetapkan_oleh: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    ditetapkan_pada: Mapped[datetime | None]


class PenetapanButir(PkUuid, Stempel, Berversi, Base):
    __tablename__ = "penetapan_butir"
    siklus_ppepp_id: Mapped[UUID] = mapped_column(ForeignKey("siklus_ppepp.id", ondelete="CASCADE"))
    butir_standar_id: Mapped[UUID] = mapped_column(ForeignKey("butir_standar_spm.id"))
    prodi_id: Mapped[UUID | None] = mapped_column(ForeignKey("prodi.id"))
    nomor_butir: Mapped[str] = mapped_column(Text)
    isi: Mapped[str] = mapped_column(Text)
    indikator: Mapped[str] = mapped_column(Text)
    target_nilai: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    target_satuan: Mapped[str | None] = mapped_column(Text)
    target_deskripsi: Mapped[str | None] = mapped_column(Text)
    periode_mulai: Mapped[date | None] = mapped_column(Date)
    periode_selesai: Mapped[date | None] = mapped_column(Date)
    penanggung_jawab_id: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    baseline_dari_id: Mapped[UUID | None] = mapped_column(ForeignKey("penetapan_butir.id"))
    baseline_nilai: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    status: Mapped[StatusPenetapan] = mapped_column(pg_enum(StatusPenetapan, "status_penetapan"), server_default="draf")
    ditetapkan_oleh: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    ditetapkan_pada: Mapped[datetime | None]


class TahapanPpepp(PkUuid, Stempel, Berversi, Base):
    __tablename__ = "tahapan_ppepp"
    penetapan_butir_id: Mapped[UUID] = mapped_column(ForeignKey("penetapan_butir.id", ondelete="CASCADE"))
    prodi_id: Mapped[UUID] = mapped_column(ForeignKey("prodi.id"))
    tahap: Mapped[TahapPpepp] = mapped_column(pg_enum(TahapPpepp, "tahap_ppepp"))
    status: Mapped[StatusTahapan] = mapped_column(pg_enum(StatusTahapan, "status_tahapan"), server_default="belum_mulai")
    uraian: Mapped[str | None] = mapped_column(Text)
    capaian_nilai: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    capaian_deskripsi: Mapped[str | None] = mapped_column(Text)
    temuan: Mapped[str | None] = mapped_column(Text)
    tindak_lanjut: Mapped[str | None] = mapped_column(Text)
    tenggat: Mapped[date | None] = mapped_column(Date)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    __table_args__ = (UniqueConstraint("penetapan_butir_id", "prodi_id", "tahap"),)
