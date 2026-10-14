"""Use case laporan: pra-cek, ajukan, setujui, kembalikan, buka kembali, riwayat, catatan validasi."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core import audit
from app.core.exceptions import TidakDitemukan, ValidasiGagal
from app.core.permissions import D, K, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.modules.bukti import public as bukti
from app.modules.laporan import public as laporan_public
from app.modules.laporan.domain.entities import KeputusanValidasi, StatusCatatan, StatusLaporan
from app.modules.laporan.domain.events import (
    LaporanDiajukan,
    LaporanDibukaKembali,
    LaporanDikembalikan,
    LaporanDisetujui,
)
from app.modules.laporan.domain.ports import PenyusunCuplikan
from app.modules.laporan.domain.rules import StatusLaporanState, terkunci
from app.modules.laporan.infrastructure.models import CatatanValidasi, Laporan, LaporanPengajuan
from app.modules.pemetaan import public as pemetaan
from app.modules.pengguna import public as pengguna
from app.modules.siklus import public as siklus


def _sekarang() -> datetime:
    return datetime.now(UTC)


class LayananLaporan:
    def __init__(self, uow: UnitOfWork, penyusun: PenyusunCuplikan):
        self.uow, self.session, self.penyusun = uow, uow.session, penyusun

    # ------------------------------------------------------------ util
    async def _siklus_untuk_baca(self, pemanggil: Pemanggil, siklus_id: UUID) -> Any:
        sk = await siklus.ambil_ringkas_siklus(self.session, siklus_id)
        pemanggil.wajib_baca_prodi(sk.prodi_id)
        return sk

    async def _laporan(self, laporan_id: UUID) -> tuple[Laporan, Any]:
        lap = await self.session.get(Laporan, laporan_id)
        if lap is None:
            raise TidakDitemukan("Laporan tidak ditemukan.")
        return lap, await siklus.ambil_ringkas_siklus(self.session, lap.siklus_id)

    @staticmethod
    def _pengajuan_dict(p: LaporanPengajuan, *, dengan_cuplikan: bool = False) -> dict[str, Any]:
        d = {
            "id": p.id,
            "nomor": p.nomor,
            "diajukan_oleh": p.diajukan_oleh,
            "diajukan_pada": p.diajukan_pada,
            "keputusan": p.keputusan,
            "diputuskan_oleh": p.diputuskan_oleh,
            "diputuskan_pada": p.diputuskan_pada,
            "catatan_umum": p.catatan_umum,
        }
        if dengan_cuplikan:
            d["cuplikan"] = p.cuplikan
        return d

    async def _pengajuan_terakhir(self, laporan_id: UUID) -> LaporanPengajuan | None:
        return (
            await self.session.execute(
                select(LaporanPengajuan).where(LaporanPengajuan.laporan_id == laporan_id).order_by(LaporanPengajuan.nomor.desc()).limit(1)
            )
        ).scalar_one_or_none()

    # ------------------------------------------------------------ status & pra-cek
    async def status(self, pemanggil: Pemanggil, siklus_id: UUID) -> dict[str, Any]:
        await self._siklus_untuk_baca(pemanggil, siklus_id)
        lap = await laporan_public.ambil_atau_buat(self.session, siklus_id)
        await self.session.commit()
        p = await self._pengajuan_terakhir(lap.id)
        catatan_terbuka = 0
        if p:
            catatan_terbuka = len(
                (
                    await self.session.execute(
                        select(CatatanValidasi.id).where(
                            CatatanValidasi.pengajuan_id == p.id, CatatanValidasi.status == StatusCatatan.TERBUKA
                        )
                    )
                )
                .scalars()
                .all()
            )
        return {
            "laporan_id": lap.id,
            "siklus_id": siklus_id,
            "status": lap.status,
            "terkunci": terkunci(lap.status),
            "row_version": lap.row_version,
            "pengajuan_terakhir": self._pengajuan_dict(p) if p else None,
            "catatan_validasi_terbuka": catatan_terbuka,
            "dibuka_kembali_pada": lap.dibuka_kembali_pada,
        }

    async def kumpulkan_masalah(self, siklus_id: UUID) -> list[dict[str, Any]]:
        """Butir yang menghalangi pengajuan: belum lengkap, bukti tidak terjangkau, menunggu dokumen direktorat, data kosong."""
        sk = await siklus.ambil_ringkas_siklus(self.session, siklus_id)
        lembar = await siklus.daftar_lembar(self.session, siklus_id)
        bermasalah = await bukti.bukti_bermasalah(self.session, [b.id for b in lembar])
        data = await pemetaan.data_banyak_butir(
            self.session, [b.instrumen_butir_id for b in lembar], sk.prodi_id, sk.ts_tahun_akademik_id, sk.jumlah_tahun_data
        )
        hasil = []
        for b in lembar:
            sumber = data.get(b.instrumen_butir_id, [])
            kosong_semua = bool(sumber) and all(s["kosong"] for s in sumber)
            masalah = siklus.masalah_pengajuan(
                status=b.status_kelengkapan,
                bukti_bermasalah=len(bermasalah.get(b.id, [])),
                menunggu_dokumen_eksternal=b.menunggu_dokumen_eksternal,
                sumber_data_kosong=[s["sumber"] for s in sumber if s["kosong"]] if kosong_semua else [],
            )
            if masalah:
                hasil.append({"butir_siklus_id": b.id, "kode": b.kode, "masalah": masalah})
        return hasil

    async def pra_cek(self, pemanggil: Pemanggil, siklus_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(K)
        sk = await siklus.ambil_ringkas_siklus(self.session, siklus_id)
        pemanggil.wajib_kaprodi(sk.prodi_id)
        masalah = await self.kumpulkan_masalah(siklus_id)
        return {"siap_diajukan": not masalah, "jumlah_masalah": len(masalah), "butir": masalah}

    # ------------------------------------------------------------ alur
    async def ajukan(self, pemanggil: Pemanggil, siklus_id: UUID, catatan: str | None) -> dict[str, Any]:
        pemanggil.wajib(K)
        sk = await siklus.ambil_ringkas_siklus(self.session, siklus_id)
        pemanggil.wajib_kaprodi(sk.prodi_id)  # AksesDitolak bila bukan Kaprodi prodi pemilik siklus (EC-11, EC-12)
        lap = await laporan_public.ambil_atau_buat(self.session, siklus_id)
        state = StatusLaporanState(lap.status, await self._nomor_terakhir(lap.id))
        masalah = await self.kumpulkan_masalah(siklus_id) if lap.status == StatusLaporan.DRAFT else []
        nomor = state.ajukan(masalah)
        cuplikan = await self.penyusun.susun(siklus_id)
        async with self.uow:
            lap.status = state.status
            pengajuan = LaporanPengajuan(
                laporan_id=lap.id, nomor=nomor, diajukan_oleh=pemanggil.id, catatan_umum=catatan, cuplikan=cuplikan
            )
            self.session.add(pengajuan)
            await self.session.flush()
            # Catatan validasi dari putaran sebelumnya dianggap sudah ditindaklanjuti dengan pengajuan ulang.
            self.uow.terbitkan(LaporanDiajukan(lap.id, siklus_id, sk.prodi_id, pengajuan.id, nomor))
            await audit.catat(
                self.session,
                "laporan.ajukan",
                pemanggil=pemanggil,
                entitas="laporan",
                entitas_id=lap.id,
                prodi_id=sk.prodi_id,
                detail={"nomor": nomor},
            )
        return {
            "laporan_id": lap.id,
            "status": lap.status,
            "pengajuan": {"id": pengajuan.id, "nomor": nomor, "diajukan_pada": pengajuan.diajukan_pada},
        }

    async def _nomor_terakhir(self, laporan_id: UUID) -> int:
        p = await self._pengajuan_terakhir(laporan_id)
        return p.nomor if p else 0

    async def setujui(self, pemanggil: Pemanggil, laporan_id: UUID, catatan_umum: str | None) -> dict[str, Any]:
        pemanggil.wajib(D)
        lap, sk = await self._laporan(laporan_id)
        pengajuan = await self._pengajuan_menunggu(lap.id)
        lembar = await siklus.daftar_lembar(self.session, sk.id)
        bermasalah = await bukti.bukti_bermasalah(self.session, [b.id for b in lembar])
        kode = {b.id: b.kode for b in lembar}
        state = StatusLaporanState(lap.status, pengajuan.nomor if pengajuan else 0)
        state.setujui(
            [
                {"butir_siklus_id": str(bid), "kode": kode.get(bid), "bukti": [{"id": str(x["id"]), "judul": x["judul"]} for x in daftar]}
                for bid, daftar in bermasalah.items()
            ]
        )
        assert pengajuan is not None
        async with self.uow:
            lap.status = state.status
            pengajuan.keputusan, pengajuan.diputuskan_oleh, pengajuan.diputuskan_pada = (
                KeputusanValidasi.DISETUJUI,
                pemanggil.id,
                _sekarang(),
            )
            pengajuan.catatan_umum = catatan_umum or pengajuan.catatan_umum
            self.uow.terbitkan(LaporanDisetujui(lap.id, sk.id, sk.prodi_id, pengajuan.nomor))
            await audit.catat(
                self.session,
                "laporan.setujui",
                pemanggil=pemanggil,
                entitas="laporan",
                entitas_id=lap.id,
                prodi_id=sk.prodi_id,
                detail={"nomor": pengajuan.nomor},
            )
        return {"laporan_id": lap.id, "status": lap.status, "pengajuan": {"nomor": pengajuan.nomor, "keputusan": pengajuan.keputusan}}

    async def _pengajuan_menunggu(self, laporan_id: UUID) -> LaporanPengajuan | None:
        return (
            await self.session.execute(
                select(LaporanPengajuan).where(
                    LaporanPengajuan.laporan_id == laporan_id, LaporanPengajuan.keputusan == KeputusanValidasi.MENUNGGU
                )
            )
        ).scalar_one_or_none()

    async def kembalikan(
        self, pemanggil: Pemanggil, laporan_id: UUID, catatan_umum: str | None, catatan_butir: list[Any]
    ) -> dict[str, Any]:
        pemanggil.wajib(D)
        lap, sk = await self._laporan(laporan_id)
        pengajuan = await self._pengajuan_menunggu(lap.id)
        state = StatusLaporanState(lap.status)
        state.kembalikan()
        assert pengajuan is not None
        if not catatan_umum and not catatan_butir:
            raise ValidasiGagal("Sertakan catatan_umum atau catatan_butir agar Kaprodi tahu apa yang diperbaiki.")
        lembar_ids = {b.id for b in await siklus.daftar_lembar(self.session, sk.id)}
        for c in catatan_butir:
            if c.butir_siklus_id not in lembar_ids:
                raise ValidasiGagal("Butir pada catatan tidak termasuk siklus ini.", details=[{"butir_siklus_id": str(c.butir_siklus_id)}])
        async with self.uow:
            lap.status = state.status
            pengajuan.keputusan, pengajuan.diputuskan_oleh, pengajuan.diputuskan_pada = (
                KeputusanValidasi.DIKEMBALIKAN,
                pemanggil.id,
                _sekarang(),
            )
            pengajuan.catatan_umum = catatan_umum
            if catatan_umum:
                self.session.add(
                    CatatanValidasi(pengajuan_id=pengajuan.id, butir_siklus_id=None, isi=catatan_umum, dibuat_oleh=pemanggil.id)
                )
            for c in catatan_butir:
                self.session.add(
                    CatatanValidasi(pengajuan_id=pengajuan.id, butir_siklus_id=c.butir_siklus_id, isi=c.isi, dibuat_oleh=pemanggil.id)
                )
            self.uow.terbitkan(LaporanDikembalikan(lap.id, sk.id, sk.prodi_id, pengajuan.nomor))
            await audit.catat(
                self.session,
                "laporan.kembalikan",
                pemanggil=pemanggil,
                entitas="laporan",
                entitas_id=lap.id,
                prodi_id=sk.prodi_id,
                detail={"nomor": pengajuan.nomor, "catatan_butir": len(catatan_butir)},
            )
        # Cuplikan pengajuan tetap tersimpan sebagai riwayat (EC-08).
        return {"laporan_id": lap.id, "status": lap.status, "pengajuan": {"nomor": pengajuan.nomor, "keputusan": pengajuan.keputusan}}

    async def buka_kembali(self, pemanggil: Pemanggil, laporan_id: UUID, alasan: str | None) -> dict[str, Any]:
        pemanggil.wajib(D)
        lap, sk = await self._laporan(laporan_id)
        state = StatusLaporanState(lap.status)
        state.buka_kembali()
        asesor_aktif = await pengguna.jumlah_asesor_aktif(self.session, sk.prodi_id)
        async with self.uow:
            lap.status, lap.dibuka_kembali_oleh, lap.dibuka_kembali_pada = state.status, pemanggil.id, _sekarang()
            self.uow.terbitkan(LaporanDibukaKembali(lap.id, sk.id, sk.prodi_id))
            await audit.catat(
                self.session,
                "laporan.buka_kembali",
                pemanggil=pemanggil,
                entitas="laporan",
                entitas_id=lap.id,
                prodi_id=sk.prodi_id,
                detail={"alasan": alasan, "asesor_aktif": asesor_aktif},
            )
        hasil: dict[str, Any] = {"laporan_id": lap.id, "status": lap.status}
        if asesor_aktif:  # EC-29: asesor tetap melihat versi terakhir yang disetujui
            hasil["peringatan"] = (
                f"Ada {asesor_aktif} asesor aktif. Mereka tetap melihat versi terakhir yang disetujui "
                "sampai versi baru diajukan dan disetujui."
            )
        return hasil

    # ------------------------------------------------------------ riwayat & catatan
    async def riwayat(self, pemanggil: Pemanggil, laporan_id: UUID) -> list[dict[str, Any]]:
        pemanggil.wajib(D, K)
        lap, sk = await self._laporan(laporan_id)
        pemanggil.wajib_baca_prodi(sk.prodi_id)
        baris = (
            (
                await self.session.execute(
                    select(LaporanPengajuan).where(LaporanPengajuan.laporan_id == lap.id).order_by(LaporanPengajuan.nomor.desc())
                )
            )
            .scalars()
            .all()
        )
        return [self._pengajuan_dict(p) for p in baris]

    async def pengajuan(self, pemanggil: Pemanggil, pengajuan_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(D, K)
        p = await self.session.get(LaporanPengajuan, pengajuan_id)
        if p is None:
            raise TidakDitemukan("Pengajuan tidak ditemukan.")
        _, sk = await self._laporan(p.laporan_id)
        pemanggil.wajib_baca_prodi(sk.prodi_id)
        catatan = (
            (
                await self.session.execute(
                    select(CatatanValidasi).where(CatatanValidasi.pengajuan_id == p.id).order_by(CatatanValidasi.created_at)
                )
            )
            .scalars()
            .all()
        )
        return self._pengajuan_dict(p, dengan_cuplikan=True) | {
            "catatan": [
                {
                    "id": c.id,
                    "butir_siklus_id": c.butir_siklus_id,
                    "isi": c.isi,
                    "status": c.status,
                    "diselesaikan_pada": c.diselesaikan_pada,
                }
                for c in catatan
            ]
        }

    async def catatan_terbuka(self, pemanggil: Pemanggil, siklus_id: UUID) -> list[dict[str, Any]]:
        """Catatan Dekan dari pengajuan terakhir yang dikembalikan, tampil per butir ke Kaprodi (EC-08)."""
        await self._siklus_untuk_baca(pemanggil, siklus_id)
        lap = await laporan_public.ambil_atau_buat(self.session, siklus_id)
        p = await self._pengajuan_terakhir(lap.id)
        if p is None:
            return []
        catatan = (
            (
                await self.session.execute(
                    select(CatatanValidasi).where(CatatanValidasi.pengajuan_id == p.id).order_by(CatatanValidasi.created_at)
                )
            )
            .scalars()
            .all()
        )
        return [{"id": c.id, "butir_siklus_id": c.butir_siklus_id, "isi": c.isi, "status": c.status} for c in catatan]

    async def selesaikan_catatan(self, pemanggil: Pemanggil, catatan_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(K)
        c = await self.session.get(CatatanValidasi, catatan_id)
        if c is None:
            raise TidakDitemukan("Catatan tidak ditemukan.")
        p = await self.session.get(LaporanPengajuan, c.pengajuan_id)
        assert p is not None
        _, sk = await self._laporan(p.laporan_id)
        pemanggil.wajib_kaprodi(sk.prodi_id)
        async with self.uow:
            c.status, c.diselesaikan_oleh, c.diselesaikan_pada = StatusCatatan.SELESAI, pemanggil.id, _sekarang()
            await audit.catat(self.session, "catatan_validasi.selesai", pemanggil=pemanggil, entitas="catatan_validasi", entitas_id=c.id)
        return {"id": c.id, "status": c.status, "diselesaikan_pada": c.diselesaikan_pada}
