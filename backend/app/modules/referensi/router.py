from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import audit
from app.core.database import get_session
from app.core.exceptions import TidakDitemukan, ValidasiGagal
from app.core.permissions import IT, SF, Pemanggil, Peran
from app.dependencies import butuh, butuh_konten
from app.modules.referensi import public
from app.modules.referensi.models import PengaturanSistem, TahunAkademik
from app.modules.referensi.schemas import (
    PengaturanIn,
    PengaturanOut,
    ProdiOut,
    TahunAkademikIn,
    TahunAkademikOut,
    TahunAkademikPatch,
)

router = APIRouter(tags=["referensi"])


@router.get("/prodi", response_model=list[ProdiOut])
async def daftar_prodi(
    pemanggil: Pemanggil = Depends(butuh(Peran.DEKAN, Peran.KAPRODI, Peran.STAF_PRODI, Peran.STAF_FAKULTAS, IT)),
    session: AsyncSession = Depends(get_session),
):
    ids = None if pemanggil.punya(Peran.DEKAN, SF, IT) else pemanggil.cakupan_baca().prodi_ids
    return [ProdiOut(id=p.id, kode=p.kode, nama=p.nama, jenjang=p.jenjang, lam=p.lam_kode) for p in await public.daftar_prodi(session, ids)]


@router.get("/tahun-akademik", response_model=list[TahunAkademikOut])
async def daftar_tahun(_: Pemanggil = Depends(butuh_konten(exclude=(Peran.ASESOR,))), session: AsyncSession = Depends(get_session)):
    hasil = await session.execute(select(TahunAkademik).order_by(TahunAkademik.tanggal_mulai.desc()))
    return hasil.scalars().all()


@router.post("/tahun-akademik", response_model=TahunAkademikOut, status_code=201)
async def buat_tahun(data: TahunAkademikIn, pemanggil: Pemanggil = Depends(butuh(SF)), session: AsyncSession = Depends(get_session)):
    ta = TahunAkademik(**data.model_dump())
    try:
        async with session.begin_nested():
            if data.is_aktif:
                await session.execute(update(TahunAkademik).values(is_aktif=False))
            session.add(ta)
            await session.flush()
    except IntegrityError as exc:
        raise ValidasiGagal("Kode tahun akademik sudah dipakai.") from exc
    await audit.catat(session, "tahun_akademik.buat", pemanggil=pemanggil, entitas="tahun_akademik", entitas_id=ta.id)
    await session.commit()
    return ta


@router.patch("/tahun-akademik/{tahun_id}", response_model=TahunAkademikOut)
async def ubah_tahun(
    tahun_id: UUID, data: TahunAkademikPatch, pemanggil: Pemanggil = Depends(butuh(SF)), session: AsyncSession = Depends(get_session)
):
    ta = await session.get(TahunAkademik, tahun_id)
    if ta is None:
        raise TidakDitemukan()
    perubahan = data.model_dump(exclude_unset=True)
    if perubahan.get("is_aktif"):
        await session.execute(update(TahunAkademik).where(TahunAkademik.id != tahun_id).values(is_aktif=False))
    for k, v in perubahan.items():
        setattr(ta, k, v)
    if ta.tanggal_selesai <= ta.tanggal_mulai:
        raise ValidasiGagal("tanggal_selesai harus setelah tanggal_mulai.")
    await audit.catat(session, "tahun_akademik.ubah", pemanggil=pemanggil, entitas="tahun_akademik", entitas_id=ta.id, detail=perubahan)
    await session.commit()
    return ta


@router.get("/pengaturan", response_model=list[PengaturanOut])
async def daftar_pengaturan(_: Pemanggil = Depends(butuh(IT)), session: AsyncSession = Depends(get_session)):
    hasil = await session.execute(select(PengaturanSistem).order_by(PengaturanSistem.kunci))
    return [PengaturanOut(kunci=p.kunci, nilai=p.nilai, deskripsi=p.deskripsi) for p in hasil.scalars()]


@router.put("/pengaturan/{kunci}", response_model=PengaturanOut)
async def ubah_pengaturan(
    kunci: str, data: PengaturanIn, pemanggil: Pemanggil = Depends(butuh(IT)), session: AsyncSession = Depends(get_session)
):
    p = await session.get(PengaturanSistem, kunci)
    if p is None:
        raise TidakDitemukan("Kunci pengaturan tidak dikenal.")
    lama = p.nilai
    p.nilai, p.updated_by = data.nilai, pemanggil.id
    await audit.catat(
        session,
        "pengaturan.ubah",
        pemanggil=pemanggil,
        entitas="pengaturan_sistem",
        detail={"kunci": kunci, "lama": lama, "baru": data.nilai},
    )
    await session.commit()
    return PengaturanOut(kunci=p.kunci, nilai=p.nilai, deskripsi=p.deskripsi)
