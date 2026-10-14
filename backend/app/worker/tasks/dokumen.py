from __future__ import annotations

from uuid import UUID

from app.core.database import get_session_factory
from app.core.unit_of_work import UnitOfWork
from app.infrastructure.documents import PerenderBerkas
from app.infrastructure.storage.minio_storage import dapatkan_penyimpanan
from app.modules.laporan.application.ekspor import LayananEkspor
from app.modules.laporan.infrastructure.penyusun_cuplikan import PenyusunCuplikanDb
from app.worker.celery_app import celery
from app.worker.runtime import jalankan


@celery.task(name="simak.ekspor_dokumen", bind=True, max_retries=0)
def ekspor_dokumen(self, ekspor_id: str) -> None:  # noqa: ANN001
    async def kerja() -> None:
        penyimpanan = dapatkan_penyimpanan()
        await penyimpanan.pastikan_bucket()
        async with get_session_factory()() as session:
            await LayananEkspor(UnitOfWork(session), PenyusunCuplikanDb(session), penyimpanan, PerenderBerkas()).proses(UUID(ekspor_id))

    jalankan(kerja)
