from __future__ import annotations

from enum import StrEnum


class StatusSiklusPpepp(StrEnum):
    DRAF = "draf"
    DITETAPKAN = "ditetapkan"
    BERJALAN = "berjalan"
    SELESAI = "selesai"


class StatusPenetapan(StrEnum):
    DRAF = "draf"
    DITETAPKAN = "ditetapkan"
    DIBATALKAN = "dibatalkan"


class StatusTahapan(StrEnum):
    BELUM_MULAI = "belum_mulai"
    BERJALAN = "berjalan"
    SELESAI = "selesai"


class Tahap(StrEnum):
    """Tahap PPEPP yang diisi prodi (P2–P5). Penetapan (P1) milik Dekan."""

    PELAKSANAAN = "pelaksanaan"
    EVALUASI = "evaluasi"
    PENGENDALIAN = "pengendalian"
    PENINGKATAN = "peningkatan"


URUTAN_TAHAP = [Tahap.PELAKSANAAN, Tahap.EVALUASI, Tahap.PENGENDALIAN, Tahap.PENINGKATAN]
