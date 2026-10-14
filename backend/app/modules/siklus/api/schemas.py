from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.siklus.domain.entities import PengelolaButir, StatusKelengkapan, StatusNarasi, StatusSiklus


class Dasar(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SiklusIn(Dasar):
    prodi_id: UUID
    instrumen_versi_id: UUID | None = Field(default=None, description="Kosong = versi aktif untuk LAM prodi")
    nama: str = Field(min_length=3)
    ts_tahun_akademik_id: UUID
    jumlah_tahun_data: int = Field(default=3, ge=1, le=7)
    tanggal_mulai: date
    tenggat: date | None = None
    target_peringkat_kode: str | None = None

    @model_validator(mode="after")
    def _tenggat(self) -> SiklusIn:
        if self.tenggat and self.tenggat < self.tanggal_mulai:
            raise ValueError("tenggat tidak boleh sebelum tanggal_mulai")
        return self


class SiklusPatch(Dasar):
    nama: str | None = None
    tenggat: date | None = None
    target_peringkat_kode: str | None = None
    status: StatusSiklus | None = None


class MigrasiIn(Dasar):
    instrumen_versi_id: UUID


class ButirSiklusPatch(Dasar):
    row_version: int
    status_kelengkapan: StatusKelengkapan | None = None
    skor_estimasi: Decimal | None = Field(default=None, ge=0, le=4)
    catatan: str | None = None


class NarasiIn(Dasar):
    row_version: int | None = Field(default=None, description="Wajib bila bagian sudah ada")
    isi: str
    status: StatusNarasi = StatusNarasi.DRAFT
    permintaan_llm_id: UUID | None = None


class PenugasanButirIn(Dasar):
    pengelola: PengelolaButir
    penanggung_jawab_id: UUID | None = None


class PenugasanMassalIn(PenugasanButirIn):
    butir_siklus_ids: list[UUID] = Field(min_length=1)
