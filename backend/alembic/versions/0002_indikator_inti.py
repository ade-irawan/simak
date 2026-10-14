"""Data konfigurasi: definisi indikator inti lintas instrumen (dasar benchmarking)

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

INDIKATOR = [
    (
        "rasio_mahasiswa_dosen",
        "Rasio mahasiswa aktif per dosen tetap",
        "mahasiswa/dosen",
        "Mahasiswa aktif (reguler+transfer) dibagi FTE dosen tetap prodi.",
        False,
    ),
    (
        "publikasi_per_dosen",
        "Publikasi per dosen tetap",
        "publikasi/dosen",
        "Jumlah publikasi terbobot atribusi prodi dibagi FTE dosen tetap.",
        True,
    ),
    (
        "dana_penelitian_per_dosen",
        "Dana penelitian per dosen tetap",
        "rupiah/dosen",
        "Dana penelitian terbobot atribusi dibagi FTE dosen tetap.",
        True,
    ),
    ("dana_pkm_per_dosen", "Dana PkM per dosen tetap", "rupiah/dosen", "Dana PkM terbobot atribusi dibagi FTE dosen tetap.", True),
    ("persen_dosen_s3", "Persentase dosen tetap berpendidikan S3", "persen", "FTE dosen tetap S3 dibagi FTE dosen tetap.", True),
    (
        "persen_dosen_bersertifikat",
        "Persentase dosen tetap bersertifikat pendidik",
        "persen",
        "FTE dosen tetap bersertifikat pendidik dibagi FTE dosen tetap.",
        True,
    ),
    (
        "persen_dosen_jabatan_tinggi",
        "Persentase dosen tetap Lektor Kepala/Guru Besar",
        "persen",
        "FTE dosen tetap berjabatan Lektor Kepala atau Guru Besar dibagi FTE dosen tetap.",
        True,
    ),
    ("ipk_rata_lulusan", "IPK rata-rata lulusan", "skala 4", "Rata-rata IPK lulusan pada tahun akademik.", True),
    ("persen_lulus_tepat_waktu", "Persentase lulusan tepat waktu", "persen", "Lulusan tepat waktu dibagi jumlah lulusan.", True),
    (
        "kerja_sama_internasional",
        "Jumlah kerja sama internasional aktif",
        "kerja sama",
        "Kerja sama tingkat internasional yang berlaku pada tahun akademik.",
        True,
    ),
]


def upgrade() -> None:
    bind = op.get_bind()
    for kode, nama, satuan, deskripsi, naik in INDIKATOR:
        bind.exec_driver_sql(
            "INSERT INTO indikator_inti (kode, nama, satuan, deskripsi, makin_tinggi_makin_baik) VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (kode) DO NOTHING",
            (kode, nama, satuan, deskripsi, naik),
        )


def downgrade() -> None:
    op.get_bind().exec_driver_sql("DELETE FROM indikator_inti WHERE kode = ANY(%s)", ([i[0] for i in INDIKATOR],))
