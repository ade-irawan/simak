from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class ProdiOut(BaseModel):
    id: UUID
    kode: str
    nama: str
    jenjang: str
    lam: str


class TahunAkademikIn(BaseModel):
    kode: str
    tanggal_mulai: date
    tanggal_selesai: date
    is_aktif: bool = False

    @model_validator(mode="after")
    def _rentang(self) -> TahunAkademikIn:
        if self.tanggal_selesai <= self.tanggal_mulai:
            raise ValueError("tanggal_selesai harus setelah tanggal_mulai")
        return self


class TahunAkademikPatch(BaseModel):
    kode: str | None = None
    tanggal_mulai: date | None = None
    tanggal_selesai: date | None = None
    is_aktif: bool | None = None


class TahunAkademikOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kode: str
    tanggal_mulai: date
    tanggal_selesai: date
    is_aktif: bool


class PengaturanOut(BaseModel):
    kunci: str
    nilai: Any
    deskripsi: str | None = None


class PengaturanIn(BaseModel):
    nilai: Any
