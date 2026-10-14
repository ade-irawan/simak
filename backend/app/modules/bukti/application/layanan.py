"""Use case bukti: unggah berkas (URL sementara) atau tautan, daftar, ubah, hapus, unduh, link-checker."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import exists, func, or_, select

from app.core import audit
from app.core.config import get_settings
from app.core.exceptions import AksesDitolak, KonflikStatus, KonflikVersi, TidakDitemukan, ValidasiGagal
from app.core.pagination import ParamHalaman, halaman
from app.core.permissions import SF, SP, A, D, K, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.modules.bukti.domain import rules
from app.modules.bukti.domain.entities import AksesTautan, JenisBukti, StatusCekBukti
from app.modules.bukti.domain.events import BuktiBermasalahTerdeteksi
from app.modules.bukti.domain.ports import PenyimpananBerkas, ProbeTautan
from app.modules.bukti.infrastructure.models import Bukti, BuktiButir, BuktiProdi
from app.modules.dokumen_eksternal import public as dokumen_eksternal
from app.modules.laporan import public as laporan
from app.modules.referensi import public as referensi
from app.modules.siklus import public as siklus


def _sekarang() -> datetime:
    return datetime.now(UTC)


class LayananBukti:
    def __init__(self, uow: UnitOfWork, penyimpanan: PenyimpananBerkas, probe: ProbeTautan):
        self.uow, self.session = uow, uow.session
        self.penyimpanan, self.probe = penyimpanan, probe

    # ------------------------------------------------------------ util
    async def _prodi_bukti(self, bukti_id: UUID) -> set[UUID]:
        return set((await self.session.execute(select(BuktiProdi.prodi_id).where(BuktiProdi.bukti_id == bukti_id))).scalars())

    async def _ke_dict(self, b: Bukti, prodi: set[UUID] | None = None) -> dict[str, Any]:
        peta = {p.id: p for p in await referensi.daftar_prodi(self.session)}
        prodi = prodi if prodi is not None else await self._prodi_bukti(b.id)
        return {
            "id": b.id,
            "jenis": b.jenis,
            "judul": b.judul,
            "url": b.url,
            "akses_tautan": b.akses_tautan,
            "nama_berkas": b.nama_berkas,
            "mime_type": b.mime_type,
            "ukuran_byte": b.ukuran_byte,
            "sumber": b.sumber,
            "tanggal_dokumen": b.tanggal_dokumen,
            "deskripsi": b.deskripsi,
            "status_cek": b.status_cek,
            "kode_http": b.kode_http,
            "dicek_pada": b.dicek_pada,
            "berlaku_untuk": [{"id": p, "kode": peta[p].kode} for p in prodi if p in peta],
            "row_version": b.row_version,
            "created_at": b.created_at,
            "updated_at": b.updated_at,
        }

    async def _muat(self, bukti_id: UUID) -> Bukti:
        b = (await self.session.execute(select(Bukti).where(Bukti.id == bukti_id, Bukti.deleted_at.is_(None)))).scalar_one_or_none()
        if b is None:
            raise TidakDitemukan("Bukti tidak ditemukan.")
        return b

    async def _boleh_baca(self, pemanggil: Pemanggil, b: Bukti, prodi: set[UUID]) -> bool:
        cakupan = pemanggil.cakupan_baca()
        if cakupan.semua:
            return True
        if any(cakupan.mengizinkan(p) for p in prodi):
            return True
        # bukti yang ditautkan ke butir milik prodinya
        butir_ids = set((await self.session.execute(select(BuktiButir.butir_siklus_id).where(BuktiButir.bukti_id == b.id))).scalars())
        prodi_butir = await siklus.prodi_dari_butir(self.session, butir_ids)
        return any(cakupan.mengizinkan(p) for p in prodi_butir)

    def _wajib_tulis(self, pemanggil: Pemanggil, prodi: set[UUID]) -> None:
        if pemanggil.punya(SF):
            return
        cakupan = pemanggil.cakupan_tulis()
        if not prodi or not all(cakupan.mengizinkan(p) for p in prodi):
            raise AksesDitolak(alasan="di_luar_cakupan_prodi")

    async def _periksa_kunci(self, prodi: set[UUID]) -> None:
        if len(prodi) == 1:
            await laporan.wajib_tidak_terkunci(self.session, next(iter(prodi)))

    def _prodi_input(self, pemanggil: Pemanggil, berlaku_untuk: list[UUID]) -> set[UUID]:
        prodi = set(berlaku_untuk)
        if not prodi and not pemanggil.punya(SF):
            prodi = set(pemanggil.prodi_dari(K, SP))
        return prodi

    # ------------------------------------------------------------ unggah
    async def minta_url_unggah(self, pemanggil: Pemanggil, nama: str, mime: str, ukuran: int) -> dict[str, Any]:
        maks = int(await referensi.ambil_pengaturan(self.session, "bukti.maks_mb", 25))
        galat = rules.periksa_berkas(nama, mime, ukuran, maks)
        if galat:
            raise ValidasiGagal(galat[0], details=[{"pesan": g} for g in galat])
        sekarang = _sekarang()
        key = f"bukti/{sekarang:%Y/%m}/{secrets.token_hex(4)}-{rules.nama_aman(nama)}"
        kedaluwarsa = timedelta(minutes=get_settings().url_sementara_menit)
        return {
            "objek_key": key,
            "url_unggah": self.penyimpanan.url_unggah(key, kedaluwarsa),
            "kedaluwarsa_pada": sekarang + kedaluwarsa,
            "metode": "PUT",
            "header": {"Content-Type": mime},
        }

    async def daftarkan(self, pemanggil: Pemanggil, data: Any) -> dict[str, Any]:
        prodi = self._prodi_input(pemanggil, data.berlaku_untuk)
        self._wajib_tulis(pemanggil, prodi)
        await self._periksa_kunci(prodi)
        b = Bukti(
            judul=data.judul,
            jenis=data.jenis,
            sumber=data.sumber,
            tanggal_dokumen=data.tanggal_dokumen,
            deskripsi=data.deskripsi,
            created_by=pemanggil.id,
            updated_by=pemanggil.id,
        )
        if data.jenis == JenisBukti.TAUTAN:
            galat = rules.periksa_url(data.url or "")
            if galat:
                raise ValidasiGagal(galat, details=[{"kolom": "url", "pesan": galat}])
            b.url, b.akses_tautan = data.url.strip(), data.akses_tautan or AksesTautan.PUBLIK
        else:
            await self._isi_dari_objek(b, data.objek_key, data.nama_berkas)
        async with self.uow:
            self.session.add(b)
            await self.session.flush()
            for p in prodi:
                self.session.add(BuktiProdi(bukti_id=b.id, prodi_id=p))
            await audit.catat(
                self.session,
                "bukti.buat",
                pemanggil=pemanggil,
                entitas="bukti",
                entitas_id=b.id,
                prodi_id=next(iter(prodi)) if len(prodi) == 1 else None,
                detail={"jenis": data.jenis},
            )
        return await self._ke_dict(b, prodi)

    async def _isi_dari_objek(self, b: Bukti, objek_key: str | None, nama_berkas: str | None) -> None:
        """Memverifikasi objek yang sudah diunggah klien ke MinIO lalu mengisi metadata berkas."""
        if not objek_key or not objek_key.startswith("bukti/"):
            raise ValidasiGagal("objek_key wajib untuk bukti berkas.", details=[{"kolom": "objek_key"}])
        maks = int(await referensi.ambil_pengaturan(self.session, "bukti.maks_mb", 25))
        ukuran = await self.penyimpanan.ukuran(objek_key)
        if ukuran is None:
            raise ValidasiGagal("Berkas belum diunggah ke penyimpanan.", details=[{"kolom": "objek_key"}])
        nama = nama_berkas or objek_key.rsplit("/", 1)[-1].split("-", 1)[-1]
        if ukuran > maks * 1024 * 1024:
            await self.penyimpanan.hapus(objek_key)
            raise ValidasiGagal(f"Ukuran berkas melebihi batas {maks} MB.")
        isi = await self.penyimpanan.baca(objek_key, maks * 1024 * 1024)
        if not rules.isi_sesuai_ekstensi(nama, isi[:8]):
            await self.penyimpanan.hapus(objek_key)
            raise ValidasiGagal("Isi berkas tidak sesuai dengan ekstensinya.")
        b.objek_key, b.nama_berkas, b.ukuran_byte = objek_key, nama, ukuran
        b.mime_type = _mime(nama)
        b.sha256 = hashlib.sha256(isi).hexdigest()
        b.url = b.akses_tautan = None  # type: ignore[assignment]
        b.status_cek, b.gagal_beruntun, b.dicek_pada = StatusCekBukti.OK, 0, _sekarang()

    # ------------------------------------------------------------ baca
    async def daftar(
        self,
        pemanggil: Pemanggil,
        param: ParamHalaman,
        *,
        prodi_id: UUID | None,
        jenis: JenisBukti | None,
        status_cek: StatusCekBukti | None,
    ) -> dict[str, Any]:
        stmt = select(Bukti).where(Bukti.deleted_at.is_(None))
        cakupan = pemanggil.cakupan_baca()
        if prodi_id and not cakupan.mengizinkan(prodi_id):
            raise AksesDitolak(alasan="di_luar_cakupan_prodi")
        if prodi_id:
            stmt = stmt.where(exists().where(BuktiProdi.bukti_id == Bukti.id, BuktiProdi.prodi_id == prodi_id))
        elif not cakupan.semua:
            stmt = stmt.where(exists().where(BuktiProdi.bukti_id == Bukti.id, BuktiProdi.prodi_id.in_(cakupan.prodi_ids)))
        if jenis:
            stmt = stmt.where(Bukti.jenis == jenis)
        if status_cek:
            stmt = stmt.where(Bukti.status_cek == status_cek)
        if param.q:
            like = f"%{param.q}%"
            stmt = stmt.where(or_(Bukti.judul.ilike(like), Bukti.sumber.ilike(like), Bukti.nama_berkas.ilike(like)))
        urut = param.urutan(
            {"judul": Bukti.judul, "updated_at": Bukti.updated_at, "created_at": Bukti.created_at}, [Bukti.updated_at.desc()]
        )
        hasil = await halaman(self.session, stmt, param, urut, lambda b: b)
        hasil["data"] = [await self._ke_dict(b) for b in hasil["data"]]
        return hasil

    async def rincian(self, pemanggil: Pemanggil, bukti_id: UUID) -> dict[str, Any]:
        b = await self._muat(bukti_id)
        prodi = await self._prodi_bukti(b.id)
        if pemanggil.punya(A) and not pemanggil.punya(D, K, SP, SF):
            await self._wajib_asesor(pemanggil, b)
        elif not await self._boleh_baca(pemanggil, b, prodi):
            raise AksesDitolak(alasan="di_luar_cakupan_prodi")
        hasil = await self._ke_dict(b, prodi)
        if not pemanggil.punya(A) or pemanggil.punya(D, K, SP, SF):
            hasil["pemakaian"] = {
                "butir": await siklus.ringkas_butir_siklus(
                    self.session,
                    list((await self.session.execute(select(BuktiButir.butir_siklus_id).where(BuktiButir.bukti_id == b.id))).scalars()),
                ),
            }
        return hasil

    async def _wajib_asesor(self, pemanggil: Pemanggil, b: Bukti) -> None:
        """Asesor hanya boleh membuka bukti yang tercantum pada versi laporan yang disetujui (US-H1)."""
        for prodi_id in pemanggil.prodi_dari(A):
            if await laporan.bukti_ada_di_cuplikan_disetujui(self.session, prodi_id, b.id):
                return
        await audit.catat_mandiri(
            "akses.ditolak", pemanggil=pemanggil, entitas="bukti", entitas_id=b.id, detail={"alasan": "bukti_di_luar_versi_disetujui"}
        )
        raise AksesDitolak(alasan="bukti_di_luar_versi_disetujui")

    async def unduh(self, pemanggil: Pemanggil, bukti_id: UUID) -> dict[str, Any]:
        b = await self._muat(bukti_id)
        prodi = await self._prodi_bukti(b.id)
        if pemanggil.punya(D, K, SP, SF):
            if not await self._boleh_baca(pemanggil, b, prodi):
                raise AksesDitolak(alasan="di_luar_cakupan_prodi")
        elif pemanggil.punya(A):
            await self._wajib_asesor(pemanggil, b)
        else:
            raise AksesDitolak(alasan="peran_tidak_sesuai")
        if pemanggil.punya(A):
            await audit.catat(self.session, "bukti.baca_asesor", pemanggil=pemanggil, entitas="bukti", entitas_id=b.id)
            await self.session.commit()
        if b.jenis == JenisBukti.TAUTAN:
            return {"jenis": "tautan", "url": b.url, "akses_tautan": b.akses_tautan}
        kedaluwarsa = timedelta(minutes=get_settings().url_sementara_menit)
        return {
            "jenis": "berkas",
            "url": self.penyimpanan.url_unduh(b.objek_key or "", b.nama_berkas, kedaluwarsa),
            "nama_berkas": b.nama_berkas,
            "kedaluwarsa_pada": _sekarang() + kedaluwarsa,
        }

    # ------------------------------------------------------------ ubah / hapus
    async def ubah(self, pemanggil: Pemanggil, bukti_id: UUID, patch: Any) -> dict[str, Any]:
        b = await self._muat(bukti_id)
        prodi = await self._prodi_bukti(b.id)
        self._wajib_tulis(pemanggil, prodi)
        await self._periksa_kunci(prodi)
        if patch.row_version != b.row_version:
            raise KonflikVersi(details=[{"row_version": b.row_version, "data": await self._ke_dict(b, prodi)}])
        data = {k: getattr(patch, k) for k in patch.model_fields_set if k != "row_version"}
        berlaku_untuk = data.pop("berlaku_untuk", None)
        async with self.uow:
            ganti_sumber = False
            if "url" in data and data["url"] is not None:
                if b.jenis != JenisBukti.TAUTAN:
                    raise ValidasiGagal("Bukti ini berupa berkas, bukan tautan.")
                galat = rules.periksa_url(data["url"])
                if galat:
                    raise ValidasiGagal(galat, details=[{"kolom": "url", "pesan": galat}])
                b.url, ganti_sumber = data["url"].strip(), True
            if data.get("objek_key"):
                if b.jenis != JenisBukti.BERKAS:
                    raise ValidasiGagal("Bukti ini berupa tautan, bukan berkas.")
                lama = b.objek_key
                await self._isi_dari_objek(b, data["objek_key"], data.get("nama_berkas"))
                if lama and lama != b.objek_key:
                    await self.penyimpanan.hapus(lama)
            for k in ("judul", "sumber", "tanggal_dokumen", "deskripsi", "akses_tautan"):
                if k in data:
                    setattr(b, k, data[k])
                    ganti_sumber = ganti_sumber or k == "akses_tautan"
            if ganti_sumber:
                b.status_cek, b.gagal_beruntun, b.dicek_pada = StatusCekBukti.BELUM_DICEK, 0, None
            if berlaku_untuk is not None:
                baru = set(berlaku_untuk)
                self._wajib_tulis(pemanggil, baru or prodi)
                for p in prodi - baru:
                    await self.session.delete(await self.session.get(BuktiProdi, (b.id, p)))
                for p in baru - prodi:
                    self.session.add(BuktiProdi(bukti_id=b.id, prodi_id=p))
                prodi = baru
            b.updated_by = pemanggil.id
            await audit.catat(
                self.session, "bukti.ubah", pemanggil=pemanggil, entitas="bukti", entitas_id=b.id, detail={"kolom": sorted(data)}
            )
        return await self._ke_dict(b, prodi)

    async def hapus(self, pemanggil: Pemanggil, bukti_id: UUID) -> None:
        pemanggil.wajib(K)
        b = await self._muat(bukti_id)
        prodi = await self._prodi_bukti(b.id)
        self._wajib_tulis(pemanggil, prodi)
        await self._periksa_kunci(prodi)
        dipakai = (await self.session.execute(select(func.count()).select_from(BuktiButir).where(BuktiButir.bukti_id == b.id))).scalar_one()
        if dipakai:
            raise KonflikStatus(f"Bukti masih ditautkan ke {dipakai} butir; lepaskan tautannya lebih dulu.")
        if await dokumen_eksternal.bukti_dipakai(self.session, b.id):
            raise KonflikStatus("Bukti merupakan dokumen resmi sebuah dokumen eksternal (tracer/kepuasan).")
        async with self.uow:
            b.deleted_at = _sekarang()
            await audit.catat(self.session, "bukti.hapus", pemanggil=pemanggil, entitas="bukti", entitas_id=b.id)

    # ------------------------------------------------------------ penautan ke butir
    async def tautkan_butir(self, pemanggil: Pemanggil, butir_siklus_id: UUID, bukti_id: UUID, keterangan: str | None) -> dict[str, Any]:
        info = await siklus.info_butir_untuk_penulisan(self.session, butir_siklus_id)
        siklus.wajib_ubah_butir(pemanggil, info)
        await laporan.wajib_tidak_terkunci(self.session, info.prodi_id)
        b = await self._muat(bukti_id)
        prodi = await self._prodi_bukti(b.id)
        if not await self._boleh_baca(pemanggil, b, prodi):
            raise AksesDitolak(alasan="di_luar_cakupan_prodi")  # bukti prodi lain tak terlihat sama sekali
        if prodi and info.prodi_id not in prodi and not pemanggil.punya(SF):
            raise ValidasiGagal("Bukti tidak berlaku untuk prodi pemilik butir ini ('Berlaku untuk').")
        async with self.uow:
            if await self.session.get(BuktiButir, (bukti_id, butir_siklus_id)) is None:
                n = (
                    await self.session.execute(
                        select(func.count()).select_from(BuktiButir).where(BuktiButir.butir_siklus_id == butir_siklus_id)
                    )
                ).scalar_one()
                self.session.add(
                    BuktiButir(bukti_id=bukti_id, butir_siklus_id=butir_siklus_id, keterangan=keterangan, urutan=n, created_by=pemanggil.id)
                )
            await audit.catat(
                self.session,
                "bukti.tautkan_butir",
                pemanggil=pemanggil,
                entitas="butir_siklus",
                entitas_id=butir_siklus_id,
                prodi_id=info.prodi_id,
                detail={"bukti_id": bukti_id},
            )
        return {"butir_siklus_id": butir_siklus_id, "bukti_id": bukti_id}

    async def lepas_butir(self, pemanggil: Pemanggil, butir_siklus_id: UUID, bukti_id: UUID) -> None:
        info = await siklus.info_butir_untuk_penulisan(self.session, butir_siklus_id)
        siklus.wajib_ubah_butir(pemanggil, info)
        await laporan.wajib_tidak_terkunci(self.session, info.prodi_id)
        async with self.uow:
            tautan = await self.session.get(BuktiButir, (bukti_id, butir_siklus_id))
            if tautan is not None:
                await self.session.delete(tautan)
            await audit.catat(
                self.session,
                "bukti.lepas_butir",
                pemanggil=pemanggil,
                entitas="butir_siklus",
                entitas_id=butir_siklus_id,
                prodi_id=info.prodi_id,
                detail={"bukti_id": bukti_id},
            )

    # ------------------------------------------------------------ link-checker (EC-23)
    async def periksa_satu(self, b: Bukti, *, batas_gagal: int = 3) -> StatusCekBukti:
        if b.jenis == JenisBukti.BERKAS:
            probe = await _probe_berkas(self.penyimpanan, b.objek_key or "")
        else:
            probe = await self.probe.periksa(b.url or "")
        sebelumnya = b.status_cek
        hasil = rules.tentukan_status(b.jenis, b.akses_tautan, probe, b.gagal_beruntun, gagal_sebelum_merah=batas_gagal)
        b.status_cek, b.gagal_beruntun, b.kode_http, b.dicek_pada = hasil.status, hasil.gagal_beruntun, hasil.kode_http, _sekarang()
        if hasil.status == StatusCekBukti.TIDAK_TERJANGKAU and sebelumnya != StatusCekBukti.TIDAK_TERJANGKAU:
            prodi = tuple(await self._prodi_bukti(b.id))
            self.uow.terbitkan(BuktiBermasalahTerdeteksi(b.id, b.judul, prodi))
        return hasil.status

    async def cek(self, pemanggil: Pemanggil, bukti_id: UUID) -> dict[str, Any]:
        b = await self._muat(bukti_id)
        prodi = await self._prodi_bukti(b.id)
        if not await self._boleh_baca(pemanggil, b, prodi):
            raise AksesDitolak(alasan="di_luar_cakupan_prodi")
        async with self.uow:
            await self.periksa_satu(b, batas_gagal=1)  # pemeriksaan manual: satu kegagalan langsung dilaporkan
        return await self._ke_dict(b, prodi)

    async def periksa_terjadwal(self, maks: int = 200) -> dict[str, int]:
        """Dipanggil Celery: bukti yang paling lama belum dicek dan sudah lewat selang pemeriksaan."""
        jam = int(await referensi.ambil_pengaturan(self.session, "bukti.jam_antar_cek", 24))
        batas = int(await referensi.ambil_pengaturan(self.session, "bukti.gagal_sebelum_merah", 3))
        lewat = _sekarang() - timedelta(hours=jam)
        antrean = (
            (
                await self.session.execute(
                    select(Bukti)
                    .where(Bukti.deleted_at.is_(None), or_(Bukti.dicek_pada.is_(None), Bukti.dicek_pada < lewat))
                    .order_by(Bukti.dicek_pada.asc().nulls_first())
                    .limit(maks)
                )
            )
            .scalars()
            .all()
        )
        rekap = {"diperiksa": 0, "bermasalah": 0}
        for b in antrean:
            async with self.uow:
                status = await self.periksa_satu(b, batas_gagal=batas)
            rekap["diperiksa"] += 1
            rekap["bermasalah"] += status == StatusCekBukti.TIDAK_TERJANGKAU
        return rekap


async def _probe_berkas(penyimpanan: PenyimpananBerkas, key: str) -> Any:
    from app.modules.bukti.domain.entities import HasilProbe

    return HasilProbe(ada=bool(key) and await penyimpanan.ada(key))


def _mime(nama: str) -> str:
    eks = rules.ekstensi(nama)
    return sorted(rules.FORMAT_BERKAS.get(eks, ({"application/octet-stream"}, None))[0])[0]
