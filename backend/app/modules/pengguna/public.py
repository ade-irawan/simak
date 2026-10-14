"""Pintu publik modul ``pengguna`` (identitas, penugasan, token). Dipakai ``auth`` dan komposisi aplikasi."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Pemanggil, Penugasan, Peran
from app.modules.pengguna.application.token import (
    buat_token_akun,
    cabut_refresh,
    cabut_semua_refresh,
    pakai_token_akun,
    putar_refresh,
    terbitkan_refresh,
)
from app.modules.pengguna.domain import rules
from app.modules.pengguna.domain.entities import JenisTokenAkun, StatusPengguna, StatusPenugasan
from app.modules.pengguna.domain.events import AsesorDiaktifkan, TokenAkunDibuat
from app.modules.pengguna.infrastructure.models import Pengguna, PenugasanPeran

__all__ = [
    "AsesorDiaktifkan",
    "JenisTokenAkun",
    "Pengguna",
    "PenugasanPeran",
    "StatusPengguna",
    "TokenAkunDibuat",
    "buat_token_akun",
    "cabut_refresh",
    "cabut_semua_refresh",
    "cari_by_email",
    "hitung_gagal_login",
    "jumlah_asesor_aktif",
    "penerima",
    "muat_pemanggil",
    "nama_pengguna",
    "pakai_token_akun",
    "penugasan_aktif",
    "putar_refresh",
    "sedang_terkunci",
    "terbitkan_refresh",
]

hitung_gagal_login = rules.hitung_gagal_login
sedang_terkunci = rules.sedang_terkunci


async def cari_by_email(session: AsyncSession, email: str) -> Pengguna | None:
    return (await session.execute(select(Pengguna).where(Pengguna.email == email))).scalar_one_or_none()


async def penugasan_aktif(session: AsyncSession, pengguna_id: UUID, sekarang: datetime | None = None) -> tuple[Penugasan, ...]:
    """Penugasan yang berlaku saat ini: status aktif dan di dalam jendela waktunya (asesor berakhir otomatis)."""
    sekarang = sekarang or datetime.now(UTC)
    baris = (
        (
            await session.execute(
                select(PenugasanPeran).where(PenugasanPeran.pengguna_id == pengguna_id, PenugasanPeran.status == StatusPenugasan.AKTIF)
            )
        )
        .scalars()
        .all()
    )
    return tuple(
        Penugasan(b.id, b.peran, b.prodi_id, b.berlaku_mulai, b.berlaku_sampai)
        for b in baris
        if rules.penugasan_berlaku(b.berlaku_mulai, b.berlaku_sampai, sekarang)
    )


async def muat_pemanggil(
    session: AsyncSession, pengguna_id: UUID, ip: str | None = None, user_agent: str | None = None
) -> Pemanggil | None:
    pengguna = await session.get(Pengguna, pengguna_id)
    if pengguna is None or pengguna.status != StatusPengguna.AKTIF:
        return None
    return Pemanggil(
        id=pengguna.id,
        nama=pengguna.nama,
        email=pengguna.email,
        penugasan=await penugasan_aktif(session, pengguna.id),
        ip=ip,
        user_agent=user_agent,
    )


async def jumlah_asesor_aktif(session: AsyncSession, prodi_id: UUID) -> int:
    """Asesor yang saat ini boleh mengakses prodi (peringatan saat laporan dibuka kembali, EC-29)."""
    sekarang = datetime.now(UTC)
    baris = (
        (
            await session.execute(
                select(PenugasanPeran).where(
                    PenugasanPeran.prodi_id == prodi_id,
                    PenugasanPeran.peran == Peran.ASESOR,
                    PenugasanPeran.status == StatusPenugasan.AKTIF,
                )
            )
        )
        .scalars()
        .all()
    )
    return sum(1 for b in baris if rules.penugasan_berlaku(b.berlaku_mulai, b.berlaku_sampai, sekarang))


async def penerima(session: AsyncSession, peran: Peran, prodi_id: UUID | None = None) -> list[Pengguna]:
    """Pengguna aktif dengan peran tertentu (pada prodi tertentu bila disebut) — sasaran notifikasi."""
    stmt = (
        select(Pengguna)
        .join(PenugasanPeran, PenugasanPeran.pengguna_id == Pengguna.id)
        .where(PenugasanPeran.peran == peran, PenugasanPeran.status == StatusPenugasan.AKTIF, Pengguna.status == StatusPengguna.AKTIF)
        .distinct()
    )
    if prodi_id is not None:
        stmt = stmt.where(PenugasanPeran.prodi_id == prodi_id)
    return list((await session.execute(stmt)).scalars().all())


async def nama_pengguna(session: AsyncSession, ids: list[UUID]) -> dict[UUID, str]:
    if not ids:
        return {}
    baris = (await session.execute(select(Pengguna.id, Pengguna.nama).where(Pengguna.id.in_(set(ids))))).all()
    return dict(baris)
