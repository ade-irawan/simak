"""Enum dan objek nilai instrumen akreditasi (Python murni)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


class StatusInstrumen(StrEnum):
    DRAF = "draf"
    AKTIF = "aktif"
    ARSIP = "arsip"


class JenisIpo(StrEnum):
    INPUT = "input"
    PROSES = "proses"
    OUTPUT = "output"


class TahapPpepp(StrEnum):
    PENETAPAN = "penetapan"
    PELAKSANAAN = "pelaksanaan"
    EVALUASI = "evaluasi"
    PENGENDALIAN = "pengendalian"
    PENINGKATAN = "peningkatan"


class JenisPenilaian(StrEnum):
    KUALITATIF = "kualitatif"
    KUANTITATIF = "kuantitatif"


class JenisEntitas(StrEnum):
    """Sumber data inti yang dapat dipetakan ke butir (enum ``jenis_entitas`` pada basis data)."""

    DOSEN = "dosen"
    MAHASISWA_STATISTIK = "mahasiswa_statistik"
    LULUSAN_STATISTIK = "lulusan_statistik"
    KURIKULUM = "kurikulum"
    MATA_KULIAH = "mata_kuliah"
    PENELITIAN = "penelitian"
    PKM = "pkm"
    PUBLIKASI = "publikasi"
    KERJA_SAMA = "kerja_sama"
    SARANA_PRASARANA = "sarana_prasarana"
    KEUANGAN = "keuangan"
    INDIKATOR_EKSTERNAL = "indikator_eksternal"
    TAHAPAN_PPEPP = "tahapan_ppepp"


@dataclass(frozen=True)
class AturanPemetaan:
    """Aturan Mapping Engine yang SUDAH disetujui: butir X dipasok oleh sumber Y dengan saringan Z."""

    id: UUID
    butir_id: UUID
    sumber: JenisEntitas
    indikator_inti_id: UUID | None
    aturan: dict[str, Any] = field(default_factory=dict)
    keterangan: str | None = None


@dataclass(frozen=True)
class ButirRingkas:
    id: UUID
    kode: str
    nomor_urut: int
    elemen: str
    kriteria_kode: str
    kriteria_nama: str
    kriteria_urutan: int
    jenis_ipo: JenisIpo | None
    tahap_ppepp: TahapPpepp | None
    jenis_penilaian: JenisPenilaian
    bobot: Decimal | None
    skema_narasi: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class PeringkatDef:
    id: UUID
    kode: str
    nama: str
    tingkat: int
    masa_berlaku_tahun: int | None
    nilai_akhir_min: Decimal | None
    nilai_akhir_maks: Decimal | None
    syarat: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AmbangButir:
    butir_id: UUID
    peringkat_id: UUID
    skor_min: Decimal
    is_syarat_perlu: bool


@dataclass(frozen=True)
class DefinisiInstrumen:
    """Semua yang dibutuhkan penilai peringkat: butir, bobot, peringkat, ambang."""

    versi_id: UUID
    lam_kode: str
    kode_versi: str
    skor_maks: int
    nilai_akhir_maks: Decimal | None
    butir: list[ButirRingkas]
    peringkat: list[PeringkatDef]
    ambang: list[AmbangButir]
    bobot_kriteria: dict[str, Decimal | None]
