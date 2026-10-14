"""Use case PPEPP: katalog standar SPM (Staf Fakultas, divalidasi Dekan), penetapan P1 (Dekan), tahapan P2–P5 (prodi)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.core import audit
from app.core.exceptions import AksesDitolak, KonflikStatus, KonflikVersi, TidakDitemukan, ValidasiGagal
from app.core.permissions import SF, SP, D, K, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.modules.bukti import public as bukti
from app.modules.instrumen.public import TahapPpepp
from app.modules.laporan import public as laporan
from app.modules.ppepp.domain import rules
from app.modules.ppepp.domain.entities import (
    URUTAN_TAHAP,
    StatusPenetapan,
    StatusSiklusPpepp,
    StatusTahapan,
)
from app.modules.ppepp.infrastructure.models import (
    ButirStandarInstrumen,
    ButirStandarSpm,
    PenetapanButir,
    SiklusPpepp,
    StandarSpm,
    TahapanPpepp,
)
from app.modules.referensi import public as referensi


def _sekarang() -> datetime:
    return datetime.now(UTC)


def _dict(o: Any, *, kecuali: tuple[str, ...] = ()) -> dict[str, Any]:
    from sqlalchemy import inspect

    return {c.key: getattr(o, c.key) for c in inspect(o).mapper.column_attrs if c.key not in kecuali}


class LayananPpepp:
    def __init__(self, uow: UnitOfWork):
        self.uow, self.session = uow, uow.session

    # ============================================================ katalog standar
    async def daftar_standar(self) -> list[dict[str, Any]]:
        standar = (await self.session.execute(select(StandarSpm).order_by(StandarSpm.kode))).scalars().all()
        butir = (await self.session.execute(select(ButirStandarSpm).order_by(ButirStandarSpm.nomor))).scalars().all()
        kaitan = (await self.session.execute(select(ButirStandarInstrumen))).scalars().all()
        peta_kaitan: dict[UUID, list[UUID]] = {}
        for k in kaitan:
            peta_kaitan.setdefault(k.butir_standar_id, []).append(k.instrumen_butir_id)
        hasil = []
        for s in standar:
            d = _dict(s)
            d["butir"] = [_dict(b) | {"instrumen_butir_ids": peta_kaitan.get(b.id, [])} for b in butir if b.standar_id == s.id]
            hasil.append(d)
        return hasil

    async def buat_standar(self, pemanggil: Pemanggil, data: Any) -> dict[str, Any]:
        pemanggil.wajib(SF)
        async with self.uow:
            s = StandarSpm(**data.model_dump(), created_by=pemanggil.id)
            self.session.add(s)
            try:
                await self.session.flush()
            except IntegrityError as exc:
                raise ValidasiGagal("Kode standar sudah dipakai.") from exc
            await audit.catat(self.session, "standar_spm.buat", pemanggil=pemanggil, entitas="standar_spm", entitas_id=s.id)
        return _dict(s) | {"butir": []}

    async def _standar(self, standar_id: UUID) -> StandarSpm:
        s = await self.session.get(StandarSpm, standar_id)
        if s is None:
            raise TidakDitemukan("Standar tidak ditemukan.")
        return s

    async def ubah_standar(self, pemanggil: Pemanggil, standar_id: UUID, data: Any) -> dict[str, Any]:
        pemanggil.wajib(SF)
        s = await self._standar(standar_id)
        async with self.uow:
            for k, v in data.model_dump(exclude_unset=True).items():
                setattr(s, k, v)
            s.divalidasi_oleh = s.divalidasi_pada = None  # perubahan katalog perlu divalidasi ulang oleh Dekan
            await audit.catat(self.session, "standar_spm.ubah", pemanggil=pemanggil, entitas="standar_spm", entitas_id=s.id)
        return _dict(s)

    async def validasi_standar(self, pemanggil: Pemanggil, standar_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(D)
        s = await self._standar(standar_id)
        async with self.uow:
            s.divalidasi_oleh, s.divalidasi_pada = pemanggil.id, _sekarang()
            await audit.catat(self.session, "standar_spm.validasi", pemanggil=pemanggil, entitas="standar_spm", entitas_id=s.id)
        return _dict(s)

    async def _simpan_kaitan(self, butir_id: UUID, ids: list[UUID]) -> None:
        await self.session.execute(delete(ButirStandarInstrumen).where(ButirStandarInstrumen.butir_standar_id == butir_id))
        for i in set(ids):
            self.session.add(ButirStandarInstrumen(butir_standar_id=butir_id, instrumen_butir_id=i))

    async def tambah_butir_standar(self, pemanggil: Pemanggil, standar_id: UUID, data: Any) -> dict[str, Any]:
        pemanggil.wajib(SF)
        s = await self._standar(standar_id)
        async with self.uow:
            b = ButirStandarSpm(standar_id=standar_id, **data.model_dump(exclude={"instrumen_butir_ids"}))
            self.session.add(b)
            try:
                await self.session.flush()
            except IntegrityError as exc:
                raise ValidasiGagal("Nomor butir sudah ada pada standar ini.") from exc
            await self._simpan_kaitan(b.id, data.instrumen_butir_ids)
            s.divalidasi_oleh = s.divalidasi_pada = None
            await audit.catat(self.session, "butir_standar.buat", pemanggil=pemanggil, entitas="butir_standar_spm", entitas_id=b.id)
        return _dict(b) | {"instrumen_butir_ids": data.instrumen_butir_ids}

    async def ubah_butir_standar(self, pemanggil: Pemanggil, butir_id: UUID, data: Any) -> dict[str, Any]:
        pemanggil.wajib(SF)
        b = await self.session.get(ButirStandarSpm, butir_id)
        if b is None:
            raise TidakDitemukan("Butir standar tidak ditemukan.")
        perubahan = data.model_dump(exclude_unset=True)
        ids = perubahan.pop("instrumen_butir_ids", None)
        async with self.uow:
            for k, v in perubahan.items():
                setattr(b, k, v)
            if ids is not None:
                await self._simpan_kaitan(b.id, ids)
            s = await self._standar(b.standar_id)
            s.divalidasi_oleh = s.divalidasi_pada = None
            await audit.catat(self.session, "butir_standar.ubah", pemanggil=pemanggil, entitas="butir_standar_spm", entitas_id=b.id)
        return _dict(b)

    # ============================================================ siklus PPEPP
    async def daftar_siklus(self) -> list[dict[str, Any]]:
        baris = (await self.session.execute(select(SiklusPpepp).order_by(SiklusPpepp.tanggal_mulai.desc()))).scalars().all()
        return [_dict(s) for s in baris]

    async def _siklus(self, siklus_id: UUID) -> SiklusPpepp:
        s = await self.session.get(SiklusPpepp, siklus_id)
        if s is None:
            raise TidakDitemukan("Siklus PPEPP tidak ditemukan.")
        return s

    async def buat_siklus(self, pemanggil: Pemanggil, data: Any) -> dict[str, Any]:
        pemanggil.wajib(D)
        await referensi.ambil_tahun_akademik(self.session, data.tahun_akademik_id)
        sebelumnya = data.siklus_sebelumnya_id
        if sebelumnya is None:  # EC-22: hasil Peningkatan siklus lama menjadi baseline siklus baru
            sebelumnya = (
                await self.session.execute(select(SiklusPpepp.id).order_by(SiklusPpepp.tanggal_mulai.desc()).limit(1))
            ).scalar_one_or_none()
        async with self.uow:
            s = SiklusPpepp(**data.model_dump(exclude={"siklus_sebelumnya_id"}), siklus_sebelumnya_id=sebelumnya)
            self.session.add(s)
            await self.session.flush()
            await audit.catat(self.session, "siklus_ppepp.buat", pemanggil=pemanggil, entitas="siklus_ppepp", entitas_id=s.id)
        return _dict(s)

    # ------------------------------------------------------------ penetapan (P1)
    async def _baseline(
        self, siklus: SiklusPpepp, butir_standar_id: UUID, prodi_id: UUID | None
    ) -> tuple[PenetapanButir | None, Decimal | None]:
        if siklus.siklus_sebelumnya_id is None:
            return None, None
        lama = (
            (
                await self.session.execute(
                    select(PenetapanButir).where(
                        PenetapanButir.siklus_ppepp_id == siklus.siklus_sebelumnya_id,
                        PenetapanButir.butir_standar_id == butir_standar_id,
                        PenetapanButir.status == StatusPenetapan.DITETAPKAN,
                    )
                )
            )
            .scalars()
            .all()
        )
        if not lama:
            return None, None
        ids = [p.id for p in lama]
        q = select(func.avg(TahapanPpepp.capaian_nilai)).where(
            TahapanPpepp.penetapan_butir_id.in_(ids),
            TahapanPpepp.tahap == TahapPpepp.PENINGKATAN,
            TahapanPpepp.capaian_nilai.is_not(None),
        )
        if prodi_id:
            q = q.where(TahapanPpepp.prodi_id == prodi_id)
        rata = (await self.session.execute(q)).scalar_one_or_none()
        return lama[0], (Decimal(str(round(rata, 4))) if rata is not None else None)

    async def _ke_dict_penetapan(self, p: PenetapanButir, siklus: SiklusPpepp | None = None) -> dict[str, Any]:
        d = _dict(p)
        if p.baseline_dari_id:
            lama = await self.session.get(PenetapanButir, p.baseline_dari_id)
            sk = await self.session.get(SiklusPpepp, lama.siklus_ppepp_id) if lama else None
            d["baseline_dari"] = {"siklus": sk.nama if sk else None, "capaian_nilai": p.baseline_nilai}
        return d

    async def daftar_penetapan(self, pemanggil: Pemanggil, siklus_id: UUID, prodi_id: UUID | None) -> list[dict[str, Any]]:
        await self._siklus(siklus_id)
        stmt = select(PenetapanButir).where(
            PenetapanButir.siklus_ppepp_id == siklus_id, PenetapanButir.status != StatusPenetapan.DIBATALKAN
        )
        cakupan = pemanggil.cakupan_baca()
        if prodi_id:
            if not cakupan.mengizinkan(prodi_id):
                raise AksesDitolak(alasan="di_luar_cakupan_prodi")
            stmt = stmt.where((PenetapanButir.prodi_id == prodi_id) | PenetapanButir.prodi_id.is_(None))
        elif not cakupan.semua:
            stmt = stmt.where(PenetapanButir.prodi_id.in_(cakupan.prodi_ids) | PenetapanButir.prodi_id.is_(None))
        if not pemanggil.punya(D, SF):  # prodi hanya melihat butir yang sudah ditetapkan Dekan (US-C1)
            stmt = stmt.where(PenetapanButir.status == StatusPenetapan.DITETAPKAN)
        baris = (await self.session.execute(stmt.order_by(PenetapanButir.nomor_butir))).scalars().all()
        return [await self._ke_dict_penetapan(p) for p in baris]

    async def tambah_penetapan(self, pemanggil: Pemanggil, siklus_id: UUID, data: Any) -> dict[str, Any]:
        pemanggil.wajib(D)
        siklus = await self._siklus(siklus_id)
        if siklus.status == StatusSiklusPpepp.SELESAI:
            raise KonflikStatus("Siklus PPEPP sudah selesai.")
        bs = await self.session.get(ButirStandarSpm, data.butir_standar_id)
        if bs is None or not bs.is_aktif:
            raise ValidasiGagal("Butir standar tidak ditemukan atau tidak aktif.")
        standar = await self._standar(bs.standar_id)
        if standar.divalidasi_pada is None or not standar.is_aktif:
            raise ValidasiGagal("Standar belum divalidasi Dekan atau tidak aktif; validasi katalog lebih dulu.")
        if data.prodi_id:
            await referensi.ambil_prodi(self.session, data.prodi_id)
        lama, baseline = await self._baseline(siklus, data.butir_standar_id, data.prodi_id)
        async with self.uow:
            p = PenetapanButir(
                siklus_ppepp_id=siklus_id,
                **data.model_dump(),
                baseline_dari_id=lama.id if lama else None,
                baseline_nilai=baseline,
            )
            self.session.add(p)
            try:
                await self.session.flush()
            except IntegrityError as exc:
                raise ValidasiGagal("Butir standar ini sudah ditetapkan pada siklus ini untuk cakupan yang sama.") from exc
            await audit.catat(
                self.session,
                "penetapan.buat",
                pemanggil=pemanggil,
                entitas="penetapan_butir",
                entitas_id=p.id,
                prodi_id=p.prodi_id,
                detail=data.model_dump(mode="json"),
            )
        return await self._ke_dict_penetapan(p)

    async def ubah_penetapan(self, pemanggil: Pemanggil, penetapan_id: UUID, patch: Any) -> dict[str, Any]:
        pemanggil.wajib(D)
        p = await self.session.get(PenetapanButir, penetapan_id)
        if p is None or p.status == StatusPenetapan.DIBATALKAN:
            raise TidakDitemukan("Penetapan tidak ditemukan.")
        if patch.row_version != p.row_version:
            raise KonflikVersi(details=[{"row_version": p.row_version, "data": await self._ke_dict_penetapan(p)}])
        perubahan = patch.model_dump(exclude_unset=True, exclude={"row_version"})
        lama = {k: getattr(p, k) for k in perubahan}
        async with self.uow:
            for k, v in perubahan.items():
                setattr(p, k, v)
            try:
                await self.session.flush()
            except StaleDataError as exc:
                raise KonflikVersi() from exc
            # Perubahan butir sasaran tercatat berversi (nilai lama → baru) di log audit (US-C1).
            await audit.catat(
                self.session,
                "penetapan.ubah",
                pemanggil=pemanggil,
                entitas="penetapan_butir",
                entitas_id=p.id,
                prodi_id=p.prodi_id,
                detail={"lama": lama, "baru": perubahan, "row_version": p.row_version},
            )
        return await self._ke_dict_penetapan(p)

    async def batalkan_penetapan(self, pemanggil: Pemanggil, penetapan_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(D)
        p = await self.session.get(PenetapanButir, penetapan_id)
        if p is None:
            raise TidakDitemukan("Penetapan tidak ditemukan.")
        async with self.uow:
            p.status = StatusPenetapan.DIBATALKAN
            await audit.catat(self.session, "penetapan.batal", pemanggil=pemanggil, entitas="penetapan_butir", entitas_id=p.id)
        return await self._ke_dict_penetapan(p)

    async def tetapkan(self, pemanggil: Pemanggil, siklus_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(D)
        siklus = await self._siklus(siklus_id)
        if siklus.status == StatusSiklusPpepp.SELESAI:
            raise KonflikStatus("Siklus PPEPP sudah selesai.")
        draf = (
            (
                await self.session.execute(
                    select(PenetapanButir).where(PenetapanButir.siklus_ppepp_id == siklus_id, PenetapanButir.status == StatusPenetapan.DRAF)
                )
            )
            .scalars()
            .all()
        )
        if not draf:
            raise ValidasiGagal("Belum ada butir sasaran berstatus draf untuk ditetapkan.")
        semua_prodi = [p.id for p in await referensi.daftar_prodi(self.session)]
        async with self.uow:
            baru = 0
            for p in draf:
                p.status, p.ditetapkan_oleh, p.ditetapkan_pada = StatusPenetapan.DITETAPKAN, pemanggil.id, _sekarang()
                for prodi in [p.prodi_id] if p.prodi_id else semua_prodi:
                    for tahap in URUTAN_TAHAP:
                        hasil = await self.session.execute(
                            pg_insert(TahapanPpepp)
                            .values(penetapan_butir_id=p.id, prodi_id=prodi, tahap=TahapPpepp(tahap.value))
                            .on_conflict_do_nothing()
                            .returning(TahapanPpepp.id)
                        )
                        baru += hasil.first() is not None
            if siklus.status == StatusSiklusPpepp.DRAF:
                siklus.status = StatusSiklusPpepp.DITETAPKAN
            siklus.ditetapkan_oleh, siklus.ditetapkan_pada = pemanggil.id, _sekarang()
            await audit.catat(
                self.session,
                "siklus_ppepp.tetapkan",
                pemanggil=pemanggil,
                entitas="siklus_ppepp",
                entitas_id=siklus.id,
                detail={"butir": len(draf), "tahapan_dibuat": baru},
            )
        return {"siklus_id": siklus.id, "status": siklus.status, "butir_ditetapkan": len(draf), "tahapan_dibuat": baru}

    async def selesaikan(self, pemanggil: Pemanggil, siklus_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(D)
        siklus = await self._siklus(siklus_id)
        async with self.uow:
            siklus.status = StatusSiklusPpepp.SELESAI
            await audit.catat(self.session, "siklus_ppepp.selesai", pemanggil=pemanggil, entitas="siklus_ppepp", entitas_id=siklus.id)
        return _dict(siklus)

    # ------------------------------------------------------------ tahapan (P2–P5)
    async def _penetapan_ditetapkan(self, penetapan_id: UUID) -> PenetapanButir:
        p = await self.session.get(PenetapanButir, penetapan_id)
        if p is None or p.status == StatusPenetapan.DIBATALKAN:
            raise TidakDitemukan("Butir sasaran tidak ditemukan.")
        return p

    async def tahapan(self, pemanggil: Pemanggil, penetapan_id: UUID, prodi_id: UUID | None) -> dict[str, Any]:
        p = await self._penetapan_ditetapkan(penetapan_id)
        cakupan = pemanggil.cakupan_baca()
        if p.prodi_id and not cakupan.mengizinkan(p.prodi_id):
            raise AksesDitolak(alasan="di_luar_cakupan_prodi")
        if prodi_id and not cakupan.mengizinkan(prodi_id):
            raise AksesDitolak(alasan="di_luar_cakupan_prodi")
        if p.status != StatusPenetapan.DITETAPKAN and not pemanggil.punya(D, SF):
            raise TidakDitemukan("Butir sasaran belum ditetapkan.")
        stmt = select(TahapanPpepp).where(TahapanPpepp.penetapan_butir_id == penetapan_id)
        if prodi_id:
            stmt = stmt.where(TahapanPpepp.prodi_id == prodi_id)
        elif not cakupan.semua:
            stmt = stmt.where(TahapanPpepp.prodi_id.in_(cakupan.prodi_ids))
        baris = (await self.session.execute(stmt)).scalars().all()
        urut = {t.value: i for i, t in enumerate(URUTAN_TAHAP)}
        return {
            # Penetapan (P1) bersifat baca-saja bagi prodi.
            "penetapan": await self._ke_dict_penetapan(p) | {"dapat_disunting": False},
            "tahapan": [
                _dict(t) | {"tahap": t.tahap.value, "selisih_target": rules.selisih_target(t.capaian_nilai, p.target_nilai)}
                for t in sorted(baris, key=lambda t: (str(t.prodi_id), urut.get(t.tahap.value, 9)))
            ],
        }

    async def isi_tahapan(
        self, pemanggil: Pemanggil, penetapan_id: UUID, tahap_nama: str, prodi_id: UUID | None, data: Any
    ) -> dict[str, Any]:
        tahap = rules.tahap_valid(tahap_nama)
        if tahap is None:
            raise ValidasiGagal(
                "Tahap harus salah satu dari pelaksanaan, evaluasi, pengendalian, peningkatan. Tahap penetapan hanya dapat dibaca."
            )
        p = await self._penetapan_ditetapkan(penetapan_id)
        if p.status != StatusPenetapan.DITETAPKAN:
            raise KonflikStatus("Butir sasaran belum ditetapkan Dekan.")
        if prodi_id is None:
            kandidat = pemanggil.prodi_dari(K, SP)
            if len(kandidat) != 1:
                raise ValidasiGagal("Parameter prodi_id wajib diisi.")
            prodi_id = next(iter(kandidat))
        if not pemanggil.cakupan_tulis().mengizinkan(prodi_id):
            raise AksesDitolak(alasan="di_luar_cakupan_prodi")
        await laporan.wajib_tidak_terkunci(self.session, prodi_id)
        t = (
            await self.session.execute(
                select(TahapanPpepp).where(
                    TahapanPpepp.penetapan_butir_id == penetapan_id,
                    TahapanPpepp.prodi_id == prodi_id,
                    TahapanPpepp.tahap == TahapPpepp(tahap.value),
                )
            )
        ).scalar_one_or_none()
        if t is None:
            raise TidakDitemukan("Tahapan untuk prodi ini tidak ditemukan.")
        if data.row_version != t.row_version:
            raise KonflikVersi(details=[{"row_version": t.row_version, "data": _dict(t)}])
        siklus = await self._siklus(p.siklus_ppepp_id)
        if siklus.status == StatusSiklusPpepp.SELESAI:
            raise KonflikStatus("Siklus PPEPP sudah selesai.")
        async with self.uow:
            for k in ("status", "uraian", "capaian_nilai", "capaian_deskripsi", "temuan", "tindak_lanjut", "tenggat"):
                setattr(t, k, getattr(data, k))
            t.updated_by = pemanggil.id
            try:
                await self.session.flush()
            except StaleDataError as exc:
                raise KonflikVersi() from exc
            await bukti.set_bukti_tahapan(self.session, t.id, data.bukti_id)
            if siklus.status == StatusSiklusPpepp.DITETAPKAN:
                siklus.status = StatusSiklusPpepp.BERJALAN
            await audit.catat(
                self.session,
                "tahapan_ppepp.isi",
                pemanggil=pemanggil,
                entitas="tahapan_ppepp",
                entitas_id=t.id,
                prodi_id=prodi_id,
                detail={"tahap": tahap.value, "status": data.status},
            )
        selisih = rules.selisih_target(t.capaian_nilai, p.target_nilai)
        saran = rules.saran_berikutnya(tahap, t.status, t.temuan, t.tindak_lanjut, selisih)
        return {
            "tahap": tahap.value,
            "status": t.status,
            "capaian_nilai": t.capaian_nilai,
            "selisih_target": selisih,
            "row_version": t.row_version,
            "saran_berikutnya": {"tahap": saran.tahap, "pesan": saran.pesan} if saran else None,
        }

    # ------------------------------------------------------------ rekap (Dekan)
    async def rekap(self, siklus_id: UUID) -> dict[str, Any]:
        siklus = await self._siklus(siklus_id)
        prodi = await referensi.daftar_prodi(self.session)
        penetapan = (
            (
                await self.session.execute(
                    select(PenetapanButir).where(
                        PenetapanButir.siklus_ppepp_id == siklus_id, PenetapanButir.status == StatusPenetapan.DITETAPKAN
                    )
                )
            )
            .scalars()
            .all()
        )
        tahapan = (
            (
                await self.session.execute(
                    select(TahapanPpepp)
                    .join(PenetapanButir, PenetapanButir.id == TahapanPpepp.penetapan_butir_id)
                    .where(PenetapanButir.siklus_ppepp_id == siklus_id)
                )
            )
            .scalars()
            .all()
        )
        hasil = []
        for pr in prodi:
            tp = [t for t in tahapan if t.prodi_id == pr.id]
            sasaran = [p for p in penetapan if p.prodi_id in (None, pr.id)]
            butir = []
            for p in sasaran:
                tb = [t for t in tp if t.penetapan_butir_id == p.id]
                evaluasi = next((t for t in tb if t.tahap.value == "evaluasi" and t.capaian_nilai is not None), None)
                peningkatan = next((t for t in tb if t.tahap.value == "peningkatan" and t.capaian_nilai is not None), None)
                capaian = (peningkatan or evaluasi).capaian_nilai if (peningkatan or evaluasi) else None
                butir.append(
                    {
                        "penetapan_id": p.id,
                        "nomor_butir": p.nomor_butir,
                        "target_nilai": p.target_nilai,
                        "capaian_nilai": capaian,
                        "selisih_target": rules.selisih_target(capaian, p.target_nilai),
                        "tahap_selesai": sum(t.status == StatusTahapan.SELESAI for t in tb),
                        "tahap_total": len(tb),
                    }
                )
            hasil.append(
                {
                    "prodi": {"id": pr.id, "kode": pr.kode, "nama": pr.nama},
                    "butir_sasaran": len(sasaran),
                    "tahap_selesai": sum(t.status == StatusTahapan.SELESAI for t in tp),
                    "tahap_total": len(tp),
                    "butir": butir,
                }
            )
        return {"siklus": _dict(siklus), "prodi": hasil}
