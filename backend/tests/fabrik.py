"""Pembuat data uji: instrumen kecil aktif untuk kedua LAM, tahun akademik, dan siklus."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.database import get_session_factory
from app.modules.instrumen.domain.entities import JenisEntitas as JE
from app.modules.instrumen.domain.entities import JenisIpo, StatusInstrumen, TahapPpepp
from app.modules.instrumen.infrastructure.models import (
    InstrumenButir,
    InstrumenButirAmbang,
    InstrumenKriteria,
    InstrumenPeringkat,
    PemetaanButir,
)
from app.modules.referensi.models import TahunAkademik
from app.seed.demo import _salin_struktur


async def tahun_akademik() -> list[UUID]:
    async with get_session_factory()() as s:
        ids = []
        for t in (2023, 2024, 2025):
            ta = TahunAkademik(kode=f"{t}/{t + 1}", tanggal_mulai=date(t, 8, 1), tanggal_selesai=date(t + 1, 7, 31), is_aktif=(t == 2025))
            s.add(ta)
            await s.flush()
            ids.append(ta.id)
        await s.commit()
        return ids


async def instrumen_lamsama(aktif: bool = True, kode: str = "uji", pemetaan: bool = True, dekan_id: UUID | None = None) -> dict[str, UUID]:
    """LAMSAMA kecil: butir 1 (A, syarat perlu), 2 (A), 3 (B). Ambang: terakreditasi≥2, unggul_2≥3, unggul_5≥4."""
    async with get_session_factory()() as s:
        v = await _salin_struktur(s, "LAMSAMA", "3.1", kode, "LAMSAMA uji")
        kr = {k.kode: k for k in (await s.execute(select(InstrumenKriteria).where(InstrumenKriteria.instrumen_versi_id == v.id))).scalars()}
        pr = {
            p.kode: p for p in (await s.execute(select(InstrumenPeringkat).where(InstrumenPeringkat.instrumen_versi_id == v.id))).scalars()
        }
        ids: dict[str, UUID] = {"versi": v.id}
        for n, kode_k in (("1", "A"), ("2", "A"), ("3", "B")):
            b = InstrumenButir(
                instrumen_versi_id=v.id,
                kriteria_id=kr[kode_k].id,
                kode=n,
                nomor_urut=int(n),
                elemen=f"Indikator {n} uji",
                skema_narasi=[{"bagian": "utama", "judul": "Uraian"}],
            )
            s.add(b)
            await s.flush()
            ids[n] = b.id
            for kp, skor in (("terakreditasi", 2), ("unggul_2", 3), ("unggul_5", 4)):
                s.add(InstrumenButirAmbang(instrumen_butir_id=b.id, peringkat_id=pr[kp].id, skor_min=skor, is_syarat_perlu=(n == "1")))
        if pemetaan:
            s.add(
                PemetaanButir(
                    instrumen_butir_id=ids["2"],
                    sumber=JE.PUBLIKASI,
                    aturan={"filter": {"jenis": "jurnal"}},
                    is_aktif=True,
                    disetujui_oleh=dekan_id,
                )
            )
            s.add(
                PemetaanButir(instrumen_butir_id=ids["3"], sumber=JE.INDIKATOR_EKSTERNAL, aturan={}, is_aktif=True, disetujui_oleh=dekan_id)
            )
        if aktif:
            v.status, v.disetujui_oleh = StatusInstrumen.AKTIF, dekan_id
        await s.commit()
        return ids


async def instrumen_infokom(aktif: bool = True, kode: str = "uji", dekan_id: UUID | None = None) -> dict[str, UUID]:
    """LAM INFOKOM kecil: A.1 (bobot 1), 1.1 (5), 1.2 (5), 2.1 (10), 3.1 (9). Σ bobot = 30 → nilai maks efektif 120."""
    async with get_session_factory()() as s:
        v = await _salin_struktur(s, "LAM_INFOKOM", "2.1", kode, "INFOKOM uji")
        kr = {k.kode: k for k in (await s.execute(select(InstrumenKriteria).where(InstrumenKriteria.instrumen_versi_id == v.id))).scalars()}
        ids: dict[str, UUID] = {"versi": v.id}
        for i, (kd, kode_k, bobot) in enumerate(
            (("A.1", "A", 1), ("1.1", "1", 5), ("1.2", "1", 5), ("2.1", "2", 10), ("3.1", "3", 9)), start=1
        ):
            b = InstrumenButir(
                instrumen_versi_id=v.id,
                kriteria_id=kr[kode_k].id,
                kode=kd,
                nomor_urut=i,
                elemen=f"Butir {kd} uji",
                bobot=Decimal(bobot),
                jenis_ipo=JenisIpo.INPUT,
                tahap_ppepp=TahapPpepp.PENETAPAN if kode_k == "1" else None,
            )
            s.add(b)
            await s.flush()
            ids[kd] = b.id
        s.add(PemetaanButir(instrumen_butir_id=ids["3.1"], sumber=JE.PUBLIKASI, aturan={}, is_aktif=True, disetujui_oleh=dekan_id))
        if aktif:
            v.status, v.disetujui_oleh = StatusInstrumen.AKTIF, dekan_id
        await s.commit()
        return ids


async def buka_siklus(dunia: Any, prodi_kode: str, ts_id: UUID, **kw: Any) -> dict[str, Any]:
    from sqlalchemy import select as sel

    from app.modules.referensi.models import Prodi

    async with get_session_factory()() as s:
        pid = (await s.execute(sel(Prodi.id).where(Prodi.kode == prodi_kode))).scalar_one()
    r = await dunia.post(
        "dekan",
        "/siklus",
        json={
            "prodi_id": str(pid),
            "nama": f"Siklus {prodi_kode}",
            "ts_tahun_akademik_id": str(ts_id),
            "tanggal_mulai": "2026-09-01",
            "tenggat": "2027-01-31",
            **kw,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()
