from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, PkUuid, Stempel


class TelaahAsesor(PkUuid, Stempel, Base):
    """Tanda 'sudah ditelaah' dan catatan baca; terikat pada pengajuan (versi) yang ditelaah dan tidak mengubah data sumber."""

    __tablename__ = "telaah_asesor"
    butir_siklus_id: Mapped[UUID] = mapped_column(ForeignKey("butir_siklus.id", ondelete="CASCADE"))
    asesor_id: Mapped[UUID] = mapped_column(ForeignKey("pengguna.id", ondelete="CASCADE"))
    pengajuan_id: Mapped[UUID] = mapped_column(ForeignKey("laporan_pengajuan.id", ondelete="CASCADE"))
    sudah_ditelaah: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    catatan: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("butir_siklus_id", "asesor_id", "pengajuan_id"),)
