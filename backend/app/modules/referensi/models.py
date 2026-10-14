from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, PkUuid, Stempel


class Fakultas(PkUuid, Stempel, Base):
    __tablename__ = "fakultas"
    kode: Mapped[str] = mapped_column(Text, unique=True)
    nama: Mapped[str] = mapped_column(Text)


class Lam(PkUuid, Base):
    __tablename__ = "lam"
    kode: Mapped[str] = mapped_column(Text, unique=True)
    nama: Mapped[str] = mapped_column(Text)


class Prodi(PkUuid, Stempel, Base):
    __tablename__ = "prodi"
    fakultas_id: Mapped[UUID] = mapped_column(ForeignKey("fakultas.id"))
    lam_id: Mapped[UUID] = mapped_column(ForeignKey("lam.id"))
    kode: Mapped[str] = mapped_column(Text, unique=True)
    nama: Mapped[str] = mapped_column(Text)
    jenjang: Mapped[str] = mapped_column(Text, server_default="S1")
    is_aktif: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class TahunAkademik(PkUuid, Base):
    __tablename__ = "tahun_akademik"
    kode: Mapped[str] = mapped_column(Text, unique=True)
    tanggal_mulai: Mapped[date] = mapped_column(Date)
    tanggal_selesai: Mapped[date] = mapped_column(Date)
    is_aktif: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class PengaturanSistem(Base):
    __tablename__ = "pengaturan_sistem"
    kunci: Mapped[str] = mapped_column(Text, primary_key=True)
    nilai: Mapped[Any] = mapped_column(JSONB)
    deskripsi: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
