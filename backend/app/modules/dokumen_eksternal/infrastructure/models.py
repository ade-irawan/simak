from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, PkUuid, Stempel


class DokumenEksternal(PkUuid, Stempel, Base):
    __tablename__ = "dokumen_eksternal"
    jenis: Mapped[str] = mapped_column(Text)
    judul: Mapped[str] = mapped_column(Text)
    sumber_unit: Mapped[str] = mapped_column(Text, server_default="Direktorat Kemahasiswaan")
    tahun_akademik_id: Mapped[UUID] = mapped_column(ForeignKey("tahun_akademik.id"))
    periode_mulai: Mapped[date | None] = mapped_column(Date)
    periode_selesai: Mapped[date | None] = mapped_column(Date)
    populasi: Mapped[int | None] = mapped_column(Integer)
    jumlah_responden: Mapped[int | None] = mapped_column(Integer)
    metodologi: Mapped[str | None] = mapped_column(Text)
    bukti_id: Mapped[UUID] = mapped_column(ForeignKey("bukti.id"))
    diterima_pada: Mapped[date | None] = mapped_column(Date)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    deleted_at: Mapped[datetime | None]


class DokumenEksternalProdi(Base):
    __tablename__ = "dokumen_eksternal_prodi"
    dokumen_id: Mapped[UUID] = mapped_column(ForeignKey("dokumen_eksternal.id", ondelete="CASCADE"), primary_key=True)
    prodi_id: Mapped[UUID] = mapped_column(ForeignKey("prodi.id"), primary_key=True)


class IndikatorEksternal(PkUuid, Stempel, Base):
    __tablename__ = "indikator_eksternal"
    dokumen_id: Mapped[UUID] = mapped_column(ForeignKey("dokumen_eksternal.id", ondelete="CASCADE"))
    prodi_id: Mapped[UUID] = mapped_column(ForeignKey("prodi.id"))
    kode: Mapped[str] = mapped_column(Text)
    nama: Mapped[str] = mapped_column(Text)
    nilai: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    satuan: Mapped[str | None] = mapped_column(Text)
    jumlah_responden: Mapped[int | None] = mapped_column(Integer)
    data_memadai: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    catatan: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("dokumen_id", "prodi_id", "kode"),)
