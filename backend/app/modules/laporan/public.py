"""Pintu publik modul ``laporan``: status/penguncian, cuplikan yang disetujui.

Sengaja ringan (hanya model sendiri + ``siklus.public``) karena dipakai hampir semua modul penulis.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import LaporanTerkunci
from app.modules.laporan.domain.entities import KeputusanValidasi, StatusLaporan
from app.modules.laporan.domain.events import (
    LaporanDiajukan,
    LaporanDibukaKembali,
    LaporanDikembalikan,
    LaporanDisetujui,
)
from app.modules.laporan.domain.rules import TERKUNCI
from app.modules.laporan.infrastructure.models import (
    CatatanValidasi,
    EksporDokumen,
    Laporan,
    LaporanPengajuan,
)
from app.modules.siklus.public import SiklusAkreditasi, StatusSiklus

__all__ = [
    "CatatanValidasi",
    "EksporDokumen",
    "Laporan",
    "LaporanDibukaKembali",
    "LaporanDiajukan",
    "LaporanDikembalikan",
    "LaporanDisetujui",
    "LaporanPengajuan",
    "StatusLaporan",
    "ambil_atau_buat",
    "bukti_ada_di_cuplikan_disetujui",
    "catatan_butir",
    "catatan_terbuka_per_butir",
    "cuplikan_disetujui_terakhir",
    "prodi_punya_laporan_disetujui",
    "status_siklus",
    "wajib_tidak_terkunci",
]

_BERJALAN = [StatusSiklus.PERSIAPAN, StatusSiklus.BERJALAN]


async def ambil_atau_buat(session: AsyncSession, siklus_id: UUID) -> Laporan:
    await session.execute(pg_insert(Laporan).values(siklus_id=siklus_id).on_conflict_do_nothing(index_elements=["siklus_id"]))
    return (await session.execute(select(Laporan).where(Laporan.siklus_id == siklus_id))).scalar_one()


async def status_siklus(session: AsyncSession, siklus_id: UUID) -> str:
    s = (await session.execute(select(Laporan.status).where(Laporan.siklus_id == siklus_id))).scalar_one_or_none()
    return (s or StatusLaporan.DRAFT).value


async def wajib_tidak_terkunci(session: AsyncSession, prodi_id: UUID) -> None:
    """Menolak penulisan bila laporan siklus berjalan milik prodi sedang menunggu validasi atau sudah disetujui."""
    status = (
        await session.execute(
            select(Laporan.status)
            .join(SiklusAkreditasi, SiklusAkreditasi.id == Laporan.siklus_id)
            .where(SiklusAkreditasi.prodi_id == prodi_id, SiklusAkreditasi.status.in_(_BERJALAN))
        )
    ).scalar_one_or_none()
    if status in TERKUNCI:
        raise LaporanTerkunci(details=[{"status_laporan": status.value}])


async def prodi_punya_laporan_disetujui(session: AsyncSession, prodi_id: UUID) -> bool:
    """Prasyarat aktivasi asesor (EC-28): ada pengajuan yang pernah disetujui Dekan untuk prodi ini."""
    return await cuplikan_disetujui_terakhir(session, prodi_id, hanya_cek=True) is not None


async def cuplikan_disetujui_terakhir(session: AsyncSession, prodi_id: UUID, *, hanya_cek: bool = False) -> dict[str, Any] | None:
    """Pengajuan disetujui terbaru untuk prodi — satu-satunya sumber tampilan asesor (EC-29)."""
    kolom = [LaporanPengajuan.id, LaporanPengajuan.nomor, LaporanPengajuan.diputuskan_pada, Laporan.siklus_id]
    if not hanya_cek:
        kolom.append(LaporanPengajuan.cuplikan)
    baris = (
        await session.execute(
            select(*kolom)
            .join(Laporan, Laporan.id == LaporanPengajuan.laporan_id)
            .join(SiklusAkreditasi, SiklusAkreditasi.id == Laporan.siklus_id)
            .where(SiklusAkreditasi.prodi_id == prodi_id, LaporanPengajuan.keputusan == KeputusanValidasi.DISETUJUI)
            .order_by(LaporanPengajuan.diputuskan_pada.desc())
            .limit(1)
        )
    ).first()
    if baris is None:
        return None
    hasil: dict[str, Any] = {"pengajuan_id": baris[0], "nomor": baris[1], "disetujui_pada": baris[2], "siklus_id": baris[3]}
    if not hanya_cek:
        hasil["cuplikan"] = baris[4]
    return hasil


async def bukti_ada_di_cuplikan_disetujui(session: AsyncSession, prodi_id: UUID, bukti_id: UUID) -> bool:
    c = await cuplikan_disetujui_terakhir(session, prodi_id, hanya_cek=True)
    if c is None:
        return False
    ada = (
        await session.execute(
            select(LaporanPengajuan.id).where(
                LaporanPengajuan.id == c["pengajuan_id"], LaporanPengajuan.cuplikan["bukti_ids"].contains([str(bukti_id)])
            )
        )
    ).first()
    return ada is not None


async def catatan_terbuka_per_butir(session: AsyncSession, butir_siklus_ids: list[UUID]) -> dict[UUID, int]:
    """Jumlah catatan validasi Dekan yang belum ditindaklanjuti, per butir."""
    from sqlalchemy import func

    from app.modules.laporan.domain.entities import StatusCatatan

    if not butir_siklus_ids:
        return {}
    baris = (
        await session.execute(
            select(CatatanValidasi.butir_siklus_id, func.count())
            .where(CatatanValidasi.butir_siklus_id.in_(butir_siklus_ids), CatatanValidasi.status == StatusCatatan.TERBUKA)
            .group_by(CatatanValidasi.butir_siklus_id)
        )
    ).all()
    return dict(baris)


async def catatan_butir(session: AsyncSession, butir_siklus_id: UUID) -> list[dict[str, Any]]:
    baris = (
        (
            await session.execute(
                select(CatatanValidasi)
                .where(CatatanValidasi.butir_siklus_id == butir_siklus_id)
                .order_by(CatatanValidasi.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [{"id": c.id, "isi": c.isi, "status": c.status, "created_at": c.created_at} for c in baris]
