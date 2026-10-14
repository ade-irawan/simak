"""Menyusun cuplikan (snapshot) laporan dari data hidup. Cuplikan pengajuan yang disetujui adalah versi
yang dilihat asesor (EC-29), sehingga seluruh isi yang relevan disalin ke dalamnya."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bukti import public as bukti
from app.modules.instrumen import public as instrumen
from app.modules.pemetaan import public as pemetaan
from app.modules.penilaian import public as penilaian
from app.modules.referensi import public as referensi
from app.modules.siklus import public as siklus


class PenyusunCuplikanDb:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def susun(self, siklus_id: UUID) -> dict[str, Any]:
        sk = await siklus.ambil_ringkas_siklus(self.session, siklus_id)
        prodi = await referensi.ambil_prodi(self.session, sk.prodi_id)
        definisi = await instrumen.muat_definisi(self.session, sk.instrumen_versi_id)
        lembar = await siklus.daftar_lembar(self.session, siklus_id, dengan_narasi=True)
        data = await pemetaan.data_banyak_butir(
            self.session, [b.instrumen_butir_id for b in lembar], sk.prodi_id, sk.ts_tahun_akademik_id, sk.jumlah_tahun_data
        )
        ta_ts = await referensi.ambil_tahun_akademik(self.session, sk.ts_tahun_akademik_id)
        skor = await penilaian.hitung_simulasi(self.session, siklus_id, None, simpan=False)

        kriteria: dict[str, dict[str, Any]] = {}
        semua_bukti: list[str] = []
        for b in lembar:
            detail = await instrumen.rincian_butir_siklus(self.session, b.instrumen_butir_id)
            daftar_bukti = await bukti.daftar_bukti_butir(self.session, b.id)
            semua_bukti += [str(x["id"]) for x in daftar_bukti]
            k = kriteria.setdefault(
                b.kriteria_kode,
                {
                    "kode": b.kriteria_kode,
                    "nama": detail["kriteria"]["nama"],
                    "bobot": definisi.bobot_kriteria.get(b.kriteria_kode),
                    "butir": [],
                },
            )
            k["butir"].append(
                {
                    "butir_siklus_id": b.id,
                    "kode": b.kode,
                    "elemen": b.elemen,
                    "deskriptor": detail["deskriptor"],
                    "jenis_ipo": detail["jenis_ipo"],
                    "tahap_ppepp": detail["tahap_ppepp"],
                    "bobot": b.bobot,
                    "skema_narasi": detail["skema_narasi"],
                    "rubrik": detail["rubrik"],
                    "ambang": detail["ambang"],
                    "status_kelengkapan": b.status_kelengkapan.value,
                    "skor_estimasi": b.skor_estimasi,
                    "catatan": b.catatan,
                    "narasi": b.narasi,
                    "bukti": daftar_bukti,
                    "data_terpetakan": data.get(b.instrumen_butir_id, []),
                }
            )
        urutan = {b.kriteria_kode: b.kriteria_urutan for b in definisi.butir}
        return jsonable_encoder(
            {
                "dibuat_pada": datetime.now(UTC),
                "siklus": {
                    "id": sk.id,
                    "nama": sk.nama,
                    "ts": ta_ts.kode,
                    "jumlah_tahun_data": sk.jumlah_tahun_data,
                    "tenggat": sk.tenggat,
                },
                "prodi": {"id": prodi.id, "kode": prodi.kode, "nama": prodi.nama, "jenjang": prodi.jenjang},
                "instrumen": {
                    "lam": definisi.lam_kode,
                    "kode_versi": definisi.kode_versi,
                    "skor_maks": definisi.skor_maks,
                    "nilai_akhir_maks": definisi.nilai_akhir_maks,
                },
                "skor": skor,
                "kriteria": sorted(kriteria.values(), key=lambda k: urutan.get(k["kode"], 99)),
                "bukti_ids": sorted(set(semua_bukti)),
            }
        )
