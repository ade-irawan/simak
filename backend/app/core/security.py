"""Hash sandi (Argon2), JWT akses, token acak sekali pakai, dan enkripsi rahasia."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.exceptions import TidakTerautentikasi, ValidasiGagal

_hasher = PasswordHasher()
MIN_PANJANG_SANDI = 10


def hash_sandi(sandi: str) -> str:
    return _hasher.hash(sandi)


def verifikasi_sandi(hash_tersimpan: str, sandi: str) -> bool:
    try:
        return _hasher.verify(hash_tersimpan, sandi)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def perlu_rehash(hash_tersimpan: str) -> bool:
    return _hasher.check_needs_rehash(hash_tersimpan)


# Hash tiruan agar waktu respons login tidak membedakan email yang ada dan tidak ada.
HASH_TIRUAN = hash_sandi("tiruan-agar-waktu-sama")


def wajib_sandi_kuat(sandi: str) -> None:
    masalah = []
    if len(sandi) < MIN_PANJANG_SANDI:
        masalah.append({"kolom": "password", "pesan": f"Minimal {MIN_PANJANG_SANDI} karakter."})
    if sandi.isalpha() or sandi.isdigit():
        masalah.append({"kolom": "password", "pesan": "Gabungkan huruf dan angka/simbol."})
    if masalah:
        raise ValidasiGagal("Sandi terlalu lemah.", details=masalah)


def buat_access_token(pengguna_id: UUID) -> tuple[str, int]:
    cfg = get_settings()
    sekarang = datetime.now(UTC)
    ttl = timedelta(minutes=cfg.access_token_menit)
    payload = {"sub": str(pengguna_id), "iat": sekarang, "exp": sekarang + ttl, "jti": secrets.token_hex(8)}
    return jwt.encode(payload, cfg.jwt_secret, algorithm=cfg.jwt_algorithm), int(ttl.total_seconds())


def baca_access_token(token: str) -> dict[str, Any]:
    cfg = get_settings()
    try:
        return jwt.decode(token, cfg.jwt_secret, algorithms=[cfg.jwt_algorithm], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError as exc:
        raise TidakTerautentikasi("Token tidak sah atau kedaluwarsa.") from exc


def buat_token_acak() -> tuple[str, str]:
    """(token untuk pengguna, hash untuk disimpan). Hanya hash yang masuk basis data."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def enkripsi_rahasia(teks: str) -> bytes:
    return Fernet(get_settings().kunci_fernet).encrypt(teks.encode())


def dekripsi_rahasia(data: bytes) -> str:
    try:
        return Fernet(get_settings().kunci_fernet).decrypt(bytes(data)).decode()
    except InvalidToken as exc:  # kunci enkripsi berubah
        raise ValidasiGagal("Rahasia tersimpan tidak dapat didekripsi dengan kunci saat ini.") from exc
