from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.permissions import A, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.dependencies import butuh, get_uow
from app.modules.asesmen.application.layanan import LayananAsesmen

router = APIRouter(prefix="/asesmen", tags=["asesmen"])


class TelaahIn(BaseModel):
    sudah_ditelaah: bool
    catatan: str | None = None


def _svc(uow: UnitOfWork = Depends(get_uow)) -> LayananAsesmen:
    return LayananAsesmen(uow)


@router.get("/siklus")
async def daftar_siklus(pemanggil: Pemanggil = Depends(butuh(A)), svc: LayananAsesmen = Depends(_svc)):
    return await svc.daftar_siklus(pemanggil)


@router.get("/siklus/{siklus_id}/butir")
async def daftar_butir(siklus_id: UUID, pemanggil: Pemanggil = Depends(butuh(A)), svc: LayananAsesmen = Depends(_svc)):
    return await svc.daftar_butir(pemanggil, siklus_id)


@router.get("/butir/{butir_siklus_id}")
async def detail_butir(butir_siklus_id: UUID, pemanggil: Pemanggil = Depends(butuh(A)), svc: LayananAsesmen = Depends(_svc)):
    return await svc.detail_butir(pemanggil, butir_siklus_id)


@router.put("/butir/{butir_siklus_id}/telaah")
async def telaah(butir_siklus_id: UUID, data: TelaahIn, pemanggil: Pemanggil = Depends(butuh(A)), svc: LayananAsesmen = Depends(_svc)):
    return await svc.telaah(pemanggil, butir_siklus_id, data.sudah_ditelaah, data.catatan)
