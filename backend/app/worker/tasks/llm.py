from __future__ import annotations

from uuid import UUID

from app.core.database import get_session_factory
from app.core.unit_of_work import UnitOfWork
from app.infrastructure.llm.openai_compatible import KlienOpenAICompatible
from app.modules.llm.application.layanan import LayananLlm
from app.worker.celery_app import celery
from app.worker.runtime import jalankan


@celery.task(name="simak.draf_llm", bind=True, max_retries=0)
def draf_llm(self, permintaan_id: str, arahan: str | None, sertakan_data: bool) -> None:  # noqa: ANN001
    async def kerja() -> None:
        async with get_session_factory()() as session:
            await LayananLlm(UnitOfWork(session), KlienOpenAICompatible()).proses(UUID(permintaan_id), arahan, sertakan_data)

    jalankan(kerja)
