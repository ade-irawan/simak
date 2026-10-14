"""Pintu publik ``dokumen_eksternal``."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dokumen_eksternal.infrastructure.models import (
    DokumenEksternal,
    DokumenEksternalProdi,
    IndikatorEksternal,
)
from app.modules.instrumen.public import AturanPemetaan

__all__ = [
    "DokumenEksternal",
    "DokumenEksternalProdi",
    "IndikatorEksternal",
    "ambil_indikator_terpetakan",
    "bukti_dipakai",
    "prodi_punya_indikator",
]


async def bukti_dipakai(session: AsyncSession, bukti_id: UUID) -> bool:
    return (
        await session.execute(
            select(DokumenEksternal.id).where(DokumenEksternal.bukti_id == bukti_id, DokumenEksternal.deleted_at.is_(None)).limit(1)
        )
    ).first() is not None


async def prodi_punya_indikator(session: AsyncSession, prodi_id: UUID) -> bool:
    n = (
        await session.execute(
            select(func.count())
            .select_from(IndikatorEksternal)
            .join(DokumenEksternal, DokumenEksternal.id == IndikatorEksternal.dokumen_id)
            .where(IndikatorEksternal.prodi_id == prodi_id, DokumenEksternal.deleted_at.is_(None))
        )
    ).scalar_one()
    return n > 0


async def ambil_indikator_terpetakan(
    session: AsyncSession, aturan: AturanPemetaan, prodi_id: UUID, tahun_ids: list[UUID], maks_contoh: int = 25
) -> dict[str, Any]:
    stmt = (
        select(IndikatorEksternal, DokumenEksternal.judul)
        .join(DokumenEksternal, DokumenEksternal.id == IndikatorEksternal.dokumen_id)
        .where(IndikatorEksternal.prodi_id == prodi_id, DokumenEksternal.deleted_at.is_(None))
    )
    if aturan.aturan.get("batasi_tahun", True) and tahun_ids:
        stmt = stmt.where(DokumenEksternal.tahun_akademik_id.in_(tahun_ids))
    kode = aturan.aturan.get("filter", {}).get("kode")
    if kode:
        stmt = stmt.where(IndikatorEksternal.kode.in_(kode if isinstance(kode, list) else [kode]))
    baris = (await session.execute(stmt.order_by(IndikatorEksternal.kode).limit(maks_contoh))).all()
    return {
        "sumber": aturan.sumber.value,
        "keterangan": aturan.keterangan,
        "agregasi": "daftar",
        "jumlah": len(baris),
        "nilai": None,
        "contoh": [
            {
                "id": i.id,
                "label": f"{i.nama}: {i.nilai if i.data_memadai else 'data tidak memadai'} {i.satuan or ''}".strip(),
                "dokumen": judul,
            }
            for i, judul in baris
        ],
    }
