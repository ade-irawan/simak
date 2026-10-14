from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.infrastructure.documents.umum import CATATAN_ESTIMASI, judul_instrumen, teks_bukti, teks_data, varian, waktu_lokal

_TEMPLAT = Path(__file__).parent / "templates"
_env = Environment(loader=FileSystemLoader(_TEMPLAT), autoescape=select_autoescape(["html"]))
_env.filters["data"] = teks_data
_env.filters["bukti"] = teks_bukti
_env.filters["waktu"] = waktu_lokal


def render_html(cuplikan: dict[str, Any], *, final: bool, metadata: dict[str, Any]) -> str:
    templat = _env.get_template(f"{varian(cuplikan)}/led.html")
    return templat.render(
        c=cuplikan, final=final, meta=metadata, judul_instrumen=judul_instrumen(cuplikan), catatan_estimasi=CATATAN_ESTIMASI
    )


def render_pdf(cuplikan: dict[str, Any], *, final: bool, metadata: dict[str, Any]) -> bytes:
    from weasyprint import HTML  # impor lambat; hanya di worker

    return HTML(string=render_html(cuplikan, final=final, metadata=metadata)).write_pdf()
