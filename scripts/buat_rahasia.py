#!/usr/bin/env python3
"""Mengisi rahasia acak pada berkas .env hasil salinan .env.example (sandi DB/MinIO, JWT, kunci enkripsi LLM)."""

import re
import secrets
import sys
from pathlib import Path

try:
    from cryptography.fernet import Fernet

    fernet = Fernet.generate_key().decode()
except ImportError:  # kunci Fernet = 32 byte urlsafe-base64
    import base64

    fernet = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()

jalur = Path(sys.argv[1] if len(sys.argv) > 1 else ".env")
teks = jalur.read_text()
pg, minio = secrets.token_urlsafe(18), secrets.token_urlsafe(18)
teks = teks.replace("ganti-sandi-db", pg).replace("ganti-sandi-minio", minio)
teks = teks.replace("ganti-dengan-rahasia-acak-minimal-32-karakter", secrets.token_urlsafe(48))
teks = re.sub(r"^LLM_ENCRYPTION_KEY=\s*$", f"LLM_ENCRYPTION_KEY={fernet}", teks, flags=re.M)
jalur.write_text(teks)
