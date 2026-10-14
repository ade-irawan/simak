"""Cara tiap sumber data inti terikat pada prodi.

* ``Langsung``  : kolom ``prodi_id`` pada tabelnya sendiri (statistik, kurikulum, keuangan).
* ``Penghubung``: tabel penghubung ``*_prodi`` (kegiatan, publikasi, kerja sama, sarana) — satu data, banyak prodi.
* ``Afiliasi``  : dosen terkait prodi lewat ``dosen_prodi`` (EC-01); tanpa afiliasi = data bersama fakultas.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidasiGagal
from app.core.permissions import CakupanProdi, Pemanggil
from app.modules.tridharma.models import DosenProdi


class Penangan:
    """Antarmuka. ``prodi`` selalu berupa himpunan UUID (kosong = bersama / tingkat UPPS)."""

    #: nama bidang input yang bukan kolom tabel utama (diabaikan saat mengisi kolom)
    bidang_ekstra: frozenset[str] = frozenset()

    async def prodi_ids(self, session: AsyncSession, obj: Any) -> set[UUID]:
        raise NotImplementedError

    def prodi_dari_input(self, pemanggil: Pemanggil, data: dict[str, Any]) -> list[tuple[UUID, Decimal]]:
        """Daftar (prodi, proporsi) dari input; default ke prodi pemanggil bila kosong."""
        raise NotImplementedError

    async def simpan(self, session: AsyncSession, obj: Any, data: dict[str, Any], prodi: list[tuple[UUID, Decimal]]) -> None:
        return None

    def lengkapi_input(self, data: dict[str, Any], prodi: list[tuple[UUID, Decimal]]) -> None:
        """Mengisi kolom turunan di ``data`` setelah prodi ditentukan (mis. ``prodi_id`` bawaan)."""

    async def ekstra(self, session: AsyncSession, obj: Any) -> dict[str, Any]:
        return {}

    def saring(self, stmt: Select[Any], model: Any, cakupan: CakupanProdi, prodi_id: UUID | None) -> Select[Any]:
        raise NotImplementedError


def _prodi_default(pemanggil: Pemanggil) -> list[tuple[UUID, Decimal]]:
    from app.core.permissions import SP, K

    ids = pemanggil.prodi_dari(K, SP)
    if len(ids) == 1:
        return [(next(iter(ids)), Decimal(1))]
    return []


class Langsung(Penangan):
    def __init__(self, kolom: str = "prodi_id", boleh_kosong: bool = False):
        self.kolom, self.boleh_kosong = kolom, boleh_kosong

    async def prodi_ids(self, session: AsyncSession, obj: Any) -> set[UUID]:
        nilai = getattr(obj, self.kolom)
        return {nilai} if nilai else set()

    def lengkapi_input(self, data: dict[str, Any], prodi: list[tuple[UUID, Decimal]]) -> None:
        data[self.kolom] = prodi[0][0] if prodi else None

    def prodi_dari_input(self, pemanggil: Pemanggil, data: dict[str, Any]) -> list[tuple[UUID, Decimal]]:
        nilai = data.get(self.kolom)
        if nilai:
            return [(nilai, Decimal(1))]
        default = _prodi_default(pemanggil)
        if default:
            return default  # Kaprodi/Staf Prodi: bawaan ke prodi sendiri
        if self.boleh_kosong:
            return []  # tingkat UPPS: hanya Staf Fakultas (diperiksa layanan)
        raise ValidasiGagal("prodi_id wajib diisi.", details=[{"kolom": self.kolom}])

    def saring(self, stmt: Select[Any], model: Any, cakupan: CakupanProdi, prodi_id: UUID | None) -> Select[Any]:
        kolom = getattr(model, self.kolom)
        if prodi_id:
            stmt = stmt.where(kolom == prodi_id)
        return cakupan.terapkan(stmt, kolom, termasuk_null=self.boleh_kosong)


class Penghubung(Penangan):
    def __init__(self, penghubung: Any, fk: str, *, bidang_input: str, proporsi: bool = False):
        self.penghubung, self.fk, self.bidang_input, self.proporsi = penghubung, fk, bidang_input, proporsi
        self.bidang_ekstra = frozenset({bidang_input})

    async def prodi_ids(self, session: AsyncSession, obj: Any) -> set[UUID]:
        kolom_fk = getattr(self.penghubung, self.fk)
        return set((await session.execute(select(self.penghubung.prodi_id).where(kolom_fk == obj.id))).scalars())

    def prodi_dari_input(self, pemanggil: Pemanggil, data: dict[str, Any]) -> list[tuple[UUID, Decimal]]:
        mentah = data.get(self.bidang_input) or []
        if mentah:
            if self.proporsi:
                return [(a.prodi_id, a.proporsi) for a in mentah]
            return [(p, Decimal(1)) for p in mentah]
        return _prodi_default(pemanggil)

    async def simpan(self, session: AsyncSession, obj: Any, data: dict[str, Any], prodi: list[tuple[UUID, Decimal]]) -> None:
        kolom_fk = getattr(self.penghubung, self.fk)
        await session.execute(delete(self.penghubung).where(kolom_fk == obj.id))
        for pid, prop in prodi:
            nilai: dict[str, Any] = {self.fk: obj.id, "prodi_id": pid}
            if self.proporsi:
                nilai["proporsi"] = prop
            session.add(self.penghubung(**nilai))

    async def ekstra(self, session: AsyncSession, obj: Any) -> dict[str, Any]:
        if not self.proporsi:
            return {}
        kolom_fk = getattr(self.penghubung, self.fk)
        baris = (await session.execute(select(self.penghubung).where(kolom_fk == obj.id))).scalars().all()
        return {"atribusi_prodi": [{"prodi_id": b.prodi_id, "proporsi": b.proporsi} for b in baris]}

    def saring(self, stmt: Select[Any], model: Any, cakupan: CakupanProdi, prodi_id: UUID | None) -> Select[Any]:
        kolom_fk = getattr(self.penghubung, self.fk)
        sub = select(kolom_fk)
        if prodi_id:
            sub = sub.where(self.penghubung.prodi_id == prodi_id)
        if not cakupan.semua:
            sub = sub.where(self.penghubung.prodi_id.in_(cakupan.prodi_ids))
            return stmt.where(model.id.in_(sub))
        return stmt.where(model.id.in_(sub)) if prodi_id else stmt


class Afiliasi(Penangan):
    bidang_ekstra = frozenset({"afiliasi"})

    async def prodi_ids(self, session: AsyncSession, obj: Any) -> set[UUID]:
        return set((await session.execute(select(DosenProdi.prodi_id).where(DosenProdi.dosen_id == obj.id))).scalars())

    def prodi_dari_input(self, pemanggil: Pemanggil, data: dict[str, Any]) -> list[tuple[UUID, Decimal]]:
        mentah = data.get("afiliasi") or []
        if mentah:
            return [(a.prodi_id, a.proporsi_beban) for a in mentah]
        return []  # dosen tanpa afiliasi awal = data bersama; layanan menambah afiliasi default untuk K/SP

    async def simpan(self, session: AsyncSession, obj: Any, data: dict[str, Any], prodi: list[tuple[UUID, Decimal]]) -> None:
        for a in data.get("afiliasi") or []:
            session.add(
                DosenProdi(
                    dosen_id=obj.id,
                    prodi_id=a.prodi_id,
                    tahun_akademik_id=a.tahun_akademik_id,
                    jenis=a.jenis,
                    proporsi_beban=a.proporsi_beban,
                    sks_diampu=a.sks_diampu,
                )
            )

    async def ekstra(self, session: AsyncSession, obj: Any) -> dict[str, Any]:
        baris = (await session.execute(select(DosenProdi).where(DosenProdi.dosen_id == obj.id))).scalars().all()
        return {
            "afiliasi": [
                {
                    "id": b.id,
                    "prodi_id": b.prodi_id,
                    "tahun_akademik_id": b.tahun_akademik_id,
                    "jenis": b.jenis,
                    "proporsi_beban": b.proporsi_beban,
                    "sks_diampu": b.sks_diampu,
                }
                for b in baris
            ]
        }

    def saring(self, stmt: Select[Any], model: Any, cakupan: CakupanProdi, prodi_id: UUID | None) -> Select[Any]:
        sub = select(DosenProdi.dosen_id)
        if prodi_id:
            sub = sub.where(DosenProdi.prodi_id == prodi_id)
        if not cakupan.semua:
            sub = sub.where(DosenProdi.prodi_id.in_(cakupan.prodi_ids))
            return stmt.where(model.id.in_(sub))
        return stmt.where(model.id.in_(sub)) if prodi_id else stmt
