from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.core.pagination import ParamHalaman
from app.core.permissions import IT, D, K, Pemanggil, Peran
from app.core.unit_of_work import UnitOfWork
from app.dependencies import butuh, get_uow
from app.modules.pengguna.api.schemas import (
    AlasanIn,
    EmailBaruIn,
    KunciOut,
    PenggunaIn,
    PenggunaOut,
    PenggunaPatch,
    PenugasanIn,
    PenugasanOut,
    PenyetujuanIn,
    SandiBaruIn,
)
from app.modules.pengguna.application.manajemen import ManajemenAkun
from app.modules.pengguna.domain.entities import StatusPengguna, StatusPenugasan

router = APIRouter(tags=["pengguna"])


def _akun(uow: UnitOfWork = Depends(get_uow)) -> ManajemenAkun:
    return ManajemenAkun(uow)


@router.get("/pengguna")
async def daftar_pengguna(
    param: ParamHalaman = Depends(),
    peran: Peran | None = None,
    prodi_id: UUID | None = None,
    status: StatusPengguna | None = None,
    terkunci: bool | None = None,
    _: Pemanggil = Depends(butuh(D, IT)),
    svc: ManajemenAkun = Depends(_akun),
):
    return await svc.daftar(param, peran=peran, prodi_id=prodi_id, status=status, terkunci=terkunci)


@router.post("/pengguna", response_model=PenggunaOut, status_code=201)
async def buat_pengguna(data: PenggunaIn, pemanggil: Pemanggil = Depends(butuh(D, IT)), svc: ManajemenAkun = Depends(_akun)):
    return await svc.buat(pemanggil, data)


@router.get("/pengguna/calon-asesor")
async def calon_asesor(
    q: str = Query(..., description="nama atau surel, minimal 3 huruf"),
    pemanggil: Pemanggil = Depends(butuh(D, K)),
    svc: ManajemenAkun = Depends(_akun),
):
    """Pencarian akun yang dapat diusulkan sebagai asesor (Dekan menetapkan, Kaprodi mengusulkan)."""
    return await svc.calon_asesor(pemanggil, q)


@router.get("/pengguna/{pengguna_id}", response_model=PenggunaOut)
async def rincian_pengguna(pengguna_id: UUID, _: Pemanggil = Depends(butuh(D, IT)), svc: ManajemenAkun = Depends(_akun)):
    return await svc.rincian(pengguna_id)


@router.patch("/pengguna/{pengguna_id}", response_model=PenggunaOut)
async def ubah_pengguna(
    pengguna_id: UUID, data: PenggunaPatch, pemanggil: Pemanggil = Depends(butuh(D)), svc: ManajemenAkun = Depends(_akun)
):
    return await svc.ubah(pemanggil, pengguna_id, data)


@router.post("/pengguna/{pengguna_id}/atur-email", response_model=PenggunaOut)
async def atur_email(pengguna_id: UUID, data: EmailBaruIn, pemanggil: Pemanggil = Depends(butuh(IT)), svc: ManajemenAkun = Depends(_akun)):
    return await svc.atur_email(pemanggil, pengguna_id, str(data.email))


@router.post("/pengguna/{pengguna_id}/buka-kunci", response_model=KunciOut)
async def buka_kunci(pengguna_id: UUID, data: AlasanIn, pemanggil: Pemanggil = Depends(butuh(IT)), svc: ManajemenAkun = Depends(_akun)):
    return await svc.buka_kunci(pemanggil, pengguna_id, data.alasan)


@router.post("/pengguna/{pengguna_id}/atur-sandi", status_code=204)
async def atur_sandi(pengguna_id: UUID, data: SandiBaruIn, pemanggil: Pemanggil = Depends(butuh(IT)), svc: ManajemenAkun = Depends(_akun)):
    """Admin IT menetapkan sandi sementara; pengguna wajib menggantinya saat masuk."""
    await svc.atur_sandi(pemanggil, pengguna_id, data.sandi_baru)
    return Response(status_code=204)


@router.post("/pengguna/{pengguna_id}/reset-sandi", status_code=202)
async def reset_sandi(pengguna_id: UUID, pemanggil: Pemanggil = Depends(butuh(IT)), svc: ManajemenAkun = Depends(_akun)):
    await svc.reset_sandi(pemanggil, pengguna_id)
    return Response(status_code=202)


@router.post("/pengguna/{pengguna_id}/nonaktifkan", response_model=PenggunaOut)
async def nonaktifkan(pengguna_id: UUID, pemanggil: Pemanggil = Depends(butuh(D, IT)), svc: ManajemenAkun = Depends(_akun)):
    return await svc.nonaktifkan(pemanggil, pengguna_id)


@router.get("/penugasan-peran")
async def daftar_penugasan(
    param: ParamHalaman = Depends(),
    peran: Peran | None = None,
    prodi_id: UUID | None = None,
    status: StatusPenugasan | None = None,
    pemanggil: Pemanggil = Depends(butuh(D, K, IT)),
    svc: ManajemenAkun = Depends(_akun),
):
    return await svc.daftar_penugasan(pemanggil, param, peran=peran, prodi_id=prodi_id, status=status)


@router.post("/penugasan-peran", response_model=PenugasanOut, status_code=201)
async def tambah_penugasan(data: PenugasanIn, pemanggil: Pemanggil = Depends(butuh(D, K, IT)), svc: ManajemenAkun = Depends(_akun)):
    return await svc.tambah_penugasan(pemanggil, data)


@router.post("/penugasan-peran/{penugasan_id}/setujui", response_model=PenugasanOut)
async def setujui_penugasan(
    penugasan_id: UUID, data: PenyetujuanIn, pemanggil: Pemanggil = Depends(butuh(D)), svc: ManajemenAkun = Depends(_akun)
):
    return await svc.setujui_penugasan(pemanggil, penugasan_id, data)


@router.post("/penugasan-peran/{penugasan_id}/cabut", response_model=PenugasanOut)
async def cabut_penugasan(penugasan_id: UUID, pemanggil: Pemanggil = Depends(butuh(D, IT)), svc: ManajemenAkun = Depends(_akun)):
    return await svc.cabut_penugasan(pemanggil, penugasan_id)


# `session` dan `Query` diimpor agar mudah menambah endpoint tanpa mengubah blok impor.
