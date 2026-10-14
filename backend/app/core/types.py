"""Tipe Pydantic bersama."""

from __future__ import annotations

from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator


def _surel(nilai: str) -> str:
    """Validasi bentuk surel tanpa cek DNS dan tanpa menolak domain internal (.test, .local) yang lazim di kampus/pengembangan."""
    try:
        return validate_email(nilai.strip(), check_deliverability=False, test_environment=True).normalized.lower()
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc


Surel = Annotated[str, AfterValidator(_surel)]
