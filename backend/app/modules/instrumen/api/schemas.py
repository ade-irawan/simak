from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.instrumen.domain.entities import JenisEntitas, JenisIpo, TahapPpepp


class RubrikIn(BaseModel):
    skor: int = Field(ge=0, le=4)
    deskriptor: str


class ButirPatch(BaseModel):
    elemen: str | None = None
    deskriptor: str | None = None
    panduan: str | None = None
    bobot: Decimal | None = None
    jenis_ipo: JenisIpo | None = None
    tahap_ppepp: TahapPpepp | None = None
    skema_narasi: list[dict[str, Any]] | None = None
    rubrik: list[RubrikIn] | None = None


class PemetaanItem(BaseModel):
    sumber: JenisEntitas
    indikator_inti_id: UUID | None = None
    aturan: dict[str, Any] = Field(default_factory=dict)
    keterangan: str | None = None
