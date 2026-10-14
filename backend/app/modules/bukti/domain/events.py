from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.events import Peristiwa


@dataclass(frozen=True)
class BuktiBermasalahTerdeteksi(Peristiwa):
    bukti_id: UUID
    judul: str
    prodi_ids: tuple[UUID, ...]
