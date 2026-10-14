"""Pengiriman tugas latar ke Celery lewat nama tugas (API tidak perlu mengimpor kode worker)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def kirim_tugas(nama: str, *args: Any, antrean: str = "default") -> str | None:
    """Mengembalikan ID tugas Celery, atau None bila broker tidak dapat dijangkau (pemanggil menandai tugas gagal)."""
    try:
        from app.worker.celery_app import celery

        return celery.send_task(nama, args=list(args), queue=antrean).id
    except Exception:
        logger.exception("Gagal mengirim tugas %s", nama)
        return None
