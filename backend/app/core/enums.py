"""Enum bersama lintas modul (kernel bersama)."""

from __future__ import annotations

from enum import StrEnum


class StatusTugas(StrEnum):
    """Status tugas latar (ekspor dokumen, permintaan LLM) — cermin ENUM ``status_tugas``."""

    ANTRE = "antre"
    DIPROSES = "diproses"
    SELESAI = "selesai"
    GAGAL = "gagal"
