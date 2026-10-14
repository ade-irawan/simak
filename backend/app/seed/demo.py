"""Data contoh untuk PENGEMBANGAN. Tidak dipakai di produksi.

Instrumen demo dimuat sebagai versi terpisah (``3.1-demo`` dan ``2.1-demo``) agar tidak bercampur dengan instrumen resmi
yang nanti diimpor Staf Admin Fakultas. Teks butir bersifat generik (bukan isi resmi IAPS); struktur kriteria, jumlah
indikator LAMSAMA (35), bobot LAM INFOKOM (total 400), dan peta tingkat-kriteria mengikuti SKPL §2.2.
"""

from __future__ import annotations

import random
import secrets
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select

import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.permissions import Peran
from app.core.security import hash_sandi
from app.core.unit_of_work import UnitOfWork
from app.modules.bukti.domain.entities import AksesTautan, JenisBukti, StatusCekBukti
from app.modules.bukti.infrastructure.models import Bukti, BuktiButir, BuktiProdi
from app.modules.dokumen_eksternal.api.schemas import DokumenIn, IndikatorIn
from app.modules.dokumen_eksternal.application.layanan import LayananDokumenEksternal
from app.modules.instrumen.domain.entities import JenisEntitas as JE
from app.modules.instrumen.domain.entities import JenisIpo, StatusInstrumen, TahapPpepp
from app.modules.instrumen.infrastructure.models import (
    InstrumenButir,
    InstrumenButirAmbang,
    InstrumenKriteria,
    InstrumenPeringkat,
    InstrumenVersi,
    PemetaanButir,
)
from app.modules.pengguna import public as pengguna_public
from app.modules.pengguna.infrastructure.models import Pengguna, PenugasanPeran
from app.modules.ppepp.api.schemas import ButirStandarIn, PenetapanIn, SiklusPpeppIn, StandarIn
from app.modules.ppepp.application.layanan import LayananPpepp
from app.modules.referensi.models import Lam, Prodi, TahunAkademik
from app.modules.siklus.api.schemas import SiklusIn
from app.modules.siklus.application.layanan import LayananSiklus
from app.modules.siklus.domain.entities import PengelolaButir, StatusKelengkapan
from app.modules.siklus.infrastructure.models import ButirSiklus, NarasiButir
from app.modules.tridharma import models as m

NAMA_LAMSAMA = {
    1: "Visi, misi, tujuan, dan strategi (VMTS)",
    2: "Tata pamong dan tata kelola",
    3: None,
    4: "Audit mutu internal dan tindak lanjutnya",
    5: "Kepuasan pemangku kepentingan",
    6: "Penerimaan mahasiswa baru",
    7: "Layanan kemahasiswaan",
    15: "Pembiayaan pendidikan",
    16: "Dosen tetap",
    17: "Kualifikasi dan jabatan dosen",
    18: "Tenaga kependidikan",
    19: "Kerja sama pendidikan",
    20: "Sarana dan prasarana pembelajaran",
    21: "Penelitian dosen dan mahasiswa",
    22: "Penelitian — hibah dan pendanaan",
    23: "Sarana penelitian",
    24: "Pembiayaan penelitian",
    25: "Kerja sama penelitian",
    26: "Pengabdian kepada masyarakat",
    27: "Pengabdian — hibah dan pendanaan",
    28: "Sarana dan pembiayaan PkM",
    29: "Luaran PkM",
    30: "Prestasi mahasiswa dan kompetensi lulusan",
    31: "Tracer study lulusan",
    32: "Publikasi ilmiah",
    33: "Prosiding dan karya ilmiah lain",
    34: "Kekayaan intelektual (HKI) dan luaran lain",
    35: "Analisis capaian kinerja dan program pengembangan",
}
KRITERIA_LAMSAMA = [
    ("A", range(1, 8)),
    ("B", range(8, 21)),
    ("C", range(21, 26)),
    ("D", range(26, 30)),
    ("E", range(30, 35)),
    ("F", range(35, 36)),
]

