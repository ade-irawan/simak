from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, LargeBinary, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, PkUuid, Stempel, pg_enum
from app.core.enums import StatusTugas
from app.modules.llm.domain.ports import ModeLlm


class KonfigurasiLlm(PkUuid, Stempel, Base):
    __tablename__ = "konfigurasi_llm"
    nama: Mapped[str] = mapped_column(Text)
    mode: Mapped[ModeLlm] = mapped_column(pg_enum(ModeLlm, "mode_llm"))
    base_url: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    api_key_terenkripsi: Mapped[bytes | None] = mapped_column(LargeBinary)
    parameter: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    is_aktif: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    disetujui_oleh: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    disetujui_pada: Mapped[datetime | None]
    diuji_pada: Mapped[datetime | None]
    hasil_uji: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))


class PermintaanLlm(PkUuid, Base):
    __tablename__ = "permintaan_llm"
    butir_siklus_id: Mapped[UUID] = mapped_column(ForeignKey("butir_siklus.id", ondelete="CASCADE"))
    bagian: Mapped[str] = mapped_column(Text, server_default="utama")
    konfigurasi_id: Mapped[UUID | None] = mapped_column(ForeignKey("konfigurasi_llm.id", ondelete="SET NULL"))
    model: Mapped[str] = mapped_column(Text)
    mode: Mapped[ModeLlm] = mapped_column(pg_enum(ModeLlm, "mode_llm"))
    status: Mapped[StatusTugas] = mapped_column(pg_enum(StatusTugas, "status_tugas"), server_default="antre")
    hasil: Mapped[str | None] = mapped_column(Text)
    galat: Mapped[str | None] = mapped_column(Text)
    token_masuk: Mapped[int | None] = mapped_column(Integer)
    token_keluar: Mapped[int | None] = mapped_column(Integer)
    task_id: Mapped[str | None] = mapped_column(Text)
    diminta_oleh: Mapped[UUID] = mapped_column(ForeignKey("pengguna.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    selesai_pada: Mapped[datetime | None]
