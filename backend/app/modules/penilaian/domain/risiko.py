"""Tingkat risiko kesiapan prodi untuk sorotan merah/kuning di dasbor Dekan (US-F1). Tanpa I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SinyalRisiko:
    persen_siap: float
    bukti_bermasalah: int
    belum_ditugaskan: int
    menunggu_eksternal: int
    tenggat: date | None
    skor_di_bawah_target: bool
    hari_ini: date


def hari_ke_tenggat(tenggat: date | None, hari_ini: date) -> int | None:
    return (tenggat - hari_ini).days if tenggat else None


def tingkat_risiko(s: SinyalRisiko) -> tuple[str, list[str]]:
    """('merah' | 'kuning' | 'hijau', alasan). Merah = butuh tindakan segera."""
    sisa = hari_ke_tenggat(s.tenggat, s.hari_ini)
    merah: list[str] = []
    kuning: list[str] = []
    if s.bukti_bermasalah:
        merah.append(f"{s.bukti_bermasalah} butir memiliki bukti tidak terjangkau")
    if sisa is not None and sisa < 0 and s.persen_siap < 100:
        merah.append("tenggat terlewat")
    elif sisa is not None and sisa <= 30 and s.persen_siap < 70:
        merah.append(f"tenggat {sisa} hari lagi, kesiapan baru {s.persen_siap:.0f}%")
    if s.persen_siap < 70:
        kuning.append(f"kesiapan {s.persen_siap:.0f}%")
    if s.belum_ditugaskan:
        kuning.append(f"{s.belum_ditugaskan} butir belum ditugaskan")
    if s.menunggu_eksternal:
        kuning.append(f"{s.menunggu_eksternal} butir menunggu dokumen Direktorat")
    if s.skor_di_bawah_target:
        kuning.append("skor simulasi di bawah peringkat target")
    if merah:
        return "merah", merah + kuning
    if kuning:
        return "kuning", kuning
    return "hijau", []