# nomor indikator LAMSAMA → [(sumber, aturan)]
PETA_LAMSAMA: dict[int, list[tuple[JE, dict[str, Any]]]] = {
    3: [(JE.TAHAPAN_PPEPP, {})],
    4: [(JE.TAHAPAN_PPEPP, {"filter": {"tahap": ["evaluasi", "pengendalian"]}})],
    5: [(JE.INDIKATOR_EKSTERNAL, {})],
    6: [(JE.MAHASISWA_STATISTIK, {})],
    7: [(JE.MAHASISWA_STATISTIK, {})],
    **{n: [(JE.KURIKULUM, {"batasi_tahun": False}), (JE.MATA_KULIAH, {})] for n in range(8, 15)},
    15: [(JE.KEUANGAN, {"filter": {"arah": "penggunaan"}, "agregasi": "jumlah", "kolom": "jumlah"})],
    16: [(JE.DOSEN, {"filter": {"status_kepegawaian": "tetap"}, "agregasi": "hitung"})],
    17: [(JE.DOSEN, {})],
    19: [(JE.KERJA_SAMA, {"filter": {"bidang_pendidikan": True}, "batasi_tahun": False})],
    20: [(JE.SARANA_PRASARANA, {})],
    21: [(JE.PENELITIAN, {})],
    22: [(JE.PENELITIAN, {"agregasi": "jumlah", "kolom": "jumlah_dana"})],
    23: [(JE.SARANA_PRASARANA, {"filter": {"jenis": "laboratorium"}})],
    24: [(JE.KEUANGAN, {"filter": {"kategori": "penelitian"}, "agregasi": "jumlah", "kolom": "jumlah"})],
    25: [(JE.KERJA_SAMA, {"filter": {"bidang_penelitian": True}, "batasi_tahun": False})],
    26: [(JE.PKM, {})],
    27: [(JE.PKM, {"agregasi": "jumlah", "kolom": "jumlah_dana"})],
    28: [(JE.KEUANGAN, {"filter": {"kategori": "pkm"}, "agregasi": "jumlah", "kolom": "jumlah"})],
    29: [(JE.PKM, {})],
    30: [(JE.LULUSAN_STATISTIK, {})],
    31: [(JE.INDIKATOR_EKSTERNAL, {})],
    32: [(JE.PUBLIKASI, {"filter": {"jenis": "jurnal"}})],
    33: [(JE.PUBLIKASI, {"filter": {"jenis": "prosiding"}})],
    34: [(JE.PUBLIKASI, {"filter": {"jenis": ["paten", "paten_sederhana", "hak_cipta"]}})],
}

# kriteria LAM INFOKOM → (nama butir generik, bobot[]) dan sumber pemetaan bergilir
BUTIR_INFOKOM: dict[str, list[int]] = {
    "A": [1],
    "B": [1],
    "1": [2, 3, 3, 2],
    "2": [4, 4, 4, 5, 5, 4, 4],
    "3": [3, 3, 4, 4, 4],
    "4": [4, 4, 4, 3],
    "5": [2, 3, 3, 2],
    "6": [3, 3, 2, 2],
    "S": [2, 3],
}
SUMBER_INFOKOM: dict[str, list[JE]] = {
    "1": [JE.TAHAPAN_PPEPP],
    "2": [JE.KURIKULUM, JE.DOSEN, JE.MAHASISWA_STATISTIK, JE.LULUSAN_STATISTIK, JE.SARANA_PRASARANA, JE.KEUANGAN, JE.INDIKATOR_EKSTERNAL],
    "3": [JE.PENELITIAN, JE.PUBLIKASI, JE.PENELITIAN, JE.KERJA_SAMA, JE.KEUANGAN],
    "4": [JE.PKM, JE.PKM, JE.KERJA_SAMA, JE.KEUANGAN],
    "5": [JE.KEUANGAN, JE.SARANA_PRASARANA, JE.TAHAPAN_PPEPP],
    "6": [JE.KERJA_SAMA, JE.PUBLIKASI, JE.PENELITIAN],
    "S": [JE.KURIKULUM, JE.MATA_KULIAH],
}


async def _pastikan_tahun(session: Any) -> list[TahunAkademik]:
    ada = (await session.execute(select(TahunAkademik).order_by(TahunAkademik.tanggal_mulai))).scalars().all()
    if ada:
        return list(ada)
    for t in (2023, 2024, 2025):
        session.add(
            TahunAkademik(kode=f"{t}/{t + 1}", tanggal_mulai=date(t, 8, 1), tanggal_selesai=date(t + 1, 7, 31), is_aktif=(t == 2025))
        )
    await session.flush()
    return list((await session.execute(select(TahunAkademik).order_by(TahunAkademik.tanggal_mulai))).scalars())


