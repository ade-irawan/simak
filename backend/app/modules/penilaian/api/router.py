from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.permissions import SF, SP, D, K, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.dependencies import butuh, get_uow
from app.modules.penilaian.application.layanan import LayananPenilaian

router = APIRouter(tags=["penilaian"])


def _svc(uow: UnitOfWork = Depends(get_uow)) -> LayananPenilaian:
    return LayananPenilaian(uow)


@router.get("/dasbor/fakultas")
async def dasbor_fakultas(
    tahun_akademik_id: UUID | None = None,
    prodi_id: UUID | None = None,
    pemanggil: Pemanggil = Depends(butuh(D, SF)),
    svc: LayananPenilaian = Depends(_svc),
):
    return await svc.dasbor_fakultas(pemanggil, tahun_akademik_id, prodi_id)


@router.get("/dasbor/prodi/{prodi_id}")
async def dasbor_prodi(prodi_id: UUID, pemanggil: Pemanggil = Depends(butuh(D, K, SP, SF)), svc: LayananPenilaian = Depends(_svc)):
    return await svc.dasbor_prodi(pemanggil, prodi_id)


@router.get("/siklus/{siklus_id}/simulasi-skor")
async def simulasi_terakhir(siklus_id: UUID, pemanggil: Pemanggil = Depends(butuh(D, K)), svc: LayananPenilaian = Depends(_svc)):
    return await svc.simulasi_terakhir(pemanggil, siklus_id)


@router.post("/siklus/{siklus_id}/simulasi-skor", status_code=201)
async def hitung_simulasi(siklus_id: UUID, pemanggil: Pemanggil = Depends(butuh(D, K)), svc: LayananPenilaian = Depends(_svc)):
    return await svc.hitung(pemanggil, siklus_id)


@router.get("/analisis/gap")
async def gap(
    siklus_id: UUID | None = None,
    siklus_ppepp_id: UUID | None = None,
    pemanggil: Pemanggil = Depends(butuh(D)),
    svc: LayananPenilaian = Depends(_svc),
):
    return await svc.gap(pemanggil, siklus_id, siklus_ppepp_id)


@router.get("/analisis/indikator")
async def daftar_indikator(pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananPenilaian = Depends(_svc)):
    return await svc.daftar_indikator(pemanggil)


@router.get("/analisis/benchmark")
async def benchmark(
    indikator: str,
    tahun_akademik_id: UUID,
    hitung_ulang: bool = Query(True),
    pemanggil: Pemanggil = Depends(butuh(D)),
    svc: LayananPenilaian = Depends(_svc),
):
    return await svc.benchmark(pemanggil, indikator, tahun_akademik_id, hitung_ulang)
