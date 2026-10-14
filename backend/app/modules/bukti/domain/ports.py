"""Port modul bukti. Implementasi ada di app/infrastructure (MinIO, HTTP)."""

from __future__ import annotations

from datetime import timedelta
from typing import Protocol

from app.modules.bukti.domain.entities import HasilProbe


class PenyimpananBerkas(Protocol):
    async def pastikan_bucket(self) -> None: ...

    def url_unggah(self, objek_key: str, kedaluwarsa: timedelta) -> str: ...

    def url_unduh(self, objek_key: str, nama_berkas: str | None, kedaluwarsa: timedelta) -> str: ...

    async def ada(self, objek_key: str) -> bool: ...

    async def ukuran(self, objek_key: str) -> int | None: ...

    async def baca(self, objek_key: str, maks_byte: int | None = None) -> bytes: ...

    async def simpan(self, objek_key: str, data: bytes, mime: str) -> None: ...

    async def hapus(self, objek_key: str) -> None: ...


class ProbeTautan(Protocol):
    async def periksa(self, url: str) -> HasilProbe: ...