async def _salin_struktur(session: Any, lam_kode: str, kode_asal: str, kode_demo: str, nama: str) -> InstrumenVersi:
    """Versi demo = salinan kriteria & peringkat versi resmi hasil seed.sql (tanpa butir)."""
    asal = (
        await session.execute(
            select(InstrumenVersi)
            .join(Lam, Lam.id == InstrumenVersi.lam_id)
            .where(Lam.kode == lam_kode, InstrumenVersi.kode_versi == kode_asal)
        )
    ).scalar_one()
    sudah = (
        await session.execute(select(InstrumenVersi).where(InstrumenVersi.lam_id == asal.lam_id, InstrumenVersi.kode_versi == kode_demo))
    ).scalar_one_or_none()
    if sudah:
        return sudah
    baru = InstrumenVersi(
        lam_id=asal.lam_id,
        kode_versi=kode_demo,
        nama=nama,
        jenjang=asal.jenjang,
        dasar_hukum="DATA DEMO — bukan instrumen resmi",
        status=StatusInstrumen.DRAF,
        skor_maks=asal.skor_maks,
        label_skor=asal.label_skor,
        nilai_akhir_maks=asal.nilai_akhir_maks,
    )
    session.add(baru)
    await session.flush()
    for k in (await session.execute(select(InstrumenKriteria).where(InstrumenKriteria.instrumen_versi_id == asal.id))).scalars():
        session.add(InstrumenKriteria(instrumen_versi_id=baru.id, kode=k.kode, nama=k.nama, bobot=k.bobot, urutan=k.urutan))
    for p in (await session.execute(select(InstrumenPeringkat).where(InstrumenPeringkat.instrumen_versi_id == asal.id))).scalars():
        session.add(
            InstrumenPeringkat(
                instrumen_versi_id=baru.id,
                kode=p.kode,
                nama=p.nama,
                tingkat=p.tingkat,
                masa_berlaku_tahun=p.masa_berlaku_tahun,
                nilai_akhir_min=p.nilai_akhir_min,
                nilai_akhir_maks=p.nilai_akhir_maks,
                syarat=p.syarat,
            )
        )
    await session.flush()
    return baru


async def _butir_lamsama(session: Any, versi: InstrumenVersi, dekan_id: Any) -> None:
    kriteria = {
        k.kode: k
        for k in (await session.execute(select(InstrumenKriteria).where(InstrumenKriteria.instrumen_versi_id == versi.id))).scalars()
    }
    peringkat = {
        p.kode: p
        for p in (await session.execute(select(InstrumenPeringkat).where(InstrumenPeringkat.instrumen_versi_id == versi.id))).scalars()
    }
    teks3 = (
        "Keterlaksanaan Sistem Penjaminan Mutu Internal (akademik dan non akademik) pendidikan, penelitian, dan PkM "
        "yang merupakan penerapan siklus PPEPP, dibuktikan dengan keberadaan 5 aspek"
    )
    for kode_k, rentang in KRITERIA_LAMSAMA:
        for n in rentang:
            elemen = teks3 if n == 3 else f"Indikator {n} — {NAMA_LAMSAMA.get(n) or 'Kebijakan dan pelaksanaan'} (contoh demo)"
            if n in (8, 9, 10, 11, 12, 13, 14):
                elemen = f"Indikator {n} — Kurikulum dan pembelajaran, aspek {n - 7} (contoh demo)"
            b = InstrumenButir(
                instrumen_versi_id=versi.id,
                kriteria_id=kriteria[kode_k].id,
                kode=str(n),
                nomor_urut=n,
                elemen=elemen,
                skema_narasi=[{"bagian": "utama", "judul": "Uraian pemenuhan indikator"}]
                if n != 35
                else [
                    {"bagian": "analisis", "judul": "Analisis capaian kinerja"},
                    {"bagian": "program", "judul": "Penetapan program pengembangan"},
                ],
            )
            session.add(b)
            await session.flush()
            for kode_p, skor_min in (
                ("terakreditasi", 3 if n == 3 else 2),
                ("unggul_2", 4 if n == 3 else 3),
                ("unggul_5", 4 if n == 3 else 3),
            ):
                session.add(
                    InstrumenButirAmbang(
                        instrumen_butir_id=b.id, peringkat_id=peringkat[kode_p].id, skor_min=skor_min, is_syarat_perlu=n in (3, 4)
                    )
                )
            for sumber, aturan in PETA_LAMSAMA.get(n, []):
                session.add(
                    PemetaanButir(
                        instrumen_butir_id=b.id, sumber=sumber, aturan=aturan, is_aktif=True, disetujui_oleh=dekan_id, created_by=dekan_id
                    )
                )


