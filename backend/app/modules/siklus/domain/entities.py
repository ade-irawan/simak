"""Enum dan objek nilai modul siklus (Python murni)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


class StatusSiklus(StrEnum):
    PERSIAPAN = "persiapan"
    BERJALAN = "berjalan"
    SELESAI = "selesai"
    ARSIP = "arsip"


class StatusKelengkapan(StrEnum):
    BELUM_MULAI = "belum_mulai"
    DRAFT = "draft"
    LENGKAP = "lengkap"


class PengelolaButir(StrEnum):
    PRODI = "prodi"
    FAKULTAS = "fakultas"


class SumberSkor(StrEnum):
    MANDIRI = "mandiri"
    SISTEM = "sistem"


class StatusNarasi(StrEnum):
    DRAFT = "draft"
    FINAL = "final"


class SumberNarasi(StrEnum):
    MANUAL = "manual"
    LLM = "llm"
    LLM_DISUNTING = "llm_disunting"


@dataclass(frozen=True)
class RingkasSiklus:
    id: UUID
    prodi_id: UUID
    instrumen_versi_id: UUID
    nama: str
    status: StatusSiklus
    ts_tahun_akademik_id: UUID
    jumlah_tahun_data: int
    tenggat: date | None
    target_peringkat_id: UUID | None


@dataclass(frozen=True)
class RingkasButirSiklus:
    """Lembar kerja satu butir, dipakai laporan, penilaian, dan asesmen."""

    id: UUID
    siklus_id: UUID
    instrumen_butir_id: UUID
    kode: str
    kriteria_kode: str
    elemen: str
    bobot: Decimal | None
    status_kelengkapan: StatusKelengkapan
    pengelola: PengelolaButir
    penanggung_jawab_id: UUID | None
    skor_estimasi: Decimal | None
    menunggu_dokumen_eksternal: bool
    catatan: str | None
    narasi: list[dict[str, Any]] = field(default_factory=list)
