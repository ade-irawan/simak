"""Pengirim surel SMTP (sinkron; dipanggil dari tugas Celery). Tanpa SMTP_HOST, isi surel hanya dicatat ke log (pengembangan)."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def kirim_surel(ke: str, subjek: str, isi: str) -> bool:
    cfg = get_settings()
    if not cfg.smtp_host:
        logger.info("[SUREL-DEV] Ke: %s | Subjek: %s\n%s", ke, subjek, isi)
        return False
    pesan = EmailMessage()
    pesan["From"], pesan["To"], pesan["Subject"] = cfg.smtp_from, ke, subjek
    pesan.set_content(isi)
    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=20) as smtp:
        smtp.starttls()
        if cfg.smtp_user:
            smtp.login(cfg.smtp_user, cfg.smtp_password)
        smtp.send_message(pesan)
    return True
