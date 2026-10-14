"""Pembacaan log audit. Dekan melihat semuanya; Admin IT hanya lapisan akun/sistem dan detail disamarkan."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.database import get_session
from app.core.pagination import ParamHalaman, halaman
from app.core.permissions import IT, D, Pemanggil
from app.dependencies import butuh
from app.modules.pengguna.public import Pengguna
from app.modules.referensi.public import Prodi

router = APIRouter(tags=["audit"])

_AKSI_SISTEM = ("login.", "logout", "akun.", "sandi.", "pengguna.", "penugasan.", "pengaturan.", "akses.")
_DETAIL_AMAN = {"alasan", "sisa", "sampai", "kunci", "peran", "email"}


def _samarkan(detail: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in (detail or {}).items() if k in _DETAIL_AMAN}


@router.get("/log-audit")
async def baca_log(
    param: ParamHalaman = Depends(),
    pengguna_id: UUID | None = None,
    aksi: str | None = None,
    entitas: str | None = None,
    prodi_id: UUID | None = None,
    dari: datetime | None = None,
    sampai: datetime | None = None,
    pemanggil: Pemanggil = Depends(butuh(D, IT)),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(log_audit, Pengguna.nama.label("nama_pengguna"), Prodi.kode.label("kode_prodi"))
        .join(Pengguna, Pengguna.id == log_audit.c.pengguna_id, isouter=True)
        .join(Prodi, Prodi.id == log_audit.c.prodi_id, isouter=True)
    )
    hanya_it = not pemanggil.punya(D)
    if hanya_it:
        stmt = stmt.where(or_(*[log_audit.c.aksi.startswith(a) for a in _AKSI_SISTEM]))
    if pengguna_id:
        stmt = stmt.where(log_audit.c.pengguna_id == pengguna_id)
    if aksi:
        stmt = stmt.where(log_audit.c.aksi.startswith(aksi))
    if entitas:
        stmt = stmt.where(log_audit.c.entitas == entitas)
    if prodi_id:
        stmt = stmt.where(log_audit.c.prodi_id == prodi_id)
    if dari:
        stmt = stmt.where(log_audit.c.waktu >= dari)
    if sampai:
        stmt = stmt.where(log_audit.c.waktu <= sampai)

    def ubah(b: Any) -> dict[str, Any]:
        return {
            "id": b.id,
            "waktu": b.waktu,
            "pengguna": {"id": b.pengguna_id, "nama": b.nama_pengguna} if b.pengguna_id else None,
            "peran": b.peran,
            "aksi": b.aksi,
            "entitas": b.entitas,
            "entitas_id": b.entitas_id,
            "prodi": b.kode_prodi,
            "ip": str(b.ip) if b.ip else None,
            "detail": _samarkan(b.detail) if hanya_it else b.detail,
        }

    urutan = param.urutan({"waktu": log_audit.c.waktu}, [log_audit.c.waktu.desc()])
    return await halaman(session, stmt, param, urutan, ubah, skalar=False)
