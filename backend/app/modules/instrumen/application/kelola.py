"""Use case instrumen: baca, sunting draf (Staf Fakultas), aktifkan (Dekan), Mapping Engine."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import audit
from app.core.exceptions import KonflikStatus, TidakDitemukan, ValidasiGagal
from app.core.permissions import SF, D, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.modules.instrumen.domain import rules
from app.modules.instrumen.domain.entities import StatusInstrumen
from app.modules.instrumen.infrastructure import repository as repo
from app.modules.instrumen.infrastructure.models import (
    InstrumenButir,
    InstrumenButirAmbang,
    InstrumenButirRubrik,
    InstrumenKriteria,
    InstrumenPeringkat,
    InstrumenVersi,
    PemetaanButir,
)
from app.modules.referensi.public import Lam


def sudah_digantikan_ids(baris: list[PemetaanButir]) -> set[UUID]:
    return {p.menggantikan_id for p in baris if p.is_aktif and p.menggantikan_id}


class KelolaInstrumen:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.session: AsyncSession = uow.session

    # ---------- baca ----------
    async def daftar_versi(self, pemanggil: Pemanggil) -> list[dict[str, Any]]:
        stmt = select(InstrumenVersi, Lam).join(Lam, Lam.id == InstrumenVersi.lam_id).order_by(Lam.kode, InstrumenVersi.kode_versi.desc())
        if not pemanggil.punya(D, SF):
            stmt = stmt.where(InstrumenVersi.status != StatusInstrumen.DRAF)
        return [
            {
                "id": v.id,
                "lam": {"kode": lam.kode, "nama": lam.nama},
                "kode_versi": v.kode_versi,
                "nama": v.nama,
                "jenjang": v.jenjang,
                "status": v.status,
                "berlaku_mulai": v.berlaku_mulai,
                "disetujui_pada": v.disetujui_pada,
            }
            for v, lam in (await self.session.execute(stmt)).all()
        ]

    async def rincian(self, pemanggil: Pemanggil, versi_id: UUID) -> dict[str, Any]:
        v = await repo.ambil_versi(self.session, versi_id)
        if v.status == StatusInstrumen.DRAF and not pemanggil.punya(D, SF):
            raise TidakDitemukan("Versi instrumen tidak ditemukan.")
        lam = await self.session.get(Lam, v.lam_id)
        kriteria = (
            await self.session.execute(
                select(InstrumenKriteria, func.count(InstrumenButir.id))
                .join(InstrumenButir, InstrumenButir.kriteria_id == InstrumenKriteria.id, isouter=True)
                .where(InstrumenKriteria.instrumen_versi_id == versi_id)
                .group_by(InstrumenKriteria.id)
                .order_by(InstrumenKriteria.urutan)
            )
        ).all()
        peringkat = (
            (
                await self.session.execute(
                    select(InstrumenPeringkat)
                    .where(InstrumenPeringkat.instrumen_versi_id == versi_id)
                    .order_by(InstrumenPeringkat.tingkat.desc())
                )
            )
            .scalars()
            .all()
        )
        return {
            "id": v.id,
            "lam": {"kode": lam.kode, "nama": lam.nama},
            "kode_versi": v.kode_versi,
            "nama": v.nama,
            "jenjang": v.jenjang,
            "dasar_hukum": v.dasar_hukum,
            "status": v.status,
            "skor_maks": v.skor_maks,
            "label_skor": v.label_skor,
            "nilai_akhir_maks": v.nilai_akhir_maks,
            "kriteria": [{"kode": k.kode, "nama": k.nama, "bobot": k.bobot, "jumlah_butir": n} for k, n in kriteria],
            "peringkat": [
                {
                    "kode": p.kode,
                    "nama": p.nama,
                    "tingkat": p.tingkat,
                    "masa_berlaku_tahun": p.masa_berlaku_tahun,
                    "nilai_akhir_min": p.nilai_akhir_min,
                    "nilai_akhir_maks": p.nilai_akhir_maks,
                    "syarat": p.syarat,
                }
                for p in peringkat
            ],
        }

    async def daftar_butir(self, versi_id: UUID, kriteria: str | None, tahap: str | None, jenis_ipo: str | None) -> list[dict[str, Any]]:
        butir = await repo.muat_butir(self.session, versi_id)
        hasil = []
        for b in butir:
            if kriteria and b.kriteria_kode != kriteria:
                continue
            if tahap and (b.tahap_ppepp is None or b.tahap_ppepp.value != tahap):
                continue
            if jenis_ipo and (b.jenis_ipo is None or b.jenis_ipo.value != jenis_ipo):
                continue
            hasil.append(
                {
                    "id": b.id,
                    "kode": b.kode,
                    "kriteria": {"kode": b.kriteria_kode, "nama": b.kriteria_nama},
                    "elemen": b.elemen,
                    "jenis_ipo": b.jenis_ipo,
                    "tahap_ppepp": b.tahap_ppepp,
                    "bobot": b.bobot,
                    "jenis_penilaian": b.jenis_penilaian,
                }
            )
        return hasil

    async def rincian_butir(self, butir_id: UUID) -> dict[str, Any]:
        baris = (
            await self.session.execute(
                select(InstrumenButir, InstrumenKriteria)
                .join(InstrumenKriteria, InstrumenKriteria.id == InstrumenButir.kriteria_id)
                .where(InstrumenButir.id == butir_id)
            )
        ).first()
        if baris is None:
            raise TidakDitemukan("Butir tidak ditemukan.")
        b, k = baris
        rubrik = (
            (
                await self.session.execute(
                    select(InstrumenButirRubrik)
                    .where(InstrumenButirRubrik.instrumen_butir_id == butir_id)
                    .order_by(InstrumenButirRubrik.skor.desc())
                )
            )
            .scalars()
            .all()
        )
        v = await repo.ambil_versi(self.session, b.instrumen_versi_id)
        ambang = (
            await self.session.execute(
                select(InstrumenButirAmbang, InstrumenPeringkat.kode)
                .join(InstrumenPeringkat, InstrumenPeringkat.id == InstrumenButirAmbang.peringkat_id)
                .where(InstrumenButirAmbang.instrumen_butir_id == butir_id)
                .order_by(InstrumenPeringkat.tingkat.desc())
            )
        ).all()
        label = v.label_skor or {}
        return {
            "id": b.id,
            "kode": b.kode,
            "instrumen_versi_id": b.instrumen_versi_id,
            "kriteria": {"kode": k.kode, "nama": k.nama},
            "elemen": b.elemen,
            "deskriptor": b.deskriptor,
            "jenis_ipo": b.jenis_ipo,
            "tahap_ppepp": b.tahap_ppepp,
            "jenis_penilaian": b.jenis_penilaian,
            "bobot": b.bobot,
            "panduan": b.panduan,
            "skema_narasi": b.skema_narasi,
            "rubrik": [{"skor": r.skor, "label": label.get(str(r.skor)), "deskriptor": r.deskriptor} for r in rubrik],
            "ambang": [{"peringkat": kode, "skor_min": a.skor_min, "is_syarat_perlu": a.is_syarat_perlu} for a, kode in ambang],
        }

    # ---------- sunting (Staf Fakultas) ----------
    async def ubah_butir(self, pemanggil: Pemanggil, butir_id: UUID, data: Any) -> dict[str, Any]:
        pemanggil.wajib(SF)
        b = await self.session.get(InstrumenButir, butir_id)
        if b is None:
            raise TidakDitemukan("Butir tidak ditemukan.")
        v = await repo.ambil_versi(self.session, b.instrumen_versi_id)
        if v.status != StatusInstrumen.DRAF:
            raise KonflikStatus("Butir hanya dapat disunting pada instrumen berstatus draf.")
        perubahan = data.model_dump(exclude_unset=True)
        rubrik = perubahan.pop("rubrik", None)
        async with self.uow:
            for k, nilai in perubahan.items():
                setattr(b, k, nilai)
            if rubrik is not None:
                await self.session.execute(delete(InstrumenButirRubrik).where(InstrumenButirRubrik.instrumen_butir_id == butir_id))
                for r in rubrik:
                    self.session.add(InstrumenButirRubrik(instrumen_butir_id=butir_id, skor=r["skor"], deskriptor=r["deskriptor"]))
            await audit.catat(
                self.session,
                "instrumen.butir.ubah",
                pemanggil=pemanggil,
                entitas="instrumen_butir",
                entitas_id=butir_id,
                detail={"kolom": sorted(perubahan) + (["rubrik"] if rubrik is not None else [])},
            )
        return await self.rincian_butir(butir_id)

    # ---------- aktivasi (Dekan) ----------
    async def aktifkan(self, pemanggil: Pemanggil, versi_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(D)
        v = await repo.ambil_versi(self.session, versi_id)
        if v.status != StatusInstrumen.DRAF:
            raise KonflikStatus("Hanya instrumen berstatus draf yang dapat diaktifkan.")
        n_butir = (
            await self.session.execute(
                select(func.count()).select_from(InstrumenButir).where(InstrumenButir.instrumen_versi_id == versi_id)
            )
        ).scalar_one()
        n_peringkat = (
            await self.session.execute(
                select(func.count()).select_from(InstrumenPeringkat).where(InstrumenPeringkat.instrumen_versi_id == versi_id)
            )
        ).scalar_one()
        kriteria = (
            await self.session.execute(
                select(InstrumenKriteria.bobot, func.count(InstrumenButir.id))
                .join(InstrumenButir, InstrumenButir.kriteria_id == InstrumenKriteria.id, isouter=True)
                .where(InstrumenKriteria.instrumen_versi_id == versi_id)
                .group_by(InstrumenKriteria.id)
            )
        ).all()
        galat, peringatan = rules.periksa_siap_aktif(
            jumlah_butir=n_butir,
            jumlah_peringkat=n_peringkat,
            bobot_kriteria=[k[0] for k in kriteria],
            nilai_akhir_maks=v.nilai_akhir_maks,
            jumlah_kriteria_kosong=sum(1 for k in kriteria if k[1] == 0),
        )
        if galat:
            raise ValidasiGagal("Instrumen belum siap diaktifkan.", details=[{"pesan": g} for g in galat])
        async with self.uow:
            # Versi aktif sebelumnya (LAM dan jenjang yang sama) diarsipkan; siklus berjalan tetap beku di versinya.
            await self.session.execute(
                update(InstrumenVersi)
                .where(
                    InstrumenVersi.lam_id == v.lam_id, InstrumenVersi.jenjang == v.jenjang, InstrumenVersi.status == StatusInstrumen.AKTIF
                )
                .values(status=StatusInstrumen.ARSIP)
            )
            v.status, v.disetujui_oleh, v.disetujui_pada = StatusInstrumen.AKTIF, pemanggil.id, datetime.now(UTC)
            v.berlaku_mulai = v.berlaku_mulai or date.today()
            await audit.catat(self.session, "instrumen.aktifkan", pemanggil=pemanggil, entitas="instrumen_versi", entitas_id=v.id)
        hasil = await self.rincian(pemanggil, versi_id)
        hasil["peringatan"] = peringatan
        return hasil

    # ---------- Mapping Engine ----------
    async def daftar_pemetaan(self, versi_id: UUID) -> list[dict[str, Any]]:
        baris = (
            await self.session.execute(
                select(PemetaanButir, InstrumenButir.kode)
                .join(InstrumenButir, InstrumenButir.id == PemetaanButir.instrumen_butir_id)
                .where(InstrumenButir.instrumen_versi_id == versi_id)
                .order_by(InstrumenButir.nomor_urut, PemetaanButir.created_at)
            )
        ).all()
        digantikan = {p.menggantikan_id for p, _ in baris if p.is_aktif and p.menggantikan_id}
        return [
            {
                "id": p.id,
                "butir_id": p.instrumen_butir_id,
                "butir_kode": kode,
                "sumber": p.sumber,
                "indikator_inti_id": p.indikator_inti_id,
                "aturan": p.aturan,
                "keterangan": p.keterangan,
                "status": "disetujui" if p.is_aktif else ("digantikan" if p.id in digantikan else "draf"),
                "menggantikan_id": p.menggantikan_id,
                "disetujui_pada": p.disetujui_pada,
            }
            for p, kode in baris
        ]

    async def susun_pemetaan(self, pemanggil: Pemanggil, butir_id: UUID, items: list[Any]) -> list[dict[str, Any]]:
        """Menyimpan aturan sebagai DRAF. Aturan lama yang berlaku tetap dipakai sampai Dekan menyetujui (EC-31)."""
        pemanggil.wajib(SF)
        b = await self.session.get(InstrumenButir, butir_id)
        if b is None:
            raise TidakDitemukan("Butir tidak ditemukan.")
        for i, it in enumerate(items):
            galat = rules.validasi_aturan(it.aturan)
            if galat:
                raise ValidasiGagal("Aturan pemetaan tidak sah.", details=[{"indeks": i, "pesan": g} for g in galat])
        async with self.uow:
            aktif = {
                p.sumber: p
                for p in (
                    await self.session.execute(
                        select(PemetaanButir).where(PemetaanButir.instrumen_butir_id == butir_id, PemetaanButir.is_aktif)
                    )
                ).scalars()
            }
            # Hanya draf yang dibersihkan; aturan lama yang sudah digantikan tetap disimpan sebagai riwayat.
            sudah_digantikan = select(PemetaanButir.menggantikan_id).where(
                PemetaanButir.is_aktif, PemetaanButir.menggantikan_id.is_not(None)
            )
            await self.session.execute(
                delete(PemetaanButir).where(
                    PemetaanButir.instrumen_butir_id == butir_id,
                    PemetaanButir.is_aktif.is_(False),
                    PemetaanButir.id.not_in(sudah_digantikan),
                )
            )
            for it in items:
                self.session.add(
                    PemetaanButir(
                        instrumen_butir_id=butir_id,
                        sumber=it.sumber,
                        indikator_inti_id=it.indikator_inti_id,
                        aturan=it.aturan,
                        keterangan=it.keterangan,
                        is_aktif=False,
                        menggantikan_id=aktif[it.sumber].id if it.sumber in aktif else None,
                        created_by=pemanggil.id,
                        updated_by=pemanggil.id,
                    )
                )
            await audit.catat(
                self.session,
                "pemetaan.susun",
                pemanggil=pemanggil,
                entitas="instrumen_butir",
                entitas_id=butir_id,
                detail={"jumlah": len(items)},
            )
        baris = (
            (
                await self.session.execute(
                    select(PemetaanButir).where(PemetaanButir.instrumen_butir_id == butir_id).order_by(PemetaanButir.created_at)
                )
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": p.id,
                "sumber": p.sumber,
                "aturan": p.aturan,
                "keterangan": p.keterangan,
                "status": "disetujui" if p.is_aktif else "draf",
                "menggantikan_id": p.menggantikan_id,
            }
            for p in baris
            if p.is_aktif or p.id not in sudah_digantikan_ids(baris)
        ]

    async def setujui_pemetaan(self, pemanggil: Pemanggil, pemetaan_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(D)
        p = await self.session.get(PemetaanButir, pemetaan_id)
        if p is None:
            raise TidakDitemukan("Aturan pemetaan tidak ditemukan.")
        if p.is_aktif:
            raise KonflikStatus("Aturan sudah disetujui.")
        async with self.uow:
            if p.menggantikan_id:
                lama = await self.session.get(PemetaanButir, p.menggantikan_id)
                if lama is not None:
                    lama.is_aktif = False
            else:
                await self.session.execute(
                    update(PemetaanButir)
                    .where(
                        PemetaanButir.instrumen_butir_id == p.instrumen_butir_id,
                        PemetaanButir.sumber == p.sumber,
                        PemetaanButir.is_aktif,
                        PemetaanButir.id != p.id,
                    )
                    .values(is_aktif=False)
                )
            p.is_aktif, p.disetujui_oleh, p.disetujui_pada = True, pemanggil.id, datetime.now(UTC)
            await audit.catat(self.session, "pemetaan.setujui", pemanggil=pemanggil, entitas="pemetaan_butir", entitas_id=p.id)
        return {"id": p.id, "status": "disetujui", "disetujui_pada": p.disetujui_pada}
