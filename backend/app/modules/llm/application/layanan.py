"""Use case LLM (opsional): konfigurasi koneksi, uji, aktivasi (persetujuan Dekan), dan permintaan draf narasi.

Prinsip (US-D4, US-G4, EC-24): offline adalah default; mode online hanya aktif setelah persetujuan eksplisit Dekan;
keluaran selalu berstatus draf yang wajib ditinjau Kaprodi; kegagalan LLM tidak pernah menghalangi penulisan manual.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update

from app.core import audit
from app.core.enums import StatusTugas
from app.core.exceptions import KonflikStatus, LlmTidakTersedia, TidakDitemukan, ValidasiGagal
from app.core.permissions import SF, D, K, Pemanggil
from app.core.security import dekripsi_rahasia, enkripsi_rahasia
from app.core.unit_of_work import UnitOfWork
from app.modules.instrumen import public as instrumen
from app.modules.laporan import public as laporan
from app.modules.llm.domain.ports import KlienLlm, ModeLlm
from app.modules.llm.infrastructure.models import KonfigurasiLlm, PermintaanLlm
from app.modules.pemetaan import public as pemetaan
from app.modules.referensi import public as referensi
from app.modules.siklus import public as siklus

logger = logging.getLogger(__name__)

SISTEM = (
    "Anda membantu program studi menyusun draf Laporan Evaluasi Diri (LED) akreditasi dalam bahasa Indonesia formal. "
    "Gunakan HANYA fakta yang diberikan pada konteks; jangan mengarang angka, nama, atau dokumen. "
    "Bila data belum cukup, tulis secara eksplisit apa yang perlu dilengkapi. Susun dalam paragraf ringkas yang sistematis."
)


def _sekarang() -> datetime:
    return datetime.now(UTC)


def _dict(k: KonfigurasiLlm) -> dict[str, Any]:
    # Kunci API TIDAK pernah dikembalikan; hanya penanda keberadaannya.
    return {
        "id": k.id,
        "nama": k.nama,
        "mode": k.mode,
        "base_url": k.base_url,
        "model": k.model,
        "parameter": k.parameter,
        "is_aktif": k.is_aktif,
        "punya_api_key": k.api_key_terenkripsi is not None,
        "disetujui_pada": k.disetujui_pada,
        "diuji_pada": k.diuji_pada,
        "hasil_uji": k.hasil_uji,
    }


class LayananLlm:
    def __init__(self, uow: UnitOfWork, klien: KlienLlm, kirim: Callable[..., str | None] | None = None):
        self.uow, self.session, self.klien, self.kirim = uow, uow.session, klien, kirim

    # ------------------------------------------------------------ konfigurasi
    async def daftar(self) -> list[dict[str, Any]]:
        return [_dict(k) for k in (await self.session.execute(select(KonfigurasiLlm).order_by(KonfigurasiLlm.nama))).scalars()]

    async def _muat(self, konfigurasi_id: UUID) -> KonfigurasiLlm:
        k = await self.session.get(KonfigurasiLlm, konfigurasi_id)
        if k is None:
            raise TidakDitemukan("Konfigurasi LLM tidak ditemukan.")
        return k

    async def buat(self, pemanggil: Pemanggil, data: Any) -> dict[str, Any]:
        pemanggil.wajib(SF)
        async with self.uow:
            k = KonfigurasiLlm(
                nama=data.nama,
                mode=data.mode,
                base_url=data.base_url.rstrip("/"),
                model=data.model,
                parameter=data.parameter,
                created_by=pemanggil.id,
                updated_by=pemanggil.id,
                api_key_terenkripsi=enkripsi_rahasia(data.api_key) if data.api_key else None,
            )
            self.session.add(k)
            await self.session.flush()
            await audit.catat(
                self.session,
                "llm.konfigurasi.buat",
                pemanggil=pemanggil,
                entitas="konfigurasi_llm",
                entitas_id=k.id,
                detail={"mode": data.mode, "model": data.model},
            )
        return _dict(k)

    async def ubah(self, pemanggil: Pemanggil, konfigurasi_id: UUID, data: Any) -> dict[str, Any]:
        pemanggil.wajib(SF)
        k = await self._muat(konfigurasi_id)
        perubahan = data.model_dump(exclude_unset=True)
        async with self.uow:
            api_key = perubahan.pop("api_key", None)
            if "base_url" in perubahan:
                perubahan["base_url"] = perubahan["base_url"].rstrip("/")
            for kolom, nilai in perubahan.items():
                setattr(k, kolom, nilai)
            if api_key:
                k.api_key_terenkripsi = enkripsi_rahasia(api_key)
            # Konfigurasi yang diubah harus diuji dan disetujui ulang sebelum dipakai.
            k.is_aktif, k.disetujui_oleh, k.disetujui_pada, k.diuji_pada, k.hasil_uji = False, None, None, None, None
            k.updated_by = pemanggil.id
            await audit.catat(
                self.session,
                "llm.konfigurasi.ubah",
                pemanggil=pemanggil,
                entitas="konfigurasi_llm",
                entitas_id=k.id,
                detail={"kolom": sorted(list(perubahan) + (["api_key"] if api_key else []))},
            )
        return _dict(k)

    async def uji(self, pemanggil: Pemanggil, konfigurasi_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(D, SF)
        k = await self._muat(konfigurasi_id)
        kunci = dekripsi_rahasia(k.api_key_terenkripsi) if k.api_key_terenkripsi else None
        try:
            hasil, ok = await self.klien.uji(k.base_url, k.model, kunci), True
        except Exception as exc:
            hasil, ok = f"GAGAL: {exc}"[:300], False
        async with self.uow:
            k.diuji_pada, k.hasil_uji = _sekarang(), hasil
            await audit.catat(
                self.session,
                "llm.konfigurasi.uji",
                pemanggil=pemanggil,
                entitas="konfigurasi_llm",
                entitas_id=k.id,
                detail={"berhasil": ok},
            )
        return {"id": k.id, "berhasil": ok, "hasil": hasil, "diuji_pada": k.diuji_pada}

    async def aktifkan(self, pemanggil: Pemanggil, konfigurasi_id: UUID, konfirmasi_online: bool) -> dict[str, Any]:
        """Hanya Dekan. Untuk mode online ini adalah persetujuan eksplisit (US-G4) dan butuh konfirmasi tertulis."""
        pemanggil.wajib(D)
        k = await self._muat(konfigurasi_id)
        if k.mode == ModeLlm.ONLINE and not konfirmasi_online:
            raise ValidasiGagal(
                "Mode online mengirim data akreditasi ke penyedia luar. Konfirmasi eksplisit diperlukan (konfirmasi_online=true).",
                details=[{"kolom": "konfirmasi_online"}],
            )
        if k.diuji_pada is None or not (k.hasil_uji or "").startswith("OK"):
            raise KonflikStatus("Uji koneksi harus berhasil sebelum konfigurasi diaktifkan.")
        async with self.uow:
            await self.session.execute(update(KonfigurasiLlm).where(KonfigurasiLlm.id != k.id).values(is_aktif=False))
            k.is_aktif, k.disetujui_oleh, k.disetujui_pada = True, pemanggil.id, _sekarang()
            await audit.catat(
                self.session,
                "llm.konfigurasi.aktifkan",
                pemanggil=pemanggil,
                entitas="konfigurasi_llm",
                entitas_id=k.id,
                detail={"mode": k.mode, "model": k.model},
            )
        return _dict(k)

    async def nonaktifkan(self, pemanggil: Pemanggil, konfigurasi_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(D)
        k = await self._muat(konfigurasi_id)
        async with self.uow:
            k.is_aktif = False
            await audit.catat(self.session, "llm.konfigurasi.nonaktifkan", pemanggil=pemanggil, entitas="konfigurasi_llm", entitas_id=k.id)
        return _dict(k)

    # ------------------------------------------------------------ draf narasi
    async def minta_draf(
        self, pemanggil: Pemanggil, butir_siklus_id: UUID, bagian: str, arahan: str | None, sertakan_data: bool
    ) -> dict[str, Any]:
        pemanggil.wajib(K)
        info = await siklus.info_butir_untuk_penulisan(self.session, butir_siklus_id)
        pemanggil.wajib_kaprodi(info.prodi_id)
        await laporan.wajib_tidak_terkunci(self.session, info.prodi_id)
        konf = (await self.session.execute(select(KonfigurasiLlm).where(KonfigurasiLlm.is_aktif))).scalar_one_or_none()
        if konf is None:
            raise LlmTidakTersedia("Tidak ada konfigurasi LLM aktif. Anda tetap dapat menulis narasi secara manual.")
        rincian = await instrumen.rincian_butir_siklus(self.session, info.instrumen_butir_id)
        bagian_sah = {x["bagian"] for x in rincian["skema_narasi"]} or {"utama"}
        if bagian not in bagian_sah:
            raise ValidasiGagal(f"Bagian narasi '{bagian}' tidak ada pada butir ini.")
        async with self.uow:
            p = PermintaanLlm(
                butir_siklus_id=butir_siklus_id,
                bagian=bagian,
                konfigurasi_id=konf.id,
                model=konf.model,
                mode=konf.mode,
                diminta_oleh=pemanggil.id,
            )
            self.session.add(p)
            await self.session.flush()
            await audit.catat(
                self.session,
                "llm.draf.minta",
                pemanggil=pemanggil,
                entitas="permintaan_llm",
                entitas_id=p.id,
                prodi_id=info.prodi_id,
                detail={"mode": konf.mode, "model": konf.model},
            )
        task_id = self.kirim("simak.draf_llm", str(p.id), arahan, sertakan_data, antrean="llm") if self.kirim else None
        async with self.uow:
            if task_id:
                p.task_id = task_id
            else:
                p.status, p.galat, p.selesai_pada = StatusTugas.GAGAL, "Antrean tugas tidak tersedia.", _sekarang()
        if not task_id:
            raise LlmTidakTersedia("Antrean tugas LLM tidak tersedia. Anda tetap dapat menulis narasi secara manual.")
        return {"id": p.id, "status": p.status, "mode": p.mode, "model": p.model}

    async def status(self, pemanggil: Pemanggil, permintaan_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(K)
        p = await self.session.get(PermintaanLlm, permintaan_id)
        if p is None:
            raise TidakDitemukan("Permintaan tidak ditemukan.")
        info = await siklus.info_butir_untuk_penulisan(self.session, p.butir_siklus_id)
        pemanggil.wajib_kaprodi(info.prodi_id)
        return {
            "id": p.id,
            "butir_siklus_id": p.butir_siklus_id,
            "bagian": p.bagian,
            "status": p.status,
            "mode": p.mode,
            "model": p.model,
            "hasil": p.hasil,
            "galat": p.galat,
            "selesai_pada": p.selesai_pada,
            "pengingat": "Hasil adalah DRAF yang wajib ditinjau dan disunting Kaprodi sebelum dipakai.",
        }

    # ------------------------------------------------------------ worker
    async def _susun_pesan(self, p: PermintaanLlm, arahan: str | None, sertakan_data: bool) -> list[dict[str, str]]:
        info = await siklus.info_butir_untuk_penulisan(self.session, p.butir_siklus_id)
        sk = await siklus.ambil_ringkas_siklus(self.session, info.siklus_id)
        rincian = await instrumen.rincian_butir_siklus(self.session, info.instrumen_butir_id)
        prodi = await referensi.ambil_prodi(self.session, sk.prodi_id)
        judul_bagian = next((x["judul"] for x in rincian["skema_narasi"] if x["bagian"] == p.bagian), "Uraian")
        baris = [f"Program studi: {prodi.nama}", f"Butir {rincian['kode']}: {rincian['elemen']}", f"Bagian yang ditulis: {judul_bagian}"]
        if rincian.get("panduan"):
            baris.append(f"Panduan pengisian: {rincian['panduan']}")
        if rincian["rubrik"]:
            baris.append(
                "Rubrik penilaian:\n" + "\n".join(f"- Skor {r['skor']} ({r['label'] or ''}): {r['deskriptor']}" for r in rincian["rubrik"])
            )
        if sertakan_data:
            tahun = await referensi.rentang_tahun(self.session, sk.ts_tahun_akademik_id, sk.jumlah_tahun_data)
            aturan = (await instrumen.aturan_aktif(self.session, [info.instrumen_butir_id])).get(info.instrumen_butir_id, [])
            for d in await pemetaan.data_untuk_butir(self.session, aturan, sk.prodi_id, tahun):
                contoh = "; ".join(c["label"] for c in d["contoh"][:15]) or "belum ada data"
                baris.append(
                    f"Data {d['sumber']} ({d['jumlah']} catatan{', nilai ' + str(d['nilai']) if d['nilai'] is not None else ''}): {contoh}"
                )
        if arahan:
            baris.append(f"Arahan Kaprodi: {arahan}")
        return [{"role": "system", "content": SISTEM}, {"role": "user", "content": "\n\n".join(baris)}]

    async def proses(self, permintaan_id: UUID, arahan: str | None, sertakan_data: bool) -> None:
        p = await self.session.get(PermintaanLlm, permintaan_id)
        if p is None:
            return
        p.status = StatusTugas.DIPROSES
        await self.session.commit()
        try:
            konf = await self.session.get(KonfigurasiLlm, p.konfigurasi_id) if p.konfigurasi_id else None
            if konf is None:
                raise LlmTidakTersedia("Konfigurasi LLM sudah dihapus.")
            kunci = dekripsi_rahasia(konf.api_key_terenkripsi) if konf.api_key_terenkripsi else None
            hasil = await self.klien.selesaikan(
                konf.base_url, konf.model, kunci, await self._susun_pesan(p, arahan, sertakan_data), konf.parameter or {}
            )
            p.hasil, p.token_masuk, p.token_keluar, p.status, p.galat = (
                hasil.teks,
                hasil.token_masuk,
                hasil.token_keluar,
                StatusTugas.SELESAI,
                None,
            )
        except Exception as exc:  # koneksi gagal/timeout: Kaprodi tetap menulis manual tanpa kehilangan data (EC-24)
            logger.warning("Permintaan LLM %s gagal: %s", permintaan_id, exc)
            p.status, p.galat = StatusTugas.GAGAL, f"{type(exc).__name__}: {exc}"[:500]
        p.selesai_pada = _sekarang()
        await self.session.commit()
