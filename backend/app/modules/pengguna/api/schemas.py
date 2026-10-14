from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.permissions import Peran
from app.core.types import Surel
from app.modules.pengguna.domain.entities import StatusPengguna, StatusPenugasan


class RingkasPengguna(BaseModel):
    id: UUID
    nama: str


class RingkasProdi(BaseModel):
    id: UUID
    kode: str
    nama: str


class PenugasanOut(BaseModel):
    id: UUID
    pengguna: RingkasPengguna
    peran: Peran
    prodi: RingkasProdi | None = None
    status: StatusPenugasan
    berlaku_mulai: datetime | None = None
    berlaku_sampai: datetime | None = None
    disetujui_oleh: RingkasPengguna | None = None
    catatan: str | None = None


class PenggunaOut(BaseModel):
    id: UUID
    nama: str
    email: str
    status: StatusPengguna
    wajib_ganti_sandi: bool
    jumlah_gagal_login: int
    terkunci_sampai: datetime | None = None
    login_terakhir: datetime | None = None
    peran: list[PenugasanOut] = []


class PenugasanAwal(BaseModel):
    peran: Peran
    prodi_id: UUID | None = None
    berlaku_mulai: datetime | None = None
    berlaku_sampai: datetime | None = None


class PenggunaIn(BaseModel):
    nama: str = Field(min_length=2)
    email: Surel
    password_awal: str | None = Field(default=None, description="Kosong = pengguna menetapkan sandi lewat tautan surel")
    penugasan: list[PenugasanAwal] = []


class PenggunaPatch(BaseModel):
    nama: str | None = Field(default=None, min_length=2)
    status: StatusPengguna | None = None


class AlasanIn(BaseModel):
    alasan: str = Field(min_length=5)


class SandiBaruIn(BaseModel):
    sandi_baru: str = Field(min_length=1, description="Sandi sementara; pengguna wajib menggantinya saat masuk")


class KunciOut(BaseModel):
    id: UUID
    status: StatusPengguna
    terkunci_sampai: datetime | None = None
    jumlah_gagal_login: int


class PenugasanIn(BaseModel):
    pengguna_id: UUID
    peran: Peran
    prodi_id: UUID | None = None
    berlaku_mulai: datetime | None = None
    berlaku_sampai: datetime | None = None
    catatan: str | None = None


class PenyetujuanIn(BaseModel):
    berlaku_mulai: datetime | None = None
    berlaku_sampai: datetime | None = None
