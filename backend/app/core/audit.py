"""Pencatat ``log_audit`` (hanya-tambah). Dipakai semua modul; pembacaannya ada di modul ``audit``."""

from __future__ import annotations

import ipaddress
import logging
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import BigInteger, Column, DateTime, Identity, Table, Text, insert, text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, get_session_factory, pg_enum
from app.core.permissions import Pemanggil, Peran

logger = logging.getLogger(__name__)

log_audit = Table(
    "log_audit",
    Base.metadata,
    Column("id", BigInteger, Identity(always=True), primary_key=True),
    Column("waktu", DateTime(timezone=True), server_default=text("now()")),
    Column("pengguna_id", PGUUID(as_uuid=True)),
    Column("peran", pg_enum(Peran, "peran_pengguna")),
    Column("aksi", Text, nullable=False),
    Column("entitas", Text),
    Column("entitas_id", PGUUID(as_uuid=True)),
    Column("prodi_id", PGUUID(as_uuid=True)),
    Column("ip", INET),
    Column("user_agent", Text),
    Column("detail", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
)


def _ip(nilai: str | None) -> Any:
    if not nilai:
        return None
    try:
        return ipaddress.ip_address(nilai)
    except ValueError:
        return None


def _baris(
    aksi: str,
    pemanggil: Pemanggil | None,
    pengguna_id: UUID | None,
    peran: Peran | None,
    entitas: str | None,
    entitas_id: UUID | None,
    prodi_id: UUID | None,
    detail: dict[str, Any] | None,
    ip: str | None,
    user_agent: str | None,
) -> dict[str, Any]:
    return {
        "aksi": aksi,
        "pengguna_id": pemanggil.id if pemanggil else pengguna_id,
        "peran": (pemanggil.peran_utama() if pemanggil else None) or peran,
        "entitas": entitas,
        "entitas_id": entitas_id,
        "prodi_id": prodi_id,
        "ip": _ip(pemanggil.ip if pemanggil else ip),
        "user_agent": (pemanggil.user_agent if pemanggil else user_agent),
        "detail": jsonable_encoder(detail or {}),
    }


async def catat(
    session: AsyncSession,
    aksi: str,
    *,
    pemanggil: Pemanggil | None = None,
    pengguna_id: UUID | None = None,
    peran: Peran | None = None,
    entitas: str | None = None,
    entitas_id: UUID | None = None,
    prodi_id: UUID | None = None,
    detail: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Mencatat dalam transaksi yang sama dengan perubahan datanya."""
    await session.execute(
        insert(log_audit).values(**_baris(aksi, pemanggil, pengguna_id, peran, entitas, entitas_id, prodi_id, detail, ip, user_agent))
    )


async def catat_mandiri(aksi: str, **kw: Any) -> None:
    """Mencatat di transaksi sendiri, agar tetap tersimpan walau transaksi permintaan di-rollback
    (mis. akses ditolak, login gagal). Kegagalan pencatatan tidak boleh menjatuhkan permintaan."""
    try:
        async with get_session_factory()() as session:
            await catat(session, aksi, **kw)
            await session.commit()
    except Exception:  # pragma: no cover - jalur darurat
        logger.exception("Gagal menulis log audit: %s", aksi)
