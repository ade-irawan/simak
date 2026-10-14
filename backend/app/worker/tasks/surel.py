from __future__ import annotations

from app.infrastructure.mail.smtp_mailer import kirim_surel
from app.worker.celery_app import celery


@celery.task(name="simak.kirim_surel", bind=True, autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def kirim_surel_task(self, ke: str, subjek: str, isi: str) -> bool:  # noqa: ANN001
    return kirim_surel(ke, subjek, isi)
