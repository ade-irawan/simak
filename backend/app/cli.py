"""Perintah pengelolaan: `python -m app.cli <perintah>`.

seed-referensi   Memuat db/seed.sql (fakultas, LAM, prodi, kerangka instrumen) bila basis data masih kosong. Idempoten.
buat-pengguna    Membuat akun beserta satu penugasan peran (sandi dari prompt atau SIMAK_PASSWORD).
seed-demo        Data contoh lengkap untuk pengembangan (menolak berjalan di produksi).
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys

from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.core.permissions import PERAN_PRODI, Peran


def seed_referensi() -> None:
    cfg = get_settings()
    engine = create_engine(cfg.database_url_sinkron)
    with engine.begin() as conn:
        if conn.execute(text("SELECT count(*) FROM lam")).scalar_one() > 0:
            print("Data referensi sudah ada; dilewati.")
        else:
            conn.connection.driver_connection.execute((cfg.folder_db / "seed.sql").read_text(encoding="utf-8"))
            print("db/seed.sql dimuat.")
        conn.execute(text("UPDATE fakultas SET nama = :n WHERE nama = '(isi nama fakultas)'"), {"n": cfg.fakultas_nama})


async def _buat_pengguna(email: str, nama: str, peran: Peran, prodi_kode: str | None, sandi: str) -> None:
    from sqlalchemy import select

    import app.models  # noqa: F401
    from app.core.database import get_session_factory
    from app.core.security import hash_sandi, wajib_sandi_kuat
    from app.modules.pengguna.infrastructure.models import Pengguna, PenugasanPeran
    from app.modules.referensi.models import Prodi

    wajib_sandi_kuat(sandi)
    async with get_session_factory()() as session:
        prodi_id = None
        if peran in PERAN_PRODI:
            if not prodi_kode:
                sys.exit(f"Peran {peran.value} membutuhkan --prodi (kode prodi).")
            prodi_id = (await session.execute(select(Prodi.id).where(Prodi.kode == prodi_kode.upper()))).scalar_one_or_none()
            if prodi_id is None:
                sys.exit(f"Prodi '{prodi_kode}' tidak ditemukan. Jalankan seed-referensi lebih dulu.")
        p = Pengguna(email=email.lower(), nama=nama, password_hash=hash_sandi(sandi), wajib_ganti_sandi=True)
        session.add(p)
        await session.flush()
        session.add(PenugasanPeran(pengguna_id=p.id, peran=peran, prodi_id=prodi_id))
        await session.commit()
        print(f"Akun {email} dibuat dengan peran {peran.value}. Pengguna wajib mengganti sandi saat masuk pertama.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="perintah", required=True)
    sub.add_parser("seed-referensi")
    bp = sub.add_parser("buat-pengguna")
    bp.add_argument("--email", required=True)
    bp.add_argument("--nama", required=True)
    bp.add_argument("--peran", required=True, choices=[p.value for p in Peran])
    bp.add_argument("--prodi", help="kode prodi (untuk kaprodi, staf_prodi, asesor)")
    dm = sub.add_parser("seed-demo")
    dm.add_argument("--paksa", action="store_true", help="izinkan di luar development")
    args = parser.parse_args()

    if args.perintah == "seed-referensi":
        seed_referensi()
    elif args.perintah == "buat-pengguna":
        sandi = os.environ.get("SIMAK_PASSWORD") or getpass.getpass("Sandi awal: ")
        asyncio.run(_buat_pengguna(args.email, args.nama, Peran(args.peran), args.prodi, sandi))
    elif args.perintah == "seed-demo":
        if get_settings().produksi and not args.paksa:
            sys.exit("seed-demo menolak berjalan di produksi.")
        from app.seed.demo import jalankan

        asyncio.run(jalankan())


if __name__ == "__main__":
    main()