async def _butir_infokom(session: Any, versi: InstrumenVersi, dekan_id: Any) -> None:
    kriteria = {
        k.kode: k
        for k in (await session.execute(select(InstrumenKriteria).where(InstrumenKriteria.instrumen_versi_id == versi.id))).scalars()
    }
    ipo = [JenisIpo.INPUT, JenisIpo.PROSES, JenisIpo.OUTPUT]
    tahap = [TahapPpepp.PENETAPAN, TahapPpepp.PELAKSANAAN, TahapPpepp.EVALUASI, TahapPpepp.PENGENDALIAN, TahapPpepp.PENINGKATAN]
    for kode_k, bobot_list in BUTIR_INFOKOM.items():
        nama_k = kriteria[kode_k].nama
        for i, bobot in enumerate(bobot_list, start=1):
            kode = {"A": "A.1", "B": "B.1"}.get(kode_k, f"{kode_k}.{i}")
            elemen = f"{nama_k} — butir {i} (contoh demo)" if kode_k not in ("A", "B") else f"{nama_k} (contoh demo)"
            if kode == "1.1":
                elemen = (
                    "Kebijakan, standar, dan indikator terkait sistem tata kelola internal UPPS dan/atau PT berikut SOP, "
                    "mencakup administrasi akademik, keuangan, SDM, dan aspek lain dalam siklus PPEPP"
                )
            b = InstrumenButir(
                instrumen_versi_id=versi.id,
                kriteria_id=kriteria[kode_k].id,
                kode=kode,
                nomor_urut=i,
                elemen=elemen,
                jenis_ipo=ipo[(i - 1) % 3] if kode_k not in ("A", "B") else None,
                tahap_ppepp=tahap[(i - 1) % 5] if kode_k not in ("A", "B", "S") else None,
                bobot=bobot,
                skema_narasi=[{"bagian": "utama", "judul": "Uraian"}]
                if kode_k not in ("A", "B")
                else [
                    {"bagian": "analisis", "judul": "Analisis lingkungan makro dan mikro"},
                    {"bagian": "peluang_ancaman", "judul": "Peluang dan ancaman"},
                ],
            )
            session.add(b)
            await session.flush()
            sumber = SUMBER_INFOKOM.get(kode_k, [])
            if sumber:
                for s in {sumber[(i - 1) % len(sumber)], sumber[i % len(sumber)]}:
                    session.add(
                        PemetaanButir(
                            instrumen_butir_id=b.id, sumber=s, aturan={}, is_aktif=True, disetujui_oleh=dekan_id, created_by=dekan_id
                        )
                    )


async def jalankan() -> None:
    cfg = get_settings()
    sandi = cfg.demo_password or (secrets.token_urlsafe(9) + "A1")
    rnd = random.Random(42)
    async with get_session_factory()() as session:
        if (await session.execute(select(Prodi.id).limit(1))).first() is None:
            raise SystemExit("Prodi belum ada. Jalankan `python -m app.cli seed-referensi` lebih dulu.")
        tahun = await _pastikan_tahun(session)
        prodi = {p.kode: p for p in (await session.execute(select(Prodi))).scalars()}

        # ---------------- akun ----------------
        akun: list[tuple[str, str, Peran, str | None]] = [
            ("dekan@simak.test", "Dekan Demo", Peran.DEKAN, None),
            ("staf.fakultas@simak.test", "Staf Fakultas Demo", Peran.STAF_FAKULTAS, None),
            ("admin.it@simak.test", "Admin IT Demo", Peran.ADMIN_IT, None),
        ]
        for kode in ("ILKOM", "KIMIA", "AKTUARIA"):
            akun += [
                (f"kaprodi.{kode.lower()}@simak.test", f"Kaprodi {prodi[kode].nama}", Peran.KAPRODI, kode),
                (f"staf.{kode.lower()}@simak.test", f"Staf Prodi {prodi[kode].nama}", Peran.STAF_PRODI, kode),
            ]
        pengguna: dict[str, Pengguna] = {}
        akun_baru = 0
        for email, nama, peran, kode in akun:
            p = (await session.execute(select(Pengguna).where(Pengguna.email == email))).scalar_one_or_none()
            if p is None:
                akun_baru += 1
                p = Pengguna(email=email, nama=nama, password_hash=hash_sandi(sandi), wajib_ganti_sandi=False)
                session.add(p)
                await session.flush()
                session.add(PenugasanPeran(pengguna_id=p.id, peran=peran, prodi_id=prodi[kode].id if kode else None))
            pengguna[email] = p
        asesor = (await session.execute(select(Pengguna).where(Pengguna.email == "asesor.ilkom@simak.test"))).scalar_one_or_none()
        if asesor is None:
            session.add(
                Pengguna(email="asesor.ilkom@simak.test", nama="Asesor Demo", password_hash=hash_sandi(sandi), wajib_ganti_sandi=False)
            )
        await session.flush()
        dekan = pengguna["dekan@simak.test"]

        # ---------------- instrumen demo (aktif) ----------------
        ada_demo = (
            (await session.execute(select(InstrumenVersi).where(InstrumenVersi.kode_versi.in_(["3.1-demo", "2.1-demo"])))).scalars().all()
        )
        if not ada_demo:
            v_sama = await _salin_struktur(session, "LAMSAMA", "3.1", "3.1-demo", "IAPS 3.1 LAMSAMA — DEMO (contoh, bukan instrumen resmi)")
            v_info = await _salin_struktur(
                session, "LAM_INFOKOM", "2.1", "2.1-demo", "IAPS 2.1 LAM INFOKOM — DEMO (contoh, bukan instrumen resmi)"
            )
            await _butir_lamsama(session, v_sama, dekan.id)
            await _butir_infokom(session, v_info, dekan.id)
            for v in (v_sama, v_info):
                v.status, v.disetujui_oleh, v.disetujui_pada, v.berlaku_mulai = StatusInstrumen.AKTIF, dekan.id, date.today(), date.today()
        await session.commit()

        # ---------------- data inti Tridharma ----------------
        if (await session.execute(select(m.Dosen.id).limit(1))).first() is None:
            await _isi_tridharma(session, prodi, tahun, pengguna, rnd)
            await session.commit()

        # ---------------- siklus akreditasi per prodi ----------------
        pemanggil = await pengguna_public.muat_pemanggil(session, dekan.id)
        assert pemanggil is not None
        ts = tahun[-1]
        for kode in ("ILKOM", "KIMIA", "AKTUARIA"):
            from app.modules.siklus.infrastructure.models import SiklusAkreditasi

            if (await session.execute(select(SiklusAkreditasi.id).where(SiklusAkreditasi.prodi_id == prodi[kode].id))).first():
                continue
            svc = LayananSiklus(UnitOfWork(session))
            hasil = await svc.buka(
                pemanggil,
                SiklusIn(
                    prodi_id=prodi[kode].id,
                    nama=f"Akreditasi {prodi[kode].nama} {ts.kode}",
                    ts_tahun_akademik_id=ts.id,
                    tanggal_mulai=date.today() - timedelta(days=30),
                    tenggat=date.today() + timedelta(days={"ILKOM": 75, "KIMIA": 140, "AKTUARIA": 20}[kode]),
                    target_peringkat_kode="unggul_3" if kode == "ILKOM" else "unggul_2",
                    instrumen_versi_id=(
                        await session.execute(
                            select(InstrumenVersi.id).where(InstrumenVersi.kode_versi == ("2.1-demo" if kode == "ILKOM" else "3.1-demo"))
                        )
                    ).scalar_one(),
                ),
            )
            await _isi_progres(session, hasil["id"], pengguna, kode, rnd)
            await session.commit()

        # ---------------- PPEPP ----------------
        if (await session.execute(select(m.Dosen.id).limit(1))).first() is not None:
            await _isi_ppepp(session, pemanggil, tahun[-1])

        await _isi_dokumen_eksternal(session, pemanggil, prodi, tahun[-1], pengguna)

    print("\n=== Akun demo ===")
    for email, nama, peran, _kode in akun + [("asesor.ilkom@simak.test", "Asesor Demo", Peran.ASESOR, None)]:
        print(f"  {peran.value:14s} {email:34s} {nama}")
    if akun_baru:
        print(f"  Kata sandi (sama untuk semua akun, tampil SEKALI ini saja): {sandi}")
    else:
        print(
            "  Akun sudah ada sebelumnya: kata sandi TIDAK diubah. Untuk memulai ulang dengan sandi baru jalankan `make reset` lalu ulangi."
        )
    print("  Catatan    : asesor belum memiliki penugasan; Dekan mengaktifkannya setelah laporan prodi disetujui.\n")


