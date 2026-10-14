"""Pengaturan aplikasi dari variabel lingkungan."""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_JWT_BAWAAN = "dev-only-jwt-secret-ganti-di-produksi-0123456789"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_base_url: str = "http://localhost:8080"
    api_prefix: str = "/api/v1"
    #: Sub-path publik tempat aplikasi dipasang di balik proxy lain (mis. "/simak"); kosong = akar.
    base_path: str = ""
    cors_origins: list[str] = Field(default_factory=list)

    database_url: str = "postgresql+asyncpg://simak:simak@localhost:5432/simak"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = _JWT_BAWAAN
    jwt_algorithm: str = "HS256"
    access_token_menit: int = 15
    refresh_token_hari: int = 7
    cookie_secure: bool = False
    cookie_name: str = "simak_refresh"
    llm_encryption_key: str = ""

    minio_endpoint: str = "minio:9000"
    minio_public_endpoint: str = "localhost:8080"
    minio_root_user: str = "simak-minio"
    minio_root_password: str = "simak-minio-secret"
    minio_bucket: str = "simak-bukti"
    minio_secure: bool = False
    minio_public_secure: bool = False
    url_sementara_menit: int = 15

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "simak@localhost"

    demo_password: str = ""
    fakultas_nama: str = "Fakultas Sains dan Ilmu Komputer"

    simak_db_dir: str = ""

    @field_validator("base_path")
    @classmethod
    def _normalkan_base_path(cls, v: str) -> str:
        v = v.strip().strip("/")
        return f"/{v}" if v else ""

    @property
    def produksi(self) -> bool:
        return self.app_env == "production"

    @property
    def database_url_sinkron(self) -> str:
        """URL SQLAlchemy sinkron (psycopg) untuk Alembic dan CLI."""
        return self.database_url.replace("+asyncpg", "+psycopg")

    @property
    def kunci_fernet(self) -> bytes:
        """Kunci enkripsi API key LLM. Di pengembangan diturunkan dari JWT_SECRET bila kosong."""
        if self.llm_encryption_key:
            return self.llm_encryption_key.encode()
        return base64.urlsafe_b64encode(hashlib.sha256(self.jwt_secret.encode()).digest())

    @property
    def folder_db(self) -> Path:
        """Folder berisi schema.sql dan seed.sql."""
        if self.simak_db_dir:
            return Path(self.simak_db_dir)
        # backend/app/core/config.py -> akar repositori/db
        return Path(__file__).resolve().parents[3] / "db"

    @model_validator(mode="after")
    def _periksa_produksi(self) -> Settings:
        if self.produksi:
            if self.jwt_secret == _JWT_BAWAAN or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET wajib diisi (minimal 32 karakter) di produksi.")
            if not self.llm_encryption_key:
                raise ValueError("LLM_ENCRYPTION_KEY wajib diisi di produksi.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
