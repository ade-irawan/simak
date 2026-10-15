from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile

from app.core.exceptions import ValidasiGagal
from app.core.pagination import ParamHalaman
from app.core.permissions import SF, SP, D, K, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.dependencies import butuh, get_uow
from app.modules.dokumen_eksternal.api.schemas import DokumenIn, DokumenPatch, IndikatorIn
from app.modules.dokumen_eksternal.application.layanan import LayananDokumenEksternal

router = APIRouter(tags=["dokumen-eksternal"])
BATAS_BYTE = 5 * 1024 * 1024


def _svc(uow: UnitOfWork = Depends(get_uow)) -> LayananDokumenEksternal:
    return LayananDokumenEksternal(uow)


@router.get("/dokumen-eksternal")
async def daftar(
    param: ParamHalaman = Depends(),
    jenis: str | None = None,
    prodi_id: UUID | None = None,
    tahun_akademik_id: UUID | None = None,
    pemanggil: Pemanggil = Depends(butuh(D, K, SP, SF)),
    svc: LayananDokumenEksternal = Depends(_svc),
):
    return await svc.daftar(pemanggil, param, jenis=jenis, prodi_id=prodi_id, tahun_akademik_id=tahun_akademik_id)


@router.post("/dokumen-eksternal", status_code=201)
async def buat(data: DokumenIn, pemanggil: Pemanggil = Depends(butuh(SF)), svc: LayananDokumenEksternal = Depends(_svc)):
    return await svc.buat(pemanggil, data)


@router.patch("/dokumen-eksternal/{dokumen_id}")
async def ubah(
    dokumen_id: UUID, data: DokumenPatch, pemanggil: Pemanggil = Depends(butuh(SF)), svc: LayananDokumenEksternal = Depends(_svc)
):
    return await svc.ubah(pemanggil, dokumen_id, data)


@router.put("/dokumen-eksternal/{dokumen_id}/indikator")
async def isi_indikator(
    dokumen_id: UUID, data: list[IndikatorIn], pemanggil: Pemanggil = Depends(butuh(SF)), svc: LayananDokumenEksternal = Depends(_svc)
):
    return await svc.isi_indikator(pemanggil, dokumen_id, data)


@router.get("/dokumen-eksternal/indikator/impor/templat")
async def templat_impor_indikator(
    format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    pemanggil: Pemanggil = Depends(butuh(SF)),
    svc: LayananDokumenEksternal = Depends(_svc),
):
    isi, tipe, nama = await svc.templat_indikator(format)
    return Response(isi, media_type=tipe, headers={"Content-Disposition": f'attachment; filename="{nama}"'})


@router.post("/dokumen-eksternal/{dokumen_id}/indikator/impor", status_code=202)
async def impor_indikator(
    dokumen_id: UUID,
    berkas: UploadFile = File(...),
    atomik: bool = Query(False),
    pemanggil: Pemanggil = Depends(butuh(SF)),
    svc: LayananDokumenEksternal = Depends(_svc),
):
    isi = await berkas.read(BATAS_BYTE + 1)
    if len(isi) > BATAS_BYTE:
        raise ValidasiGagal("Berkas impor terlalu besar (maks 5 MB).")
    return await svc.impor_indikator(pemanggil, dokumen_id, berkas.filename or "impor.csv", isi, atomik)


@router.get("/prodi/{prodi_id}/indikator-eksternal")
async def indikator_prodi(
    prodi_id: UUID, pemanggil: Pemanggil = Depends(butuh(D, K, SP, SF)), svc: LayananDokumenEksternal = Depends(_svc)
):
    return await svc.indikator_prodi(pemanggil, prodi_id)
