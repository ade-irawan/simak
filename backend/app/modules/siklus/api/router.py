from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.pagination import ParamHalaman
from app.core.permissions import SF, SP, D, K, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.dependencies import butuh, get_uow
from app.modules.siklus.api.schemas import (
    ButirSiklusPatch,
    MigrasiIn,
    NarasiIn,
    PenugasanButirIn,
    PenugasanMassalIn,
    SiklusIn,
    SiklusPatch,
)
from app.modules.siklus.application.layanan import LayananSiklus

router = APIRouter(tags=["siklus"])
baca = butuh(D, K, SP, SF)


def _svc(uow: UnitOfWork = Depends(get_uow)) -> LayananSiklus:
    return LayananSiklus(uow)


@router.get("/siklus")
async def daftar_siklus(_: Pemanggil = Depends(baca), pemanggil: Pemanggil = Depends(baca), svc: LayananSiklus = Depends(_svc)):
    return await svc.daftar(pemanggil)


@router.post("/siklus", status_code=201)
async def buka_siklus(data: SiklusIn, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananSiklus = Depends(_svc)):
    return await svc.buka(pemanggil, data)


@router.get("/siklus/{siklus_id}")
async def rincian_siklus(siklus_id: UUID, pemanggil: Pemanggil = Depends(baca), svc: LayananSiklus = Depends(_svc)):
    return await svc.rincian(pemanggil, siklus_id)


@router.patch("/siklus/{siklus_id}")
async def ubah_siklus(siklus_id: UUID, data: SiklusPatch, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananSiklus = Depends(_svc)):
    return await svc.ubah(pemanggil, siklus_id, data)


@router.post("/siklus/{siklus_id}/migrasi-instrumen")
async def migrasi_instrumen(siklus_id: UUID, data: MigrasiIn, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananSiklus = Depends(_svc)):
    return await svc.migrasi(pemanggil, siklus_id, data.instrumen_versi_id)


@router.get("/siklus/{siklus_id}/butir")
async def daftar_butir(
    siklus_id: UUID,
    param: ParamHalaman = Depends(),
    status_kelengkapan: str | None = None,
    kriteria: str | None = None,
    pengelola: str | None = None,
    penanggung_jawab_id: UUID | None = None,
    belum_ditugaskan: bool = Query(False),
    bukti_bermasalah: bool = Query(False),
    menunggu_dokumen_eksternal: bool = Query(False),
    pemanggil: Pemanggil = Depends(baca),
    svc: LayananSiklus = Depends(_svc),
):
    filt = {
        "status_kelengkapan": status_kelengkapan,
        "kriteria": kriteria,
        "pengelola": pengelola,
        "penanggung_jawab_id": penanggung_jawab_id,
        "belum_ditugaskan": belum_ditugaskan,
        "bukti_bermasalah": bukti_bermasalah,
        "menunggu_dokumen_eksternal": menunggu_dokumen_eksternal,
    }
    return await svc.daftar_butir(pemanggil, siklus_id, param, filt)


@router.get("/siklus/{siklus_id}/butir-belum-ditugaskan")
async def belum_ditugaskan(siklus_id: UUID, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananSiklus = Depends(_svc)):
    return await svc.antrean_belum_ditugaskan(pemanggil, siklus_id)


@router.post("/siklus/{siklus_id}/penugasan-massal")
async def penugasan_massal(
    siklus_id: UUID, data: PenugasanMassalIn, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananSiklus = Depends(_svc)
):
    return await svc.penugasan_massal(pemanggil, siklus_id, data)


@router.get("/saya/butir")
async def papan_saya(pemanggil: Pemanggil = Depends(butuh(SP, SF)), svc: LayananSiklus = Depends(_svc)):
    return await svc.papan_saya(pemanggil)


@router.get("/butir-siklus/{butir_id}")
async def detail_butir(butir_id: UUID, pemanggil: Pemanggil = Depends(baca), svc: LayananSiklus = Depends(_svc)):
    return await svc.detail_butir(pemanggil, butir_id)


@router.patch("/butir-siklus/{butir_id}")
async def ubah_butir(
    butir_id: UUID, data: ButirSiklusPatch, pemanggil: Pemanggil = Depends(butuh(K, SP, SF)), svc: LayananSiklus = Depends(_svc)
):
    return await svc.ubah_butir(pemanggil, butir_id, data)


@router.get("/butir-siklus/{butir_id}/data")
async def data_terpetakan(butir_id: UUID, pemanggil: Pemanggil = Depends(baca), svc: LayananSiklus = Depends(_svc)):
    return await svc.data_terpetakan(pemanggil, butir_id)


@router.put("/butir-siklus/{butir_id}/narasi/{bagian}")
async def simpan_narasi(
    butir_id: UUID, bagian: str, data: NarasiIn, pemanggil: Pemanggil = Depends(butuh(K, SP, SF)), svc: LayananSiklus = Depends(_svc)
):
    """Peran selain Kaprodi dijawab 403 (EC-30), termasuk bila ia penanggung jawab butir."""
    return await svc.simpan_narasi(pemanggil, butir_id, bagian, data)


@router.put("/butir-siklus/{butir_id}/penugasan")
async def tetapkan_penugasan(
    butir_id: UUID, data: PenugasanButirIn, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananSiklus = Depends(_svc)
):
    return await svc.tetapkan_penugasan(pemanggil, butir_id, data)
