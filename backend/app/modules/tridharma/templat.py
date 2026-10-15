"""Templat impor data inti, diturunkan dari skema Pydantic yang sama dengan yang memvalidasi impor,
sehingga daftar kolom, kolom wajib, dan pilihan nilai tidak pernah menyimpang dari aturan sebenarnya."""

from __future__ import annotations

import types
from datetime import date
from decimal import Decimal
from typing import Any, Literal, Union, get_args, get_origin
from uuid import UUID

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from app.infrastructure.documents.templat_impor import KolomImpor
from app.modules.tridharma.registry import Spec

#: Kolom acuan prodi dan tahun akademik dipakai lewat kode yang mudah dibaca, bukan UUID.
KOLOM_PRODI = ("prodi_id", "prodi_ids", "atribusi_prodi")
CONTOH_KHAS: dict[str, Any] = {
    "email": "nama@kampus.ac.id",
    "doi": "10.1234/contoh.2024.001",
    "url": "https://contoh.ac.id/dokumen",
    "nidn": "0012345678",
    "nuptk": "1234567890123456",
    "bidang_pendidikan": "TRUE",  # kerja sama wajib punya minimal satu bidang
}


def _buka(anotasi: Any) -> Any:
    """Optional[X] → X."""
    if get_origin(anotasi) in (Union, types.UnionType):
        sisa = [a for a in get_args(anotasi) if a is not type(None)]
        if len(sisa) == 1:
            return sisa[0]
    return anotasi


def _batas(medan: FieldInfo) -> str:
    bagian = []
    for m in medan.metadata:
        for atribut, teks in (("ge", "≥ {}"), ("gt", "> {}"), ("le", "≤ {}"), ("lt", "< {}"), ("min_length", "minimal {} karakter")):
            nilai = getattr(m, atribut, None)
            if nilai is not None:
                bagian.append(teks.format(nilai))
    return ", ".join(bagian)


def _contoh_bulat(medan: FieldInfo) -> int:
    ge = next((m.ge for m in medan.metadata if getattr(m, "ge", None) is not None), None)
    le = next((m.le for m in medan.metadata if getattr(m, "le", None) is not None), None)
    contoh = 1
    if ge is not None and contoh < ge:
        contoh = 2024 if ge <= 2024 and (le is None or 2024 <= le) else ge
    return contoh


def _tipe_dan_contoh(nama: str, medan: FieldInfo) -> tuple[str, Any, str]:
    dasar = _buka(medan.annotation)
    batas = _batas(medan)
    if get_origin(dasar) is Literal:
        pilihan = [str(v) for v in get_args(dasar)]
        tipe, contoh, ket = "pilihan: " + " | ".join(pilihan), pilihan[0], "Tulis persis salah satu pilihan."
    elif dasar is bool:
        tipe, contoh, ket = "TRUE / FALSE", "FALSE", ""
    elif dasar is int:
        tipe, contoh, ket = "bilangan bulat", _contoh_bulat(medan), batas
    elif dasar is Decimal:
        tipe, contoh, ket = "angka (desimal pakai titik)", 1, batas
    elif dasar is date:
        tipe, contoh, ket = "tanggal (YYYY-MM-DD)", "2024-01-31", ""
    else:
        tipe, contoh, ket = "teks", f"Contoh {nama.replace('_', ' ')}", batas
    return tipe, CONTOH_KHAS.get(nama, contoh), ket


def kolom_impor(spec: Spec, *, kode_prodi: str, kode_tahun: str) -> list[KolomImpor]:
    """Kolom berurutan sesuai skema. Medan bersarang (daftar dosen/penulis/afiliasi) dan rujukan UUID lain tidak
    dapat diimpor lewat berkas datar sehingga dilewati."""
    kolom: list[KolomImpor] = []
    for nama, medan in spec.skema.model_fields.items():
        if nama in KOLOM_PRODI:
            if any(k.nama == "prodi_kode" for k in kolom):
                continue
            jamak = nama != "prodi_id"
            wajib = nama == "prodi_id" and medan.is_required()
            ket = "Kode prodi (lihat lembar 'referensi')."
            if jamak:
                ket += " Beberapa prodi dipisah koma; kosong = prodi Anda sendiri."
            elif not wajib:
                ket += " Kosong = tingkat fakultas/UPPS (Staf Fakultas)."
            kolom.append(KolomImpor("prodi_kode", wajib, "kode prodi", ket, kode_prodi))
            continue
        if nama == "tahun_akademik_id":
            kolom.append(
                KolomImpor(
                    "tahun_akademik",
                    medan.is_required(),
                    "kode tahun akademik",
                    "Kode tahun akademik (lihat lembar 'referensi').",
                    kode_tahun,
                )
            )
            continue
        dasar = _buka(medan.annotation)
        isi_daftar = get_args(dasar)[0] if get_origin(dasar) is list and get_args(dasar) else None
        if (
            dasar is UUID
            or (get_origin(dasar) is list and isi_daftar is not str)
            or (isinstance(dasar, type) and issubclass(dasar, BaseModel))
        ):
            continue
        tipe, contoh, ket = _tipe_dan_contoh(nama, medan)
        if medan.description:
            ket = f"{medan.description}. {ket}".strip()
        if not medan.is_required() and medan.default is not PydanticUndefined and medan.default not in (None, ""):
            bawaan = str(medan.default).upper() if isinstance(medan.default, bool) else medan.default
            ket = f"{ket + '.' if ket and not ket.endswith('.') else ket} Bawaan bila kosong: {bawaan}.".strip()
        kolom.append(KolomImpor(nama, medan.is_required(), tipe, ket, contoh))
    return kolom