async def _isi_tridharma(
    session: Any, prodi: dict[str, Prodi], tahun: list[TahunAkademik], pengguna: dict[str, Pengguna], rnd: random.Random
) -> None:
    pembuat = pengguna["dekan@simak.test"].id
    jabatan = ["asisten_ahli", "lektor", "lektor", "lektor_kepala", "guru_besar", "asisten_ahli"]
    pendidikan = ["s3", "s3", "s2", "s3", "s3", "s2"]
    for kode, p in prodi.items():
        dosen_ids = []
        for i in range(6):
            d = m.Dosen(
                nidn=f"{kode[:2]}{rnd.randint(10**7, 10**8 - 1)}",
                nama=f"Dr. Contoh {kode.title()} {chr(65 + i)}",
                pendidikan_tertinggi=pendidikan[i],
                jabatan_akademik=jabatan[i],
                status_kepegawaian="tetap",
                punya_sertifikat_pendidik=i % 3 != 2,
                bidang_keahlian="Demo",
                status_data=m.StatusData.TERVERIFIKASI,
                created_by=pembuat,
            )
            session.add(d)
            await session.flush()
            dosen_ids.append(d.id)
            for t in tahun:
                session.add(
                    m.DosenProdi(
                        dosen_id=d.id,
                        prodi_id=p.id,
                        tahun_akademik_id=t.id,
                        jenis="homebase",
                        proporsi_beban=Decimal(1),
                        sks_diampu=Decimal(12),
                    )
                )
        for i, t in enumerate(tahun):
            session.add(
                m.MahasiswaStatistik(
                    prodi_id=p.id,
                    tahun_akademik_id=t.id,
                    daya_tampung=80,
                    pendaftar=300 + 40 * i,
                    lulus_seleksi=120,
                    maba_reguler=75 + i,
                    maba_transfer=2,
                    aktif_reguler=280 + 10 * i,
                    aktif_transfer=6,
                    mahasiswa_asing=1,
                    status_data=m.StatusData.TERVERIFIKASI,
                    created_by=pembuat,
                )
            )
            session.add(
                m.LulusanStatistik(
                    prodi_id=p.id,
                    tahun_akademik_id=t.id,
                    jumlah_lulusan=60 + i * 3,
                    ipk_min=Decimal("2.60"),
                    ipk_rata=Decimal("3.35"),
                    ipk_maks=Decimal("3.95"),
                    masa_studi_rata_tahun=Decimal("4.1"),
                    lulus_tepat_waktu=40 + 2 * i,
                    status_data=m.StatusData.TERVERIFIKASI,
                    created_by=pembuat,
                )
            )
            for arah, kat, jml in (
                ("perolehan", "operasional_pendidikan", 4_000_000_000),
                ("penggunaan", "operasional_pendidikan", 3_600_000_000),
                ("penggunaan", "penelitian", 450_000_000 + i * 50_000_000),
                ("penggunaan", "pkm", 180_000_000 + i * 20_000_000),
            ):
                session.add(
                    m.Keuangan(
                        prodi_id=p.id,
                        tahun_akademik_id=t.id,
                        arah=arah,
                        kategori=kat,
                        jumlah=Decimal(jml),
                        status_data=m.StatusData.DRAFT,
                        created_by=pembuat,
                    )
                )
        kur = m.Kurikulum(
            prodi_id=p.id, nama=f"Kurikulum {p.nama} 2022", tahun_berlaku=2022, status_data=m.StatusData.TERVERIFIKASI, created_by=pembuat
        )
        session.add(kur)
        await session.flush()
        for j in range(1, 9):
            session.add(
                m.MataKuliah(
                    kurikulum_id=kur.id,
                    kode=f"{kode[:3]}{100 + j}",
                    nama=f"Mata kuliah contoh {j}",
                    sks=Decimal(3),
                    semester=(j + 1) // 2,
                    jenis="wajib" if j < 7 else "pilihan",
                    ada_rps=True,
                )
            )
        for j, jenis in enumerate(["penelitian", "penelitian", "penelitian", "pkm", "pkm"]):
            t = tahun[j % len(tahun)]
            k = m.KegiatanTridharma(
                jenis=jenis,
                judul=f"{jenis.upper()} contoh {kode} #{j + 1}",
                tahun_akademik_id=t.id,
                sumber_dana=["dalam_negeri", "pt_mandiri", "luar_negeri"][j % 3],
                jumlah_dana=Decimal(rnd.randint(30, 150) * 1_000_000),
                jumlah_mahasiswa=2,
                status_data=m.StatusData.TERVERIFIKASI,
                created_by=pembuat,
            )
            session.add(k)
            await session.flush()
            session.add(m.KegiatanProdi(kegiatan_id=k.id, prodi_id=p.id, proporsi=Decimal(1)))
            session.add(m.KegiatanDosen(kegiatan_id=k.id, dosen_id=dosen_ids[j % 6], peran="ketua"))
        for j, (jenis, tingkat) in enumerate(
            [
                ("jurnal", "internasional_bereputasi"),
                ("jurnal", "nasional_terakreditasi"),
                ("jurnal", "internasional"),
                ("prosiding", "internasional"),
                ("prosiding", "nasional"),
                ("paten", "nasional"),
            ]
        ):
            t = tahun[j % len(tahun)]
            pub = m.Publikasi(
                judul=f"Publikasi contoh {kode} #{j + 1}",
                jenis=jenis,
                tingkat=tingkat,
                nama_media="Media Contoh",
                tahun_terbit=2023 + j % 3,
                tahun_akademik_id=t.id,
                doi=f"10.9999/demo.{kode.lower()}.{j + 1}",
                jumlah_sitasi=rnd.randint(0, 20),
                status_data=m.StatusData.TERVERIFIKASI,
                created_by=pembuat,
            )
            session.add(pub)
            await session.flush()
            session.add(m.PublikasiProdi(publikasi_id=pub.id, prodi_id=p.id, proporsi=Decimal(1)))
            session.add(m.PublikasiDosen(publikasi_id=pub.id, dosen_id=dosen_ids[j % 6], urutan_penulis=1, is_korespondensi=True))
        ks = m.KerjaSama(
            nama_mitra=f"Mitra Contoh {kode}",
            tingkat="internasional" if kode == "ILKOM" else "nasional",
            judul_kegiatan="Kolaborasi riset dan magang",
            bidang_pendidikan=True,
            bidang_penelitian=True,
            tanggal_mulai=date(2024, 1, 1),
            tanggal_selesai=date(2027, 12, 31),
            status_data=m.StatusData.TERVERIFIKASI,
            created_by=pembuat,
        )
        session.add(ks)
        await session.flush()
        session.add(m.KerjaSamaProdi(kerja_sama_id=ks.id, prodi_id=p.id))
        for nama, jenis in (("Laboratorium Dasar", "laboratorium"), ("Ruang Kuliah Utama", "ruang_kuliah")):
            sp = m.SaranaPrasarana(
                nama=f"{nama} {kode}", jenis=jenis, kapasitas=40, jumlah=2, status_data=m.StatusData.TERVERIFIKASI, created_by=pembuat
            )
            session.add(sp)
            await session.flush()
            session.add(m.SaranaProdi(sarana_id=sp.id, prodi_id=p.id))
    # data bersama fakultas
    perpus = m.SaranaPrasarana(
        nama="Perpustakaan Fakultas",
        jenis="perpustakaan",
        kapasitas=120,
        jumlah=1,
        is_bersama=True,
        status_data=m.StatusData.TERVERIFIKASI,
        created_by=pembuat,
    )
    session.add(perpus)
    await session.flush()
    for p in prodi.values():
        session.add(m.SaranaProdi(sarana_id=perpus.id, prodi_id=p.id))


