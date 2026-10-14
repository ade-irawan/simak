from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.events import Peristiwa


@dataclass(frozen=True)
class TokenAkunDibuat(Peristiwa):
    """Dipakai modul notifikasi untuk mengirim tautan reset sandi / buka kunci lewat surel."""

    pengguna_id: UUID
    email: str
    nama: str
    jenis: str
    token: str


@dataclass(frozen=True)
class AsesorDiaktifkan(Peristiwa):
    penugasan_id: UUID
    pengguna_id: UUID
    prodi_id: UUID
