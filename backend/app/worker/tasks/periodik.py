"""Tugas terjadwal: link-checker bukti, indikator inti, simulasi skor, pengingat tenggat."""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select

from app.core.database import get_session_factory
from app.core.permissions import D, K
from app.core.unit_of_work import UnitOfWork
from app.infrastructure.http.link_probe import HttpLinkProbe
from app.infrastructure.storage.minio_storage import dapatkan_penyimpanan
from app.modules.bukti.application.layanan import LayananBukti
from app.modules.notifikasi import public as notifikasi
from app.modules.pengguna import public as pengguna
from app.modules.penilaian import public as penilaian
from app.modules.referensi import public as referensi
from app.modules.siklus import public as siklus
from app.worker.celery_app import celery
from app.worker.runtime import jalankan

logger = logging.getLogger(__name__)


@celery.task(name="simak.periksa_bukti")
def periksa_bukti() -> dict[str, int]:
    async def kerja() -> dict[str, int]:
        async with get_session_factory()() as session:
            return await LayananBukti(UnitOfWork(session), dapatkan_penyimpanan(), HttpLinkProbe()).periksa_terjadwal()

    hasil = jalankan(kerja)
    logger.info("Link-checker: %s", hasil)
    return hasil


@celery.task(name="simak.hitung_indikator")
def hitung_indikator() -> int:
    async def kerja() -> int:
        async with get_session_factory()() as session:
            ta = await referensi.tahun_akademik_aktif(session)
            if ta is None:
                return 0
            n = await penilaian.hitung_indikator_inti(session, ta.id)
            await session.commit()
            return n

    return jalankan(kerja)


@celery.task(name="simak.hitung_simulasi_semua")
def hitung_simulasi_semua() -> int:
    async def kerja() -> int:
        async with get_session_factory()() as session:
            baris = (
                (
                    await session.execute(
                        select(siklus.SiklusAkreditasi.id).where(
                            siklus.SiklusAkreditasi.status.in_([siklus.StatusSiklus.PERSIAPAN, siklus.StatusSiklus.BERJALAN])
                        )
                    )
                )
                .scalars()
                .all()
            )
            for sid in baris:
                await penilaian.hitung_simulasi(session, sid, None)
            await session.commit()
            return len(baris)

    return jalankan(kerja)


@celery.task(name="simak.ingatkan_tenggat")
def ingatkan_tenggat() -> int:
    """Notifikasi bagi Kaprodi dan Dekan bila tenggat siklus tinggal 30/14/7/3/1 hari atau terlewat (EC-21)."""

    async def kerja() -> int:
        async with get_session_factory()() as session:
            n = 0
            hari_ini = date.today()
            for sk in (
                await session.execute(
                    select(siklus.SiklusAkreditasi).where(
                        siklus.SiklusAkreditasi.status.in_([siklus.StatusSiklus.PERSIAPAN, siklus.StatusSiklus.BERJALAN]),
                        siklus.SiklusAkreditasi.tenggat.is_not(None),
                    )
                )
            ).scalars():
                sisa = (sk.tenggat - hari_ini).days
                if sisa not in {30, 14, 7, 3, 1} and sisa >= 0:
                    continue
                prodi = await referensi.ambil_prodi(session, sk.prodi_id)
                judul = f"Tenggat {prodi.nama}: {sisa} hari lagi" if sisa >= 0 else f"Tenggat {prodi.nama} terlewat {-sisa} hari"
                for peran, pid in ((K, sk.prodi_id), (D, None)):
                    for u in await pengguna.penerima(session, peran, pid):
                        await notifikasi.kirim(session, u.id, "tenggat.dekat", judul, f"Siklus {sk.nama}", f"/siklus/{sk.id}")
                        n += 1
            await session.commit()
            return n

    return jalankan(kerja)