async def _isi_progres(session: Any, siklus_id: Any, pengguna: dict[str, Pengguna], kode: str, rnd: random.Random) -> None:
    """Sebagian butir dikerjakan agar dasbor berisi: ILKOM ±60%, KIMIA ±35%, AKTUARIA ±80%."""
    persen = {"ILKOM": 0.6, "KIMIA": 0.35, "AKTUARIA": 0.8}[kode]
    staf_prodi = pengguna[f"staf.{kode.lower()}@simak.test"].id
    staf_fak = pengguna["staf.fakultas@simak.test"].id
    butir = (await session.execute(select(ButirSiklus).where(ButirSiklus.siklus_id == siklus_id))).scalars().all()
    butir.sort(key=lambda b: str(b.instrumen_butir_id))
    rnd.shuffle(butir)
    for i, b in enumerate(butir):
        ke_fakultas = i % 6 == 0
        b.pengelola = PengelolaButir.FAKULTAS if ke_fakultas else PengelolaButir.PRODI
        b.penanggung_jawab_id = None if i % 11 == 0 else (staf_fak if ke_fakultas else staf_prodi)
        r = rnd.random()
        if r < persen:
            b.status_kelengkapan, b.skor_estimasi = StatusKelengkapan.LENGKAP, Decimal(rnd.choice([2, 3, 3, 3, 4]))
        elif r < persen + 0.2:
            b.status_kelengkapan, b.skor_estimasi = StatusKelengkapan.DRAFT, Decimal(rnd.choice([2, 3]))
        if i < 3:
            session.add(
                NarasiButir(
                    butir_siklus_id=b.id,
                    bagian="utama",
                    isi="Narasi contoh yang diisi Kaprodi untuk demonstrasi.",
                    updated_by=pengguna[f"kaprodi.{kode.lower()}@simak.test"].id,
                )
            )
    # bukti tautan contoh pada tiga butir pertama
    prodi_id = (await session.execute(select(Prodi.id).where(Prodi.kode == kode))).scalar_one()
    for i, b in enumerate(butir[:3]):
        bk = Bukti(
            judul=f"Dokumen bukti contoh {i + 1} ({kode})",
            jenis=JenisBukti.TAUTAN,
            url="https://example.org/",
            akses_tautan=AksesTautan.PUBLIK,
            sumber="Demo",
            status_cek=StatusCekBukti.OK,
            created_by=staf_prodi,
        )
        session.add(bk)
        await session.flush()
        session.add(BuktiProdi(bukti_id=bk.id, prodi_id=prodi_id))
        session.add(BuktiButir(bukti_id=bk.id, butir_siklus_id=b.id, created_by=staf_prodi))


