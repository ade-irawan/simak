"""Templat berkas impor (XLSX/CSV) yang dapat diunduh pengguna.

XLSX berisi empat lembar. ``data`` selalu lembar pertama karena itulah yang dibaca importer: hanya judul kolom,
kolom wajib diberi warna. ``petunjuk`` menjelaskan tiap kolom, ``contoh`` memperlihatkan satu baris terisi (terpisah dari
``data`` agar contoh tidak ikut terimpor), dan ``referensi`` memuat daftar kode yang sah (prodi, tahun akademik).
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

TIPE_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TIPE_CSV = "text/csv; charset=utf-8"

_WAJIB = PatternFill("solid", fgColor="FFD9A0")
_OPSIONAL = PatternFill("solid", fgColor="DDE7F5")
_TEBAL = Font(bold=True)


@dataclass(frozen=True)
class KolomImpor:
    nama: str
    wajib: bool
    tipe: str
    keterangan: str = ""
    contoh: Any = None


def _lebar(ws: Any, lebar: list[int]) -> None:
    for i, w in enumerate(lebar, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def buat_csv(kolom: list[KolomImpor]) -> bytes:
    """Hanya baris judul; BOM agar Excel membaca UTF-8 dengan benar."""
    buf = io.StringIO()
    csv.writer(buf).writerow([k.nama for k in kolom])
    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")


def buat_xlsx(
    judul: str,
    kolom: list[KolomImpor],
    *,
    catatan: list[str] | None = None,
    referensi: dict[str, tuple[list[str], list[list[Any]]]] | None = None,
) -> bytes:
    """``referensi``: nama lembar → (judul kolom, baris)."""
    wb = Workbook()

    ws = wb.active
    ws.title = "data"
    ws.append([k.nama for k in kolom])
    for i, k in enumerate(kolom, start=1):
        c = ws.cell(row=1, column=i)
        c.font, c.fill = _TEBAL, _WAJIB if k.wajib else _OPSIONAL
    ws.freeze_panes = "A2"
    _lebar(ws, [max(16, len(k.nama) + 4) for k in kolom])

    pt = wb.create_sheet("petunjuk")
    pt.append([f"Templat impor: {judul}"])
    pt["A1"].font = Font(bold=True, size=13)
    pt.append([])
    langkah = [
        "1. Isi lembar 'data' mulai baris 2. Jangan mengubah, menambah, atau menghapus judul kolom pada baris 1.",
        "2. Kolom berlatar oranye wajib diisi; kolom berlatar biru boleh dikosongkan.",
        "3. Lembar 'contoh' memperlihatkan satu baris terisi. Lembar 'contoh', 'petunjuk', dan 'referensi' tidak ikut diimpor.",
        "4. Simpan sebagai .xlsx (atau ekspor lembar 'data' sebagai .csv UTF-8), lalu unggah di halaman impor.",
        "5. Maksimal 2000 baris dan 5 MB per berkas. Baris yang bermasalah dilaporkan dengan nomor barisnya.",
        *(catatan or []),
    ]
    for t in langkah:
        pt.append([t])
    pt.append([])
    pt.append(["Kolom", "Wajib", "Tipe", "Keterangan"])
    for c in pt[pt.max_row]:
        c.font, c.fill = _TEBAL, _OPSIONAL
    for k in kolom:
        pt.append([k.nama, "Ya" if k.wajib else "Tidak", k.tipe, k.keterangan])
    _lebar(pt, [30, 8, 34, 90])
    for baris in pt.iter_rows(min_row=1):
        for c in baris:
            c.alignment = Alignment(wrap_text=True, vertical="top")

    ct = wb.create_sheet("contoh")
    ct.append([k.nama for k in kolom])
    ct.append([k.contoh for k in kolom])
    for c in ct[1]:
        c.font = _TEBAL
    _lebar(ct, [max(16, len(k.nama) + 4) for k in kolom])

    for nama, (judul_ref, baris_ref) in (referensi or {}).items():
        rf = wb.create_sheet(nama)
        rf.append(judul_ref)
        for c in rf[1]:
            c.font, c.fill = _TEBAL, _OPSIONAL
        for r in baris_ref:
            rf.append(r)
        _lebar(rf, [24] * len(judul_ref))

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
