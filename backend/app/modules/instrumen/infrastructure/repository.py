"""Pembacaan definisi instrumen dari basis data menjadi objek domain."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TidakDitemukan
from app.modules.instrumen.domain.entities import (
    AmbangButir,
    AturanPemetaan,
    ButirRingkas,
    DefinisiInstrumen,
    PeringkatDef,
    StatusInstrumen,
)
from app.modules.instrumen.infrastructure.models import (
    InstrumenButir,
    InstrumenButirAmbang,
    InstrumenKriteria,
    InstrumenPeringkat,
    InstrumenVersi,
    PemetaanButir,
)
from app.modules.referensi.public import Lam


def ke_butir_ringkas(b: InstrumenButir, k: InstrumenKriteria) -> ButirRingkas:
    return ButirRingkas(
        id=b.id,
        kode=b.kode,
        nomor_urut=b.nomor_urut,
        elemen=b.elemen,
        kriteria_kode=k.kode,
        kriteria_nama=k.nama,
        kriteria_urutan=k.urutan,
        jenis_ipo=b.jenis_ipo,
        tahap_ppepp=b.tahap_ppepp,
        jenis_penilaian=b.jenis_penilaian,
        bobot=b.bobot,
        skema_narasi=list(b.skema_narasi or []),
    )


async def ambil_versi(session: AsyncSession, versi_id: UUID) -> InstrumenVersi:
    v = await session.get(InstrumenVersi, versi_id)
    if v is None:
        raise TidakDitemukan("Versi instrumen tidak ditemukan.")
    return v


async def muat_butir(session: AsyncSession, versi_id: UUID) -> list[ButirRingkas]:
    baris = (
        await session.execute(
            select(InstrumenButir, InstrumenKriteria)
            .join(InstrumenKriteria, InstrumenKriteria.id == InstrumenButir.kriteria_id)
            .where(InstrumenButir.instrumen_versi_id == versi_id)
            .order_by(InstrumenKriteria.urutan, InstrumenButir.nomor_urut)
        )
    ).all()
    return [ke_butir_ringkas(b, k) for b, k in baris]


async def muat_definisi(session: AsyncSession, versi_id: UUID) -> DefinisiInstrumen:
    v = await ambil_versi(session, versi_id)
    lam = await session.get(Lam, v.lam_id)
    butir = await muat_butir(session, versi_id)
    peringkat = (
        (
            await session.execute(
                select(InstrumenPeringkat).where(InstrumenPeringkat.instrumen_versi_id == versi_id).order_by(InstrumenPeringkat.tingkat)
            )
        )
        .scalars()
        .all()
    )
    ambang = (
        (
            await session.execute(
                select(InstrumenButirAmbang)
                .join(InstrumenPeringkat, InstrumenPeringkat.id == InstrumenButirAmbang.peringkat_id)
                .where(InstrumenPeringkat.instrumen_versi_id == versi_id)
            )
        )
        .scalars()
        .all()
    )
    kriteria = (await session.execute(select(InstrumenKriteria).where(InstrumenKriteria.instrumen_versi_id == versi_id))).scalars().all()
    return DefinisiInstrumen(
        versi_id=v.id,
        lam_kode=lam.kode if lam else "",
        kode_versi=v.kode_versi,
        skor_maks=v.skor_maks,
        nilai_akhir_maks=v.nilai_akhir_maks,
        butir=butir,
        peringkat=[
            PeringkatDef(p.id, p.kode, p.nama, p.tingkat, p.masa_berlaku_tahun, p.nilai_akhir_min, p.nilai_akhir_maks, dict(p.syarat or {}))
            for p in peringkat
        ],
        ambang=[AmbangButir(a.instrumen_butir_id, a.peringkat_id, a.skor_min, a.is_syarat_perlu) for a in ambang],
        bobot_kriteria={k.kode: k.bobot for k in kriteria},
    )


async def aturan_aktif(session: AsyncSession, butir_ids: list[UUID]) -> dict[UUID, list[AturanPemetaan]]:
    """Hanya aturan yang sudah disetujui Dekan (``is_aktif``); draf tidak pernah memengaruhi butir (EC-31)."""
    if not butir_ids:
        return {}
    baris = (
        (await session.execute(select(PemetaanButir).where(PemetaanButir.instrumen_butir_id.in_(butir_ids), PemetaanButir.is_aktif)))
        .scalars()
        .all()
    )
    hasil: dict[UUID, list[AturanPemetaan]] = {}
    for r in baris:
        hasil.setdefault(r.instrumen_butir_id, []).append(
            AturanPemetaan(r.id, r.instrumen_butir_id, r.sumber, r.indikator_inti_id, dict(r.aturan or {}), r.keterangan)
        )
    return hasil


async def versi_aktif_lam(session: AsyncSession, lam_id: UUID, jenjang: str = "S1") -> InstrumenVersi | None:
    return (
        (
            await session.execute(
                select(InstrumenVersi)
                .where(InstrumenVersi.lam_id == lam_id, InstrumenVersi.jenjang == jenjang, InstrumenVersi.status == StatusInstrumen.AKTIF)
                .order_by(InstrumenVersi.berlaku_mulai.desc().nulls_last(), InstrumenVersi.created_at.desc())
            )
        )
        .scalars()
        .first()
    )