async def _isi_ppepp(session: Any, dekan: Any, ta: TahunAkademik) -> None:
    from app.modules.ppepp.infrastructure.models import SiklusPpepp, StandarSpm

    if (await session.execute(select(SiklusPpepp.id).limit(1))).first():
        return
    sf = await pengguna_public.muat_pemanggil(
        session, (await session.execute(select(Pengguna.id).where(Pengguna.email == "staf.fakultas@simak.test"))).scalar_one()
    )
    assert sf is not None
    svc = LayananPpepp(UnitOfWork(session))
    if (await session.execute(select(StandarSpm.id).limit(1))).first() is None:
        st = await svc.buat_standar(
            sf,
            StandarIn(kode="STD-PEN", nama="Standar Penelitian (contoh demo)", kategori="penelitian", dokumen_sumber="Dokumen SPM contoh"),
        )
        b1 = await svc.tambah_butir_standar(
            sf,
            st["id"],
            ButirStandarIn(
                nomor="STD-PEN-03",
                pernyataan="Setiap dosen tetap menghasilkan publikasi ilmiah pada jurnal bereputasi.",
                indikator="Rata-rata publikasi jurnal per dosen tetap per tahun",
                target_default="1",
                satuan="publikasi/dosen/tahun",
            ),
        )
        b2 = await svc.tambah_butir_standar(
            sf,
            st["id"],
            ButirStandarIn(
                nomor="STD-PEN-05",
                pernyataan="Program studi mengalokasikan dana penelitian yang memadai.",
                indikator="Dana penelitian per dosen tetap",
                target_default="10000000",
                satuan="rupiah/dosen",
            ),
        )
        await svc.validasi_standar(dekan, st["id"])
    else:
        return
    sk = await svc.buat_siklus(
        dekan,
        SiklusPpeppIn(nama=f"PPEPP {ta.kode}", tahun_akademik_id=ta.id, tanggal_mulai=ta.tanggal_mulai, tanggal_selesai=ta.tanggal_selesai),
    )
    await svc.tambah_penetapan(
        dekan,
        sk["id"],
        PenetapanIn(
            butir_standar_id=b1["id"],
            nomor_butir="STD-PEN-03",
            isi=b1["pernyataan"],
            indikator=b1["indikator"],
            target_nilai=Decimal("1.0"),
            target_satuan="publikasi/dosen/tahun",
            periode_mulai=ta.tanggal_mulai,
            periode_selesai=ta.tanggal_selesai,
        ),
    )
    await svc.tambah_penetapan(
        dekan,
        sk["id"],
        PenetapanIn(
            butir_standar_id=b2["id"],
            nomor_butir="STD-PEN-05",
            isi=b2["pernyataan"],
            indikator=b2["indikator"],
            target_nilai=Decimal("10000000"),
            target_satuan="rupiah/dosen",
            periode_mulai=ta.tanggal_mulai,
            periode_selesai=ta.tanggal_selesai,
        ),
    )
    await svc.tetapkan(dekan, sk["id"])
    await session.commit()


