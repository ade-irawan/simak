"""Engine, session factory, Base deklaratif, dan mixin umum.

Skema fisik berasal dari ``db/schema.sql`` (dijalankan migrasi Alembic 0001); model
SQLAlchemy di tiap modul memetakan tabel itu, bukan membuatnya.
"""

from __future__ import annotations

import enum
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Integer, text
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from app.core.config import get_settings


class Base(DeclarativeBase):
    type_annotation_map = {UUID: PGUUID(as_uuid=True), datetime: DateTime(timezone=True)}


def pg_enum(kelas: type[enum.Enum], nama: str) -> PGEnum:
    """Memetakan StrEnum Python ke tipe ENUM PostgreSQL yang sudah ada."""
    return PGEnum(kelas, name=nama, create_type=False, values_callable=lambda e: [m.value for m in e])


class PkUuid:
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))


class Stempel:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))


class Berversi:
    """Penguncian optimistik (EC-10): ORM menaikkan ``row_version`` di setiap UPDATE."""

    row_version: Mapped[int] = mapped_column(Integer, server_default=text("1"))

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:  # noqa: N805
        return {"version_id_col": cls.row_version}


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, pool_pre_ping=True, pool_size=10, max_overflow=10)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def reset_engine() -> None:
    """Dipakai pengujian untuk mengganti engine antar-loop."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine, _session_factory = None, None


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session
