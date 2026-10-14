"""Pemanggil (peran + cakupan prodi) dan aturan otorisasi dasar.

``Pemanggil`` dibangun di server dari ``penugasan_peran`` yang aktif saat permintaan;
klien tidak pernah mengirim peran (docs/arsitektur/03-spesifikasi-api.md §1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.core.exceptions import AksesDitolak


class Peran(StrEnum):
    DEKAN = "dekan"
    KAPRODI = "kaprodi"
    STAF_PRODI = "staf_prodi"
    STAF_FAKULTAS = "staf_fakultas"
    ASESOR = "asesor"
    ADMIN_IT = "admin_it"


# Kode ringkas di dokumen API → peran.
KODE_PERAN: dict[str, Peran] = {
    "D": Peran.DEKAN,
    "K": Peran.KAPRODI,
    "SP": Peran.STAF_PRODI,
    "SF": Peran.STAF_FAKULTAS,
    "A": Peran.ASESOR,
    "IT": Peran.ADMIN_IT,
}

D, K, SP, SF, A, IT = (KODE_PERAN[k] for k in ("D", "K", "SP", "SF", "A", "IT"))
PERAN_PRODI = frozenset({K, SP, A})  # wajib punya prodi_id (ck_penugasan_cakupan)
PERAN_KONTEN = frozenset({D, K, SP, SF, A})  # boleh menyentuh isi data akreditasi (Admin IT tidak)


@dataclass(frozen=True)
class Penugasan:
    id: UUID
    peran: Peran
    prodi_id: UUID | None = None
    berlaku_mulai: datetime | None = None
    berlaku_sampai: datetime | None = None


@dataclass(frozen=True)
class CakupanProdi:
    """Himpunan prodi yang boleh disentuh. Tiap kueri daftar wajib memakainya (tanpa cakupan = tanpa daftar)."""

    semua: bool = False
    prodi_ids: frozenset[UUID] = frozenset()

    def mengizinkan(self, prodi_id: UUID | None) -> bool:
        return self.semua or (prodi_id is not None and prodi_id in self.prodi_ids)

    def terapkan(self, stmt: Any, kolom: Any, *, termasuk_null: bool = False) -> Any:
        """Menambah saringan prodi ke ``select``. ``termasuk_null``: baris tingkat UPPS (prodi NULL) ikut."""
        if self.semua:
            return stmt
        kondisi = kolom.in_(self.prodi_ids)
        if termasuk_null:
            kondisi = kondisi | kolom.is_(None)
        return stmt.where(kondisi)


TANPA_CAKUPAN = CakupanProdi()


@dataclass(frozen=True)
class Pemanggil:
    id: UUID
    nama: str
    email: str
    penugasan: tuple[Penugasan, ...] = ()
    #: Prodi yang butirnya ditugaskan Dekan kepada pemanggil (tanda ¹ di matriks hak akses).
    prodi_ditugaskan: frozenset[UUID] = frozenset()
    ip: str | None = None
    user_agent: str | None = None
    ekstra: dict[str, Any] = field(default_factory=dict, compare=False)

    # ---- peran ----
    @property
    def peran(self) -> frozenset[Peran]:
        return frozenset(p.peran for p in self.penugasan)

    def punya(self, *peran: Peran) -> bool:
        return bool(self.peran & set(peran))

    def wajib(self, *peran: Peran) -> None:
        if not self.punya(*peran):
            raise AksesDitolak(alasan="peran_tidak_sesuai")

    def wajib_bukan_admin_it_saja(self) -> None:
        if not self.punya(*PERAN_KONTEN):
            raise AksesDitolak(alasan="admin_it_tanpa_akses_konten")

    def peran_utama(self) -> Peran | None:
        urutan = [D, K, SF, SP, A, IT]
        return next((p for p in urutan if p in self.peran), None)

    # ---- cakupan prodi ----
    def prodi_dari(self, *peran: Peran) -> frozenset[UUID]:
        return frozenset(p.prodi_id for p in self.penugasan if p.peran in peran and p.prodi_id)

    def cakupan_baca(self, *, termasuk_asesor: bool = False) -> CakupanProdi:
        """Prodi yang boleh dibaca lewat modul biasa. Asesor memakai modul ``asesmen`` (cuplikan)."""
        if self.punya(D, SF):
            return CakupanProdi(semua=True)
        peran = (K, SP, A) if termasuk_asesor else (K, SP)
        return CakupanProdi(prodi_ids=self.prodi_dari(*peran))

    def cakupan_tulis(self) -> CakupanProdi:
        """Prodi tempat pemanggil boleh mengubah data inti: Kaprodi/Staf Prodi di prodinya,
        Staf Fakultas hanya di prodi yang butirnya ditugaskan Dekan (¹)."""
        ids = set(self.prodi_dari(K, SP))
        if self.punya(SF):
            ids |= set(self.prodi_ditugaskan)
        return CakupanProdi(prodi_ids=frozenset(ids))

    def boleh_baca_prodi(self, prodi_id: UUID | None) -> bool:
        return self.cakupan_baca().mengizinkan(prodi_id)

    def wajib_baca_prodi(self, prodi_id: UUID | None) -> None:
        if not self.boleh_baca_prodi(prodi_id):
            raise AksesDitolak(alasan="di_luar_cakupan_prodi")

    def boleh_tulis_prodi(self, prodi_id: UUID | None) -> bool:
        return self.cakupan_tulis().mengizinkan(prodi_id)

    def wajib_tulis_prodi(self, prodi_id: UUID | None) -> None:
        if not self.boleh_tulis_prodi(prodi_id):
            raise AksesDitolak(alasan="di_luar_cakupan_prodi")

    def wajib_kaprodi(self, prodi_id: UUID) -> None:
        if prodi_id not in self.prodi_dari(K):
            raise AksesDitolak(alasan="bukan_kaprodi_prodi_ini")

    def wajib_asesor(self, prodi_id: UUID) -> None:
        if prodi_id not in self.prodi_dari(A):
            raise AksesDitolak(alasan="di_luar_cakupan_prodi")
