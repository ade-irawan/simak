from __future__ import annotations

from enum import StrEnum

from app.core.enums import StatusTugas

__all__ = ["FormatEkspor", "JenisEkspor", "KeputusanValidasi", "StatusCatatan", "StatusLaporan", "StatusTugas"]


class StatusLaporan(StrEnum):
    DRAFT = "draft"
    MENUNGGU_VALIDASI = "menunggu_validasi"
    DISETUJUI = "disetujui"


class KeputusanValidasi(StrEnum):
    MENUNGGU = "menunggu"
    DISETUJUI = "disetujui"
    DIKEMBALIKAN = "dikembalikan"


class StatusCatatan(StrEnum):
    TERBUKA = "terbuka"
    SELESAI = "selesai"


class JenisEkspor(StrEnum):
    LED = "led"
    DATA_KUANTITATIF = "data_kuantitatif"
    GAP_ANALYSIS = "gap_analysis"


class FormatEkspor(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
