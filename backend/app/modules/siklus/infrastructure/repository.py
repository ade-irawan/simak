"""Kueri baca modul siklus (dipakai use case dan ``public.py``)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TidakDitemukan
from app.modules.instrumen.public import InstrumenButir, InstrumenKriteria
from app.modules.siklus.domain.entities import RingkasButirSiklus, RingkasSiklus, StatusSiklus
from app.modules.siklus.infrastructure.models import ButirSiklus, NarasiButir, SiklusAkreditasi


def ke_ringkas_siklus(s: SiklusAkreditasi) -> RingkasSiklus:
    return RingkasSiklus(
        id=s.id,
        prodi_id=s.prodi_id,
        instrumen_versi_id=s.instrumen_versi_id,
        nama=s.nama,
        status=s.status,
        ts_tahun_akademik_id=s.ts_tahun_akademik_id,
        jumlah_tahun_data=s.jumlah_tahun_data,
        tenggat=s.tenggat,
        target_peringkat_id=s.target_peringkat_id,
    )


async def ambil_siklus(session: AsyncSession, siklus_id: UUID) -> SiklusAkreditasi:
    s = await session.get(SiklusAkreditasi, siklus_id)
    if s is None:
        raise TidakDitemukan("Siklus tidak ditemukan.")
    return s


async def siklus_aktif_prodi(session: AsyncSession, prodi_id: UUID) -> SiklusAkreditasi | None:
    return (
        await session.execute(
            select(SiklusAkreditasi).where(
                SiklusAkreditasi.prodi_id == prodi_id,
                SiklusAkreditasi.status.in_([StatusSiklus.PERSIAPAN, StatusSiklus.BERJALAN]),
            )
        )
    ).scalar_one_or_none()


async def lembar_siklus(session: AsyncSession, siklus: SiklusAkreditasi, *, dengan_narasi: bool = False) -> list[RingkasButirSiklus]:
    """Lembar kerja butir pada versi instrumen yang sedang dipakai siklus (urut kriteria lalu nomor)."""
    baris = (
        await session.execute(
            select(ButirSiklus, InstrumenButir, InstrumenKriteria)
            .join(InstrumenButir, InstrumenButir.id == ButirSiklus.instrumen_butir_id)
            .join(InstrumenKriteria, InstrumenKriteria.id == InstrumenButir.kriteria_id)
            .where(ButirSiklus.siklus_id == siklus.id, InstrumenButir.instrumen_versi_id == siklus.instrumen_versi_id)
            .order_by(InstrumenKriteria.urutan, InstrumenButir.nomor_urut)
        )
    ).all()
    narasi: dict[UUID, list[dict]] = {}
    if dengan_narasi and baris:
        ids = [b.id for b, _, _ in baris]
        for n in (
            await session.execute(select(NarasiButir).where(NarasiButir.butir_siklus_id.in_(ids)).order_by(NarasiButir.bagian))
        ).scalars():
            narasi.setdefault(n.butir_siklus_id, []).append(
                {
                    "bagian": n.bagian,
                    "isi": n.isi,
                    "status": n.status.value,
                    "sumber": n.sumber.value,
                    "row_version": n.row_version,
                    "updated_at": n.updated_at.isoformat() if n.updated_at else None,
                }
            )
    return [
        RingkasButirSiklus(
            id=bs.id,
            siklus_id=bs.siklus_id,
            instrumen_butir_id=ib.id,
            kode=ib.kode,
            kriteria_kode=k.kode,
            elemen=ib.elemen,
            bobot=ib.bobot,
            status_kelengkapan=bs.status_kelengkapan,
            pengelola=bs.pengelola,
            penanggung_jawab_id=bs.penanggung_jawab_id,
            skor_estimasi=bs.skor_estimasi,
            menunggu_dokumen_eksternal=bs.menunggu_dokumen_eksternal,
            catatan=bs.catatan,
            narasi=narasi.get(bs.id, []),
        )
        for bs, ib, k in baris
    ]
