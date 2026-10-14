from __future__ import annotations

import json
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.core import audit
from app.core.exceptions import ValidasiGagal
from app.core.permissions import SF, SP, D, K, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.dependencies import butuh, get_uow
from app.modules.instrumen.api.schemas import ButirPatch, PemetaanItem
from app.modules.instrumen.application.impor import buat_templat_xlsx, impor_instrumen
from app.modules.instrumen.application.kelola import KelolaInstrumen
from app.modules.referensi.public import Lam

router = APIRouter(tags=["instrumen"])
BATAS_IMPOR_BYTE = 5 * 1024 * 1024


def _svc(uow: UnitOfWork = Depends(get_uow)) -> KelolaInstrumen:
    return KelolaInstrumen(uow)


@router.get("/instrumen")
async def daftar_instrumen(pemanggil: Pemanggil = Depends(butuh(D, K, SP, SF)), svc: KelolaInstrumen = Depends(_svc)):
    return await svc.daftar_versi(pemanggil)


@router.get("/instrumen/impor/templat")
async def unduh_templat(_: Pemanggil = Depends(butuh(SF))):
    return Response(
        buat_templat_xlsx(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="templat-instrumen.xlsx"'},
    )


@router.post("/instrumen/impor", status_code=202)
async def impor(
    berkas: UploadFile = File(...),
    lam_kode: str = Form(...),
    kode_versi: str = Form(...),
    nama: str = Form(...),
    jenjang: str = Form("S1"),
    skor_maks: int = Form(4),
    label_skor: str = Form("{}", description='JSON, mis. {"4":"Sangat Baik"}'),
    nilai_akhir_maks: Decimal | None = Form(None),
    dasar_hukum: str | None = Form(None),
    pemanggil: Pemanggil = Depends(butuh(SF)),
    uow: UnitOfWork = Depends(get_uow),
):
    isi = await berkas.read(BATAS_IMPOR_BYTE + 1)
    if len(isi) > BATAS_IMPOR_BYTE:
        raise ValidasiGagal("Berkas impor terlalu besar (maks 5 MB).")
    try:
        label = json.loads(label_skor or "{}")
    except json.JSONDecodeError as exc:
        raise ValidasiGagal("label_skor bukan JSON yang valid.") from exc
    lam = (await uow.session.execute(select(Lam).where(Lam.kode == lam_kode))).scalar_one_or_none()
    if lam is None:
        raise ValidasiGagal(f"LAM '{lam_kode}' tidak dikenal.")
    async with uow:
        hasil = await impor_instrumen(
            uow.session,
            isi,
            lam_id=lam.id,
            kode_versi=kode_versi,
            nama=nama,
            jenjang=jenjang,
            skor_maks=skor_maks,
            label_skor=label,
            nilai_akhir_maks=nilai_akhir_maks,
            dasar_hukum=dasar_hukum,
            disusun_oleh=pemanggil.id,
        )
        await audit.catat(
            uow.session,
            "instrumen.impor",
            pemanggil=pemanggil,
            entitas="instrumen_versi",
            entitas_id=hasil["id"],
            detail={k: v for k, v in hasil.items() if k != "id"},
        )
    return JSONResponse(status_code=202, content=json.loads(json.dumps(hasil, default=str)))


@router.get("/instrumen/{versi_id}")
async def rincian_instrumen(versi_id: UUID, pemanggil: Pemanggil = Depends(butuh(D, K, SP, SF)), svc: KelolaInstrumen = Depends(_svc)):
    return await svc.rincian(pemanggil, versi_id)


@router.get("/instrumen/{versi_id}/butir")
async def daftar_butir(
    versi_id: UUID,
    kriteria: str | None = None,
    tahap_ppepp: str | None = None,
    jenis_ipo: str | None = None,
    _: Pemanggil = Depends(butuh(D, K, SP, SF)),
    svc: KelolaInstrumen = Depends(_svc),
):
    return await svc.daftar_butir(versi_id, kriteria, tahap_ppepp, jenis_ipo)


@router.post("/instrumen/{versi_id}/aktifkan")
async def aktifkan(versi_id: UUID, pemanggil: Pemanggil = Depends(butuh(D)), svc: KelolaInstrumen = Depends(_svc)):
    return await svc.aktifkan(pemanggil, versi_id)


@router.get("/instrumen/{versi_id}/pemetaan")
async def daftar_pemetaan(versi_id: UUID, _: Pemanggil = Depends(butuh(D, K, SF)), svc: KelolaInstrumen = Depends(_svc)):
    return await svc.daftar_pemetaan(versi_id)


@router.get("/butir-instrumen/{butir_id}")
async def rincian_butir(butir_id: UUID, _: Pemanggil = Depends(butuh(D, K, SP, SF)), svc: KelolaInstrumen = Depends(_svc)):
    return await svc.rincian_butir(butir_id)


@router.patch("/butir-instrumen/{butir_id}")
async def ubah_butir(butir_id: UUID, data: ButirPatch, pemanggil: Pemanggil = Depends(butuh(SF)), svc: KelolaInstrumen = Depends(_svc)):
    return await svc.ubah_butir(pemanggil, butir_id, data)


@router.put("/butir-instrumen/{butir_id}/pemetaan")
async def susun_pemetaan(
    butir_id: UUID, data: list[PemetaanItem], pemanggil: Pemanggil = Depends(butuh(SF)), svc: KelolaInstrumen = Depends(_svc)
):
    return await svc.susun_pemetaan(pemanggil, butir_id, data)


@router.post("/pemetaan/{pemetaan_id}/setujui")
async def setujui_pemetaan(pemetaan_id: UUID, pemanggil: Pemanggil = Depends(butuh(D)), svc: KelolaInstrumen = Depends(_svc)):
    return await svc.setujui_pemetaan(pemanggil, pemetaan_id)
