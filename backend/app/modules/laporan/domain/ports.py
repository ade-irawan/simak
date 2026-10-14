"""Port modul laporan. Implementasi: penyusun cuplikan (infrastructure/) dan perender dokumen (app/infrastructure/documents)."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from app.modules.laporan.domain.entities import FormatEkspor, JenisEkspor


class PenyusunCuplikan(Protocol):
    async def susun(self, siklus_id: UUID) -> dict[str, Any]:
        """Salinan isi laporan saat ini: narasi, skor estimasi, bukti, dan data terpetakan."""


class PerenderDokumen(Protocol):
    def render(
        self, jenis: JenisEkspor, format_: FormatEkspor, cuplikan: dict[str, Any], *, final: bool, metadata: dict[str, Any]
    ) -> tuple[bytes, str]:
        """Mengembalikan (isi berkas, tipe MIME)."""
