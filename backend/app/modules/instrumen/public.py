"""Pintu publik modul ``instrumen``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TidakDitemukan
from app.modules.instrumen.domain.entities import (
    AmbangButir,
    AturanPemetaan,
    ButirRingkas,
    DefinisiInstrumen,
    JenisEntitas,
    JenisIpo,
    JenisPenilaian,
    PeringkatDef,
    StatusInstrumen,
    TahapPpepp,
)
from app.modules.instrumen.infrastructure import repository as repo
from app.modules.instrumen.infrastructure.models import (
    IndikatorInti,
    InstrumenButir,
    InstrumenButirAmbang,
    InstrumenButirPadanan,
    InstrumenButirRubrik,
    InstrumenKriteria,
    InstrumenPeringkat,
    InstrumenVersi,
    PemetaanButir,
)
from app.modules.referensi.public import Lam

__all__ = [
    "AmbangButir",
    "AturanPemetaan",
    "ButirRingkas",
    "ButirTerpasok",
    "DefinisiInstrumen",
    "IndikatorInti",
    "InstrumenButir",
    "InstrumenKriteria",
    "InstrumenPeringkat",
    "InstrumenVersi",
    "JenisEntitas",
    "JenisIpo",
    "JenisPenilaian",
    "PeringkatDef",
    "StatusInstrumen",
    "TahapPpepp",
    "aturan_aktif",
    "butir_terpasok_oleh",
    "muat_butir",
    "muat_definisi",
    "padanan_butir",
    "rincian_butir_siklus",
    "versi_aktif",
    "versi_aktif_per_lam",
]

muat_definisi = repo.muat_definisi
muat_butir = repo.muat_butir
aturan_aktif = repo.aturan_aktif


async def versi_aktif_per_lam(session: AsyncSession) -> dict[str, str]:
    """{kode LAM: kode_versi aktif} untuk profil pengguna (instrumen otomatis mengikuti prodi)."""
    baris = (
        await session.execute(
            select(Lam.kode, InstrumenVersi.kode_versi)
            .join(InstrumenVersi, InstrumenVersi.lam_id == Lam.id)
            .where(InstrumenVersi.status == StatusInstrumen.AKTIF)
            .order_by(InstrumenVersi.berlaku_mulai.nulls_first())
        )
    ).all()
    return dict(baris)


async def versi_aktif(session: AsyncSession, lam_id: UUID, jenjang: str = "S1") -> InstrumenVersi:
    v = await repo.versi_aktif_lam(session, lam_id, jenjang)
    if v is None:
        raise TidakDitemukan("Belum ada versi instrumen aktif untuk LAM ini. Minta Dekan mengaktifkan instrumen.")
    return v


@dataclass(frozen=True)
class ButirTerpasok:
    instrumen: str
    kode: str
    elemen: str
    butir_id: UUID


async def butir_terpasok_oleh(session: AsyncSession, sumber: JenisEntitas) -> list[ButirTerpasok]:
    """Butir (pada instrumen aktif) yang dipasok sumber data ini, menurut aturan pemetaan yang sudah disetujui."""
    baris = (
        await session.execute(
            select(Lam.kode, InstrumenVersi.kode_versi, InstrumenButir.id, InstrumenButir.kode, InstrumenButir.elemen)
            .select_from(PemetaanButir)
            .join(InstrumenButir, InstrumenButir.id == PemetaanButir.instrumen_butir_id)
            .join(InstrumenVersi, InstrumenVersi.id == InstrumenButir.instrumen_versi_id)
            .join(Lam, Lam.id == InstrumenVersi.lam_id)
            .where(PemetaanButir.sumber == sumber, PemetaanButir.is_aktif, InstrumenVersi.status == StatusInstrumen.AKTIF)
            .order_by(Lam.kode, InstrumenButir.nomor_urut)
        )
    ).all()
    return [ButirTerpasok(f"{lam.replace('_', ' ')} {versi}", kode, elemen, bid) for lam, versi, bid, kode, elemen in baris]


async def padanan_butir(session: AsyncSession, versi_lama_id: UUID, versi_baru_id: UUID) -> dict[UUID, UUID]:
    """{butir lama → butir baru} untuk migrasi siklus (EC-14): padanan eksplisit, lalu kode yang sama."""
    lama = {b.kode: b.id for b in await repo.muat_butir(session, versi_lama_id)}
    baru = {b.kode: b.id for b in await repo.muat_butir(session, versi_baru_id)}
    peta = {lama[k]: baru[k] for k in lama.keys() & baru.keys()}
    eksplisit = (
        await session.execute(
            select(InstrumenButirPadanan.butir_lama_id, InstrumenButirPadanan.butir_baru_id)
            .join(InstrumenButir, InstrumenButir.id == InstrumenButirPadanan.butir_lama_id)
            .where(InstrumenButir.instrumen_versi_id == versi_lama_id)
        )
    ).all()
    for a, b in eksplisit:
        peta[a] = b
    return peta


async def rincian_butir_siklus(session: AsyncSession, butir_id: UUID) -> dict[str, Any]:
    """Butir + rubrik + ambang untuk lembar kerja dan cuplikan laporan."""
    b = await session.get(InstrumenButir, butir_id)
    if b is None:
        raise TidakDitemukan("Butir tidak ditemukan.")
    v = await session.get(InstrumenVersi, b.instrumen_versi_id)
    k = (await session.execute(select(InstrumenKriteria).where(InstrumenKriteria.id == b.kriteria_id))).scalar_one()
    label = (v.label_skor if v else {}) or {}
    rubrik = (
        (
            await session.execute(
                select(InstrumenButirRubrik)
                .where(InstrumenButirRubrik.instrumen_butir_id == butir_id)
                .order_by(InstrumenButirRubrik.skor.desc())
            )
        )
        .scalars()
        .all()
    )
    ambang = (
        await session.execute(
            select(InstrumenButirAmbang, InstrumenPeringkat.kode, InstrumenPeringkat.nama)
            .join(InstrumenPeringkat, InstrumenPeringkat.id == InstrumenButirAmbang.peringkat_id)
            .where(InstrumenButirAmbang.instrumen_butir_id == butir_id)
            .order_by(InstrumenPeringkat.tingkat.desc())
        )
    ).all()
    return {
        "id": b.id,
        "kode": b.kode,
        "elemen": b.elemen,
        "deskriptor": b.deskriptor,
        "panduan": b.panduan,
        "kriteria": {"kode": k.kode, "nama": k.nama},
        "jenis_ipo": b.jenis_ipo,
        "tahap_ppepp": b.tahap_ppepp,
        "bobot": b.bobot,
        "skema_narasi": list(b.skema_narasi or []),
        "rubrik": [{"skor": r.skor, "label": label.get(str(r.skor)), "deskriptor": r.deskriptor} for r in rubrik],
        "ambang": [
            {"peringkat": kode, "nama": nama, "skor_min": a.skor_min, "is_syarat_perlu": a.is_syarat_perlu} for a, kode, nama in ambang
        ],
    }
