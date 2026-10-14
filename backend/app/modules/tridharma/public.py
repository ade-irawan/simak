"""Pintu publik ``tridharma``: model data inti dan pembaca data terpetakan (hasil Mapping Engine)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CakupanProdi
from app.modules.instrumen.public import AturanPemetaan, JenisEntitas
from app.modules.tridharma import models as m
from app.modules.tridharma.registry import SPEC_ENTITAS

__all__ = ["ambil_data_terpetakan", "sumber_ditangani", "m"]


def sumber_ditangani(sumber: JenisEntitas) -> bool:
    return sumber in SPEC_ENTITAS or sumber == JenisEntitas.MATA_KULIAH


def _label(obj: Any) -> str:
    for k in ("judul", "nama", "nama_mitra", "kategori"):
        if hasattr(obj, k) and getattr(obj, k):
            return str(getattr(obj, k))
    return str(obj.id)


def _terapkan_filter(stmt: Select[Any], model: Any, saring: dict[str, Any]) -> Select[Any]:
    kolom_ada = {c.key for c in inspect(model).mapper.column_attrs}
    for k, v in saring.items():
        if k not in kolom_ada:
            continue  # kolom tak dikenal diabaikan (aturan dapat usang setelah skema berubah)
        kolom = getattr(model, k)
        stmt = stmt.where(kolom.in_(v) if isinstance(v, list) else kolom == v)
    return stmt


async def ambil_data_terpetakan(
    session: AsyncSession, aturan: AturanPemetaan, prodi_id: UUID, tahun_ids: list[UUID], maks_contoh: int = 25
) -> dict[str, Any]:
    """Data inti yang memasok satu butir untuk satu prodi pada rentang TS-n..TS.

    Tidak ada salinan: hasilnya dibaca langsung dari tabel sumber (satu sumber kebenaran).
    """
    cakupan = CakupanProdi(prodi_ids=frozenset({prodi_id}))
    batas_tahun = aturan.aturan.get("batasi_tahun", True)

    if aturan.sumber == JenisEntitas.MATA_KULIAH:
        model: Any = m.MataKuliah
        stmt = (
            select(m.MataKuliah)
            .join(m.Kurikulum, m.Kurikulum.id == m.MataKuliah.kurikulum_id)
            .where(m.Kurikulum.prodi_id == prodi_id, m.Kurikulum.deleted_at.is_(None))
        )
    else:
        spec = SPEC_ENTITAS[aturan.sumber]
        model = spec.model
        stmt = select(model)
        if hasattr(model, "deleted_at"):
            stmt = stmt.where(model.deleted_at.is_(None))
        for k, v in spec.tetap.items():
            stmt = stmt.where(getattr(model, k) == v)
        if aturan.sumber == JenisEntitas.KEUANGAN:  # keuangan tingkat UPPS (prodi NULL) ikut menopang tiap prodi
            stmt = stmt.where((m.Keuangan.prodi_id == prodi_id) | m.Keuangan.prodi_id.is_(None))
        else:
            stmt = spec.penangan.saring(stmt, model, cakupan, prodi_id)
        if aturan.sumber == JenisEntitas.DOSEN:
            if batas_tahun and tahun_ids:
                stmt = stmt.where(
                    m.Dosen.id.in_(
                        select(m.DosenProdi.dosen_id).where(
                            m.DosenProdi.prodi_id == prodi_id, m.DosenProdi.tahun_akademik_id.in_(tahun_ids)
                        )
                    )
                )
        elif batas_tahun and spec.kolom_tahun and tahun_ids:
            stmt = stmt.where(getattr(model, spec.kolom_tahun).in_(tahun_ids))

    stmt = _terapkan_filter(stmt, model, aturan.aturan.get("filter", {}))
    agregasi = aturan.aturan.get("agregasi", "daftar")
    jumlah = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    nilai: float | int | None = None
    if agregasi == "hitung":
        nilai = jumlah
    elif agregasi in {"jumlah", "rata_rata"} and jumlah:
        kolom = getattr(model, aturan.aturan["kolom"], None)
        if kolom is not None:
            fungsi = func.sum if agregasi == "jumlah" else func.avg
            sub = stmt.subquery()
            hasil = (await session.execute(select(fungsi(sub.c[aturan.aturan["kolom"]])))).scalar_one()
            nilai = float(hasil) if hasil is not None else None
    contoh = (await session.execute(stmt.limit(maks_contoh))).scalars().all()
    return {
        "sumber": aturan.sumber.value,
        "keterangan": aturan.keterangan,
        "agregasi": agregasi,
        "jumlah": jumlah,
        "nilai": nilai,
        "contoh": [{"id": o.id, "label": _label(o)} for o in contoh],
    }
