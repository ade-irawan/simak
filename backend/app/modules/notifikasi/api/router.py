from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import TidakDitemukan
from app.core.pagination import ParamHalaman, halaman
from app.core.permissions import Pemanggil
from app.dependencies import get_pemanggil
from app.modules.notifikasi.infrastructure.models import Notifikasi

router = APIRouter(tags=["notifikasi"])


def _out(n: Notifikasi) -> dict:
    return {
        "id": n.id,
        "jenis": n.jenis,
        "judul": n.judul,
        "isi": n.isi,
        "tautan": n.tautan,
        "dibaca_pada": n.dibaca_pada,
        "created_at": n.created_at,
    }


@router.get("/notifikasi")
async def daftar_notifikasi(
    belum_dibaca: bool = False,
    param: ParamHalaman = Depends(),
    pemanggil: Pemanggil = Depends(get_pemanggil),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Notifikasi).where(Notifikasi.pengguna_id == pemanggil.id)
    if belum_dibaca:
        stmt = stmt.where(Notifikasi.dibaca_pada.is_(None))
    hasil = await halaman(session, stmt, param, [Notifikasi.created_at.desc()], _out)
    hasil["meta"]["belum_dibaca"] = (
        await session.execute(
            select(func.count()).select_from(Notifikasi).where(Notifikasi.pengguna_id == pemanggil.id, Notifikasi.dibaca_pada.is_(None))
        )
    ).scalar_one()
    return hasil


@router.post("/notifikasi/{notifikasi_id}/baca")
async def tandai_dibaca(notifikasi_id: UUID, pemanggil: Pemanggil = Depends(get_pemanggil), session: AsyncSession = Depends(get_session)):
    hasil = await session.execute(
        update(Notifikasi)
        .where(Notifikasi.id == notifikasi_id, Notifikasi.pengguna_id == pemanggil.id)
        .values(dibaca_pada=datetime.now(UTC))
        .returning(Notifikasi.id)
    )
    if hasil.first() is None:
        raise TidakDitemukan()
    await session.commit()
    return {"id": notifikasi_id, "dibaca": True}
