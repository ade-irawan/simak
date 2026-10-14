from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.pagination import ParamHalaman
from app.core.permissions import SF, SP, A, D, K, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.dependencies import butuh, get_uow
from app.infrastructure.http.link_probe import HttpLinkProbe
from app.infrastructure.storage.minio_storage import dapatkan_penyimpanan
from app.modules.bukti.api.schemas import BuktiIn, BuktiPatch, TautkanButirIn, UnggahanIn
from app.modules.bukti.application.layanan import LayananBukti
from app.modules.bukti.domain.entities import JenisBukti, StatusCekBukti

router = APIRouter(tags=["bukti"])


def _layanan(uow: UnitOfWork = Depends(get_uow)) -> LayananBukti:
    return LayananBukti(uow, dapatkan_penyimpanan(), HttpLinkProbe())


@router.post("/bukti/unggahan")
async def minta_url_unggah(data: UnggahanIn, pemanggil: Pemanggil = Depends(butuh(K, SP, SF)), svc: LayananBukti = Depends(_layanan)):
    return await svc.minta_url_unggah(pemanggil, data.nama_berkas, data.mime_type, data.ukuran_byte)


@router.post("/bukti", status_code=201)
async def daftarkan_bukti(data: BuktiIn, pemanggil: Pemanggil = Depends(butuh(K, SP, SF)), svc: LayananBukti = Depends(_layanan)):
    return await svc.daftarkan(pemanggil, data)


@router.get("/bukti")
async def daftar_bukti(
    param: ParamHalaman = Depends(),
    prodi_id: UUID | None = None,
    jenis: JenisBukti | None = None,
    status_cek: StatusCekBukti | None = None,
    pemanggil: Pemanggil = Depends(butuh(D, K, SP, SF)),
    svc: LayananBukti = Depends(_layanan),
):
    return await svc.daftar(pemanggil, param, prodi_id=prodi_id, jenis=jenis, status_cek=status_cek)


@router.get("/bukti/{bukti_id}")
async def rincian_bukti(bukti_id: UUID, pemanggil: Pemanggil = Depends(butuh(D, K, SP, SF, A)), svc: LayananBukti = Depends(_layanan)):
    return await svc.rincian(pemanggil, bukti_id)


@router.patch("/bukti/{bukti_id}")
async def ubah_bukti(
    bukti_id: UUID, data: BuktiPatch, pemanggil: Pemanggil = Depends(butuh(K, SP, SF)), svc: LayananBukti = Depends(_layanan)
):
    return await svc.ubah(pemanggil, bukti_id, data)


@router.delete("/bukti/{bukti_id}", status_code=204)
async def hapus_bukti(bukti_id: UUID, pemanggil: Pemanggil = Depends(butuh(K)), svc: LayananBukti = Depends(_layanan)):
    await svc.hapus(pemanggil, bukti_id)


@router.get("/bukti/{bukti_id}/unduh")
async def unduh_bukti(bukti_id: UUID, pemanggil: Pemanggil = Depends(butuh(D, K, SP, SF, A)), svc: LayananBukti = Depends(_layanan)):
    return await svc.unduh(pemanggil, bukti_id)


@router.post("/bukti/{bukti_id}/cek")
async def cek_bukti(bukti_id: UUID, pemanggil: Pemanggil = Depends(butuh(K, SP, SF)), svc: LayananBukti = Depends(_layanan)):
    return await svc.cek(pemanggil, bukti_id)


@router.put("/butir-siklus/{butir_siklus_id}/bukti/{bukti_id}")
async def tautkan_ke_butir(
    butir_siklus_id: UUID,
    bukti_id: UUID,
    data: TautkanButirIn | None = None,
    pemanggil: Pemanggil = Depends(butuh(K, SP, SF)),
    svc: LayananBukti = Depends(_layanan),
):
    return await svc.tautkan_butir(pemanggil, butir_siklus_id, bukti_id, data.keterangan if data else None)


@router.delete("/butir-siklus/{butir_siklus_id}/bukti/{bukti_id}", status_code=204)
async def lepas_dari_butir(
    butir_siklus_id: UUID, bukti_id: UUID, pemanggil: Pemanggil = Depends(butuh(K, SP, SF)), svc: LayananBukti = Depends(_layanan)
):
    await svc.lepas_butir(pemanggil, butir_siklus_id, bukti_id)
