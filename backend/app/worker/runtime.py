"""Menjalankan korutin dari tugas Celery (sinkron) dengan engine basis data segar per eksekusi."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.database import reset_engine
from app.core.logging import setup_logging
from app.modules.notifikasi.application.penangan import daftarkan_penangan

T = TypeVar("T")


def jalankan[T](fn: Callable[[], Awaitable[T]]) -> T:
    setup_logging()
    daftarkan_penangan()

    async def utama() -> T:
        await reset_engine()
        try:
            return await fn()
        finally:
            await reset_engine()

    return asyncio.run(utama())
