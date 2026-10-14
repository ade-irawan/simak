"""Pintu publik modul ``referensi``: satu-satunya yang boleh diimpor modul lain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TidakDitemukan
from app.modules.referensi.models import Fakultas, Lam, PengaturanSistem, Prodi, TahunAkademik

__all__ = [
    "Fakultas",
    "Lam",
    "Prodi",
    "ProdiRingkas",
    "TahunAkademik",
    "ambil_pengaturan",
    "ambil_prodi",
    "daftar_prodi",
    "ambil_tahun_akademik",
    "tahun_akademik_aktif",
    "rentang_tahun",
]


@dataclass(frozen=True)
class ProdiRingkas:
    id: UUID
    kode: str
    nama: str
    lam_kode: str
    jenjang: str


def _ringkas(p: Prodi, lam: Lam) -> ProdiRingkas:
    return ProdiRingkas(id=p.id, kode=p.kode, nama=p.nama, lam_kode=lam.kode, jenjang=p.jenjang)


async def ambil_prodi(session: AsyncSession, prodi_id: UUID) -> ProdiRingkas:
    baris = (await session.execute(select(Prodi, Lam).join(Lam, Lam.id == Prodi.lam_id).where(Prodi.id == prodi_id))).first()
    if baris is None:
        raise TidakDitemukan("Prodi tidak ditemukan.")
    return _ringkas(*baris)


async def daftar_prodi(session: AsyncSession, ids: set[UUID] | frozenset[UUID] | None = None) -> list[ProdiRingkas]:
    stmt = select(Prodi, Lam).join(Lam, Lam.id == Prodi.lam_id).where(Prodi.is_aktif).order_by(Prodi.kode)
    if ids is not None:
        stmt = stmt.where(Prodi.id.in_(ids))
    return [_ringkas(p, lam) for p, lam in (await session.execute(stmt)).all()]


async def ambil_pengaturan(session: AsyncSession, kunci: str, bawaan: Any = None) -> Any:
    baris = (await session.execute(select(PengaturanSistem.nilai).where(PengaturanSistem.kunci == kunci))).first()
    return bawaan if baris is None else baris[0]


async def ambil_tahun_akademik(session: AsyncSession, tahun_id: UUID) -> TahunAkademik:
    ta = await session.get(TahunAkademik, tahun_id)
    if ta is None:
        raise TidakDitemukan("Tahun akademik tidak ditemukan.")
    return ta


async def tahun_akademik_aktif(session: AsyncSession) -> TahunAkademik | None:
    return (await session.execute(select(TahunAkademik).where(TahunAkademik.is_aktif))).scalar_one_or_none()


async def rentang_tahun(session: AsyncSession, ts_id: UUID, jumlah: int) -> list[UUID]:
    """ID tahun akademik TS-(jumlah-1) .. TS, berurutan menurut tanggal mulai (EC-04)."""
    ts = await ambil_tahun_akademik(session, ts_id)
    baris = (
        (
            await session.execute(
                select(TahunAkademik.id)
                .where(TahunAkademik.tanggal_mulai <= ts.tanggal_mulai)
                .order_by(TahunAkademik.tanggal_mulai.desc())
                .limit(jumlah)
            )
        )
        .scalars()
        .all()
    )
    return list(reversed(baris))
