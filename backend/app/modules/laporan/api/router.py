from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.permissions import SF, SP, D, K, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.dependencies import butuh, get_uow
from app.infrastructure.antrean import kirim_tugas
from app.infrastructure.documents import PerenderBerkas
from app.infrastructure.storage.minio_storage import dapatkan_penyimpanan
from app.modules.laporan.api.schemas import AjukanIn, BukaKembaliIn, EksporIn, KembalikanIn, SetujuiIn
from app.modules.laporan.application.ekspor import LayananEkspor
from app.modules.laporan.application.layanan import LayananLaporan
from app.modules.laporan.infrastructure.penyusun_cuplikan import PenyusunCuplikanDb

router = APIRouter(tags=["laporan"])


def _svc(uow: UnitOfWork = Depends(get_uow)) -> LayananLaporan:
    return LayananLaporan(uow, PenyusunCuplikanDb(uow.session))


def _ekspor(uow: UnitOfWork = Depends(get_uow)) -> LayananEkspor:
    return LayananEkspor(uow, PenyusunCuplikanDb(uow.session), dapatkan_penyimpanan(), PerenderBerkas(), kirim_tugas)


@router.get("/siklus/{siklus_id}/laporan")
async def status_laporan(siklus_id: UUID, pemanggil: Pemanggil = Depends(butuh(D, K, SP, SF)), svc: LayananLaporan = Depends(_svc)):
    return await svc.status(pemanggil, siklus_id)


@router.get("/siklus/{siklus_id}/laporan/pra-cek")
async def pra_cek(siklus_id: UUID, pemanggil: Pemanggil = Depends(butuh(K)), svc: LayananLaporan = Depends(_svc)):
    return await svc.pra_cek(pemanggil, siklus_id)


@router.get("/siklus/{siklus_id}/laporan/catatan")
async def catatan_terbuka(siklus_id: UUID, pemanggil: Pemanggil = Depends(butuh(D, K, SP, SF)), svc: LayananLaporan = Depends(_svc)):
    return await svc.catatan_terbuka(pemanggil, siklus_id)


@router.post("/siklus/{siklus_id}/laporan/ajukan", status_code=201)
async def ajukan(
    siklus_id: UUID, data: AjukanIn | None = None, pemanggil: Pemanggil = Depends(butuh(K)), svc: LayananLaporan = Depends(_svc)
):
    return await svc.ajukan(pemanggil, siklus_id, data.catatan if data else None)


@router.post("/laporan/{laporan_id}/setujui")
async def setujui(
    laporan_id: UUID, data: SetujuiIn | None = None, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananLaporan = Depends(_svc)
):
    return await svc.setujui(pemanggil, laporan_id, data.catatan_umum if data else None)


@router.post("/laporan/{laporan_id}/kembalikan")
async def kembalikan(laporan_id: UUID, data: KembalikanIn, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananLaporan = Depends(_svc)):
    return await svc.kembalikan(pemanggil, laporan_id, data.catatan_umum, data.catatan_butir)


@router.post("/laporan/{laporan_id}/buka-kembali")
async def buka_kembali(
    laporan_id: UUID, data: BukaKembaliIn | None = None, pemanggil: Pemanggil = Depends(butuh(D)), svc: LayananLaporan = Depends(_svc)
):
    return await svc.buka_kembali(pemanggil, laporan_id, data.alasan if data else None)


@router.get("/laporan/{laporan_id}/pengajuan")
async def riwayat(laporan_id: UUID, pemanggil: Pemanggil = Depends(butuh(D, K)), svc: LayananLaporan = Depends(_svc)):
    return await svc.riwayat(pemanggil, laporan_id)


@router.get("/pengajuan/{pengajuan_id}")
async def pengajuan(pengajuan_id: UUID, pemanggil: Pemanggil = Depends(butuh(D, K)), svc: LayananLaporan = Depends(_svc)):
    return await svc.pengajuan(pemanggil, pengajuan_id)


@router.patch("/catatan-validasi/{catatan_id}")
async def selesaikan_catatan(catatan_id: UUID, pemanggil: Pemanggil = Depends(butuh(K)), svc: LayananLaporan = Depends(_svc)):
    return await svc.selesaikan_catatan(pemanggil, catatan_id)


@router.post("/siklus/{siklus_id}/ekspor", status_code=202)
async def minta_ekspor(
    siklus_id: UUID, data: EksporIn, pemanggil: Pemanggil = Depends(butuh(D, K, SP, SF)), svc: LayananEkspor = Depends(_ekspor)
):
    return await svc.minta(pemanggil, siklus_id, data.jenis, data.format, data.final)


@router.get("/ekspor/{ekspor_id}")
async def status_ekspor(ekspor_id: UUID, pemanggil: Pemanggil = Depends(butuh(D, K, SP, SF)), svc: LayananEkspor = Depends(_ekspor)):
    return await svc.status(pemanggil, ekspor_id)


@router.get("/ekspor/{ekspor_id}/unduh")
async def unduh_ekspor(ekspor_id: UUID, pemanggil: Pemanggil = Depends(butuh(D, K, SP, SF)), svc: LayananEkspor = Depends(_ekspor)):
    return await svc.unduh(pemanggil, ekspor_id)
