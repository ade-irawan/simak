"""Batas transaksi satu use case. Peristiwa domain disebarkan setelah commit berhasil."""

from __future__ import annotations

from types import TracebackType
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.core.events import sebarkan


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._peristiwa: list[Any] = []

    def terbitkan(self, peristiwa: Any) -> None:
        self._peristiwa.append(peristiwa)

    async def __aenter__(self) -> UnitOfWork:
        return self

    async def __aexit__(self, tipe: type[BaseException] | None, nilai: BaseException | None, tb: TracebackType | None) -> None:
        if tipe is not None:
            await self.session.rollback()
            self._peristiwa.clear()
            return
        await self.session.commit()
        antrean, self._peristiwa = self._peristiwa, []
        for p in antrean:
            await sebarkan(p, get_session_factory())

    async def simpan(self) -> None:
        """Commit di tengah use case (jarang dibutuhkan)."""
        await self.session.commit()
