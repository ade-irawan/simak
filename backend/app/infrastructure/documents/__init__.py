"""Perender dokumen ekspor: DOCX (python-docx), PDF (Jinja2 + WeasyPrint), XLSX (openpyxl)."""

from __future__ import annotations

from typing import Any

from app.infrastructure.documents.docx_renderer import render_docx
from app.infrastructure.documents.pdf_renderer import render_pdf
from app.infrastructure.documents.xlsx_renderer import render_gap_xlsx, render_kuantitatif_xlsx
from app.modules.laporan.domain.entities import FormatEkspor, JenisEkspor

MIME = {
    FormatEkspor.PDF: "application/pdf",
    FormatEkspor.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    FormatEkspor.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class PerenderBerkas:
    """Memenuhi port ``PerenderDokumen`` modul laporan."""

    def render(
        self, jenis: JenisEkspor, format_: FormatEkspor, cuplikan: dict[str, Any], *, final: bool, metadata: dict[str, Any]
    ) -> tuple[bytes, str]:
        if jenis == JenisEkspor.LED and format_ == FormatEkspor.DOCX:
            isi = render_docx(cuplikan, final=final, metadata=metadata)
        elif jenis == JenisEkspor.LED and format_ == FormatEkspor.PDF:
            isi = render_pdf(cuplikan, final=final, metadata=metadata)
        elif jenis == JenisEkspor.DATA_KUANTITATIF:
            isi = render_kuantitatif_xlsx(cuplikan, final=final, metadata=metadata)
        elif jenis == JenisEkspor.GAP_ANALYSIS:
            isi = render_gap_xlsx(cuplikan, metadata=metadata)
        else:
            raise ValueError(f"Kombinasi {jenis.value}/{format_.value} tidak didukung")
        return isi, MIME[format_]
