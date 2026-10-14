from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, INET
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, PkUuid, Stempel, pg_enum
from app.core.permissions import Peran
from app.modules.pengguna.domain.entities import JenisTokenAkun, StatusPengguna, StatusPenugasan


class Pengguna(PkUuid, Stempel, Base):
    __tablename__ = "pengguna"
    email: Mapped[str] = mapped_column(CITEXT, unique=True)
    nama: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    status: Mapped[StatusPengguna] = mapped_column(pg_enum(StatusPengguna, "status_pengguna"), server_default="aktif")
    wajib_ganti_sandi: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    jumlah_gagal_login: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    terkunci_sampai: Mapped[datetime | None]
    login_terakhir: Mapped[datetime | None]


class PenugasanPeran(PkUuid, Stempel, Base):
    __tablename__ = "penugasan_peran"
    pengguna_id: Mapped[UUID] = mapped_column(ForeignKey("pengguna.id", ondelete="CASCADE"))
    peran: Mapped[Peran] = mapped_column(pg_enum(Peran, "peran_pengguna"))
    prodi_id: Mapped[UUID | None] = mapped_column(ForeignKey("prodi.id"))
    status: Mapped[StatusPenugasan] = mapped_column(pg_enum(StatusPenugasan, "status_penugasan"), server_default="aktif")
    berlaku_mulai: Mapped[datetime | None]
    berlaku_sampai: Mapped[datetime | None]
    diusulkan_oleh: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    disetujui_oleh: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    disetujui_pada: Mapped[datetime | None]
    dicabut_oleh: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    dicabut_pada: Mapped[datetime | None]
    catatan: Mapped[str | None] = mapped_column(Text)


class TokenRefresh(PkUuid, Base):
    __tablename__ = "token_refresh"
    pengguna_id: Mapped[UUID] = mapped_column(ForeignKey("pengguna.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    kedaluwarsa_pada: Mapped[datetime]
    dicabut_pada: Mapped[datetime | None]
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class TokenAkun(PkUuid, Base):
    __tablename__ = "token_akun"
    pengguna_id: Mapped[UUID] = mapped_column(ForeignKey("pengguna.id", ondelete="CASCADE"))
    jenis: Mapped[JenisTokenAkun] = mapped_column(pg_enum(JenisTokenAkun, "jenis_token_akun"))
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    kedaluwarsa_pada: Mapped[datetime]
    dipakai_pada: Mapped[datetime | None]
    dibuat_oleh: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
