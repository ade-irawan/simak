"""Mesin status laporan evaluasi diri.

    draft ──ajukan──► menunggu_validasi ──setujui──► disetujui ──buka_kembali──► draft
                              │
                              └──kembalikan──► draft

Python murni agar seluruh transisi dapat diuji tanpa basis data. Galat memakai pengecualian domain bersama.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.exceptions import BuktiBermasalah, KonflikStatus, LaporanBelumLengkap
from app.modules.laporan.domain.entities import FormatEkspor, JenisEkspor, StatusLaporan

TERKUNCI = {StatusLaporan.MENUNGGU_VALIDASI, StatusLaporan.DISETUJUI}


def terkunci(status: StatusLaporan) -> bool:
    """Saat menunggu validasi atau disetujui, penulisan lembar kerja/narasi/bukti/data prodi dikunci (EC-07, EC-09)."""
    return status in TERKUNCI


@dataclass
class StatusLaporanState:
    status: StatusLaporan
    nomor_terakhir: int = 0

    def ajukan(self, masalah: list[dict[str, Any]]) -> int:
        """Mengembalikan nomor pengajuan baru. Butir bermasalah memblokir (EC-06)."""
        if self.status != StatusLaporan.DRAFT:
            raise KonflikStatus("Laporan hanya dapat diajukan dari status draft.")
        if masalah:
            raise LaporanBelumLengkap(details=masalah)
        self.status = StatusLaporan.MENUNGGU_VALIDASI
        self.nomor_terakhir += 1
        return self.nomor_terakhir

    def setujui(self, butir_bukti_bermasalah: list[dict[str, Any]]) -> None:
        if self.status != StatusLaporan.MENUNGGU_VALIDASI:
            raise KonflikStatus("Hanya laporan berstatus menunggu_validasi yang dapat disetujui.")
        if butir_bukti_bermasalah:  # EC-23: validasi final Dekan diblokir
            raise BuktiBermasalah(details=butir_bukti_bermasalah)
        self.status = StatusLaporan.DISETUJUI

    def kembalikan(self) -> None:
        if self.status != StatusLaporan.MENUNGGU_VALIDASI:
            raise KonflikStatus("Hanya laporan berstatus menunggu_validasi yang dapat dikembalikan.")
        self.status = StatusLaporan.DRAFT

    def buka_kembali(self) -> None:
        if self.status != StatusLaporan.DISETUJUI:
            raise KonflikStatus("Hanya laporan berstatus disetujui yang dapat dibuka kembali.")
        self.status = StatusLaporan.DRAFT


def periksa_ekspor(jenis: JenisEkspor, format_: FormatEkspor, final: bool, status: StatusLaporan) -> None:
    """Kombinasi jenis/format yang sah, dan syarat dokumen final (hanya dari laporan yang disetujui)."""
    sah = {
        JenisEkspor.LED: {FormatEkspor.PDF, FormatEkspor.DOCX},
        JenisEkspor.DATA_KUANTITATIF: {FormatEkspor.XLSX},
        JenisEkspor.GAP_ANALYSIS: {FormatEkspor.XLSX},
    }
    if format_ not in sah[jenis]:
        raise KonflikStatus(f"Jenis {jenis.value} hanya tersedia dalam format {sorted(f.value for f in sah[jenis])}.")
    if final and status != StatusLaporan.DISETUJUI:
        raise KonflikStatus("Dokumen final hanya dapat dibuat dari laporan berstatus disetujui.")
