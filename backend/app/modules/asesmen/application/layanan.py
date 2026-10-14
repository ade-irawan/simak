"""Tampilan telaah asesor: seluruhnya dibaca dari cuplikan pengajuan terakhir yang DISETUJUI Dekan.

Modul ini tidak pernah membuka lembar kerja berjalan (``butir_siklus``, ``narasi_butir``) — perubahan setelah
persetujuan tidak tampil sampai disetujui lagi (EC-29).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core import audit
from app.core.exceptions import AksesDitolak, TidakDitemukan
from app.core.permissions import A, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.modules.asesmen.infrastructure.models import TelaahAsesor
from app.modules.laporan import public as laporan
from app.modules.referensi import public as referensi
from app.modules.siklus import public as siklus


class LayananAsesmen:
    def __init__(self, uow: UnitOfWork):
        self.uow, self.session = uow, uow.session

    async def _cuplikan_untuk_siklus(self, pemanggil: Pemanggil, siklus_id: UUID) -> dict[str, Any]:
        sk = await siklus.ambil_ringkas_siklus(self.session, siklus_id)
        try:
            pemanggil.wajib_asesor(sk.prodi_id)  # prodi lain / luar jendela → 403 + audit (EC-26)
        except AksesDitolak:
            raise
        c = await laporan.cuplikan_disetujui_terakhir(self.session, sk.prodi_id)
        if c is None or c["siklus_id"] != siklus_id:
            raise TidakDitemukan("Belum ada versi laporan yang disetujui untuk siklus ini.")
        return c

    def _jendela(self, pemanggil: Pemanggil, prodi_id: UUID) -> dict[str, Any]:
        t = next((t for t in pemanggil.penugasan if t.peran == A and t.prodi_id == prodi_id), None)
        return {"mulai": t.berlaku_mulai, "sampai": t.berlaku_sampai} if t else {}

    async def _telaah(self, asesor_id: UUID, pengajuan_id: UUID) -> dict[UUID, TelaahAsesor]:
        baris = (
            (
                await self.session.execute(
                    select(TelaahAsesor).where(TelaahAsesor.asesor_id == asesor_id, TelaahAsesor.pengajuan_id == pengajuan_id)
                )
            )
            .scalars()
            .all()
        )
        return {t.butir_siklus_id: t for t in baris}

    async def daftar_siklus(self, pemanggil: Pemanggil) -> dict[str, Any]:
        pemanggil.wajib(A)
        hasil = []
        for prodi_id in pemanggil.prodi_dari(A):
            c = await laporan.cuplikan_disetujui_terakhir(self.session, prodi_id)
            if c is None:
                continue
            prodi = await referensi.ambil_prodi(self.session, prodi_id)
            cup = c["cuplikan"]
            butir = [b for k in cup["kriteria"] for b in k["butir"]]
            telaah = await self._telaah(pemanggil.id, c["pengajuan_id"])
            hasil.append(
                {
                    "siklus_id": c["siklus_id"],
                    "prodi": {"kode": prodi.kode, "nama": prodi.nama},
                    "instrumen": f"{cup['instrumen']['lam'].replace('_', ' ')} {cup['instrumen']['kode_versi']}",
                    "versi_laporan": {"pengajuan_id": c["pengajuan_id"], "nomor": c["nomor"], "disetujui_pada": c["disetujui_pada"]},
                    "jendela_asesmen": self._jendela(pemanggil, prodi_id),
                    "butir": {"jumlah": len(butir), "sudah_ditelaah": sum(1 for t in telaah.values() if t.sudah_ditelaah)},
                }
            )
        async with self.uow:
            await audit.catat(self.session, "asesmen.baca_siklus", pemanggil=pemanggil)
        return {"data": hasil, "meta": {"page": 1, "per_page": max(len(hasil), 1), "total": len(hasil)}}

    async def daftar_butir(self, pemanggil: Pemanggil, siklus_id: UUID) -> list[dict[str, Any]]:
        pemanggil.wajib(A)
        c = await self._cuplikan_untuk_siklus(pemanggil, siklus_id)
        telaah = await self._telaah(pemanggil.id, c["pengajuan_id"])
        hasil = []
        for k in c["cuplikan"]["kriteria"]:
            butir = []
            for b in k["butir"]:
                bid = UUID(b["butir_siklus_id"])
                t = telaah.get(bid)
                butir.append(
                    {
                        "butir_siklus_id": bid,
                        "kode": b["kode"],
                        "elemen": b["elemen"],
                        "skor_estimasi": b["skor_estimasi"],
                        "jumlah_bukti": len(b["bukti"]),
                        "sudah_ditelaah": bool(t and t.sudah_ditelaah),
                        "catatan": t.catatan if t else None,
                    }
                )
            hasil.append({"kode": k["kode"], "nama": k["nama"], "butir": butir})
        return hasil

    async def _cari_butir(self, pemanggil: Pemanggil, butir_siklus_id: UUID) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        info = await siklus.info_butir_untuk_penulisan(self.session, butir_siklus_id)
        c = await self._cuplikan_untuk_siklus(pemanggil, info.siklus_id)
        for k in c["cuplikan"]["kriteria"]:
            for b in k["butir"]:
                if b["butir_siklus_id"] == str(butir_siklus_id):
                    return c, k, b
        raise TidakDitemukan("Butir tidak ada pada versi laporan yang disetujui.")

    async def detail_butir(self, pemanggil: Pemanggil, butir_siklus_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(A)
        c, k, b = await self._cari_butir(pemanggil, butir_siklus_id)
        t = (await self._telaah(pemanggil.id, c["pengajuan_id"])).get(butir_siklus_id)
        async with self.uow:
            await audit.catat(
                self.session,
                "asesmen.baca_butir",
                pemanggil=pemanggil,
                entitas="butir_siklus",
                entitas_id=butir_siklus_id,
                detail={"pengajuan_nomor": c["nomor"]},
            )
        return {
            "versi_laporan": {"pengajuan_id": c["pengajuan_id"], "nomor": c["nomor"], "disetujui_pada": c["disetujui_pada"]},
            "kriteria": {"kode": k["kode"], "nama": k["nama"]},
            "butir": {
                kk: b[kk]
                for kk in (
                    "butir_siklus_id",
                    "kode",
                    "elemen",
                    "deskriptor",
                    "jenis_ipo",
                    "tahap_ppepp",
                    "bobot",
                    "rubrik",
                    "ambang",
                    "skema_narasi",
                )
            },
            "skor_estimasi": b["skor_estimasi"],
            "estimasi_internal": True,
            "narasi": b["narasi"],
            "bukti": b["bukti"],
            "data_terpetakan": b["data_terpetakan"],
            "telaah": {"sudah_ditelaah": bool(t and t.sudah_ditelaah), "catatan": t.catatan if t else None},
            "hanya_baca": True,
        }

    async def telaah(self, pemanggil: Pemanggil, butir_siklus_id: UUID, sudah_ditelaah: bool, catatan: str | None) -> dict[str, Any]:
        pemanggil.wajib(A)
        c, _, _ = await self._cari_butir(pemanggil, butir_siklus_id)
        async with self.uow:
            nilai = {"sudah_ditelaah": sudah_ditelaah, "catatan": catatan}
            await self.session.execute(
                pg_insert(TelaahAsesor)
                .values(butir_siklus_id=butir_siklus_id, asesor_id=pemanggil.id, pengajuan_id=c["pengajuan_id"], **nilai)
                .on_conflict_do_update(index_elements=["butir_siklus_id", "asesor_id", "pengajuan_id"], set_=nilai)
            )
            await audit.catat(
                self.session,
                "asesmen.telaah",
                pemanggil=pemanggil,
                entitas="butir_siklus",
                entitas_id=butir_siklus_id,
                detail={"sudah_ditelaah": sudah_ditelaah},
            )
        t = (await self._telaah(pemanggil.id, c["pengajuan_id"]))[butir_siklus_id]
        return {
            "butir_siklus_id": butir_siklus_id,
            "pengajuan_nomor": c["nomor"],
            "sudah_ditelaah": t.sudah_ditelaah,
            "updated_at": t.updated_at,
        }
