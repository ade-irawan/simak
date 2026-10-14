"""Aplikasi Celery. Tugas hanyalah pembungkus tipis yang memanggil use case yang sama dengan API."""

from __future__ import annotations

from celery import Celery
from kombu import Queue

from app.core.config import get_settings
from app.worker.beat_schedule import JADWAL

cfg = get_settings()
celery = Celery(
    "simak",
    broker=cfg.redis_url,
    include=["app.worker.tasks.dokumen", "app.worker.tasks.llm", "app.worker.tasks.periodik", "app.worker.tasks.surel"],
)
celery.conf.update(
    task_default_queue="default",
    task_queues=(Queue("default"), Queue("dokumen"), Queue("llm"), Queue("periodik")),
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    timezone="Asia/Jakarta",
    enable_utc=True,
    task_track_started=True,
    beat_schedule=JADWAL,
    broker_connection_retry_on_startup=True,
    # Hasil tugas ditulis ke tabel (ekspor_dokumen, permintaan_llm), bukan ke backend hasil Celery.
    task_ignore_result=True,
)
