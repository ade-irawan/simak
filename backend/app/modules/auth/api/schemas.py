from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.permissions import Peran
from app.core.types import Surel


class LoginIn(BaseModel):
    email: Surel
    password: str = Field(min_length=1)


class ProdiRingkas(BaseModel):
    id: UUID
    kode: str
    nama: str


class InstrumenRingkas(BaseModel):
    lam: str
    kode_versi: str | None = None


class PeranOut(BaseModel):
    penugasan_id: UUID
    peran: Peran
    prodi: ProdiRingkas | None = None
    instrumen: InstrumenRingkas | None = None
    berlaku_sampai: datetime | None = None


class ProfilOut(BaseModel):
    id: UUID
    nama: str
    email: str
    wajib_ganti_sandi: bool
    peran: list[PeranOut]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    pengguna: ProfilOut


class GantiSandiIn(BaseModel):
    sandi_lama: str
    sandi_baru: str


class LupaSandiIn(BaseModel):
    email: Surel


class ResetSandiIn(BaseModel):
    token: str
    password_baru: str


class BukaKunciIn(BaseModel):
    token: str
