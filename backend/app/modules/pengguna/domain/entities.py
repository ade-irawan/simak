"""Enum dan nilai domain modul pengguna (Python murni)."""

from __future__ import annotations

from enum import StrEnum


class StatusPengguna(StrEnum):
    AKTIF = "aktif"
    NONAKTIF = "nonaktif"


class StatusPenugasan(StrEnum):
    DIUSULKAN = "diusulkan"
    AKTIF = "aktif"
    DICABUT = "dicabut"


class JenisTokenAkun(StrEnum):
    RESET_SANDI = "reset_sandi"
    BUKA_KUNCI = "buka_kunci"
