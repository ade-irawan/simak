"""Peristiwa domain dalam proses. Efek samping lintas modul (notifikasi, surel) memakainya,
bukan impor langsung antarmodul."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

E = TypeVar("E")
Penangan = Callable[[Any, AsyncSession], Awaitable[None]]

_penangan: dict[type, list[Penangan]] = defaultdict(list)


@dataclass(frozen=True)
class Peristiwa:
    """Kelas dasar peristiwa domain."""


def pada[E](tipe: type[E]) -> Callable[[Penangan], Penangan]:
    """Mendaftarkan penangan. Penangan berjalan SETELAH transaksi use case berhasil, di sesi sendiri."""

    def dekorator(fn: Penangan) -> Penangan:
        _penangan[tipe].append(fn)
        return fn

    return dekorator


async def sebarkan(peristiwa: Any, session_factory: Callable[[], AsyncSession]) -> None:
    for tipe in type(peristiwa).__mro__:
        for fn in _penangan.get(tipe, []):
            try:
                async with session_factory() as session:
                    await fn(peristiwa, session)
                    await session.commit()
            except Exception:
                logger.exception("Penangan peristiwa %s gagal", type(peristiwa).__name__)


def kosongkan_penangan() -> None:  # untuk pengujian
    _penangan.clear()
