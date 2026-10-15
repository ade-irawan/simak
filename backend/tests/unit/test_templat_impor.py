"""Templat impor diturunkan dari skema yang sama dengan validasi impor: baris contohnya harus lolos validasi."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.modules.tridharma.registry import SPEC_LIST
from app.modules.tridharma.service import LayananDataInti
from app.modules.tridharma.templat import kolom_impor


@pytest.mark.parametrize("spec", SPEC_LIST, ids=lambda s: s.path)
def test_baris_contoh_templat_lolos_validasi_skema(spec):
    kolom = kolom_impor(spec, kode_prodi="KIMIA", kode_tahun="2025/2026")
    nama = [k.nama for k in kolom]
    assert len(nama) == len(set(nama)), "judul kolom tidak boleh ganda"
    assert "prodi_id" not in nama and "tahun_akademik_id" not in nama, "rujukan harus berupa kode yang bisa dibaca"
    svc = object.__new__(LayananDataInti)
    svc.spec = spec
    baris = svc._siapkan_baris({k.nama: k.contoh for k in kolom}, {"KIMIA": uuid4()}, {"2025/2026": uuid4()})
    spec.skema.model_validate(baris)  # tidak boleh melempar
    # kolom wajib pada skema harus muncul sebagai kolom wajib di templat (kecuali yang tidak dapat diimpor datar)
    wajib_templat = {k.nama for k in kolom if k.wajib}
    for n, medan in spec.skema.model_fields.items():
        if medan.is_required() and n in nama:
            assert n in wajib_templat
