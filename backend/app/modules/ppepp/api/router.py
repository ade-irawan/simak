from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.permissions import SF, SP, D, K, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.dependencies import butuh, get_uow
from app.modules.ppepp.api.schemas import (
    ButirStandarIn,
    ButirStandarPatch,
    PenetapanIn,
    PenetapanPatch,
    SiklusPpeppIn,
    StandarIn,
    StandarPatch,
    TahapanIn,
)
from app.modules.ppepp.application.layanan import LayananPpepp

router = APIRouter(tags=["ppepp"])


def _svc(uow: UnitOfWork = Depends(get_uow)) -> LayananPpepp:
    return LayananPpepp(uow)


# ---- katalog standar SPM ----
@router.get("/standar-spm")
async def daftar_standar(_: Pemanggil = Depends(butuh(D, K, SF)), svc: LayananPpepp = Depends(_svc)):
    return await svc.daftar_standar()


@router.post("/standar-spm", status_code=201)
async def buat_standar(data: StandarIn, pemanggil: Pemanggil = Depends(butuh(SF)), svc: LayananPpepp = Depends(_svc)):
    return await svc.buat_standar(pemanggil, data)


@router.patch("/standar-spm/{standar_id}")
async def ubah_standar(standar_id: UUID, data: StandarPatch, pemanggil: Pemanggil = Depends(butuh(SF)), svc: LayananPpepp = Depends(_svc)):
    return await svc.ubah_standar(pemanggil, standar_id, data)


@router.post("/standar-spm/{standar_id}/butir", status_code=201)
async def tambah_butir_standar(
    standar_id: UUID, data: ButirStandarIn, pemanggil: Pemanggil = Depends(butuh(SF)), svc: LayananPpepp = Depends(_svc)
):
    return await svc.tambah_butir_standar(pemanggil, standar_id, data)


@router.patch("/butir-standar/{butir_id}")
async def ubah_butir_standar(
    butir_id: UUID, data: ButirStandarPatch, pemanggil: Pemanggil = Depends(butuh(SF)), svc: LayananPpepp = Depends(_svc)
):
    return await svc.ubah_butir_standar(pemanggil, butir_id, data)


@router.post("/standar-spm/{standar_id}/validasi")
async def validasi_standar(standar_id: UUID, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananPpepp = Depends(_svc)):
    return await svc.validasi_standar(pemanggil, standar_id)


# ---- siklus PPEPP & penetapan (P1) ----
@router.get("/siklus-ppepp")
async def daftar_siklus(_: Pemanggil = Depends(butuh(D, K, SP, SF)), svc: LayananPpepp = Depends(_svc)):
    return await svc.daftar_siklus()


@router.post("/siklus-ppepp", status_code=201)
async def buat_siklus(data: SiklusPpeppIn, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananPpepp = Depends(_svc)):
    return await svc.buat_siklus(pemanggil, data)


@router.get("/siklus-ppepp/{siklus_id}/penetapan")
async def daftar_penetapan(
    siklus_id: UUID, prodi_id: UUID | None = None, pemanggil: Pemanggil = Depends(butuh(D, K, SP, SF)), svc: LayananPpepp = Depends(_svc)
):
    return await svc.daftar_penetapan(pemanggil, siklus_id, prodi_id)


@router.post("/siklus-ppepp/{siklus_id}/penetapan", status_code=201)
async def tambah_penetapan(siklus_id: UUID, data: PenetapanIn, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananPpepp = Depends(_svc)):
    return await svc.tambah_penetapan(pemanggil, siklus_id, data)


@router.patch("/penetapan/{penetapan_id}")
async def ubah_penetapan(
    penetapan_id: UUID, data: PenetapanPatch, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananPpepp = Depends(_svc)
):
    return await svc.ubah_penetapan(pemanggil, penetapan_id, data)


@router.delete("/penetapan/{penetapan_id}")
async def batalkan_penetapan(penetapan_id: UUID, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananPpepp = Depends(_svc)):
    return await svc.batalkan_penetapan(pemanggil, penetapan_id)


@router.post("/siklus-ppepp/{siklus_id}/tetapkan")
async def tetapkan(siklus_id: UUID, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananPpepp = Depends(_svc)):
    return await svc.tetapkan(pemanggil, siklus_id)


@router.post("/siklus-ppepp/{siklus_id}/selesai")
async def selesai(siklus_id: UUID, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananPpepp = Depends(_svc)):
    return await svc.selesaikan(pemanggil, siklus_id)


@router.get("/siklus-ppepp/{siklus_id}/rekap")
async def rekap(siklus_id: UUID, _: Pemanggil = Depends(butuh(D)), svc: LayananPpepp = Depends(_svc)):
    return await svc.rekap(siklus_id)


# ---- tahapan P2–P5 ----
@router.get("/penetapan/{penetapan_id}/tahapan")
async def tahapan(
    penetapan_id: UUID, prodi_id: UUID | None = None, pemanggil: Pemanggil = Depends(butuh(D, K, SP, SF)), svc: LayananPpepp = Depends(_svc)
):
    return await svc.tahapan(pemanggil, penetapan_id, prodi_id)


@router.put("/penetapan/{penetapan_id}/tahapan/{tahap}")
async def isi_tahapan(
    penetapan_id: UUID,
    tahap: str,
    data: TahapanIn,
    prodi_id: UUID | None = None,
    pemanggil: Pemanggil = Depends(butuh(K, SP, SF)),
    svc: LayananPpepp = Depends(_svc),
):
    return await svc.isi_tahapan(pemanggil, penetapan_id, tahap, prodi_id, data)
