"""Penghitung indikator inti lintas instrumen (dasar benchmarking yang adil, US-F2 / EC-20).

Dosen lintas prodi dihitung proporsional ``proporsi_beban`` (FTE) dan publikasi/kegiatan menurut ``proporsi`` atribusi,
sehingga tidak ada penghitungan ganda pada agregat fakultas (EC-01, EC-02).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.instrumen.public import IndikatorInti
from app.modules.penilaian.infrastructure.models import NilaiIndikator
from app.modules.referensi import public as referensi
from app.modules.tridharma.public import m


@dataclass(frozen=True)
class Hasil:
    nilai: Decimal | None
    rincian: dict[str, Any]


Penghitung = Callable[[AsyncSession, UUID, UUID], Awaitable[Hasil]]


def _bagi(a: Decimal | int | None, b: Decimal | int | None, kali: int = 1) -> Decimal | None:
    if a is None or not b:
        return None
    return (Decimal(a) * kali / Decimal(b)).quantize(Decimal("0.0001"))


async def _dosen_tetap(session: AsyncSession, prodi_id: UUID, tahun_id: UUID, *syarat: Any) -> Decimal:
    """FTE dosen tetap prodi pada tahun akademik (opsional disaring ``syarat``)."""
    stmt = (
        select(func.coalesce(func.sum(m.DosenProdi.proporsi_beban), 0))
        .join(m.Dosen, m.Dosen.id == m.DosenProdi.dosen_id)
        .where(
            m.DosenProdi.prodi_id == prodi_id,
            m.DosenProdi.tahun_akademik_id == tahun_id,
            m.Dosen.deleted_at.is_(None),
            m.Dosen.status_kepegawaian == "tetap",
            *syarat,
        )
    )
    return Decimal((await session.execute(stmt)).scalar_one())


async def rasio_mahasiswa_dosen(session: AsyncSession, prodi_id: UUID, tahun_id: UUID) -> Hasil:
    ms = (
        await session.execute(
            select(m.MahasiswaStatistik).where(
                m.MahasiswaStatistik.prodi_id == prodi_id, m.MahasiswaStatistik.tahun_akademik_id == tahun_id
            )
        )
    ).scalar_one_or_none()
    fte = await _dosen_tetap(session, prodi_id, tahun_id)
    aktif = (ms.aktif_reguler or 0) + (ms.aktif_transfer or 0) if ms else None
    return Hasil(_bagi(aktif, fte), {"mahasiswa_aktif": aktif, "dosen_tetap_fte": float(fte)})


async def publikasi_per_dosen(session: AsyncSession, prodi_id: UUID, tahun_id: UUID) -> Hasil:
    total = (
        await session.execute(
            select(func.coalesce(func.sum(m.PublikasiProdi.proporsi), 0))
            .join(m.Publikasi, m.Publikasi.id == m.PublikasiProdi.publikasi_id)
            .where(m.PublikasiProdi.prodi_id == prodi_id, m.Publikasi.tahun_akademik_id == tahun_id, m.Publikasi.deleted_at.is_(None))
        )
    ).scalar_one()
    fte = await _dosen_tetap(session, prodi_id, tahun_id)
    return Hasil(_bagi(Decimal(total), fte), {"publikasi_terbobot": float(total), "dosen_tetap_fte": float(fte)})


async def _dana(session: AsyncSession, jenis: str, prodi_id: UUID, tahun_id: UUID) -> Hasil:
    total = (
        await session.execute(
            select(func.coalesce(func.sum(m.KegiatanTridharma.jumlah_dana * m.KegiatanProdi.proporsi), 0))
            .join(m.KegiatanProdi, m.KegiatanProdi.kegiatan_id == m.KegiatanTridharma.id)
            .where(
                m.KegiatanProdi.prodi_id == prodi_id,
                m.KegiatanTridharma.tahun_akademik_id == tahun_id,
                m.KegiatanTridharma.jenis == jenis,
                m.KegiatanTridharma.deleted_at.is_(None),
            )
        )
    ).scalar_one()
    fte = await _dosen_tetap(session, prodi_id, tahun_id)
    return Hasil(_bagi(Decimal(total), fte), {"dana_terbobot": float(total), "dosen_tetap_fte": float(fte)})


async def dana_penelitian_per_dosen(session: AsyncSession, prodi_id: UUID, tahun_id: UUID) -> Hasil:
    return await _dana(session, "penelitian", prodi_id, tahun_id)


async def dana_pkm_per_dosen(session: AsyncSession, prodi_id: UUID, tahun_id: UUID) -> Hasil:
    return await _dana(session, "pkm", prodi_id, tahun_id)


async def persen_dosen_s3(session: AsyncSession, prodi_id: UUID, tahun_id: UUID) -> Hasil:
    s3 = await _dosen_tetap(session, prodi_id, tahun_id, m.Dosen.pendidikan_tertinggi == "s3")
    return await _persen(session, prodi_id, tahun_id, s3)


async def persen_dosen_bersertifikat(session: AsyncSession, prodi_id: UUID, tahun_id: UUID) -> Hasil:
    n = await _dosen_tetap(session, prodi_id, tahun_id, m.Dosen.punya_sertifikat_pendidik.is_(True))
    return await _persen(session, prodi_id, tahun_id, n)


async def persen_dosen_jabatan_tinggi(session: AsyncSession, prodi_id: UUID, tahun_id: UUID) -> Hasil:
    n = await _dosen_tetap(session, prodi_id, tahun_id, m.Dosen.jabatan_akademik.in_(["lektor_kepala", "guru_besar"]))
    return await _persen(session, prodi_id, tahun_id, n)


async def _persen(session: AsyncSession, prodi_id: UUID, tahun_id: UUID, bagian: Decimal) -> Hasil:
    fte = await _dosen_tetap(session, prodi_id, tahun_id)
    return Hasil(_bagi(bagian, fte, 100), {"dosen_memenuhi_fte": float(bagian), "dosen_tetap_fte": float(fte)})


async def ipk_rata_lulusan(session: AsyncSession, prodi_id: UUID, tahun_id: UUID) -> Hasil:
    ls = (
        await session.execute(
            select(m.LulusanStatistik).where(m.LulusanStatistik.prodi_id == prodi_id, m.LulusanStatistik.tahun_akademik_id == tahun_id)
        )
    ).scalar_one_or_none()
    return Hasil(ls.ipk_rata if ls else None, {"jumlah_lulusan": ls.jumlah_lulusan if ls else None})


async def persen_lulus_tepat_waktu(session: AsyncSession, prodi_id: UUID, tahun_id: UUID) -> Hasil:
    ls = (
        await session.execute(
            select(m.LulusanStatistik).where(m.LulusanStatistik.prodi_id == prodi_id, m.LulusanStatistik.tahun_akademik_id == tahun_id)
        )
    ).scalar_one_or_none()
    return Hasil(
        _bagi(ls.lulus_tepat_waktu, ls.jumlah_lulusan, 100) if ls else None,
        {"lulus_tepat_waktu": ls.lulus_tepat_waktu if ls else None, "jumlah_lulusan": ls.jumlah_lulusan if ls else None},
    )


async def kerja_sama_internasional(session: AsyncSession, prodi_id: UUID, tahun_id: UUID) -> Hasil:
    ta = await referensi.ambil_tahun_akademik(session, tahun_id)
    n = (
        await session.execute(
            select(func.count())
            .select_from(m.KerjaSama)
            .join(m.KerjaSamaProdi, m.KerjaSamaProdi.kerja_sama_id == m.KerjaSama.id)
            .where(
                m.KerjaSamaProdi.prodi_id == prodi_id,
                m.KerjaSama.deleted_at.is_(None),
                m.KerjaSama.tingkat == "internasional",
                m.KerjaSama.tanggal_mulai <= ta.tanggal_selesai,
                (m.KerjaSama.tanggal_selesai.is_(None)) | (m.KerjaSama.tanggal_selesai >= ta.tanggal_mulai),
            )
        )
    ).scalar_one()
    return Hasil(Decimal(n), {})


#: kode ``indikator_inti`` → penghitung. Menambah indikator = tambah baris di tabel + satu entri di sini.
PENGHITUNG: dict[str, Penghitung] = {
    "rasio_mahasiswa_dosen": rasio_mahasiswa_dosen,
    "publikasi_per_dosen": publikasi_per_dosen,
    "dana_penelitian_per_dosen": dana_penelitian_per_dosen,
    "dana_pkm_per_dosen": dana_pkm_per_dosen,
    "persen_dosen_s3": persen_dosen_s3,
    "persen_dosen_bersertifikat": persen_dosen_bersertifikat,
    "persen_dosen_jabatan_tinggi": persen_dosen_jabatan_tinggi,
    "ipk_rata_lulusan": ipk_rata_lulusan,
    "persen_lulus_tepat_waktu": persen_lulus_tepat_waktu,
    "kerja_sama_internasional": kerja_sama_internasional,
}


async def hitung_dan_simpan(session: AsyncSession, tahun_id: UUID, prodi_ids: list[UUID] | None = None) -> int:
    """Menghitung ulang semua indikator inti dan menyimpannya (dijalankan tiap malam dan saat diminta)."""
    daftar = (await session.execute(select(IndikatorInti))).scalars().all()
    prodi = [p.id for p in await referensi.daftar_prodi(session)] if prodi_ids is None else prodi_ids
    n = 0
    for ind in daftar:
        fungsi = PENGHITUNG.get(ind.kode)
        if fungsi is None:
            continue
        for pid in prodi:
            h = await fungsi(session, pid, tahun_id)
            nilai = {"nilai": h.nilai, "rincian": h.rincian}
            await session.execute(
                pg_insert(NilaiIndikator)
                .values(indikator_inti_id=ind.id, prodi_id=pid, tahun_akademik_id=tahun_id, **nilai)
                .on_conflict_do_update(
                    index_elements=["indikator_inti_id", "prodi_id", "tahun_akademik_id"], set_={**nilai, "dihitung_pada": func.now()}
                )
            )
            n += 1
    return n
