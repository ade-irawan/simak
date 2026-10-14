"""Pintu publik ``ppepp``."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.instrumen.public import AturanPemetaan
from app.modules.ppepp.domain.entities import StatusPenetapan, StatusSiklusPpepp, StatusTahapan
from app.modules.ppepp.infrastructure.models import PenetapanButir, SiklusPpepp, TahapanPpepp

__all__ = ["PenetapanButir", "SiklusPpepp", "TahapanPpepp", "ambil_tahapan_terpetakan", "rekap", "ringkasan_prodi"]

_AKTIF = [StatusSiklusPpepp.DITETAPKAN, StatusSiklusPpepp.BERJALAN]


async def ringkasan_prodi(session: AsyncSession, prodi_id: UUID) -> dict[str, int]:
    """Kemajuan PPEPP satu prodi pada siklus PPEPP yang sedang berjalan (untuk dasbor)."""
    siklus = (
        await session.execute(
            select(SiklusPpepp.id).where(SiklusPpepp.status.in_(_AKTIF)).order_by(SiklusPpepp.tanggal_mulai.desc()).limit(1)
        )
    ).scalar_one_or_none()
    if siklus is None:
        return {"butir_sasaran": 0, "tahap_selesai": 0, "tahap_total": 0}
    sasaran = (
        await session.execute(
            select(func.count())
            .select_from(PenetapanButir)
            .where(
                PenetapanButir.siklus_ppepp_id == siklus,
                PenetapanButir.status == StatusPenetapan.DITETAPKAN,
                (PenetapanButir.prodi_id == prodi_id) | PenetapanButir.prodi_id.is_(None),
            )
        )
    ).scalar_one()
    total, selesai = (
        await session.execute(
            select(func.count(), func.count().filter(TahapanPpepp.status == StatusTahapan.SELESAI))
            .select_from(TahapanPpepp)
            .join(PenetapanButir, PenetapanButir.id == TahapanPpepp.penetapan_butir_id)
            .where(PenetapanButir.siklus_ppepp_id == siklus, TahapanPpepp.prodi_id == prodi_id)
        )
    ).one()
    return {"butir_sasaran": sasaran, "tahap_selesai": selesai, "tahap_total": total}


async def ambil_tahapan_terpetakan(
    session: AsyncSession, aturan: AturanPemetaan, prodi_id: UUID, tahun_ids: list[UUID], maks_contoh: int = 25
) -> dict[str, Any]:
    """Tahapan PPEPP prodi sebagai bukti pelaksanaan SPMI pada butir terkait. ``filter.tahap`` opsional."""
    from app.modules.instrumen.public import TahapPpepp
    from app.modules.referensi.public import TahunAkademik

    stmt = (
        select(TahapanPpepp, PenetapanButir.nomor_butir)
        .join(PenetapanButir, PenetapanButir.id == TahapanPpepp.penetapan_butir_id)
        .join(SiklusPpepp, SiklusPpepp.id == PenetapanButir.siklus_ppepp_id)
        .where(TahapanPpepp.prodi_id == prodi_id)
    )
    if aturan.aturan.get("batasi_tahun", True) and tahun_ids:
        stmt = stmt.where(SiklusPpepp.tahun_akademik_id.in_(tahun_ids))
    tahap = aturan.aturan.get("filter", {}).get("tahap")
    if tahap:
        stmt = stmt.where(TahapanPpepp.tahap.in_([TahapPpepp(t) for t in (tahap if isinstance(tahap, list) else [tahap])]))
    if aturan.aturan.get("filter", {}).get("status"):
        stmt = stmt.where(TahapanPpepp.status == aturan.aturan["filter"]["status"])
    baris = (await session.execute(stmt.limit(maks_contoh))).all()
    _ = TahunAkademik
    return {
        "sumber": aturan.sumber.value,
        "keterangan": aturan.keterangan,
        "agregasi": "daftar",
        "jumlah": len(baris),
        "nilai": None,
        "contoh": [{"id": t.id, "label": f"{nomor} — {t.tahap.value} ({t.status.value})"} for t, nomor in baris],
    }


async def rekap(session: AsyncSession, siklus_ppepp_id: UUID) -> dict[str, Any]:
    """Rekap target vs capaian semua prodi (dasar gap analysis PPEPP)."""
    from app.core.unit_of_work import UnitOfWork
    from app.modules.ppepp.application.layanan import LayananPpepp

    return await LayananPpepp(UnitOfWork(session)).rekap(siklus_ppepp_id)
