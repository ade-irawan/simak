"""Pintu publik modul ``bukti``."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TidakDitemukan
from app.modules.bukti.domain.entities import JenisBukti, StatusCekBukti
from app.modules.bukti.domain.events import BuktiBermasalahTerdeteksi
from app.modules.bukti.domain.ports import PenyimpananBerkas, ProbeTautan
from app.modules.bukti.infrastructure.models import Bukti, BuktiButir, BuktiDataInti, BuktiTahapanPpepp
from app.modules.instrumen.public import JenisEntitas

__all__ = [
    "Bukti",
    "PenyimpananBerkas",
    "ProbeTautan",
    "BuktiBermasalahTerdeteksi",
    "BuktiButir",
    "BuktiTahapanPpepp",
    "JenisBukti",
    "StatusCekBukti",
    "bukti_bermasalah",
    "daftar_bukti_butir",
    "daftar_bukti_data_inti",
    "hitung_bukti_per_butir",
    "lepas_data_inti",
    "lepas_semua_data_inti",
    "pindahkan_data_inti",
    "ringkas_bukti",
    "tautkan_data_inti",
    "pastikan_bukti_ada",
    "salin_tautan_butir",
    "set_bukti_tahapan",
    "bukti_tahapan",
]


def _ringkas(b: Bukti) -> dict[str, Any]:
    return {
        "id": b.id,
        "judul": b.judul,
        "jenis": b.jenis,
        "status_cek": b.status_cek,
        "url": b.url,
        "akses_tautan": b.akses_tautan,
        "nama_berkas": b.nama_berkas,
        "ukuran_byte": b.ukuran_byte,
        "sumber": b.sumber,
        "tanggal_dokumen": b.tanggal_dokumen,
    }


async def pastikan_bukti_ada(session: AsyncSession, bukti_id: UUID) -> Bukti:
    b = (await session.execute(select(Bukti).where(Bukti.id == bukti_id, Bukti.deleted_at.is_(None)))).scalar_one_or_none()
    if b is None:
        raise TidakDitemukan("Bukti tidak ditemukan.")
    return b


async def ringkas_bukti(session: AsyncSession, ids: list[UUID]) -> dict[UUID, dict[str, Any]]:
    if not ids:
        return {}
    baris = (await session.execute(select(Bukti).where(Bukti.id.in_(ids)))).scalars().all()
    return {b.id: _ringkas(b) for b in baris}


# ---------------- kaitan ke data inti ----------------
async def daftar_bukti_data_inti(session: AsyncSession, jenis: JenisEntitas, entitas_id: UUID) -> list[dict[str, Any]]:
    baris = (
        (
            await session.execute(
                select(Bukti)
                .join(BuktiDataInti, BuktiDataInti.bukti_id == Bukti.id)
                .where(BuktiDataInti.jenis_entitas == jenis, BuktiDataInti.entitas_id == entitas_id, Bukti.deleted_at.is_(None))
                .order_by(BuktiDataInti.created_at)
            )
        )
        .scalars()
        .all()
    )
    return [_ringkas(b) for b in baris]


async def tautkan_data_inti(session: AsyncSession, bukti_id: UUID, jenis: JenisEntitas, entitas_id: UUID, pengguna_id: UUID) -> None:
    await pastikan_bukti_ada(session, bukti_id)
    await session.execute(
        pg_insert(BuktiDataInti)
        .values(bukti_id=bukti_id, jenis_entitas=jenis, entitas_id=entitas_id, created_by=pengguna_id)
        .on_conflict_do_nothing()
    )


async def lepas_data_inti(session: AsyncSession, bukti_id: UUID, jenis: JenisEntitas, entitas_id: UUID) -> None:
    await session.execute(
        delete(BuktiDataInti).where(
            BuktiDataInti.bukti_id == bukti_id, BuktiDataInti.jenis_entitas == jenis, BuktiDataInti.entitas_id == entitas_id
        )
    )


async def lepas_semua_data_inti(session: AsyncSession, jenis: JenisEntitas, entitas_id: UUID) -> None:
    await session.execute(delete(BuktiDataInti).where(BuktiDataInti.jenis_entitas == jenis, BuktiDataInti.entitas_id == entitas_id))


async def pindahkan_data_inti(session: AsyncSession, jenis: JenisEntitas, dari_id: UUID, ke_id: UUID) -> None:
    """Dipakai penggabungan duplikat: bukti milik catatan sumber berpindah ke catatan tujuan."""
    baris = (
        (await session.execute(select(BuktiDataInti).where(BuktiDataInti.jenis_entitas == jenis, BuktiDataInti.entitas_id == dari_id)))
        .scalars()
        .all()
    )
    for b in baris:
        await session.execute(
            pg_insert(BuktiDataInti)
            .values(bukti_id=b.bukti_id, jenis_entitas=jenis, entitas_id=ke_id, created_by=b.created_by)
            .on_conflict_do_nothing()
        )
    await lepas_semua_data_inti(session, jenis, dari_id)


# ---------------- kaitan ke butir ----------------
async def bukti_bermasalah(session: AsyncSession, butir_siklus_ids: list[UUID]) -> dict[UUID, list[dict[str, Any]]]:
    """{butir_siklus_id: [bukti tidak terjangkau]} — dasar tanda merah dan pemblokiran validasi final (EC-23)."""
    if not butir_siklus_ids:
        return {}
    baris = (
        await session.execute(
            select(BuktiButir.butir_siklus_id, Bukti)
            .join(Bukti, Bukti.id == BuktiButir.bukti_id)
            .where(
                BuktiButir.butir_siklus_id.in_(butir_siklus_ids),
                Bukti.deleted_at.is_(None),
                Bukti.status_cek == StatusCekBukti.TIDAK_TERJANGKAU,
            )
        )
    ).all()
    hasil: dict[UUID, list[dict[str, Any]]] = {}
    for butir_id, b in baris:
        hasil.setdefault(butir_id, []).append({"id": b.id, "judul": b.judul, "jenis": b.jenis, "status_cek": b.status_cek})
    return hasil


async def hitung_bukti_per_butir(session: AsyncSession, butir_siklus_ids: list[UUID]) -> dict[UUID, tuple[int, int]]:
    """{butir_siklus_id: (jumlah_bukti, jumlah_bermasalah)}."""
    if not butir_siklus_ids:
        return {}
    baris = (
        await session.execute(
            select(
                BuktiButir.butir_siklus_id,
                func.count(),
                func.count().filter(Bukti.status_cek == StatusCekBukti.TIDAK_TERJANGKAU),
            )
            .join(Bukti, Bukti.id == BuktiButir.bukti_id)
            .where(BuktiButir.butir_siklus_id.in_(butir_siklus_ids), Bukti.deleted_at.is_(None))
            .group_by(BuktiButir.butir_siklus_id)
        )
    ).all()
    return {b: (n, bm) for b, n, bm in baris}


async def daftar_bukti_butir(session: AsyncSession, butir_siklus_id: UUID) -> list[dict[str, Any]]:
    baris = (
        await session.execute(
            select(Bukti, BuktiButir.keterangan)
            .join(BuktiButir, BuktiButir.bukti_id == Bukti.id)
            .where(BuktiButir.butir_siklus_id == butir_siklus_id, Bukti.deleted_at.is_(None))
            .order_by(BuktiButir.urutan, BuktiButir.created_at)
        )
    ).all()
    return [_ringkas(b) | {"keterangan": ket} for b, ket in baris]


async def salin_tautan_butir(session: AsyncSession, dari_butir_id: UUID, ke_butir_id: UUID) -> None:
    """Migrasi instrumen (EC-14): tautan bukti ikut dipindahkan ke butir pada versi baru."""
    await session.execute(update(BuktiButir).where(BuktiButir.butir_siklus_id == dari_butir_id).values(butir_siklus_id=ke_butir_id))


async def set_bukti_tahapan(session: AsyncSession, tahapan_id: UUID, bukti_ids: list[UUID]) -> None:
    """Mengganti bukti yang melekat pada satu tahapan PPEPP."""
    await session.execute(delete(BuktiTahapanPpepp).where(BuktiTahapanPpepp.tahapan_id == tahapan_id))
    for bid in set(bukti_ids):
        await pastikan_bukti_ada(session, bid)
        session.add(BuktiTahapanPpepp(bukti_id=bid, tahapan_id=tahapan_id))


async def bukti_tahapan(session: AsyncSession, tahapan_ids: list[UUID]) -> dict[UUID, list[dict[str, Any]]]:
    if not tahapan_ids:
        return {}
    baris = (
        await session.execute(
            select(BuktiTahapanPpepp.tahapan_id, Bukti)
            .join(Bukti, Bukti.id == BuktiTahapanPpepp.bukti_id)
            .where(BuktiTahapanPpepp.tahapan_id.in_(tahapan_ids), Bukti.deleted_at.is_(None))
        )
    ).all()
    hasil: dict[UUID, list[dict[str, Any]]] = {}
    for tid, b in baris:
        hasil.setdefault(tid, []).append(_ringkas(b))
    return hasil
