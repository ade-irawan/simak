"""Use case siklus akreditasi dan lembar kerja butir."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.core import audit
from app.core.exceptions import AksesDitolak, KonflikStatus, KonflikVersi, TidakDitemukan, ValidasiGagal
from app.core.pagination import ParamHalaman
from app.core.permissions import SF, SP, D, K, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.modules.bukti import public as bukti
from app.modules.dokumen_eksternal import public as dokumen_eksternal
from app.modules.instrumen import public as instrumen
from app.modules.laporan import public as laporan
from app.modules.llm import public as llm
from app.modules.notifikasi import public as notifikasi
from app.modules.pemetaan import public as pemetaan
from app.modules.pengguna import public as pengguna
from app.modules.referensi import public as referensi
from app.modules.siklus.domain import rules
from app.modules.siklus.domain.entities import (
    PengelolaButir,
    StatusKelengkapan,
    StatusSiklus,
    SumberNarasi,
    SumberSkor,
)
from app.modules.siklus.infrastructure import repository as repo
from app.modules.siklus.infrastructure.models import ButirSiklus, NarasiButir, SiklusAkreditasi

URUTAN_STATUS = [StatusSiklus.PERSIAPAN, StatusSiklus.BERJALAN, StatusSiklus.SELESAI, StatusSiklus.ARSIP]


def _sekarang() -> datetime:
    return datetime.now(UTC)


class LayananSiklus:
    def __init__(self, uow: UnitOfWork):
        self.uow, self.session = uow, uow.session

    # ============================================================ siklus
    async def _ke_dict(self, s: SiklusAkreditasi, *, dengan_kesiapan: bool = False) -> dict[str, Any]:
        prodi = await referensi.ambil_prodi(self.session, s.prodi_id)
        definisi = await instrumen.muat_definisi(self.session, s.instrumen_versi_id)
        target = next((p for p in definisi.peringkat if p.id == s.target_peringkat_id), None)
        hasil = {
            "id": s.id,
            "nama": s.nama,
            "status": s.status,
            "prodi": {"id": prodi.id, "kode": prodi.kode, "nama": prodi.nama},
            "instrumen": {"versi_id": s.instrumen_versi_id, "lam": definisi.lam_kode, "kode_versi": definisi.kode_versi},
            "ts_tahun_akademik_id": s.ts_tahun_akademik_id,
            "jumlah_tahun_data": s.jumlah_tahun_data,
            "tanggal_mulai": s.tanggal_mulai,
            "tenggat": s.tenggat,
            "target_peringkat": {"kode": target.kode, "nama": target.nama} if target else None,
            "peringkat_tersedia": [{"kode": p.kode, "nama": p.nama} for p in sorted(definisi.peringkat, key=lambda x: -x.tingkat)],
            "laporan": await laporan.status_siklus(self.session, s.id),
        }
        if dengan_kesiapan:
            baris = (
                (await self.session.execute(text("SELECT * FROM v_kesiapan_siklus WHERE siklus_id = :i"), {"i": s.id})).mappings().first()
            )
            hasil["kesiapan"] = dict(baris) if baris else None
        return hasil

    async def daftar(self, pemanggil: Pemanggil) -> list[dict[str, Any]]:
        stmt = select(SiklusAkreditasi).order_by(SiklusAkreditasi.tanggal_mulai.desc())
        cakupan = pemanggil.cakupan_baca()
        if not cakupan.semua:
            stmt = stmt.where(SiklusAkreditasi.prodi_id.in_(cakupan.prodi_ids))
        return [await self._ke_dict(s) for s in (await self.session.execute(stmt)).scalars()]

    async def _muat(self, pemanggil: Pemanggil, siklus_id: UUID) -> SiklusAkreditasi:
        s = await repo.ambil_siklus(self.session, siklus_id)
        pemanggil.wajib_baca_prodi(s.prodi_id)
        return s

    async def rincian(self, pemanggil: Pemanggil, siklus_id: UUID) -> dict[str, Any]:
        return await self._ke_dict(await self._muat(pemanggil, siklus_id), dengan_kesiapan=True)

    async def buka(self, pemanggil: Pemanggil, data: Any) -> dict[str, Any]:
        pemanggil.wajib(D)
        prodi = await referensi.ambil_prodi(self.session, data.prodi_id)
        await referensi.ambil_tahun_akademik(self.session, data.ts_tahun_akademik_id)
        lam_id = (await self.session.execute(select(referensi.Prodi.lam_id).where(referensi.Prodi.id == prodi.id))).scalar_one()
        if data.instrumen_versi_id:
            versi = await self.session.get(instrumen.InstrumenVersi, data.instrumen_versi_id)
            if versi is None or versi.lam_id != lam_id or versi.status != instrumen.StatusInstrumen.AKTIF:
                raise ValidasiGagal("Versi instrumen harus aktif dan sesuai LAM prodi ini.")
        else:
            versi = await instrumen.versi_aktif(self.session, lam_id, prodi.jenjang)
        definisi = await instrumen.muat_definisi(self.session, versi.id)
        target_id = None
        if data.target_peringkat_kode:
            target = next((p for p in definisi.peringkat if p.kode == data.target_peringkat_kode), None)
            if target is None:
                raise ValidasiGagal(f"Peringkat '{data.target_peringkat_kode}' tidak ada pada instrumen ini.")
            target_id = target.id
        punya_indikator = await dokumen_eksternal.prodi_punya_indikator(self.session, prodi.id)
        butuh_eksternal = {
            b.butir_id for b in await instrumen.butir_terpasok_oleh(self.session, instrumen.JenisEntitas.INDIKATOR_EKSTERNAL)
        }
        async with self.uow:
            s = SiklusAkreditasi(
                prodi_id=prodi.id,
                instrumen_versi_id=versi.id,
                nama=data.nama,
                ts_tahun_akademik_id=data.ts_tahun_akademik_id,
                jumlah_tahun_data=data.jumlah_tahun_data,
                tanggal_mulai=data.tanggal_mulai,
                tenggat=data.tenggat,
                target_peringkat_id=target_id,
                status=StatusSiklus.PERSIAPAN,
                created_by=pemanggil.id,
            )
            self.session.add(s)
            try:
                await self.session.flush()
            except IntegrityError as exc:
                raise KonflikStatus("Prodi ini sudah memiliki siklus akreditasi yang sedang berjalan.") from exc
            for b in definisi.butir:  # satu lembar kerja per butir instrumen
                self.session.add(
                    ButirSiklus(
                        siklus_id=s.id,
                        instrumen_butir_id=b.id,
                        menunggu_dokumen_eksternal=(b.id in butuh_eksternal and not punya_indikator),
                    )
                )
            await laporan.ambil_atau_buat(self.session, s.id)
            await audit.catat(
                self.session,
                "siklus.buka",
                pemanggil=pemanggil,
                entitas="siklus_akreditasi",
                entitas_id=s.id,
                prodi_id=prodi.id,
                detail={"butir": len(definisi.butir), "instrumen": f"{definisi.lam_kode} {definisi.kode_versi}"},
            )
        return await self._ke_dict(s, dengan_kesiapan=True)

    async def ubah(self, pemanggil: Pemanggil, siklus_id: UUID, patch: Any) -> dict[str, Any]:
        pemanggil.wajib(D)
        s = await repo.ambil_siklus(self.session, siklus_id)
        data = patch.model_dump(exclude_unset=True)
        async with self.uow:
            if "target_peringkat_kode" in data:
                definisi = await instrumen.muat_definisi(self.session, s.instrumen_versi_id)
                kode = data.pop("target_peringkat_kode")
                target = next((p for p in definisi.peringkat if p.kode == kode), None) if kode else None
                if kode and target is None:
                    raise ValidasiGagal(f"Peringkat '{kode}' tidak ada pada instrumen ini.")
                s.target_peringkat_id = target.id if target else None
            if "status" in data:
                baru = data.pop("status")
                if URUTAN_STATUS.index(baru) < URUTAN_STATUS.index(s.status):
                    raise KonflikStatus("Status siklus hanya dapat maju (persiapan → berjalan → selesai → arsip).")
                s.status = baru
            for k, v in data.items():
                setattr(s, k, v)
            if s.tenggat and s.tenggat < s.tanggal_mulai:
                raise ValidasiGagal("tenggat tidak boleh sebelum tanggal_mulai")
            await audit.catat(
                self.session,
                "siklus.ubah",
                pemanggil=pemanggil,
                entitas="siklus_akreditasi",
                entitas_id=s.id,
                prodi_id=s.prodi_id,
                detail=patch.model_dump(exclude_unset=True, mode="json"),
            )
        return await self._ke_dict(s, dengan_kesiapan=True)

    async def migrasi(self, pemanggil: Pemanggil, siklus_id: UUID, versi_baru_id: UUID) -> dict[str, Any]:
        """Memindahkan siklus ke versi instrumen baru tanpa menghapus narasi (EC-14)."""
        pemanggil.wajib(D)
        s = await repo.ambil_siklus(self.session, siklus_id)
        await laporan.wajib_tidak_terkunci(self.session, s.prodi_id)
        if versi_baru_id == s.instrumen_versi_id:
            raise ValidasiGagal("Siklus sudah memakai versi instrumen ini.")
        baru = await self.session.get(instrumen.InstrumenVersi, versi_baru_id)
        lama = await self.session.get(instrumen.InstrumenVersi, s.instrumen_versi_id)
        if baru is None or lama is None or baru.lam_id != lama.lam_id or baru.status != instrumen.StatusInstrumen.AKTIF:
            raise ValidasiGagal("Versi baru harus aktif dan berasal dari LAM yang sama.")
        peta = await instrumen.padanan_butir(self.session, lama.id, baru.id)
        definisi_baru = await instrumen.muat_definisi(self.session, baru.id)
        definisi_lama = await instrumen.muat_definisi(self.session, lama.id)
        lembar_lama = {b.instrumen_butir_id: b for b in await repo.lembar_siklus(self.session, s)}
        kode_lama = {b.id: b.kode for b in definisi_lama.butir}
        dipakai: set[UUID] = set()
        dipetakan, tidak_terpetakan = 0, []
        async with self.uow:
            baris_baru: dict[UUID, ButirSiklus] = {}
            for b in definisi_baru.butir:
                bs = ButirSiklus(siklus_id=s.id, instrumen_butir_id=b.id)
                self.session.add(bs)
                baris_baru[b.id] = bs
            await self.session.flush()
            for butir_lama_id, ringkas in lembar_lama.items():
                butir_baru_id = peta.get(butir_lama_id)
                if butir_baru_id is None or butir_baru_id in dipakai or butir_baru_id not in baris_baru:
                    tidak_terpetakan.append(kode_lama.get(butir_lama_id, str(butir_lama_id)))
                    continue
                dipakai.add(butir_baru_id)
                tujuan = baris_baru[butir_baru_id]
                lama_orm = await self.session.get(ButirSiklus, ringkas.id)
                assert lama_orm is not None
                for kolom in (
                    "status_kelengkapan",
                    "pengelola",
                    "penanggung_jawab_id",
                    "ditugaskan_oleh",
                    "ditugaskan_pada",
                    "skor_estimasi",
                    "sumber_skor",
                    "catatan",
                ):
                    setattr(tujuan, kolom, getattr(lama_orm, kolom))
                await self.session.flush()
                await self.session.execute(
                    update(NarasiButir).where(NarasiButir.butir_siklus_id == lama_orm.id).values(butir_siklus_id=tujuan.id)
                )
                await bukti.salin_tautan_butir(self.session, lama_orm.id, tujuan.id)
                dipetakan += 1
            s.instrumen_versi_id = baru.id
            if s.target_peringkat_id:
                kode_target = next((p.kode for p in definisi_lama.peringkat if p.id == s.target_peringkat_id), None)
                s.target_peringkat_id = next((p.id for p in definisi_baru.peringkat if p.kode == kode_target), None)
            await audit.catat(
                self.session,
                "siklus.migrasi_instrumen",
                pemanggil=pemanggil,
                entitas="siklus_akreditasi",
                entitas_id=s.id,
                prodi_id=s.prodi_id,
                detail={"dari": str(lama.id), "ke": str(baru.id), "dipetakan": dipetakan, "tidak_terpetakan": tidak_terpetakan},
            )
        return {
            "siklus_id": s.id,
            "instrumen_versi_id": baru.id,
            "butir_dipetakan": dipetakan,
            "butir_baru": len(definisi_baru.butir) - dipetakan,
            "butir_lama_tanpa_padanan": tidak_terpetakan,
        }

    # ============================================================ butir
    async def daftar_butir(self, pemanggil: Pemanggil, siklus_id: UUID, param: ParamHalaman, filt: dict[str, Any]) -> dict[str, Any]:
        s = await self._muat(pemanggil, siklus_id)
        lembar = await repo.lembar_siklus(self.session, s)
        ids = [b.id for b in lembar]
        hitung = await bukti.hitung_bukti_per_butir(self.session, ids)
        catatan = await laporan.catatan_terbuka_per_butir(self.session, ids)
        nama = await pengguna.nama_pengguna(self.session, [b.penanggung_jawab_id for b in lembar if b.penanggung_jawab_id])
        butir_orm = {b.id: b for b in (await self.session.execute(select(ButirSiklus).where(ButirSiklus.id.in_(ids)))).scalars()}
        definisi = {b.id: b for b in await instrumen.muat_butir(self.session, s.instrumen_versi_id)}

        baris = []
        for b in lembar:
            n_bukti, n_masalah = hitung.get(b.id, (0, 0))
            if filt.get("status_kelengkapan") and b.status_kelengkapan.value != filt["status_kelengkapan"]:
                continue
            if filt.get("kriteria") and b.kriteria_kode != filt["kriteria"]:
                continue
            if filt.get("pengelola") and b.pengelola.value != filt["pengelola"]:
                continue
            if filt.get("penanggung_jawab_id") and b.penanggung_jawab_id != filt["penanggung_jawab_id"]:
                continue
            if filt.get("belum_ditugaskan") and b.penanggung_jawab_id is not None:
                continue
            if filt.get("bukti_bermasalah") and not n_masalah:
                continue
            if filt.get("menunggu_dokumen_eksternal") and not b.menunggu_dokumen_eksternal:
                continue
            if param.q and param.q.lower() not in f"{b.kode} {b.elemen}".lower():
                continue
            d = definisi[b.instrumen_butir_id]
            baris.append(
                {
                    "id": b.id,
                    "butir": {
                        "kode": b.kode,
                        "kriteria": {"kode": b.kriteria_kode, "nama": d.kriteria_nama},
                        "elemen": b.elemen,
                        "jenis_ipo": d.jenis_ipo,
                        "tahap_ppepp": d.tahap_ppepp,
                        "bobot": b.bobot,
                    },
                    "status_kelengkapan": b.status_kelengkapan,
                    "pengelola": b.pengelola,
                    "penanggung_jawab": {"id": b.penanggung_jawab_id, "nama": nama.get(b.penanggung_jawab_id)}
                    if b.penanggung_jawab_id
                    else None,
                    "skor_estimasi": b.skor_estimasi,
                    "jumlah_bukti": n_bukti,
                    "jumlah_bukti_bermasalah": n_masalah,
                    "menunggu_dokumen_eksternal": b.menunggu_dokumen_eksternal,
                    "catatan_validasi_terbuka": catatan.get(b.id, 0),
                    "updated_at": butir_orm[b.id].updated_at,
                }
            )
        total = len(baris)
        halaman = baris[param.offset : param.offset + param.per_page]
        return {"data": halaman, "meta": {"page": param.page, "per_page": param.per_page, "total": total}}

    async def _butir_orm(self, butir_id: UUID) -> tuple[ButirSiklus, SiklusAkreditasi]:
        b = await self.session.get(ButirSiklus, butir_id)
        if b is None:
            raise TidakDitemukan("Butir tidak ditemukan.")
        return b, await repo.ambil_siklus(self.session, b.siklus_id)

    async def detail_butir(self, pemanggil: Pemanggil, butir_id: UUID) -> dict[str, Any]:
        b, s = await self._butir_orm(butir_id)
        pemanggil.wajib_baca_prodi(s.prodi_id)
        info = await instrumen.rincian_butir_siklus(self.session, b.instrumen_butir_id)
        terkunci = await self._terkunci(s.prodi_id)
        narasi = (
            (await self.session.execute(select(NarasiButir).where(NarasiButir.butir_siklus_id == b.id).order_by(NarasiButir.bagian)))
            .scalars()
            .all()
        )
        nama = await pengguna.nama_pengguna(self.session, [b.penanggung_jawab_id] if b.penanggung_jawab_id else [])
        catatan = await laporan.catatan_butir(self.session, b.id)
        boleh = rules.boleh_ubah_butir(pemanggil, prodi_id=s.prodi_id, pengelola=b.pengelola, penanggung_jawab_id=b.penanggung_jawab_id)
        return {
            "id": b.id,
            "siklus_id": b.siklus_id,
            "row_version": b.row_version,
            "butir": {
                "id": info["id"],
                "kode": info["kode"],
                "elemen": info["elemen"],
                "deskriptor": info["deskriptor"],
                "panduan": info["panduan"],
                "kriteria": info["kriteria"],
                "jenis_ipo": info["jenis_ipo"],
                "tahap_ppepp": info["tahap_ppepp"],
                "bobot": info["bobot"],
                "rubrik": info["rubrik"],
                "ambang": info["ambang"],
                "skema_narasi": info["skema_narasi"],
            },
            "status_kelengkapan": b.status_kelengkapan,
            "pengelola": b.pengelola,
            "penanggung_jawab": {"id": b.penanggung_jawab_id, "nama": nama.get(b.penanggung_jawab_id)} if b.penanggung_jawab_id else None,
            "skor_estimasi": b.skor_estimasi,
            "sumber_skor": b.sumber_skor,
            "catatan": b.catatan,
            "menunggu_dokumen_eksternal": b.menunggu_dokumen_eksternal,
            "narasi": [
                {
                    "bagian": n.bagian,
                    "isi": n.isi,
                    "status": n.status,
                    "sumber": n.sumber,
                    "row_version": n.row_version,
                    "updated_at": n.updated_at,
                }
                for n in narasi
            ],
            "bukti": await bukti.daftar_bukti_butir(self.session, b.id),
            "catatan_validasi": catatan,
            "terkunci": terkunci,
            "dapat_disunting": boleh and not terkunci,
            "narasi_dapat_disunting": pemanggil.punya(K) and s.prodi_id in pemanggil.prodi_dari(K) and not terkunci,
        }

    async def _terkunci(self, prodi_id: UUID) -> bool:
        try:
            await laporan.wajib_tidak_terkunci(self.session, prodi_id)
            return False
        except Exception:
            return True

    async def data_terpetakan(self, pemanggil: Pemanggil, butir_id: UUID) -> dict[str, Any]:
        b, s = await self._butir_orm(butir_id)
        pemanggil.wajib_baca_prodi(s.prodi_id)
        tahun_ids = await referensi.rentang_tahun(self.session, s.ts_tahun_akademik_id, s.jumlah_tahun_data)
        aturan = (await instrumen.aturan_aktif(self.session, [b.instrumen_butir_id])).get(b.instrumen_butir_id, [])
        data = await pemetaan.data_untuk_butir(self.session, aturan, s.prodi_id, tahun_ids)
        kosong = [d["sumber"] for d in data if d["kosong"]]
        return {
            "butir_siklus_id": b.id,
            "tahun_akademik_ids": tahun_ids,
            "sumber": data,
            "data_kurang": kosong,
            "belum_lengkap": bool(data) and len(kosong) == len(data),
        }

    async def ubah_butir(self, pemanggil: Pemanggil, butir_id: UUID, patch: Any) -> dict[str, Any]:
        b, s = await self._butir_orm(butir_id)
        rules.wajib_ubah_butir(pemanggil, prodi_id=s.prodi_id, pengelola=b.pengelola, penanggung_jawab_id=b.penanggung_jawab_id)
        await laporan.wajib_tidak_terkunci(self.session, s.prodi_id)
        if patch.row_version != b.row_version:
            raise KonflikVersi(details=[{"row_version": b.row_version, "updated_at": b.updated_at}])
        data = patch.model_dump(exclude_unset=True, exclude={"row_version"})
        async with self.uow:
            if "status_kelengkapan" in data and data["status_kelengkapan"] is not None:
                b.status_kelengkapan = data["status_kelengkapan"]
            if "skor_estimasi" in data:
                b.skor_estimasi, b.sumber_skor, b.skor_dihitung_pada = data["skor_estimasi"], SumberSkor.MANDIRI, _sekarang()
            if "catatan" in data:
                b.catatan = data["catatan"]
            b.updated_by = pemanggil.id
            try:
                await self.session.flush()
            except StaleDataError as exc:
                raise KonflikVersi() from exc
            await audit.catat(
                self.session,
                "butir_siklus.ubah",
                pemanggil=pemanggil,
                entitas="butir_siklus",
                entitas_id=b.id,
                prodi_id=s.prodi_id,
                detail=patch.model_dump(exclude_unset=True, mode="json"),
            )
        return await self.detail_butir(pemanggil, butir_id)

    # ------------------------------------------------------------ narasi (hanya Kaprodi — EC-30)
    async def simpan_narasi(self, pemanggil: Pemanggil, butir_id: UUID, bagian: str, data: Any) -> dict[str, Any]:
        if not pemanggil.punya(K):  # EC-30: Staf Admin Prodi/Fakultas tidak menyunting narasi
            raise AksesDitolak("Narasi hanya dapat disunting Kaprodi.", alasan="narasi_hanya_kaprodi")
        b, s = await self._butir_orm(butir_id)
        pemanggil.wajib_kaprodi(s.prodi_id)
        await laporan.wajib_tidak_terkunci(self.session, s.prodi_id)
        info = await instrumen.rincian_butir_siklus(self.session, b.instrumen_butir_id)
        bagian_sah = {x["bagian"] for x in info["skema_narasi"]} or {"utama"}
        if bagian not in bagian_sah:
            raise ValidasiGagal(f"Bagian narasi '{bagian}' tidak ada pada butir ini.", details=[{"bagian_tersedia": sorted(bagian_sah)}])
        sumber = SumberNarasi.MANUAL
        if data.permintaan_llm_id:
            hasil_llm = await llm.hasil_permintaan(self.session, data.permintaan_llm_id, b.id)
            if hasil_llm is None:
                raise ValidasiGagal("Permintaan LLM tidak ditemukan atau belum selesai untuk butir ini.")
            sumber = SumberNarasi.LLM if data.isi.strip() == hasil_llm.strip() else SumberNarasi.LLM_DISUNTING
        n = (
            await self.session.execute(select(NarasiButir).where(NarasiButir.butir_siklus_id == b.id, NarasiButir.bagian == bagian))
        ).scalar_one_or_none()
        async with self.uow:
            if n is None:
                n = NarasiButir(butir_siklus_id=b.id, bagian=bagian)
                self.session.add(n)
            elif data.row_version is None or data.row_version != n.row_version:
                raise KonflikVersi(details=[{"row_version": n.row_version, "updated_at": n.updated_at}])
            n.isi, n.status, n.sumber, n.updated_by = data.isi, data.status, sumber, pemanggil.id
            n.permintaan_llm_id = data.permintaan_llm_id if data.permintaan_llm_id else n.permintaan_llm_id
            try:
                await self.session.flush()
            except StaleDataError as exc:
                raise KonflikVersi(details=[{"pesan": "Narasi diubah pengguna lain."}]) from exc
            # Perubahan narasi tidak dicatat penuh di log audit (auto-save sering); cukup metadata.
            if b.status_kelengkapan == StatusKelengkapan.BELUM_MULAI:
                b.status_kelengkapan = StatusKelengkapan.DRAFT
        return {"bagian": n.bagian, "status": n.status, "sumber": n.sumber, "row_version": n.row_version, "updated_at": n.updated_at}

    # ------------------------------------------------------------ penugasan (Dekan — US-G3)
    async def _periksa_penanggung_jawab(self, prodi_id: UUID, pengelola: PengelolaButir, pj_id: UUID | None) -> None:
        if pj_id is None:
            return
        penugasan = await pengguna.penugasan_aktif(self.session, pj_id)
        peran_sf = any(p.peran == SF for p in penugasan)
        peran_sp = any(p.peran == SP and p.prodi_id == prodi_id for p in penugasan)
        if pengelola == PengelolaButir.FAKULTAS and not peran_sf:
            raise ValidasiGagal("Butir yang dikelola fakultas harus ditugaskan kepada Staf Admin Fakultas.")
        if pengelola == PengelolaButir.PRODI and not (peran_sp or peran_sf):
            raise ValidasiGagal("Butir yang dikelola prodi harus ditugaskan kepada Staf Admin Prodi (atau Staf Fakultas yang membantu).")

    async def tetapkan_penugasan(self, pemanggil: Pemanggil, butir_id: UUID, data: Any) -> dict[str, Any]:
        pemanggil.wajib(D)
        b, s = await self._butir_orm(butir_id)
        await self._periksa_penanggung_jawab(s.prodi_id, data.pengelola, data.penanggung_jawab_id)
        async with self.uow:
            await self._terapkan_penugasan(pemanggil, b, s, data.pengelola, data.penanggung_jawab_id)
        return await self.detail_butir(pemanggil, butir_id)

    async def _terapkan_penugasan(
        self, pemanggil: Pemanggil, b: ButirSiklus, s: SiklusAkreditasi, pengelola: PengelolaButir, pj: UUID | None
    ) -> None:
        lama = (b.pengelola, b.penanggung_jawab_id)
        b.pengelola, b.penanggung_jawab_id = pengelola, pj
        b.ditugaskan_oleh, b.ditugaskan_pada = pemanggil.id, _sekarang()
        await audit.catat(
            self.session,
            "butir_siklus.penugasan",
            pemanggil=pemanggil,
            entitas="butir_siklus",
            entitas_id=b.id,
            prodi_id=s.prodi_id,
            detail={"lama": {"pengelola": lama[0], "pj": lama[1]}, "baru": {"pengelola": pengelola, "pj": pj}},
        )
        if pj and pj != lama[1]:
            await notifikasi.kirim(
                self.session,
                pj,
                "butir.ditugaskan",
                "Butir baru ditugaskan kepada Anda",
                f"Dekan menugaskan satu butir akreditasi kepada Anda (siklus {s.nama}).",
                f"/butir/{b.id}",
            )

    async def penugasan_massal(self, pemanggil: Pemanggil, siklus_id: UUID, data: Any) -> dict[str, Any]:
        pemanggil.wajib(D)
        s = await repo.ambil_siklus(self.session, siklus_id)
        await self._periksa_penanggung_jawab(s.prodi_id, data.pengelola, data.penanggung_jawab_id)
        butir = (
            (
                await self.session.execute(
                    select(ButirSiklus).where(ButirSiklus.id.in_(data.butir_siklus_ids), ButirSiklus.siklus_id == siklus_id)
                )
            )
            .scalars()
            .all()
        )
        if len(butir) != len(set(data.butir_siklus_ids)):
            raise ValidasiGagal("Ada butir yang tidak termasuk siklus ini.")
        async with self.uow:
            for b in butir:
                await self._terapkan_penugasan(pemanggil, b, s, data.pengelola, data.penanggung_jawab_id)
        return {"siklus_id": siklus_id, "jumlah": len(butir), "pengelola": data.pengelola, "penanggung_jawab_id": data.penanggung_jawab_id}

    async def papan_saya(self, pemanggil: Pemanggil) -> dict[str, Any]:
        """Papan kerja staf: hanya butir yang ditugaskan kepadanya + antrean butir yang belum bertuan di bagiannya."""
        pemanggil.wajib(SP, SF)
        aktif = [StatusSiklus.PERSIAPAN, StatusSiklus.BERJALAN]
        stmt = (
            select(ButirSiklus, SiklusAkreditasi)
            .join(SiklusAkreditasi, SiklusAkreditasi.id == ButirSiklus.siklus_id)
            .where(SiklusAkreditasi.status.in_(aktif))
        )
        baris = (await self.session.execute(stmt)).all()
        ids = [b.id for b, _ in baris]
        rincian = {
            x.id: x
            for x in [item for s_ in {s.instrumen_versi_id for _, s in baris} for item in await instrumen.muat_butir(self.session, s_)]
        }
        hitung = await bukti.hitung_bukti_per_butir(self.session, ids)
        prodi = {p.id: p for p in await referensi.daftar_prodi(self.session)}
        milik, antrean = [], []
        prodi_sp = pemanggil.prodi_dari(SP)

        def item(b: ButirSiklus, s: SiklusAkreditasi) -> dict[str, Any]:
            d = rincian.get(b.instrumen_butir_id)
            return {
                "id": b.id,
                "siklus_id": s.id,
                "prodi": prodi[s.prodi_id].kode,
                "kode": d.kode if d else None,
                "elemen": d.elemen if d else None,
                "status_kelengkapan": b.status_kelengkapan,
                "pengelola": b.pengelola,
                "jumlah_bukti": hitung.get(b.id, (0, 0))[0],
                "jumlah_bukti_bermasalah": hitung.get(b.id, (0, 0))[1],
                "menunggu_dokumen_eksternal": b.menunggu_dokumen_eksternal,
            }

        for b, s in baris:
            if b.penanggung_jawab_id == pemanggil.id:
                milik.append(item(b, s))
            elif b.penanggung_jawab_id is None:
                if pemanggil.punya(SF) and b.pengelola == PengelolaButir.FAKULTAS:
                    antrean.append(item(b, s))
                elif pemanggil.punya(SP) and b.pengelola == PengelolaButir.PRODI and s.prodi_id in prodi_sp:
                    antrean.append(item(b, s))
        return {"ditugaskan": milik, "antrean_belum_bertuan": antrean}

    async def antrean_belum_ditugaskan(self, pemanggil: Pemanggil, siklus_id: UUID) -> list[dict[str, Any]]:
        """EC-27: butir tanpa penanggung jawab, hanya terlihat Dekan."""
        pemanggil.wajib(D)
        s = await repo.ambil_siklus(self.session, siklus_id)
        return [
            {"id": b.id, "kode": b.kode, "elemen": b.elemen, "pengelola": b.pengelola}
            for b in await repo.lembar_siklus(self.session, s)
            if b.penanggung_jawab_id is None
        ]
