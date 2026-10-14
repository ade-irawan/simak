"""Use case penilaian: simulasi skor & prediksi peringkat, dasbor, gap analysis, benchmarking."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import audit
from app.core.exceptions import TidakDitemukan, ValidasiGagal
from app.core.permissions import SF, SP, D, K, Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.modules.instrumen import public as instrumen
from app.modules.laporan import public as laporan
from app.modules.pengguna import public as pengguna
from app.modules.penilaian.application import indikator as hitung_indikator
from app.modules.penilaian.domain import risiko
from app.modules.penilaian.domain.penilai import MasukanButir, pilih_penilai
from app.modules.penilaian.infrastructure.models import NilaiIndikator, SimulasiSkor
from app.modules.ppepp import public as ppepp
from app.modules.referensi import public as referensi
from app.modules.siklus import public as siklus

PERINGATAN = "Skor ini adalah estimasi internal, bukan penilaian resmi asesor."


def _sekarang() -> datetime:
    return datetime.now(UTC)


async def hitung_simulasi(session: AsyncSession, siklus_id: UUID, oleh: UUID | None, *, simpan: bool = True) -> dict[str, Any]:
    """Menghitung simulasi sesuai instrumen siklus. Dipakai API, tugas malam, dan cuplikan laporan."""
    sk = await siklus.ambil_ringkas_siklus(session, siklus_id)
    definisi = await instrumen.muat_definisi(session, sk.instrumen_versi_id)
    lembar = await siklus.daftar_lembar(session, siklus_id)
    masukan = [MasukanButir(b.instrumen_butir_id, b.id, b.kode, b.kriteria_kode, b.bobot, b.skor_estimasi) for b in lembar]
    target = next((p for p in definisi.peringkat if p.id == sk.target_peringkat_id), None)
    hasil = pilih_penilai(definisi).hitung(definisi, masukan, target)
    sekarang = _sekarang()
    if simpan:
        session.add(
            SimulasiSkor(
                siklus_id=siklus_id,
                nilai_akhir=hasil.nilai_akhir,
                prediksi_peringkat_id=hasil.peringkat.id,
                rincian=_jsonable(hasil.rincian),
                dihitung_oleh=oleh,
                dihitung_pada=sekarang,
            )
        )
    return {
        "siklus_id": siklus_id,
        "estimasi_internal": True,
        "peringatan": PERINGATAN,
        "dihitung_pada": sekarang,
        "nilai_akhir": hasil.nilai_akhir,
        "nilai_akhir_maks": definisi.nilai_akhir_maks,
        "prediksi_peringkat": {"kode": hasil.peringkat.kode, "nama": hasil.peringkat.nama},
        "target_peringkat": {"kode": target.kode, "nama": target.nama} if target else None,
        "di_bawah_target": bool(target and hasil.peringkat.tingkat < target.tingkat),
        "butir_belum_dinilai": hasil.butir_belum_dinilai,
        "rincian": _jsonable(hasil.rincian),
        "catatan": hasil.catatan,
    }


def _jsonable(x: Any) -> Any:
    from fastapi.encoders import jsonable_encoder

    return jsonable_encoder(x)


async def hitung_gap_siklus(session: AsyncSession, siklus_id: UUID) -> dict[str, Any]:
    sk = await siklus.ambil_ringkas_siklus(session, siklus_id)
    definisi = await instrumen.muat_definisi(session, sk.instrumen_versi_id)
    target = next((p for p in definisi.peringkat if p.id == sk.target_peringkat_id), None)
    lembar = await siklus.daftar_lembar(session, siklus_id)
    syarat = (target.syarat or {}) if target else {}
    ambang = {a.butir_id: a for a in definisi.ambang if target and a.peringkat_id == target.id}
    baris = []
    for b in lembar:
        a = ambang.get(b.instrumen_butir_id)
        sasaran = (
            a.skor_min if a else (Decimal(str(syarat["skor_butir_min"])) if "skor_butir_min" in syarat else Decimal(definisi.skor_maks))
        )
        skor = b.skor_estimasi
        baris.append(
            {
                "butir_siklus_id": b.id,
                "kode": b.kode,
                "kriteria": b.kriteria_kode,
                "bobot": b.bobot,
                "skor_estimasi": skor,
                "skor_target": sasaran,
                "selisih": (skor - sasaran) if skor is not None else None,
                "is_syarat_perlu": bool(a and a.is_syarat_perlu),
            }
        )
    baris.sort(key=lambda x: (x["selisih"] is None, x["selisih"] if x["selisih"] is not None else 0))
    return {
        "jenis": "akreditasi",
        "estimasi_internal": True,
        "target_peringkat": target.nama if target else None,
        "butir": baris,
        "butir_di_bawah_target": sum(1 for x in baris if x["selisih"] is not None and x["selisih"] < 0),
    }


class LayananPenilaian:
    def __init__(self, uow: UnitOfWork):
        self.uow, self.session = uow, uow.session

    # ------------------------------------------------------------ simulasi
    async def _periksa_akses_siklus(self, pemanggil: Pemanggil, siklus_id: UUID) -> Any:
        sk = await siklus.ambil_ringkas_siklus(self.session, siklus_id)
        pemanggil.wajib_baca_prodi(sk.prodi_id)
        return sk

    async def simulasi_terakhir(self, pemanggil: Pemanggil, siklus_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(D, K)
        sk = await self._periksa_akses_siklus(pemanggil, siklus_id)
        terakhir = (
            await self.session.execute(
                select(SimulasiSkor).where(SimulasiSkor.siklus_id == siklus_id).order_by(SimulasiSkor.dihitung_pada.desc()).limit(1)
            )
        ).scalar_one_or_none()
        if terakhir is None:
            return await self.hitung(pemanggil, siklus_id)
        definisi = await instrumen.muat_definisi(self.session, sk.instrumen_versi_id)
        peta = {p.id: p for p in definisi.peringkat}
        prediksi = peta.get(terakhir.prediksi_peringkat_id)
        target = peta.get(sk.target_peringkat_id)
        return {
            "siklus_id": siklus_id,
            "estimasi_internal": True,
            "peringatan": PERINGATAN,
            "dihitung_pada": terakhir.dihitung_pada,
            "nilai_akhir": terakhir.nilai_akhir,
            "nilai_akhir_maks": definisi.nilai_akhir_maks,
            "prediksi_peringkat": {"kode": prediksi.kode, "nama": prediksi.nama} if prediksi else None,
            "target_peringkat": {"kode": target.kode, "nama": target.nama} if target else None,
            "di_bawah_target": bool(target and prediksi and prediksi.tingkat < target.tingkat),
            "butir_belum_dinilai": sum(1 for b in await siklus.daftar_lembar(self.session, siklus_id) if b.skor_estimasi is None),
            "rincian": terakhir.rincian,
        }

    async def hitung(self, pemanggil: Pemanggil, siklus_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(D, K)
        await self._periksa_akses_siklus(pemanggil, siklus_id)
        async with self.uow:
            hasil = await hitung_simulasi(self.session, siklus_id, pemanggil.id)
            await audit.catat(self.session, "simulasi_skor.hitung", pemanggil=pemanggil, entitas="siklus_akreditasi", entitas_id=siklus_id)
        return hasil

    # ------------------------------------------------------------ dasbor
    async def _kesiapan(self, siklus_ids: list[UUID]) -> dict[UUID, Any]:
        if not siklus_ids:
            return {}
        baris = (
            (await self.session.execute(text("SELECT * FROM v_kesiapan_siklus WHERE siklus_id = ANY(:ids)"), {"ids": siklus_ids}))
            .mappings()
            .all()
        )
        return {b["siklus_id"]: b for b in baris}

    async def _satu_prodi(self, prodi: Any, tahun_akademik_id: UUID | None, hari_ini: date) -> dict[str, Any]:
        sk = await siklus.siklus_aktif_prodi(self.session, prodi.id)
        if sk is None:
            return {
                "prodi": {"id": prodi.id, "kode": prodi.kode, "nama": prodi.nama},
                "siklus_id": None,
                "instrumen": None,
                "persen_siap": 0.0,
                "butir": None,
                "ppepp": await ppepp.ringkasan_prodi(self.session, prodi.id),
                "laporan": None,
                "simulasi": None,
                "tingkat_risiko": "abu",
                "alasan_risiko": ["Belum ada siklus akreditasi aktif"],
            }
        kesiapan = (await self._kesiapan([sk.id])).get(sk.id)
        definisi_nama = await instrumen.muat_definisi(self.session, sk.instrumen_versi_id)
        terakhir = (
            await self.session.execute(
                select(SimulasiSkor).where(SimulasiSkor.siklus_id == sk.id).order_by(SimulasiSkor.dihitung_pada.desc()).limit(1)
            )
        ).scalar_one_or_none()
        peta = {p.id: p for p in definisi_nama.peringkat}
        prediksi = peta.get(terakhir.prediksi_peringkat_id) if terakhir else None
        nilai_akhir = terakhir.nilai_akhir if terakhir else None
        dihitung_pada = terakhir.dihitung_pada if terakhir else None
        if terakhir is None:  # belum ada hasil tersimpan: hitung langsung (tidak disimpan) agar dasbor tidak kosong
            live = await hitung_simulasi(self.session, sk.id, None, simpan=False)
            prediksi = next((p for p in definisi_nama.peringkat if p.kode == live["prediksi_peringkat"]["kode"]), None)
            nilai_akhir, dihitung_pada = live["nilai_akhir"], live["dihitung_pada"]
        target = peta.get(sk.target_peringkat_id)
        di_bawah = bool(prediksi and target and prediksi.tingkat < target.tingkat)
        k = kesiapan or {}
        tingkat, alasan = risiko.tingkat_risiko(
            risiko.SinyalRisiko(
                float(k.get("persen_siap", 0) or 0),
                int(k.get("butir_bukti_bermasalah", 0) or 0),
                int(k.get("butir_belum_ditugaskan", 0) or 0),
                int(k.get("butir_menunggu_eksternal", 0) or 0),
                sk.tenggat,
                di_bawah,
                hari_ini,
            )
        )
        return {
            "prodi": {"id": prodi.id, "kode": prodi.kode, "nama": prodi.nama},
            "instrumen": f"{definisi_nama.lam_kode.replace('_', ' ')} {definisi_nama.kode_versi}",
            "siklus_id": sk.id,
            "tenggat": sk.tenggat,
            "persen_siap": float(k.get("persen_siap", 0) or 0),
            "butir": {
                "jumlah": k.get("jumlah_butir", 0),
                "lengkap": k.get("butir_lengkap", 0),
                "draft": k.get("butir_draft", 0),
                "belum_mulai": k.get("butir_belum_mulai", 0),
                "belum_ditugaskan": k.get("butir_belum_ditugaskan", 0),
                "bukti_bermasalah": k.get("butir_bukti_bermasalah", 0),
                "menunggu_dokumen_eksternal": k.get("butir_menunggu_eksternal", 0),
            },
            "ppepp": await ppepp.ringkasan_prodi(self.session, prodi.id),
            "laporan": await laporan.status_siklus(self.session, sk.id),
            "simulasi": {
                "nilai_akhir": nilai_akhir,
                "prediksi_peringkat": prediksi.nama if prediksi else None,
                "target_peringkat": target.nama if target else None,
                "dihitung_pada": dihitung_pada,
                "estimasi_internal": True,
            },
            "tingkat_risiko": tingkat,
            "alasan_risiko": alasan,
        }

    async def dasbor_fakultas(self, pemanggil: Pemanggil, tahun_akademik_id: UUID | None, prodi_id: UUID | None) -> dict[str, Any]:
        pemanggil.wajib(D, SF)
        ta = (
            await referensi.ambil_tahun_akademik(self.session, tahun_akademik_id)
            if tahun_akademik_id
            else await referensi.tahun_akademik_aktif(self.session)
        )
        hari_ini = date.today()
        prodi = [p for p in await referensi.daftar_prodi(self.session) if not prodi_id or p.id == prodi_id]
        return {"tahun_akademik": ta.kode if ta else None, "prodi": [await self._satu_prodi(p, tahun_akademik_id, hari_ini) for p in prodi]}

    async def dasbor_prodi(self, pemanggil: Pemanggil, prodi_id: UUID) -> dict[str, Any]:
        pemanggil.wajib(D, K, SP, SF)
        if not pemanggil.punya(D, SF):
            pemanggil.wajib_baca_prodi(prodi_id)
        elif pemanggil.punya(SF) and not pemanggil.punya(D):
            pass  # Staf Fakultas membaca dasbor prodi (matriks: R¹; penulisan dibatasi di tempat lain)
        p = await referensi.ambil_prodi(self.session, prodi_id)
        ringkasan = await self._satu_prodi(p, None, date.today())
        belum: list[dict[str, Any]] = []
        if ringkasan["siklus_id"]:
            lembar = await siklus.daftar_lembar(self.session, ringkasan["siklus_id"])
            nama = await _nama_pengguna(self.session, [b.penanggung_jawab_id for b in lembar if b.penanggung_jawab_id])
            belum = [
                {
                    "butir_siklus_id": b.id,
                    "kode": b.kode,
                    "elemen": b.elemen,
                    "status_kelengkapan": b.status_kelengkapan,
                    "pengelola": b.pengelola,
                    "penanggung_jawab": nama.get(b.penanggung_jawab_id) if b.penanggung_jawab_id else None,
                    "menunggu_dokumen_eksternal": b.menunggu_dokumen_eksternal,
                }
                for b in lembar
                if b.status_kelengkapan.value != "lengkap"
            ]
        return ringkasan | {"butir_belum_lengkap": belum}

    # ------------------------------------------------------------ gap analysis & benchmarking (Dekan)
    async def gap(self, pemanggil: Pemanggil, siklus_id: UUID | None, siklus_ppepp_id: UUID | None) -> dict[str, Any]:
        pemanggil.wajib(D)
        if bool(siklus_id) == bool(siklus_ppepp_id):
            raise ValidasiGagal("Isi tepat salah satu: siklus_id atau siklus_ppepp_id.")
        if siklus_ppepp_id:
            return {"jenis": "ppepp", **await ppepp.rekap(self.session, siklus_ppepp_id)}
        assert siklus_id
        return await hitung_gap_siklus(self.session, siklus_id)

    async def benchmark(
        self, pemanggil: Pemanggil, kode_indikator: str, tahun_akademik_id: UUID, hitung_ulang: bool = True
    ) -> dict[str, Any]:
        """Perbandingan antarprodi HANYA pada indikator inti yang setara (EC-20); tidak ada skor mentah lintas-LAM."""
        pemanggil.wajib(D)
        ind = (
            await self.session.execute(select(instrumen.IndikatorInti).where(instrumen.IndikatorInti.kode == kode_indikator))
        ).scalar_one_or_none()
        if ind is None:
            raise TidakDitemukan("Indikator inti tidak dikenal.")
        ta = await referensi.ambil_tahun_akademik(self.session, tahun_akademik_id)
        if hitung_ulang:
            async with self.uow:
                await hitung_indikator.hitung_dan_simpan(self.session, tahun_akademik_id)
        baris = (
            (
                await self.session.execute(
                    select(NilaiIndikator).where(
                        NilaiIndikator.indikator_inti_id == ind.id, NilaiIndikator.tahun_akademik_id == tahun_akademik_id
                    )
                )
            )
            .scalars()
            .all()
        )
        prodi = {p.id: p for p in await referensi.daftar_prodi(self.session)}
        data = [
            {"prodi": prodi[b.prodi_id].kode, "prodi_nama": prodi[b.prodi_id].nama, "nilai": b.nilai, "rincian": b.rincian}
            for b in baris
            if b.prodi_id in prodi
        ]
        data.sort(key=lambda x: (x["nilai"] is None, -(x["nilai"] or 0) if ind.makin_tinggi_makin_baik else (x["nilai"] or 0)))
        return {
            "indikator": {"kode": ind.kode, "nama": ind.nama, "satuan": ind.satuan, "makin_tinggi_makin_baik": ind.makin_tinggi_makin_baik},
            "tahun_akademik": ta.kode,
            "data": data,
        }

    async def daftar_indikator(self, pemanggil: Pemanggil) -> list[dict[str, Any]]:
        pemanggil.wajib(D)
        baris = (await self.session.execute(select(instrumen.IndikatorInti).order_by(instrumen.IndikatorInti.nama))).scalars().all()
        return [
            {
                "kode": i.kode,
                "nama": i.nama,
                "satuan": i.satuan,
                "deskripsi": i.deskripsi,
                "makin_tinggi_makin_baik": i.makin_tinggi_makin_baik,
            }
            for i in baris
        ]


async def _nama_pengguna(session: AsyncSession, ids: list[UUID]) -> dict[UUID, str]:
    if not ids:
        return {}
    baris = (await session.execute(select(pengguna.Pengguna.id, pengguna.Pengguna.nama).where(pengguna.Pengguna.id.in_(set(ids))))).all()
    return dict(baris)
