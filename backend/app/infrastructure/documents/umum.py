"""Fungsi bantu bersama perender dokumen."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

CATATAN_ESTIMASI = "Skor adalah estimasi internal SIMAK, bukan penilaian resmi asesor."


def varian(cuplikan: dict[str, Any]) -> str:
    """Folder templat menurut LAM: format LED tiap lembaga berbeda meski data intinya satu."""
    return "lam_infokom_2_1" if cuplikan["instrumen"]["lam"] == "LAM_INFOKOM" else "lamsama_3_1"


def judul_instrumen(cuplikan: dict[str, Any]) -> str:
    ins = cuplikan["instrumen"]
    return f"IAPS {ins['kode_versi']} {ins['lam'].replace('_', ' ')}"


def teks_data(d: dict[str, Any]) -> str:
    """Ringkasan satu sumber data terpetakan untuk dokumen."""
    if d.get("kosong"):
        return f"{d['sumber']}: belum ada data"
    if d.get("nilai") is not None:
        return f"{d['sumber']}: {d['jumlah']} catatan, nilai {d['nilai']}"
    return f"{d['sumber']}: {d['jumlah']} catatan"


def teks_bukti(b: dict[str, Any]) -> str:
    sumber = b.get("url") or b.get("nama_berkas") or "-"
    tanda = " [TIDAK TERJANGKAU]" if b.get("status_cek") == "tidak_terjangkau" else ""
    return f"{b['judul']} — {sumber}{tanda}"


def waktu_lokal(iso: str | None) -> str:
    """ISO 8601 → "14 Okt 2026 08:06 WIB" (zona waktu kampus)."""
    if not iso:
        return "-"
    try:
        dt = datetime.fromisoformat(iso).astimezone(ZoneInfo("Asia/Jakarta"))
    except ValueError:
        return iso
    bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"][dt.month - 1]
    return f"{dt.day} {bulan} {dt.year} {dt:%H:%M} WIB"
