"""Mapping Engine (runtime): menyelesaikan aturan pemetaan yang SUDAH disetujui Dekan menjadi data nyata.

Tidak ada salinan data: setiap aturan dibaca langsung dari tabel sumbernya, sehingga perubahan satu data
otomatis tercermin di semua butir yang merujuknya (EC-05, US-B1). Modul ini hanya merangkai pembaca dari
``tridharma``, ``dokumen_eksternal`` dan ``ppepp``; penyusunan dan persetujuan aturan ada di ``instrumen``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dokumen_eksternal import public as dokumen_eksternal
from app.modules.instrumen import public as instrumen
from app.modules.instrumen.public import AturanPemetaan, JenisEntitas
from app.modules.ppepp import public as ppepp
from app.modules.referensi import public as referensi
from app.modules.tridharma import public as tridharma

__all__ = ["data_untuk_butir", "data_banyak_butir"]


async def _satu(session: AsyncSession, aturan: AturanPemetaan, prodi_id: UUID, tahun_ids: list[UUID]) -> dict[str, Any]:
    if aturan.sumber == JenisEntitas.INDIKATOR_EKSTERNAL:
        return await dokumen_eksternal.ambil_indikator_terpetakan(session, aturan, prodi_id, tahun_ids)
    if aturan.sumber == JenisEntitas.TAHAPAN_PPEPP:
        return await ppepp.ambil_tahapan_terpetakan(session, aturan, prodi_id, tahun_ids)
    return await tridharma.ambil_data_terpetakan(session, aturan, prodi_id, tahun_ids)


async def data_untuk_butir(
    session: AsyncSession, aturan_butir: list[AturanPemetaan], prodi_id: UUID, tahun_ids: list[UUID]
) -> list[dict[str, Any]]:
    """Data terpetakan untuk satu butir. Sumber yang kosong ditandai ``kosong`` → butir 'Belum Lengkap' (US-D1)."""
    hasil = []
    for a in aturan_butir:
        d = await _satu(session, a, prodi_id, tahun_ids)
        d["kosong"] = d["jumlah"] == 0
        d["aturan_id"] = a.id
        hasil.append(d)
    return hasil


async def data_banyak_butir(
    session: AsyncSession, butir_ids: list[UUID], prodi_id: UUID, ts_tahun_id: UUID, jumlah_tahun: int
) -> dict[UUID, list[dict[str, Any]]]:
    """Untuk cuplikan laporan dan pra-cek: data terpetakan semua butir sekaligus."""
    tahun_ids = await referensi.rentang_tahun(session, ts_tahun_id, jumlah_tahun)
    aturan = await instrumen.aturan_aktif(session, butir_ids)
    return {b: await data_untuk_butir(session, aturan.get(b, []), prodi_id, tahun_ids) for b in butir_ids}
