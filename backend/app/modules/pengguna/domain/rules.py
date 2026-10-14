"""Aturan akun: kunci setelah gagal login berturut-turut, validitas penugasan. Tanpa I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.permissions import PERAN_PRODI, Peran


@dataclass(frozen=True)
class HasilGagalLogin:
    jumlah_gagal: int
    terkunci_sampai: datetime | None
    sisa_percobaan: int


def sedang_terkunci(terkunci_sampai: datetime | None, sekarang: datetime) -> bool:
    """Kunci terbuka otomatis begitu masa tunggu lewat (US-A1)."""
    return terkunci_sampai is not None and terkunci_sampai > sekarang


def hitung_gagal_login(jumlah_sebelumnya: int, *, maks_gagal: int, menit_kunci: int, sekarang: datetime) -> HasilGagalLogin:
    jumlah = jumlah_sebelumnya + 1
    if jumlah >= maks_gagal:
        return HasilGagalLogin(jumlah, sekarang + timedelta(minutes=menit_kunci), 0)
    return HasilGagalLogin(jumlah, None, maks_gagal - jumlah)


def penugasan_berlaku(mulai: datetime | None, sampai: datetime | None, sekarang: datetime) -> bool:
    """Jendela waktu penugasan; ``None`` berarti terbuka (mis. Dekan tanpa batas)."""
    return (mulai is None or mulai <= sekarang) and (sampai is None or sampai >= sekarang)


def prodi_wajib(peran: Peran) -> bool:
    return peran in PERAN_PRODI


def periksa_cakupan(peran: Peran, prodi_ada: bool) -> str | None:
    """Pesan galat bila cakupan prodi tidak sesuai peran (cermin ck_penugasan_cakupan)."""
    if prodi_wajib(peran) and not prodi_ada:
        return f"Peran {peran.value} wajib memiliki prodi."
    if not prodi_wajib(peran) and prodi_ada:
        return f"Peran {peran.value} tidak terikat pada satu prodi."
    return None
