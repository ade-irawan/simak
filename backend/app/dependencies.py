"""Dependensi FastAPI bersama (akar komposisi): pemanggil terautentikasi, pemeriksa peran, UnitOfWork."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import audit
from app.core.database import get_session
from app.core.exceptions import AksesDitolak, TidakTerautentikasi
from app.core.permissions import PERAN_KONTEN, SF, SP, Pemanggil, Peran
from app.core.security import baca_access_token
from app.core.unit_of_work import UnitOfWork
from app.modules.pengguna import public as pengguna_public
from app.modules.siklus import public as siklus_public

_bearer = HTTPBearer(auto_error=False, description="JWT akses dari /auth/login")


async def get_pemanggil(
    request: Request,
    kredensial: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> Pemanggil:
    if kredensial is None:
        raise TidakTerautentikasi()
    payload = baca_access_token(kredensial.credentials)
    try:
        pengguna_id = UUID(payload["sub"])
    except ValueError as exc:
        raise TidakTerautentikasi("Token tidak sah.") from exc
    ip = request.client.host if request.client else None
    pemanggil = await pengguna_public.muat_pemanggil(session, pengguna_id, ip, request.headers.get("user-agent"))
    if pemanggil is None:
        raise TidakTerautentikasi("Sesi tidak berlaku.")  # akun dinonaktifkan / dihapus
    if not pemanggil.penugasan:
        # Semua penugasan berakhir (mis. jendela asesmen lewat): ditolak total dan dicatat (EC-26).
        await audit.catat_mandiri(
            "akses.ditolak",
            pengguna_id=pemanggil.id,
            ip=ip,
            user_agent=request.headers.get("user-agent"),
            detail={"alasan": "tanpa_penugasan_aktif", "path": request.url.path},
        )
        raise AksesDitolak("Akses Anda telah berakhir atau belum diaktifkan.", alasan="tanpa_penugasan_aktif", dicatat=True)
    if pemanggil.punya(SP, SF):
        ditugaskan = await siklus_public.prodi_ditugaskan(session, pemanggil.id)
        pemanggil = replace(pemanggil, prodi_ditugaskan=ditugaskan)
    request.state.pemanggil = pemanggil
    return pemanggil


def butuh(*peran: Peran) -> Callable[..., Pemanggil]:
    """Dependensi: pemanggil harus memiliki salah satu peran. Gagal → 403 + log audit."""

    async def dependensi(pemanggil: Pemanggil = Depends(get_pemanggil)) -> Pemanggil:
        pemanggil.wajib(*peran)
        return pemanggil

    return dependensi


def butuh_konten(exclude: tuple[Peran, ...] = ()) -> Callable[..., Pemanggil]:
    """Peran yang boleh menyentuh isi data akreditasi (semua kecuali Admin IT), dikurangi ``exclude``."""
    izin = tuple(p for p in PERAN_KONTEN if p not in exclude)
    return butuh(*izin)


async def get_uow(session: AsyncSession = Depends(get_session)) -> UnitOfWork:
    return UnitOfWork(session)


__all__ = ["SP", "SF", "butuh", "butuh_konten", "get_pemanggil", "get_uow"]
