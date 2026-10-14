"""Penomoran halaman: ``page``, ``per_page``, ``sort``, ``q`` → ``{"data": [], "meta": {...}}``."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class Meta(BaseModel):
    page: int
    per_page: int
    total: int


class Halaman[T](BaseModel):
    data: list[T]
    meta: Meta


class ParamHalaman:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
        sort: str | None = Query(None, description="mis. -updated_at"),
        q: str | None = Query(None, description="pencarian teks"),
    ):
        self.page, self.per_page, self.sort, self.q = page, per_page, sort, q

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    def urutan(self, kolom_boleh: dict[str, Any], bawaan: Sequence[Any] = ()) -> list[Any]:
        """Memetakan ``sort`` (koma, awalan ``-`` = menurun) ke ekspresi ORDER BY; kolom tak dikenal diabaikan."""
        hasil: list[Any] = []
        for bagian in (self.sort or "").split(","):
            bagian = bagian.strip()
            if not bagian:
                continue
            menurun = bagian.startswith("-")
            kolom = kolom_boleh.get(bagian.lstrip("-"))
            if kolom is not None:
                hasil.append(kolom.desc() if menurun else kolom.asc())
        return hasil or list(bawaan)


async def halaman(
    session: AsyncSession,
    stmt: Select[Any],
    param: ParamHalaman,
    urutan: Sequence[Any],
    ubah: Callable[[Any], Any],
    *,
    skalar: bool = True,
) -> dict[str, Any]:
    """Menjalankan ``stmt`` dengan COUNT + LIMIT/OFFSET. ``ubah`` mengubah tiap baris menjadi item respons."""
    total = (await session.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))).scalar_one()
    hasil = await session.execute(stmt.order_by(*urutan).limit(param.per_page).offset(param.offset))
    baris = hasil.scalars().all() if skalar else hasil.all()
    return {
        "data": [ubah(b) for b in baris],
        "meta": {"page": param.page, "per_page": param.per_page, "total": total},
    }
