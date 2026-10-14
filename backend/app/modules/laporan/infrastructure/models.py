from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, Berversi, PkUuid, Stempel, pg_enum
from app.modules.laporan.domain.entities import (
    FormatEkspor,
    JenisEkspor,
    KeputusanValidasi,
    StatusCatatan,
    StatusLaporan,
    StatusTugas,
)


class Laporan(PkUuid, Stempel, Berversi, Base):
    __tablename__ = "laporan"
    siklus_id: Mapped[UUID] = mapped_column(ForeignKey("siklus_akreditasi.id", ondelete="CASCADE"), unique=True)
    status: Mapped[StatusLaporan] = mapped_column(pg_enum(StatusLaporan, "status_laporan"), server_default="draft")
    dibuka_kembali_oleh: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    dibuka_kembali_pada: Mapped[datetime | None]


class LaporanPengajuan(PkUuid, Base):
    __tablename__ = "laporan_pengajuan"
    laporan_id: Mapped[UUID] = mapped_column(ForeignKey("laporan.id", ondelete="CASCADE"))
    nomor: Mapped[int] = mapped_column(Integer)
    diajukan_oleh: Mapped[UUID] = mapped_column(ForeignKey("pengguna.id"))
    diajukan_pada: Mapped[datetime] = mapped_column(server_default=text("now()"))
    keputusan: Mapped[KeputusanValidasi] = mapped_column(pg_enum(KeputusanValidasi, "keputusan_validasi"), server_default="menunggu")
    diputuskan_oleh: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    diputuskan_pada: Mapped[datetime | None]
    catatan_umum: Mapped[str | None] = mapped_column(Text)
    cuplikan: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    cuplikan_objek_key: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("laporan_id", "nomor"),)


class CatatanValidasi(PkUuid, Base):
    __tablename__ = "catatan_validasi"
    pengajuan_id: Mapped[UUID] = mapped_column(ForeignKey("laporan_pengajuan.id", ondelete="CASCADE"))
    butir_siklus_id: Mapped[UUID | None] = mapped_column(ForeignKey("butir_siklus.id", ondelete="CASCADE"))
    isi: Mapped[str] = mapped_column(Text)
    status: Mapped[StatusCatatan] = mapped_column(pg_enum(StatusCatatan, "status_catatan"), server_default="terbuka")
    dibuat_oleh: Mapped[UUID] = mapped_column(ForeignKey("pengguna.id"))
    diselesaikan_oleh: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    diselesaikan_pada: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class EksporDokumen(PkUuid, Base):
    __tablename__ = "ekspor_dokumen"
    siklus_id: Mapped[UUID] = mapped_column(ForeignKey("siklus_akreditasi.id", ondelete="CASCADE"))
    pengajuan_id: Mapped[UUID | None] = mapped_column(ForeignKey("laporan_pengajuan.id"))
    jenis: Mapped[JenisEkspor] = mapped_column(pg_enum(JenisEkspor, "jenis_ekspor"))
    format: Mapped[FormatEkspor] = mapped_column(pg_enum(FormatEkspor, "format_ekspor"))
    status: Mapped[StatusTugas] = mapped_column(pg_enum(StatusTugas, "status_tugas"), server_default="antre")
    objek_key: Mapped[str | None] = mapped_column(Text)
    ukuran_byte: Mapped[int | None] = mapped_column(BigInteger)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, server_default=text("'{}'::jsonb"))
    galat: Mapped[str | None] = mapped_column(Text)
    task_id: Mapped[str | None] = mapped_column(Text)
    diminta_oleh: Mapped[UUID] = mapped_column(ForeignKey("pengguna.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    selesai_pada: Mapped[datetime | None]
