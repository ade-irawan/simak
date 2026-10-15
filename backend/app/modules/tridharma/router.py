# Catatan: tanpa ``from __future__ import annotations`` — rute dibuat dinamis dari registri,
# sehingga anotasi (skema per sumber) harus dievaluasi saat fungsi didefinisikan.
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, Query, Request, Response, UploadFile
from pydantic import BaseModel, create_model
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import audit
from app.core.database import get_session
from app.core.exceptions import AksesDitolak, TidakDitemukan, ValidasiGagal
from app.core.pagination import ParamHalaman
from app.core.permissions import SF, SP, D, K, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.dependencies import butuh, get_uow
from app.modules.laporan import public as laporan
from app.modules.tridharma import models as m
from app.modules.tridharma.registry import SPEC, SPEC_LIST, Spec
from app.modules.tridharma.schemas import AfiliasiIn, Dasar, GabungIn, MataKuliahIn
from app.modules.tridharma.service import LayananDataInti

router = APIRouter()
BATAS_IMPOR_BYTE = 5 * 1024 * 1024

baca = butuh(D, K, SP, SF)
tulis = butuh(K, SP, SF)
hanya_kaprodi = butuh(K)
impor_peran = butuh(SP, SF)


def buat_skema_patch(skema: type[BaseModel]) -> type[BaseModel]:
    """Semua bidang opsional + ``row_version`` wajib (penguncian optimistik, EC-10)."""
    bidang: dict[str, Any] = {n: (f.annotation | None, None) for n, f in skema.model_fields.items()}
    return create_model(f"{skema.__name__}Patch", __base__=Dasar, row_version=(int, ...), **bidang)


def daftarkan(spec: Spec) -> None:
    tag = [spec.path]
    prefix = f"/{spec.path}"
    skema = spec.skema
    skema_patch = buat_skema_patch(skema)

    def layanan(uow: UnitOfWork = Depends(get_uow)) -> LayananDataInti:
        return LayananDataInti(spec, uow)

    @router.get(prefix, tags=tag, name=f"daftar_{spec.path}")
    async def daftar(
        request: Request,
        param: ParamHalaman = Depends(),
        prodi_id: UUID | None = None,
        tahun_akademik_id: UUID | None = None,
        status_data: str | None = None,
        pemanggil: Pemanggil = Depends(baca),
        svc: LayananDataInti = Depends(layanan),
    ):
        lain = {k: v for k, v in request.query_params.items() if k in spec.filter_boleh}
        return await svc.daftar(
            pemanggil, param, prodi_id=prodi_id, tahun_akademik_id=tahun_akademik_id, status_data=status_data, filter_lain=lain
        )

    @router.post(prefix, tags=tag, status_code=201, name=f"buat_{spec.path}")
    async def buat(
        data: skema = Body(...),
        abaikan_kemiripan: bool = Query(False, description="Lewati peringatan kemiripan judul (DOI sama tetap ditolak)"),
        pemanggil: Pemanggil = Depends(tulis),
        svc: LayananDataInti = Depends(layanan),
    ):
        return await svc.buat(pemanggil, data, abaikan_kemiripan=abaikan_kemiripan)

    @router.get(f"{prefix}/impor/templat", tags=tag, name=f"templat_impor_{spec.path}")
    async def templat_impor(
        format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
        pemanggil: Pemanggil = Depends(impor_peran),
        svc: LayananDataInti = Depends(layanan),
    ):
        isi, tipe, nama_berkas = await svc.templat_impor(format)
        return Response(isi, media_type=tipe, headers={"Content-Disposition": f'attachment; filename="{nama_berkas}"'})

    @router.post(f"{prefix}/impor", tags=tag, status_code=202, name=f"impor_{spec.path}")
    async def impor(
        berkas: UploadFile = File(...),
        atomik: bool = Query(False, description="True = batalkan semua bila ada baris bermasalah (EC-17)"),
        pemanggil: Pemanggil = Depends(impor_peran),
        svc: LayananDataInti = Depends(layanan),
    ):
        isi = await berkas.read(BATAS_IMPOR_BYTE + 1)
        if len(isi) > BATAS_IMPOR_BYTE:
            raise ValidasiGagal("Berkas impor terlalu besar (maks 5 MB).")
        return await svc.impor(pemanggil, berkas.filename or "impor.csv", isi, atomik=atomik)

    @router.get(f"{prefix}/{{obj_id}}", tags=tag, name=f"rincian_{spec.path}")
    async def rincian(obj_id: UUID, pemanggil: Pemanggil = Depends(baca), svc: LayananDataInti = Depends(layanan)):
        return await svc.rincian(pemanggil, obj_id)

    @router.patch(f"{prefix}/{{obj_id}}", tags=tag, name=f"ubah_{spec.path}")
    async def ubah(
        obj_id: UUID,
        data: skema_patch = Body(...),
        abaikan_kemiripan: bool = Query(False),
        pemanggil: Pemanggil = Depends(tulis),
        svc: LayananDataInti = Depends(layanan),
    ):
        return await svc.ubah(pemanggil, obj_id, data, abaikan_kemiripan=abaikan_kemiripan)

    @router.delete(f"{prefix}/{{obj_id}}", tags=tag, status_code=204, name=f"hapus_{spec.path}")
    async def hapus(obj_id: UUID, pemanggil: Pemanggil = Depends(hanya_kaprodi), svc: LayananDataInti = Depends(layanan)):
        await svc.hapus(pemanggil, obj_id)

    @router.post(f"{prefix}/{{obj_id}}/verifikasi", tags=tag, name=f"verifikasi_{spec.path}")
    async def verifikasi(obj_id: UUID, pemanggil: Pemanggil = Depends(hanya_kaprodi), svc: LayananDataInti = Depends(layanan)):
        return await svc.verifikasi(pemanggil, obj_id)

    @router.get(f"{prefix}/{{obj_id}}/bukti", tags=tag, name=f"bukti_{spec.path}")
    async def daftar_bukti(obj_id: UUID, pemanggil: Pemanggil = Depends(baca), svc: LayananDataInti = Depends(layanan)):
        return await svc.daftar_bukti(pemanggil, obj_id)

    @router.put(f"{prefix}/{{obj_id}}/bukti/{{bukti_id}}", tags=tag, name=f"lampir_bukti_{spec.path}")
    async def lampirkan(obj_id: UUID, bukti_id: UUID, pemanggil: Pemanggil = Depends(tulis), svc: LayananDataInti = Depends(layanan)):
        return await svc.lampirkan_bukti(pemanggil, obj_id, bukti_id)

    @router.delete(f"{prefix}/{{obj_id}}/bukti/{{bukti_id}}", tags=tag, status_code=204, name=f"lepas_bukti_{spec.path}")
    async def lepas(obj_id: UUID, bukti_id: UUID, pemanggil: Pemanggil = Depends(tulis), svc: LayananDataInti = Depends(layanan)):
        await svc.lepas_bukti(pemanggil, obj_id, bukti_id)

    @router.get(f"{prefix}/{{obj_id}}/butir", tags=tag, name=f"butir_{spec.path}")
    async def butir(obj_id: UUID, pemanggil: Pemanggil = Depends(baca), svc: LayananDataInti = Depends(layanan)):
        """Butir instrumen yang merujuk data ini — peringatan dampak sebelum mengubah/menghapus (EC-05)."""
        return await svc.butir_terkait(pemanggil, obj_id)

    if spec.path == "publikasi":

        @router.post(f"{prefix}/{{obj_id}}/gabung", tags=tag, name="gabung_publikasi")
        async def gabung(
            obj_id: UUID, data: GabungIn, pemanggil: Pemanggil = Depends(hanya_kaprodi), svc: LayananDataInti = Depends(layanan)
        ):
            return await svc.gabung(pemanggil, obj_id, data.sumber_id)


