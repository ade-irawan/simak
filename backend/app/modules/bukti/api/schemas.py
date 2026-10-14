from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.bukti.domain.entities import AksesTautan, JenisBukti


class UnggahanIn(BaseModel):
    nama_berkas: str = Field(min_length=1, max_length=255)
    mime_type: str
    ukuran_byte: int = Field(ge=0)


class BuktiIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jenis: JenisBukti
    judul: str = Field(min_length=3, max_length=300)
    objek_key: str | None = None
    nama_berkas: str | None = None
    url: str | None = None
    akses_tautan: AksesTautan | None = None
    sumber: str | None = None
    tanggal_dokumen: date | None = None
    deskripsi: str | None = None
    berlaku_untuk: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def _sesuai_jenis(self) -> BuktiIn:
        if self.jenis == JenisBukti.BERKAS and not self.objek_key:
            raise ValueError("objek_key wajib untuk bukti berkas")
        if self.jenis == JenisBukti.TAUTAN and not self.url:
            raise ValueError("url wajib untuk bukti tautan")
        return self


class BuktiPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    row_version: int
    judul: str | None = Field(default=None, min_length=3, max_length=300)
    url: str | None = None
    objek_key: str | None = None
    nama_berkas: str | None = None
    akses_tautan: AksesTautan | None = None
    sumber: str | None = None
    tanggal_dokumen: date | None = None
    deskripsi: str | None = None
    berlaku_untuk: list[UUID] | None = None


class TautkanButirIn(BaseModel):
    keterangan: str | None = None
