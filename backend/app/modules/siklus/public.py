"""Pintu publik modul ``siklus``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TidakDitemukan
from app.core.permissions import Pemanggil
from app.modules.instrumen.public import InstrumenButir
from app.modules.siklus.domain import rules
from app.modules.siklus.domain.entities import (
    PengelolaButir,
    RingkasButirSiklus,
    RingkasSiklus,
    StatusKelengkapan,
    StatusNarasi,
    StatusSiklus,
    SumberNarasi,
    SumberSkor,
)
from app.modules.siklus.domain.rules import masalah_pengajuan
from app.modules.siklus.infrastructure import repository as repo
from app.modules.siklus.infrastructure.models import ButirSiklus, NarasiButir, SiklusAkreditasi

__all__ = [
    "ButirSiklus",
    "InfoButir",
    "NarasiButir",
    "PengelolaButir",
    "RingkasButirSiklus",
    "RingkasSiklus",
    "SiklusAkreditasi",
    "StatusKelengkapan",
    "StatusNarasi",
    "StatusSiklus",
    "SumberNarasi",
    "SumberSkor",
    "ambil_ringkas_siklus",
    "daftar_lembar",
    "masalah_pengajuan",
    "info_butir_untuk_penulisan",
    "prodi_dari_butir",
    "prodi_ditugaskan",
    "ringkas_butir_siklus",
    "siklus_aktif_prodi",
    "sinkron_menunggu_eksternal",
    "wajib_ubah_butir",
]


@dataclass(frozen=True)
class InfoButir:
    id: UUID
    siklus_id: UUID
    prodi_id: UUID
    pengelola: PengelolaButir
    penanggung_jawab_id: UUID | None
    instrumen_butir_id: UUID


async def prodi_ditugaskan(session: AsyncSession, pengguna_id: UUID) -> frozenset[UUID]:
    """Prodi yang butirnya ditugaskan Dekan kepada pengguna ini (tanda ¹ pada matriks hak akses)."""
    baris = (
        await session.execute(
            select(SiklusAkreditasi.prodi_id)
            .join(ButirSiklus, ButirSiklus.siklus_id == SiklusAkreditasi.id)
            .where(
                ButirSiklus.penanggung_jawab_id == pengguna_id, SiklusAkreditasi.status.in_([StatusSiklus.PERSIAPAN, StatusSiklus.BERJALAN])
            )
            .distinct()
        )
    ).scalars()
    return frozenset(baris)


async def info_butir_untuk_penulisan(session: AsyncSession, butir_siklus_id: UUID) -> InfoButir:
    baris = (
        await session.execute(
            select(ButirSiklus, SiklusAkreditasi.prodi_id)
            .join(SiklusAkreditasi, SiklusAkreditasi.id == ButirSiklus.siklus_id)
            .where(ButirSiklus.id == butir_siklus_id)
        )
    ).first()
    if baris is None:
        raise TidakDitemukan("Butir siklus tidak ditemukan.")
    b, prodi_id = baris
    return InfoButir(b.id, b.siklus_id, prodi_id, b.pengelola, b.penanggung_jawab_id, b.instrumen_butir_id)


def wajib_ubah_butir(pemanggil: Pemanggil, info: InfoButir) -> None:
    rules.wajib_ubah_butir(pemanggil, prodi_id=info.prodi_id, pengelola=info.pengelola, penanggung_jawab_id=info.penanggung_jawab_id)


async def prodi_dari_butir(session: AsyncSession, butir_siklus_ids: set[UUID]) -> set[UUID]:
    if not butir_siklus_ids:
        return set()
    baris = (
        await session.execute(
            select(SiklusAkreditasi.prodi_id)
            .join(ButirSiklus, ButirSiklus.siklus_id == SiklusAkreditasi.id)
            .where(ButirSiklus.id.in_(butir_siklus_ids))
            .distinct()
        )
    ).scalars()
    return set(baris)


async def ringkas_butir_siklus(session: AsyncSession, butir_siklus_ids: list[UUID]) -> list[dict[str, Any]]:
    if not butir_siklus_ids:
        return []
    baris = (
        await session.execute(
            select(ButirSiklus.id, ButirSiklus.siklus_id, InstrumenButir.kode, InstrumenButir.elemen, SiklusAkreditasi.prodi_id)
            .join(InstrumenButir, InstrumenButir.id == ButirSiklus.instrumen_butir_id)
            .join(SiklusAkreditasi, SiklusAkreditasi.id == ButirSiklus.siklus_id)
            .where(ButirSiklus.id.in_(butir_siklus_ids))
        )
    ).all()
    return [{"butir_siklus_id": i, "siklus_id": s, "kode": k, "elemen": e, "prodi_id": p} for i, s, k, e, p in baris]


async def ambil_ringkas_siklus(session: AsyncSession, siklus_id: UUID) -> RingkasSiklus:
    return repo.ke_ringkas_siklus(await repo.ambil_siklus(session, siklus_id))


async def siklus_aktif_prodi(session: AsyncSession, prodi_id: UUID) -> RingkasSiklus | None:
    s = await repo.siklus_aktif_prodi(session, prodi_id)
    return repo.ke_ringkas_siklus(s) if s else None


async def daftar_lembar(session: AsyncSession, siklus_id: UUID, *, dengan_narasi: bool = False) -> list[RingkasButirSiklus]:
    return await repo.lembar_siklus(session, await repo.ambil_siklus(session, siklus_id), dengan_narasi=dengan_narasi)


async def sinkron_menunggu_eksternal(session: AsyncSession, prodi_id: UUID, ada_dokumen: bool, butir_instrumen_ids: list[UUID]) -> int:
    """Mengatur tanda 'Menunggu dokumen dari Direktorat' (EC-15) pada butir siklus berjalan milik prodi yang
    dipasok indikator eksternal. Mengembalikan jumlah butir yang dibebaskan dari tanda tersebut."""
    siklus = await repo.siklus_aktif_prodi(session, prodi_id)
    if siklus is None or not butir_instrumen_ids:
        return 0
    sebelum = (
        (
            await session.execute(
                select(ButirSiklus.id).where(
                    ButirSiklus.siklus_id == siklus.id,
                    ButirSiklus.instrumen_butir_id.in_(butir_instrumen_ids),
                    ButirSiklus.menunggu_dokumen_eksternal.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    await session.execute(
        update(ButirSiklus)
        .where(ButirSiklus.siklus_id == siklus.id, ButirSiklus.instrumen_butir_id.in_(butir_instrumen_ids))
        .values(menunggu_dokumen_eksternal=not ada_dokumen)
    )
    return len(sebelum) if ada_dokumen else 0
