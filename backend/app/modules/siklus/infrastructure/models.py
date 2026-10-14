from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, SmallInteger, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, Berversi, PkUuid, Stempel, pg_enum
from app.modules.siklus.domain.entities import (
    PengelolaButir,
    StatusKelengkapan,
    StatusNarasi,
    StatusSiklus,
    SumberNarasi,
    SumberSkor,
)


class SiklusAkreditasi(PkUuid, Stempel, Base):
    __tablename__ = "siklus_akreditasi"
    prodi_id: Mapped[UUID] = mapped_column(ForeignKey("prodi.id"))
    instrumen_versi_id: Mapped[UUID] = mapped_column(ForeignKey("instrumen_versi.id"))
    nama: Mapped[str] = mapped_column(Text)
    ts_tahun_akademik_id: Mapped[UUID] = mapped_column(ForeignKey("tahun_akademik.id"))
    jumlah_tahun_data: Mapped[int] = mapped_column(SmallInteger, server_default=text("3"))
    tanggal_mulai: Mapped[date] = mapped_column(Date)
    tenggat: Mapped[date | None] = mapped_column(Date)
    target_peringkat_id: Mapped[UUID | None] = mapped_column(ForeignKey("instrumen_peringkat.id"))
    status: Mapped[StatusSiklus] = mapped_column(pg_enum(StatusSiklus, "status_siklus"), server_default="persiapan")
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))


class ButirSiklus(PkUuid, Stempel, Berversi, Base):
    __tablename__ = "butir_siklus"
    siklus_id: Mapped[UUID] = mapped_column(ForeignKey("siklus_akreditasi.id", ondelete="CASCADE"))
    instrumen_butir_id: Mapped[UUID] = mapped_column(ForeignKey("instrumen_butir.id"))
    status_kelengkapan: Mapped[StatusKelengkapan] = mapped_column(
        pg_enum(StatusKelengkapan, "status_kelengkapan"), server_default="belum_mulai"
    )
    pengelola: Mapped[PengelolaButir] = mapped_column(pg_enum(PengelolaButir, "pengelola_butir"), server_default="prodi")
    penanggung_jawab_id: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    ditugaskan_oleh: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    ditugaskan_pada: Mapped[datetime | None]
    skor_estimasi: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    sumber_skor: Mapped[SumberSkor | None] = mapped_column(pg_enum(SumberSkor, "sumber_skor"))
    skor_dihitung_pada: Mapped[datetime | None]
    menunggu_dokumen_eksternal: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    catatan: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    __table_args__ = (UniqueConstraint("siklus_id", "instrumen_butir_id"),)


class NarasiButir(PkUuid, Stempel, Berversi, Base):
    __tablename__ = "narasi_butir"
    butir_siklus_id: Mapped[UUID] = mapped_column(ForeignKey("butir_siklus.id", ondelete="CASCADE"))
    bagian: Mapped[str] = mapped_column(Text, server_default="utama")
    isi: Mapped[str] = mapped_column(Text, server_default="")
    status: Mapped[StatusNarasi] = mapped_column(pg_enum(StatusNarasi, "status_narasi"), server_default="draft")
    sumber: Mapped[SumberNarasi] = mapped_column(pg_enum(SumberNarasi, "sumber_narasi"), server_default="manual")
    permintaan_llm_id: Mapped[UUID | None] = mapped_column(ForeignKey("permintaan_llm.id", ondelete="SET NULL"))
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    __table_args__ = (UniqueConstraint("butir_siklus_id", "bagian"),)
