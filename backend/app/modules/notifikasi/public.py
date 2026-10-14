"""Pintu publik ``notifikasi``: modul lain memakai ``kirim`` bila perlu notifikasi langsung;
umumnya efek samping dijalankan lewat peristiwa domain (lihat application/penangan.py)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifikasi.infrastructure.models import Notifikasi


async def kirim(
    session: AsyncSession, pengguna_id: UUID, jenis: str, judul: str, isi: str | None = None, tautan: str | None = None
) -> None:
    session.add(Notifikasi(pengguna_id=pengguna_id, jenis=jenis, judul=judul, isi=isi, tautan=tautan))


__all__ = ["Notifikasi", "kirim"]
