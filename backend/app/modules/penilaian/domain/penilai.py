"""Penilai peringkat. Dua strategi memenuhi satu antarmuka dan dipilih dari DATA instrumen,
sehingga LAM baru dengan pola serupa tidak menuntut perubahan kode di modul lain.

* ``PenilaiBerbobot``   — pola LAM INFOKOM: nilai akhir = Σ(skor × bobot butir); rentang nilai akhir + syarat
                          rerata kriteria + skor butir minimum.
* ``PenilaiAmbangButir`` — pola LAMSAMA: tiap peringkat menuntut skor minimum per indikator; sebagian ditandai
                          syarat perlu. Tanpa nilai akhir.

Hasil selalu berupa ESTIMASI INTERNAL, bukan penilaian resmi asesor (US-F4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Protocol
from uuid import UUID

from app.modules.instrumen.public import DefinisiInstrumen, PeringkatDef

DUA = Decimal("0.01")


def q2(x: Decimal | None) -> Decimal | None:
    return None if x is None else x.quantize(DUA, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class MasukanButir:
    butir_id: UUID  # instrumen_butir.id
    butir_siklus_id: UUID
    kode: str
    kriteria_kode: str
    bobot: Decimal | None
    skor: Decimal | None  # skor_estimasi; None = belum dinilai


@dataclass
class HasilPenilaian:
    nilai_akhir: Decimal | None
    peringkat: PeringkatDef
    rincian: dict[str, Any]
    butir_belum_dinilai: int
    syarat_terpenuhi: bool = True
    catatan: list[str] = field(default_factory=list)


class PenilaiPeringkat(Protocol):
    def hitung(self, definisi: DefinisiInstrumen, masukan: list[MasukanButir], target: PeringkatDef | None) -> HasilPenilaian: ...


def _terendah(peringkat: list[PeringkatDef]) -> PeringkatDef:
    return min(peringkat, key=lambda p: p.tingkat)


class PenilaiBerbobot:
    def hitung(self, definisi: DefinisiInstrumen, masukan: list[MasukanButir], target: PeringkatDef | None) -> HasilPenilaian:
        belum = sum(1 for m in masukan if m.skor is None)
        # Butir belum dinilai dihitung 0 agar prediksi tidak terlalu optimistis.
        nilai = {m.butir_siklus_id: (m.skor or Decimal(0)) for m in masukan}
        akhir = sum((nilai[m.butir_siklus_id] * (m.bobot or Decimal(0)) for m in masukan), Decimal(0))

        per_kriteria: dict[str, list[MasukanButir]] = {}
        for m in masukan:
            per_kriteria.setdefault(m.kriteria_kode, []).append(m)

        def rerata(kode: str) -> Decimal:
            butir = per_kriteria.get(kode, [])
            bobot = sum((m.bobot or Decimal(0) for m in butir), Decimal(0))
            if not bobot:
                return Decimal(0)
            return sum((nilai[m.butir_siklus_id] * (m.bobot or Decimal(0)) for m in butir), Decimal(0)) / bobot

        syarat_gagal: list[dict[str, Any]] = []
        kriteria_out: dict[str, dict[str, Any]] = {}

        def periksa_syarat(p: PeringkatDef, catat: bool) -> bool:
            s = p.syarat or {}
            if "kriteria" not in s:
                return True
            gagal: list[dict[str, Any]] = []
            for kode in s["kriteria"]:
                r = rerata(kode)
                batas = Decimal(str(s.get("rerata_kriteria_min", 0)))
                if r < batas:
                    gagal.append({"syarat": "rerata_kriteria_min", "kriteria": kode, "nilai": float(q2(r)), "ambang": float(batas)})
                batas_butir = Decimal(str(s.get("skor_butir_min", 0)))
                for m in per_kriteria.get(kode, []):
                    if nilai[m.butir_siklus_id] < batas_butir:
                        gagal.append(
                            {
                                "syarat": "skor_butir_min",
                                "butir": m.kode,
                                "nilai": float(nilai[m.butir_siklus_id]),
                                "ambang": float(batas_butir),
                            }
                        )
            if catat:
                syarat_gagal.extend(gagal)
            return not gagal

        def dalam_rentang(p: PeringkatDef) -> bool:
            if p.nilai_akhir_min is not None and akhir < p.nilai_akhir_min:
                return False
            return not (p.nilai_akhir_maks is not None and akhir >= p.nilai_akhir_maks)

        prediksi = _terendah(definisi.peringkat)
        for p in sorted(definisi.peringkat, key=lambda x: x.tingkat, reverse=True):
            if not dalam_rentang(p):
                continue
            # Syarat dicatat hanya untuk peringkat yang nilainya sudah mencukupi tetapi syaratnya gagal.
            if periksa_syarat(p, catat=True):
                prediksi = p
                break

        kode_syarat = {k for p in definisi.peringkat for k in (p.syarat or {}).get("kriteria", [])}
        batas_target = Decimal(str((target.syarat or {}).get("rerata_kriteria_min", 0))) if target else Decimal(0)
        for kode, bobot_kriteria in definisi.bobot_kriteria.items():
            if kode in per_kriteria:
                r = rerata(kode)
                kriteria_out[kode] = {
                    "kode": kode,
                    "rerata": float(q2(r)),
                    "bobot": float(bobot_kriteria) if bobot_kriteria is not None else None,
                    "memenuhi_syarat": (r >= batas_target) if kode in kode_syarat and target else None,
                }

        prioritas = self._prioritas(definisi, masukan, nilai, target, kode_syarat)
        return HasilPenilaian(
            nilai_akhir=q2(akhir),
            peringkat=prediksi,
            butir_belum_dinilai=belum,
            syarat_terpenuhi=not syarat_gagal,
            rincian={
                "kriteria": list(kriteria_out.values()),
                "syarat_gagal": syarat_gagal,
                "prioritas_perbaikan": prioritas,
            },
        )

    @staticmethod
    def _prioritas(
        definisi: DefinisiInstrumen,
        masukan: list[MasukanButir],
        nilai: dict[UUID, Decimal],
        target: PeringkatDef | None,
        kode_syarat: set[str],
    ) -> list[dict[str, Any]]:
        """Butir yang paling menekan peringkat: di bawah skor minimum syarat target, lalu skor terendah × bobot tertinggi."""
        skor_min = Decimal(str((target.syarat or {}).get("skor_butir_min", 0))) if target else Decimal(0)
        kandidat = []
        for m in masukan:
            s = nilai[m.butir_siklus_id]
            di_bawah = m.kriteria_kode in kode_syarat and s < skor_min
            kehilangan = (Decimal(definisi.skor_maks) - s) * (m.bobot or Decimal(0))
            if di_bawah or (s < Decimal(definisi.skor_maks) and (m.bobot or 0)):
                kandidat.append((not di_bawah, -kehilangan, m, s))
        kandidat.sort(key=lambda x: (x[0], x[1]))
        return [
            {
                "butir_siklus_id": str(m.butir_siklus_id),
                "kode": m.kode,
                "bobot": float(m.bobot) if m.bobot is not None else None,
                "skor_estimasi": float(s) if m.skor is not None else None,
                "alasan": "di_bawah_skor_minimum" if not tidak else "potensi_nilai",
            }
            for tidak, _, m, s in kandidat[:10]
        ]


class PenilaiAmbangButir:
    """Peringkat tercapai bila SEMUA ambang peringkat itu terpenuhi, kecuali bila ``syarat.toleransi`` pada
    peringkat mengizinkan sejumlah butir BUKAN syarat-perlu berada di bawah ambang. Butir yang belum dinilai
    dianggap tidak memenuhi."""

    def hitung(self, definisi: DefinisiInstrumen, masukan: list[MasukanButir], target: PeringkatDef | None) -> HasilPenilaian:
        skor = {m.butir_id: m for m in masukan}
        belum = sum(1 for m in masukan if m.skor is None)
        ambang_per_peringkat: dict[UUID, list[Any]] = {}
        for a in definisi.ambang:
            ambang_per_peringkat.setdefault(a.peringkat_id, []).append(a)

        terurut = sorted(definisi.peringkat, key=lambda p: p.tingkat, reverse=True)
        per_peringkat: list[dict[str, Any]] = []
        prediksi = _terendah(definisi.peringkat)
        terpilih = False
        for p in terurut:
            daftar = ambang_per_peringkat.get(p.id, [])
            if not daftar:  # peringkat terendah (Tidak Terakreditasi) tanpa ambang
                continue
            di_bawah = []
            for a in daftar:
                m = skor.get(a.butir_id)
                nilai = m.skor if m else None
                if nilai is None or nilai < a.skor_min:
                    di_bawah.append(
                        {
                            "kode": m.kode if m else str(a.butir_id),
                            "butir_siklus_id": str(m.butir_siklus_id) if m else None,
                            "skor_estimasi": float(nilai) if nilai is not None else None,
                            "skor_min": float(a.skor_min),
                            "is_syarat_perlu": a.is_syarat_perlu,
                        }
                    )
            toleransi = int((p.syarat or {}).get("toleransi", 0))
            gagal_syarat_perlu = [d for d in di_bawah if d["is_syarat_perlu"]]
            gagal_lain = [d for d in di_bawah if not d["is_syarat_perlu"]]
            tercapai = not gagal_syarat_perlu and len(gagal_lain) <= toleransi
            per_peringkat.append({"kode": p.kode, "nama": p.nama, "tercapai": tercapai, "butir_di_bawah_ambang": di_bawah})
            if tercapai and not terpilih:
                prediksi, terpilih = p, True
        # Prioritas: butir syarat-perlu yang gagal pada peringkat target (atau peringkat berikutnya di atas prediksi).
        sasaran = target or next((p for p in sorted(definisi.peringkat, key=lambda x: x.tingkat) if p.tingkat > prediksi.tingkat), None)
        prioritas = []
        if sasaran:
            for item in next((x["butir_di_bawah_ambang"] for x in per_peringkat if x["kode"] == sasaran.kode), []):
                prioritas.append({**item, "alasan": "syarat_perlu" if item["is_syarat_perlu"] else "di_bawah_ambang"})
            prioritas.sort(key=lambda x: (not x["is_syarat_perlu"], x["kode"]))
        return HasilPenilaian(
            nilai_akhir=None,
            peringkat=prediksi,
            butir_belum_dinilai=belum,
            syarat_terpenuhi=terpilih,
            rincian={"per_peringkat": per_peringkat, "prioritas_perbaikan": prioritas[:10]},
            catatan=["Peringkat tercapai bila semua ambang butir terpenuhi (kecuali toleransi pada syarat peringkat)."],
        )


def pilih_penilai(definisi: DefinisiInstrumen) -> PenilaiPeringkat:
    """Instrumen dengan nilai akhir berbobot memakai ``PenilaiBerbobot``; selain itu ambang per butir."""
    return PenilaiBerbobot() if definisi.nilai_akhir_maks is not None else PenilaiAmbangButir()
