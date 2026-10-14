from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.permissions import SF, D, K, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.dependencies import butuh, get_uow
from app.infrastructure.antrean import kirim_tugas
from app.infrastructure.llm.openai_compatible import KlienOpenAICompatible
from app.modules.llm.api.schemas import AktifkanIn, DrafIn, KonfigurasiIn, KonfigurasiPatch
from app.modules.llm.application.layanan import LayananLlm

router = APIRouter(tags=["llm"])


def _svc(uow: UnitOfWork = Depends(get_uow)) -> LayananLlm:
    return LayananLlm(uow, KlienOpenAICompatible(), kirim_tugas)


@router.get("/konfigurasi-llm")
async def daftar(_: Pemanggil = Depends(butuh(D, SF)), svc: LayananLlm = Depends(_svc)):
    return await svc.daftar()


@router.post("/konfigurasi-llm", status_code=201)
async def buat(data: KonfigurasiIn, pemanggil: Pemanggil = Depends(butuh(SF)), svc: LayananLlm = Depends(_svc)):
    return await svc.buat(pemanggil, data)


@router.patch("/konfigurasi-llm/{konfigurasi_id}")
async def ubah(konfigurasi_id: UUID, data: KonfigurasiPatch, pemanggil: Pemanggil = Depends(butuh(SF)), svc: LayananLlm = Depends(_svc)):
    return await svc.ubah(pemanggil, konfigurasi_id, data)


@router.post("/konfigurasi-llm/{konfigurasi_id}/uji")
async def uji(konfigurasi_id: UUID, pemanggil: Pemanggil = Depends(butuh(D, SF)), svc: LayananLlm = Depends(_svc)):
    return await svc.uji(pemanggil, konfigurasi_id)


@router.post("/konfigurasi-llm/{konfigurasi_id}/aktifkan")
async def aktifkan(
    konfigurasi_id: UUID, data: AktifkanIn | None = None, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananLlm = Depends(_svc)
):
    return await svc.aktifkan(pemanggil, konfigurasi_id, bool(data and data.konfirmasi_online))


@router.post("/konfigurasi-llm/{konfigurasi_id}/nonaktifkan")
async def nonaktifkan(konfigurasi_id: UUID, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananLlm = Depends(_svc)):
    return await svc.nonaktifkan(pemanggil, konfigurasi_id)


@router.post("/butir-siklus/{butir_siklus_id}/narasi/{bagian}/draf-llm", status_code=202)
async def minta_draf(
    butir_siklus_id: UUID,
    bagian: str,
    data: DrafIn | None = None,
    pemanggil: Pemanggil = Depends(butuh(K)),
    svc: LayananLlm = Depends(_svc),
):
    data = data or DrafIn()
    return await svc.minta_draf(pemanggil, butir_siklus_id, bagian, data.arahan, data.sertakan_data_terpetakan)


@router.get("/permintaan-llm/{permintaan_id}")
async def status_permintaan(permintaan_id: UUID, pemanggil: Pemanggil = Depends(butuh(K)), svc: LayananLlm = Depends(_svc)):
    return await svc.status(pemanggil, permintaan_id)
