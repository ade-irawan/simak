from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.laporan.domain.entities import FormatEkspor, JenisEkspor


class AjukanIn(BaseModel):
    catatan: str | None = None


class SetujuiIn(BaseModel):
    catatan_umum: str | None = None


class CatatanButirIn(BaseModel):
    butir_siklus_id: UUID
    isi: str = Field(min_length=3)


class KembalikanIn(BaseModel):
    catatan_umum: str | None = None
    catatan_butir: list[CatatanButirIn] = Field(default_factory=list)


class BukaKembaliIn(BaseModel):
    alasan: str | None = None


class EksporIn(BaseModel):
    jenis: JenisEkspor = JenisEkspor.LED
    format: FormatEkspor = FormatEkspor.DOCX
    final: bool = False
