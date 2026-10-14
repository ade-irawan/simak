"""Aturan instrumen: validasi aturan pemetaan dan kesiapan aktivasi. Tanpa I/O."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

AGREGASI_VALID = {"daftar", "hitung", "jumlah", "rata_rata"}
KUNCI_ATURAN_VALID = {"filter", "agregasi", "kolom", "batasi_tahun"}


def validasi_aturan(aturan: dict[str, Any]) -> list[str]:
    """Daftar pesan galat untuk ``pemetaan_butir.aturan``; kosong bila sah.

    Bentuk: ``{"filter": {kolom: nilai | [nilai]}, "agregasi": "daftar|hitung|jumlah|rata_rata",
    "kolom": "<kolom angka>", "batasi_tahun": true}``. ``batasi_tahun`` membatasi data pada TS-n..TS siklus (EC-04).
    """
    galat: list[str] = []
    for kunci in aturan:
        if kunci not in KUNCI_ATURAN_VALID:
            galat.append(f"Kunci aturan tidak dikenal: {kunci}.")
    filt = aturan.get("filter", {})
    if not isinstance(filt, dict):
        galat.append("'filter' harus berupa objek {kolom: nilai}.")
    agregasi = aturan.get("agregasi", "daftar")
    if agregasi not in AGREGASI_VALID:
        galat.append(f"Agregasi harus salah satu dari {sorted(AGREGASI_VALID)}.")
    if agregasi in {"jumlah", "rata_rata"} and not aturan.get("kolom"):
        galat.append(f"Agregasi '{agregasi}' membutuhkan 'kolom'.")
    return galat


def periksa_siap_aktif(
    *,
    jumlah_butir: int,
    jumlah_peringkat: int,
    bobot_kriteria: list[Decimal | None],
    nilai_akhir_maks: Decimal | None,
    jumlah_kriteria_kosong: int,
) -> tuple[list[str], list[str]]:
    """(galat penghalang, peringatan) sebelum Dekan mengaktifkan versi instrumen."""
    galat: list[str] = []
    peringatan: list[str] = []
    if jumlah_butir == 0:
        galat.append("Instrumen belum memiliki butir.")
    if jumlah_peringkat < 2:
        galat.append("Instrumen minimal memiliki dua peringkat.")
    berbobot = [b for b in bobot_kriteria if b is not None]
    if nilai_akhir_maks is not None and berbobot and sum(berbobot) != nilai_akhir_maks:
        peringatan.append(f"Jumlah bobot kriteria ({sum(berbobot)}) berbeda dari nilai akhir maksimum ({nilai_akhir_maks}).")
    if jumlah_kriteria_kosong:
        peringatan.append(f"{jumlah_kriteria_kosong} kriteria belum memiliki butir.")
    return galat, peringatan
