"""Aturan PPEPP: selisih terhadap target, saran tahap berikutnya, baseline. Tanpa I/O."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.ppepp.domain.entities import StatusTahapan, Tahap


@dataclass(frozen=True)
class Saran:
    tahap: str
    pesan: str


def selisih_target(capaian: Decimal | None, target: Decimal | None) -> Decimal | None:
    """capaian − target (negatif = di bawah target). None bila salah satunya belum ada."""
    if capaian is None or target is None:
        return None
    return capaian - target


def saran_berikutnya(
    tahap: Tahap, status: StatusTahapan, temuan: str | None, tindak_lanjut: str | None, selisih: Decimal | None
) -> Saran | None:
    """US-C2: temuan pada Evaluasi mendorong tindak lanjut pada Pengendalian; Pengendalian mendorong Peningkatan."""
    if tahap == Tahap.EVALUASI and status == StatusTahapan.SELESAI:
        if (temuan and temuan.strip()) or (selisih is not None and selisih < 0):
            return Saran("pengendalian", "Ada temuan atau capaian di bawah target. Susun tindak lanjut pada tahap Pengendalian.")
        return Saran("peningkatan", "Tidak ada temuan. Lanjutkan ke tahap Peningkatan.")
    if tahap == Tahap.PENGENDALIAN and status == StatusTahapan.SELESAI and tindak_lanjut:
        return Saran("peningkatan", "Tindak lanjut tercatat. Dokumentasikan hasilnya pada tahap Peningkatan.")
    if tahap == Tahap.PELAKSANAAN and status == StatusTahapan.SELESAI:
        return Saran("evaluasi", "Pelaksanaan selesai. Lakukan evaluasi capaian terhadap target.")
    if tahap == Tahap.PENINGKATAN and status == StatusTahapan.SELESAI:
        return Saran("arsip", "Siklus untuk butir ini selesai. Hasil menjadi baseline siklus PPEPP berikutnya.")
    return None


def tahap_valid(nama: str) -> Tahap | None:
    try:
        return Tahap(nama)
    except ValueError:
        return None
