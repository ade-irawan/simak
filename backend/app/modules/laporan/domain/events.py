from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.events import Peristiwa


@dataclass(frozen=True)
class LaporanDiajukan(Peristiwa):
    laporan_id: UUID
    siklus_id: UUID
    prodi_id: UUID
    pengajuan_id: UUID
    nomor: int


@dataclass(frozen=True)
class LaporanDisetujui(Peristiwa):
    laporan_id: UUID
    siklus_id: UUID
    prodi_id: UUID
    nomor: int


@dataclass(frozen=True)
class LaporanDikembalikan(Peristiwa):
    laporan_id: UUID
    siklus_id: UUID
    prodi_id: UUID
    nomor: int


@dataclass(frozen=True)
class LaporanDibukaKembali(Peristiwa):
    laporan_id: UUID
    siklus_id: UUID
    prodi_id: UUID
