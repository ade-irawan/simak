"""Pintu publik ``llm``."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import StatusTugas
from app.modules.llm.infrastructure.models import KonfigurasiLlm, PermintaanLlm

__all__ = ["KonfigurasiLlm", "PermintaanLlm", "hasil_permintaan"]


async def hasil_permintaan(session: AsyncSession, permintaan_id: UUID, butir_siklus_id: UUID) -> str | None:
    """Teks draf LLM yang sudah selesai untuk butir ini; None bila tidak ada/belum selesai/bukan milik butir ini."""
    return (
        await session.execute(
            select(PermintaanLlm.hasil).where(
                PermintaanLlm.id == permintaan_id,
                PermintaanLlm.butir_siklus_id == butir_siklus_id,
                PermintaanLlm.status == StatusTugas.SELESAI,
            )
        )
    ).scalar_one_or_none()
