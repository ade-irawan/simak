from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.ppepp.domain.entities import StatusTahapan


class Dasar(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StandarIn(Dasar):
    kode: str = Field(min_length=1)
    nama: str = Field(min_length=3)
    kategori: str | None = None
    dokumen_sumber: str | None = None
    versi: str | None = None
    is_aktif: bool = True


class StandarPatch(Dasar):
    nama: str | None = None
    kategori: str | None = None
    dokumen_sumber: str | None = None
    versi: str | None = None
    is_aktif: bool | None = None


class ButirStandarIn(Dasar):
    nomor: str = Field(min_length=1)
    pernyataan: str = Field(min_length=3)
    indikator: str | None = None
    target_default: str | None = None
    satuan: str | None = None
    is_aktif: bool = True
    instrumen_butir_ids: list[UUID] = Field(default_factory=list, description="Butir instrumen LAM yang dipenuhi")


class ButirStandarPatch(Dasar):
    nomor: str | None = None
    pernyataan: str | None = None
    indikator: str | None = None
    target_default: str | None = None
    satuan: str | None = None
    is_aktif: bool | None = None
    instrumen_butir_ids: list[UUID] | None = None


class SiklusPpeppIn(Dasar):
    nama: str = Field(min_length=3)
    tahun_akademik_id: UUID
    tanggal_mulai: date
    tanggal_selesai: date | None = None
    siklus_sebelumnya_id: UUID | None = None

    @model_validator(mode="after")
    def _rentang(self) -> SiklusPpeppIn:
        if self.tanggal_selesai and self.tanggal_selesai <= self.tanggal_mulai:
            raise ValueError("tanggal_selesai harus setelah tanggal_mulai")
        return self


class PenetapanIn(Dasar):
    butir_standar_id: UUID
    prodi_id: UUID | None = Field(default=None, description="Kosong = berlaku untuk semua prodi")
    nomor_butir: str = Field(min_length=1)
    isi: str = Field(min_length=3)
    indikator: str = Field(min_length=3)
    target_nilai: Decimal | None = None
    target_satuan: str | None = None
    target_deskripsi: str | None = None
    periode_mulai: date | None = None
    periode_selesai: date | None = None
    penanggung_jawab_id: UUID | None = None

    @model_validator(mode="after")
    def _periode(self) -> PenetapanIn:
        if self.periode_mulai and self.periode_selesai and self.periode_selesai < self.periode_mulai:
            raise ValueError("periode_selesai tidak boleh sebelum periode_mulai")
        return self


class PenetapanPatch(Dasar):
    row_version: int
    nomor_butir: str | None = None
    isi: str | None = None
    indikator: str | None = None
    target_nilai: Decimal | None = None
    target_satuan: str | None = None
    target_deskripsi: str | None = None
    periode_mulai: date | None = None
    periode_selesai: date | None = None
    penanggung_jawab_id: UUID | None = None


class TahapanIn(Dasar):
    row_version: int
    status: StatusTahapan
    uraian: str | None = None
    capaian_nilai: Decimal | None = None
    capaian_deskripsi: str | None = None
    temuan: str | None = None
    tindak_lanjut: str | None = None
    tenggat: date | None = None
    bukti_id: list[UUID] = Field(default_factory=list)
