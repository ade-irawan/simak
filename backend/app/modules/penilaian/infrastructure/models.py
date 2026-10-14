from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, PkUuid


class SimulasiSkor(PkUuid, Base):
    __tablename__ = "simulasi_skor"
    siklus_id: Mapped[UUID] = mapped_column(ForeignKey("siklus_akreditasi.id", ondelete="CASCADE"))
    nilai_akhir: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    prediksi_peringkat_id: Mapped[UUID | None] = mapped_column(ForeignKey("instrumen_peringkat.id"))
    rincian: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    dihitung_oleh: Mapped[UUID | None] = mapped_column(ForeignKey("pengguna.id"))
    dihitung_pada: Mapped[datetime] = mapped_column(server_default=text("now()"))


class NilaiIndikator(PkUuid, Base):
    __tablename__ = "nilai_indikator"
    indikator_inti_id: Mapped[UUID] = mapped_column(ForeignKey("indikator_inti.id", ondelete="CASCADE"))
    prodi_id: Mapped[UUID] = mapped_column(ForeignKey("prodi.id"))
    tahun_akademik_id: Mapped[UUID] = mapped_column(ForeignKey("tahun_akademik.id"))
    nilai: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    rincian: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    dihitung_pada: Mapped[datetime] = mapped_column(server_default=text("now()"))
    __table_args__ = (UniqueConstraint("indikator_inti_id", "prodi_id", "tahun_akademik_id"),)