async def _isi_dokumen_eksternal(
    session: Any, dekan: Any, prodi: dict[str, Prodi], ta: TahunAkademik, pengguna: dict[str, Pengguna]
) -> None:
    from app.modules.dokumen_eksternal.infrastructure.models import DokumenEksternal

    if (await session.execute(select(DokumenEksternal.id).limit(1))).first():
        return
    sf = await pengguna_public.muat_pemanggil(session, pengguna["staf.fakultas@simak.test"].id)
    assert sf is not None
    bk = Bukti(
        judul="Laporan Tracer Study Lulusan (contoh demo)",
        jenis=JenisBukti.TAUTAN,
        url="https://example.org/",
        akses_tautan=AksesTautan.PUBLIK,
        sumber="Direktorat Kemahasiswaan",
        status_cek=StatusCekBukti.OK,
        created_by=sf.id,
    )
    session.add(bk)
    await session.flush()
    for p in prodi.values():
        session.add(BuktiProdi(bukti_id=bk.id, prodi_id=p.id))
    await session.commit()
    svc = LayananDokumenEksternal(UnitOfWork(session))
    # Hanya KIMIA & AKTUARIA yang dokumennya sudah diterima; ILKOM masih "Menunggu dokumen dari Direktorat" (EC-15).
    d = await svc.buat(
        sf,
        DokumenIn(
            jenis="tracer_study",
            judul="Laporan Tracer Study Lulusan (contoh demo)",
            tahun_akademik_id=ta.id,
            populasi=412,
            jumlah_responden=287,
            metodologi="Survei daring terhadap lulusan satu tahun setelah wisuda.",
            bukti_id=bk.id,
            diterima_pada=date.today() - timedelta(days=20),
            prodi_id=[prodi["KIMIA"].id, prodi["AKTUARIA"].id],
        ),
    )
    await svc.isi_indikator(
        sf,
        d["id"],
        [
            IndikatorIn(prodi_id=prodi[k].id, kode=kode, nama=nama, nilai=Decimal(nilai), satuan=satuan)
            for k in ("KIMIA", "AKTUARIA")
            for kode, nama, nilai, satuan in (
                ("masa_tunggu_bulan", "Masa tunggu mendapat pekerjaan pertama", "4.2", "bulan"),
                ("kesesuaian_bidang_persen", "Kesesuaian bidang kerja dengan bidang studi", "78", "persen"),
                ("kepuasan_pengguna", "Kepuasan pengguna lulusan", "3.6", "skala 4"),
            )
        ],
    )
    await session.commit()
