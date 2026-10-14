"""Adaptor MinIO untuk port ``PenyimpananBerkas``.

Dua klien: ``internal`` (nama layanan Docker, untuk operasi sisi server) dan ``publik`` (host yang dilihat
peramban lewat Nginx, hanya untuk menandatangani URL sementara — tanpa panggilan jaringan karena region diberikan).
"""

from __future__ import annotations

import asyncio
import io
import logging
from datetime import timedelta
from functools import lru_cache

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings

logger = logging.getLogger(__name__)
REGION = "us-east-1"


class MinioStorage:
    def __init__(self) -> None:
        cfg = get_settings()
        self.bucket = cfg.minio_bucket
        self._internal = Minio(cfg.minio_endpoint, cfg.minio_root_user, cfg.minio_root_password, secure=cfg.minio_secure, region=REGION)
        self._publik = Minio(
            cfg.minio_public_endpoint, cfg.minio_root_user, cfg.minio_root_password, secure=cfg.minio_public_secure, region=REGION
        )

    async def pastikan_bucket(self) -> None:
        """Membuat bucket privat bila belum ada; mengulang sampai MinIO siap (urutan start Docker tidak pasti)."""
        for percobaan in range(1, 31):
            try:
                ada = await asyncio.to_thread(self._internal.bucket_exists, self.bucket)
                if not ada:
                    await asyncio.to_thread(self._internal.make_bucket, self.bucket)
                return
            except Exception as exc:  # MinIO belum siap
                logger.warning("MinIO belum siap (percobaan %s): %s", percobaan, exc)
                await asyncio.sleep(2)
        raise RuntimeError("MinIO tidak dapat dijangkau.")

    def url_unggah(self, objek_key: str, kedaluwarsa: timedelta) -> str:
        return self._publik.presigned_put_object(self.bucket, objek_key, expires=kedaluwarsa)

    def url_unduh(self, objek_key: str, nama_berkas: str | None, kedaluwarsa: timedelta) -> str:
        header = {"response-content-disposition": f'attachment; filename="{nama_berkas}"'} if nama_berkas else None
        return self._publik.presigned_get_object(self.bucket, objek_key, expires=kedaluwarsa, response_headers=header)

    async def ada(self, objek_key: str) -> bool:
        return await self.ukuran(objek_key) is not None

    async def ukuran(self, objek_key: str) -> int | None:
        try:
            st = await asyncio.to_thread(self._internal.stat_object, self.bucket, objek_key)
            return int(st.size or 0)
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
                return None
            raise

    async def baca(self, objek_key: str, maks_byte: int | None = None) -> bytes:
        def _baca() -> bytes:
            resp = self._internal.get_object(self.bucket, objek_key)
            try:
                return resp.read(maks_byte) if maks_byte else resp.read()
            finally:
                resp.close()
                resp.release_conn()

        return await asyncio.to_thread(_baca)

    async def simpan(self, objek_key: str, data: bytes, mime: str) -> None:
        await asyncio.to_thread(self._internal.put_object, self.bucket, objek_key, io.BytesIO(data), len(data), content_type=mime)

    async def hapus(self, objek_key: str) -> None:
        await asyncio.to_thread(self._internal.remove_object, self.bucket, objek_key)


@lru_cache
def dapatkan_penyimpanan() -> MinioStorage:
    return MinioStorage()
