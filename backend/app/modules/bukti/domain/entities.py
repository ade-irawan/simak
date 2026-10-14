from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class JenisBukti(StrEnum):
    BERKAS = "berkas"
    TAUTAN = "tautan"


class AksesTautan(StrEnum):
    PUBLIK = "publik"
    TERBATAS = "terbatas"


class StatusCekBukti(StrEnum):
    BELUM_DICEK = "belum_dicek"
    OK = "ok"
    TIDAK_TERJANGKAU = "tidak_terjangkau"


@dataclass(frozen=True)
class HasilProbe:
    """Hasil satu pemeriksaan keterjangkauan. ``kode_http`` None = gagal jaringan / berkas tidak ada."""

    ada: bool
    kode_http: int | None = None
    galat: str | None = None


@dataclass(frozen=True)
class HasilCek:
    status: StatusCekBukti
    gagal_beruntun: int
    kode_http: int | None
