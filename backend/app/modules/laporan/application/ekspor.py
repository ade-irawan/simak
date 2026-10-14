"""Ekspor dokumen (PDF/DOCX/XLSX). API hanya membuat catatan tugas; perenderan berat dijalankan Celery (antrean ``dokumen``)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core import audit
from app.core.config import get_settings
from app.core.exceptions import AksesDitolak, KonflikStatus, TidakDitemukan
from app.core.permissions import SF, SP, D, K, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.modules.bukti.public import PenyimpananBerkas
from app.modules.laporan import public as laporan_public
from app.modules.laporan.domain.entities import (
    FormatEkspor,
    JenisEkspor,
    KeputusanValidasi,
    StatusTugas,
)
from app.modules.laporan.domain.ports import PenyusunCuplikan, PerenderDokumen
from app.modules.laporan.domain.rules import periksa_ekspor
from app.modules.laporan.infrastructure.models import EksporDokumen, LaporanPengajuan
from app.modules.penilaian import public as penilaian
from app.modules.referensi import public as referensi
from app.modules.siklus import public as siklus

logger = logging.getLogger(__name__)


def _sekarang() -> datetime:
    return datetime.now(UTC)


class LayananEkspor:
    def __init__(
        self,
        uow: UnitOfWork,
        penyusun: PenyusunCuplikan,
        penyimpanan: PenyimpananBerkas,
        perender: PerenderDokumen | None = None,
        kirim: Callable[..., str | None] | None = None,
    ):
        self.uow, self.session = uow, uow.session
        self.penyusun, self.penyimpanan, self.perender, self.kirim = penyusun, penyimpanan, perender, kirim

    @staticmethod
    def _dict(e: EksporDokumen) -> dict[str, Any]:
        return {
            "id": e.id,
            "status": e.status,
            "jenis": e.jenis,
            "format": e.format,
            "ukuran_byte": e.ukuran_byte,
            "metadata": e.metadata_,
            "galat": e.galat,
            "selesai_pada": e.selesai_pada,
            "created_at": e.created_at,
        }

    # ------------------------------------------------------------ API
    async def minta(self, pemanggil: Pemanggil, siklus_id: UUID, jenis: JenisEkspor, format_: FormatEkspor, final: bool) -> dict[str, Any]:
        pemanggil.wajib(D, K, SP, SF)
        sk = await siklus.ambil_ringkas_siklus(self.session, siklus_id)
        pemanggil.wajib_baca_prodi(sk.prodi_id)
        if jenis == JenisEkspor.GAP_ANALYSIS:
            pemanggil.wajib(D)
        lap = await laporan_public.ambil_atau_buat(self.session, siklus_id)
        periksa_ekspor(jenis, format_, final, lap.status)
        pengajuan_id = None
        if final:
            # Dokumen final selalu dari cuplikan pengajuan yang disetujui, bukan data yang sedang berjalan.
            pengajuan_id = (
                await self.session.execute(
                    select(LaporanPengajuan.id)
                    .where(LaporanPengajuan.laporan_id == lap.id, LaporanPengajuan.keputusan == KeputusanValidasi.DISETUJUI)
                    .order_by(LaporanPengajuan.nomor.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if pengajuan_id is None:
                raise KonflikStatus("Belum ada pengajuan yang disetujui.")
        async with self.uow:
            e = EksporDokumen(
                siklus_id=siklus_id,
                pengajuan_id=pengajuan_id,
                jenis=jenis,
                format=format_,
                diminta_oleh=pemanggil.id,
                metadata_={"final": final},
            )
            self.session.add(e)
            await self.session.flush()
            await audit.catat(
                self.session,
                "ekspor.minta",
                pemanggil=pemanggil,
                entitas="ekspor_dokumen",
                entitas_id=e.id,
                prodi_id=sk.prodi_id,
                detail={"jenis": jenis, "format": format_, "final": final},
            )
        task_id = self.kirim("simak.ekspor_dokumen", str(e.id), antrean="dokumen") if self.kirim else None
        async with self.uow:
            if task_id:
                e.task_id = task_id
            else:
                e.status, e.galat = StatusTugas.GAGAL, "Antrean tugas tidak tersedia. Coba lagi beberapa saat."
        return {"id": e.id, "status": e.status, "jenis": jenis, "format": format_}

    async def _muat_untuk_pemohon(self, pemanggil: Pemanggil, ekspor_id: UUID) -> EksporDokumen:
        e = await self.session.get(EksporDokumen, ekspor_id)
        if e is None:
            raise TidakDitemukan("Ekspor tidak ditemukan.")
        if e.diminta_oleh != pemanggil.id and not pemanggil.punya(D):
            raise AksesDitolak(alasan="bukan_pemohon")
        return e

    async def status(self, pemanggil: Pemanggil, ekspor_id: UUID) -> dict[str, Any]:
        return self._dict(await self._muat_untuk_pemohon(pemanggil, ekspor_id))

    async def unduh(self, pemanggil: Pemanggil, ekspor_id: UUID) -> dict[str, Any]:
        e = await self._muat_untuk_pemohon(pemanggil, ekspor_id)
        if e.status != StatusTugas.SELESAI or not e.objek_key:
            raise KonflikStatus("Dokumen belum selesai dibuat.")
        kedaluwarsa = timedelta(minutes=get_settings().url_sementara_menit)
        nama = e.objek_key.rsplit("/", 1)[-1]
        return {
            "url": self.penyimpanan.url_unduh(e.objek_key, nama, kedaluwarsa),
            "nama_berkas": nama,
            "kedaluwarsa_pada": _sekarang() + kedaluwarsa,
        }

    # ------------------------------------------------------------ worker
    async def proses(self, ekspor_id: UUID) -> None:
        """Dijalankan Celery. Hasil ditulis ke tabel ``ekspor_dokumen`` sehingga status dapat dibaca API tanpa backend hasil Celery."""
        assert self.perender is not None
        e = await self.session.get(EksporDokumen, ekspor_id)
        if e is None:
            return
        e.status = StatusTugas.DIPROSES
        await self.session.commit()
        try:
            final = bool(e.metadata_.get("final"))
            sk = await siklus.ambil_ringkas_siklus(self.session, e.siklus_id)
            nomor: int | None = None
            if e.jenis == JenisEkspor.GAP_ANALYSIS:
                cuplikan: dict[str, Any] = await penilaian.hitung_gap_siklus(self.session, e.siklus_id)
                data_per = _sekarang()
            elif final and e.pengajuan_id:
                p = await self.session.get(LaporanPengajuan, e.pengajuan_id)
                assert p is not None and p.cuplikan is not None
                cuplikan, nomor, data_per = p.cuplikan, p.nomor, p.diajukan_pada
            else:
                cuplikan = await self.penyusun.susun(e.siklus_id)
                data_per = _sekarang()
            prodi = await referensi.ambil_prodi(self.session, sk.prodi_id)
            definisi_nama = cuplikan.get("instrumen") or {}
            metadata = {
                "final": final,
                "prodi": prodi.nama,
                "pengajuan_nomor": nomor,
                "data_per": data_per.isoformat(),
                "instrumen": f"{str(definisi_nama.get('lam', '')).replace('_', ' ')} {definisi_nama.get('kode_versi', '')}".strip(),
            }
            isi, _mime = self.perender.render(e.jenis, e.format, cuplikan, final=final, metadata=metadata)
            key = f"ekspor/{e.siklus_id}/{e.id}-{e.jenis.value}{'-final' if final else '-draf'}.{e.format.value}"
            await self.penyimpanan.simpan(key, isi, _mime)
            e.objek_key, e.ukuran_byte, e.metadata_ = key, len(isi), metadata
            e.status, e.selesai_pada, e.galat = StatusTugas.SELESAI, _sekarang(), None
        except Exception as exc:
            logger.exception("Ekspor %s gagal", ekspor_id)
            e.status, e.galat, e.selesai_pada = StatusTugas.GAGAL, f"{type(exc).__name__}: {exc}"[:500], _sekarang()
        await self.session.commit()
