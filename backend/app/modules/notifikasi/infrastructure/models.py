from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, PkUuid


class Notifikasi(PkUuid, Base):
    __tablename__ = "notifikasi"
    pengguna_id: Mapped[UUID] = mapped_column(ForeignKey("pengguna.id", ondelete="CASCADE"))
    jenis: Mapped[str] = mapped_column(Text)
    judul: Mapped[str] = mapped_column(Text)
    isi: Mapped[str | None] = mapped_column(Text)
    tautan: Mapped[str | None] = mapped_column(Text)
    dibaca_pada: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
