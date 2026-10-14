from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

JenisDokumen = Literal[
    "tracer_study",
    "kepuasan_mahasiswa",
    "kepuasan_dosen",
    "kepuasan_tendik",
    "kepuasan_lulusan",
    "kepuasan_pengguna_lulusan",
    "kepuasan_mitra",
]


class DokumenIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jenis: JenisDokumen
    judul: str = Field(min_length=3)
    sumber_unit: str = "Direktorat Kemahasiswaan"
    tahun_akademik_id: UUID
    periode_mulai: date | None = None
    periode_selesai: date | None = None
    populasi: int | None = Field(default=None, ge=0)
    jumlah_responden: int | None = Field(default=None, ge=0)
    metodologi: str | None = None
    bukti_id: UUID
    diterima_pada: date | None = None
    prodi_id: list[UUID] = Field(min_length=1, description="Prodi yang dituju dokumen ini")

    @model_validator(mode="after")
    def _periksa(self) -> DokumenIn:
        if self.periode_mulai and self.periode_selesai and self.periode_selesai < self.periode_mulai:
            raise ValueError("periode_selesai tidak boleh sebelum periode_mulai")
        if self.populasi is not None and self.jumlah_responden is not None and self.jumlah_responden > self.populasi:
            raise ValueError("jumlah_responden tidak boleh melebihi populasi")
        return self


class DokumenPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    judul: str | None = None
    periode_mulai: date | None = None
    periode_selesai: date | None = None
    populasi: int | None = Field(default=None, ge=0)
    jumlah_responden: int | None = Field(default=None, ge=0)
    metodologi: str | None = None
    diterima_pada: date | None = None
    prodi_id: list[UUID] | None = None


class IndikatorIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prodi_id: UUID
    kode: str = Field(min_length=2)
    nama: str = Field(min_length=2)
    nilai: Decimal | None = None
    satuan: str | None = None
    jumlah_responden: int | None = Field(default=None, ge=0)
    catatan: str | None = None