for _spec in SPEC_LIST:
    daftarkan(_spec)


# ---------------------------------------------------------------- mata kuliah (anak kurikulum)
def _svc_kurikulum(uow: UnitOfWork) -> LayananDataInti:
    return LayananDataInti(SPEC["kurikulum"], uow)


@router.get("/kurikulum/{kurikulum_id}/mata-kuliah", tags=["kurikulum"])
async def daftar_mata_kuliah(kurikulum_id: UUID, pemanggil: Pemanggil = Depends(baca), uow: UnitOfWork = Depends(get_uow)):
    await _svc_kurikulum(uow).rincian(pemanggil, kurikulum_id)  # memeriksa cakupan baca
    baris = (
        (
            await uow.session.execute(
                select(m.MataKuliah).where(m.MataKuliah.kurikulum_id == kurikulum_id).order_by(m.MataKuliah.semester, m.MataKuliah.kode)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": b.id,
            "kurikulum_id": b.kurikulum_id,
            "kode": b.kode,
            "nama": b.nama,
            "sks": b.sks,
            "semester": b.semester,
            "jenis": b.jenis,
            "ada_rps": b.ada_rps,
        }
        for b in baris
    ]


async def _wajib_tulis_kurikulum(pemanggil: Pemanggil, uow: UnitOfWork, kurikulum_id: UUID) -> None:
    svc = _svc_kurikulum(uow)
    kur = await svc._muat(kurikulum_id)
    await svc._wajib_tulis(pemanggil, {kur.prodi_id}, kur)


@router.post("/kurikulum/{kurikulum_id}/mata-kuliah", tags=["kurikulum"], status_code=201)
async def tambah_mata_kuliah(
    kurikulum_id: UUID, data: MataKuliahIn, pemanggil: Pemanggil = Depends(tulis), uow: UnitOfWork = Depends(get_uow)
):
    await _wajib_tulis_kurikulum(pemanggil, uow, kurikulum_id)
    mk = m.MataKuliah(kurikulum_id=kurikulum_id, **data.model_dump())
    async with uow:
        uow.session.add(mk)
        try:
            await uow.session.flush()
        except Exception as exc:
            raise ValidasiGagal("Kode mata kuliah sudah ada pada kurikulum ini.") from exc
        await audit.catat(uow.session, "mata_kuliah.buat", pemanggil=pemanggil, entitas="mata_kuliah", entitas_id=mk.id)
    return {"id": mk.id, "kurikulum_id": kurikulum_id, **data.model_dump()}


@router.patch("/mata-kuliah/{mk_id}", tags=["kurikulum"])
async def ubah_mata_kuliah(
    mk_id: UUID, data: dict[str, Any] = Body(...), pemanggil: Pemanggil = Depends(tulis), uow: UnitOfWork = Depends(get_uow)
):
    mk = await uow.session.get(m.MataKuliah, mk_id)
    if mk is None:
        raise TidakDitemukan()
    await _wajib_tulis_kurikulum(pemanggil, uow, mk.kurikulum_id)
    boleh = set(MataKuliahIn.model_fields)
    if set(data) - boleh:
        raise ValidasiGagal(f"Kolom tidak dikenal: {sorted(set(data) - boleh)}")
    async with uow:
        for k, v in data.items():
            setattr(mk, k, v)
        await audit.catat(uow.session, "mata_kuliah.ubah", pemanggil=pemanggil, entitas="mata_kuliah", entitas_id=mk_id)
    return {"id": mk.id, "kode": mk.kode, "nama": mk.nama, "sks": mk.sks, "semester": mk.semester, "jenis": mk.jenis, "ada_rps": mk.ada_rps}


@router.delete("/mata-kuliah/{mk_id}", tags=["kurikulum"], status_code=204)
async def hapus_mata_kuliah(mk_id: UUID, pemanggil: Pemanggil = Depends(hanya_kaprodi), uow: UnitOfWork = Depends(get_uow)):
    mk = await uow.session.get(m.MataKuliah, mk_id)
    if mk is None:
        raise TidakDitemukan()
    await _wajib_tulis_kurikulum(pemanggil, uow, mk.kurikulum_id)
    async with uow:
        await uow.session.delete(mk)
        await audit.catat(uow.session, "mata_kuliah.hapus", pemanggil=pemanggil, entitas="mata_kuliah", entitas_id=mk_id)


# ---------------------------------------------------------------- afiliasi dosen (EC-01)
@router.get("/dosen/{dosen_id}/afiliasi", tags=["dosen"])
async def daftar_afiliasi(dosen_id: UUID, pemanggil: Pemanggil = Depends(baca), uow: UnitOfWork = Depends(get_uow)):
    return (await LayananDataInti(SPEC["dosen"], uow).rincian(pemanggil, dosen_id))["afiliasi"]


@router.put("/dosen/{dosen_id}/afiliasi", tags=["dosen"])
async def ganti_afiliasi(
    dosen_id: UUID,
    data: list[AfiliasiIn],
    pemanggil: Pemanggil = Depends(tulis),
    session: AsyncSession = Depends(get_session),
    uow: UnitOfWork = Depends(get_uow),
):
    """Mengganti afiliasi pada prodi yang boleh ditulis pemanggil; afiliasi prodi lain dibiarkan."""
    svc = LayananDataInti(SPEC["dosen"], uow)
    dosen = await svc._muat(dosen_id)
    cakupan = pemanggil.cakupan_tulis()
    for a in data:
        if not (pemanggil.punya(SF) or cakupan.mengizinkan(a.prodi_id)):
            raise AksesDitolak(alasan="di_luar_cakupan_prodi")
        await laporan.wajib_tidak_terkunci(session, a.prodi_id)
    async with uow:
        baris = (await session.execute(select(m.DosenProdi).where(m.DosenProdi.dosen_id == dosen_id))).scalars().all()
        for b in baris:
            if pemanggil.punya(SF) or cakupan.mengizinkan(b.prodi_id):
                await session.delete(b)
        await session.flush()
        for a in data:
            session.add(
                m.DosenProdi(
                    dosen_id=dosen_id,
                    prodi_id=a.prodi_id,
                    tahun_akademik_id=a.tahun_akademik_id,
                    jenis=a.jenis,
                    proporsi_beban=a.proporsi_beban,
                    sks_diampu=a.sks_diampu,
                )
            )
        try:
            await session.flush()
        except Exception as exc:
            raise ValidasiGagal("Afiliasi bentrok (satu homebase per tahun, satu baris per prodi-tahun).") from exc
        dosen.updated_by = pemanggil.id
        await audit.catat(session, "dosen.afiliasi", pemanggil=pemanggil, entitas="dosen", entitas_id=dosen_id)
    return (await svc._ke_dict(dosen))["afiliasi"]
