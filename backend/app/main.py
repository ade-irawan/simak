"""Titik masuk FastAPI: `uvicorn app.main:create_app --factory`."""

from __future__ import annotations

import asyncio
import logging
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

import app.models  # noqa: F401  (registrasi model)
from app.core import audit
from app.core.config import get_settings
from app.core.database import get_engine
from app.core.exceptions import AksesDitolak, GalatDomain
from app.core.logging import request_id_ctx, setup_logging
from app.infrastructure.storage.minio_storage import dapatkan_penyimpanan
from app.modules.asesmen.api.router import router as r_asesmen
from app.modules.audit.api.router import router as r_audit
from app.modules.auth.api.router import router as r_auth
from app.modules.bukti.api.router import router as r_bukti
from app.modules.dokumen_eksternal.api.router import router as r_dokumen_eksternal
from app.modules.instrumen.api.router import router as r_instrumen
from app.modules.laporan.api.router import router as r_laporan
from app.modules.llm.api.router import router as r_llm
from app.modules.notifikasi.api.router import router as r_notifikasi
from app.modules.notifikasi.application.penangan import daftarkan_penangan
from app.modules.pengguna.api.router import router as r_pengguna
from app.modules.penilaian.api.router import router as r_penilaian
from app.modules.ppepp.api.router import router as r_ppepp
from app.modules.referensi.router import router as r_referensi
from app.modules.siklus.api.router import router as r_siklus
from app.modules.tridharma.router import router as r_tridharma

logger = logging.getLogger(__name__)
VERSI = "0.1.0"

_STATUS_KODE = {
    400: "PERMINTAAN_TIDAK_SAH",
    401: "TIDAK_TERAUTENTIKASI",
    403: "AKSES_DITOLAK",
    404: "TIDAK_DITEMUKAN",
    405: "METODE_TIDAK_DIIZINKAN",
    413: "BERKAS_TERLALU_BESAR",
    429: "TERLALU_BANYAK_PERMINTAAN",
}


def _galat(status: int, kode: str, pesan: str, details: list[Any] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=jsonable_encoder({"error": {"code": kode, "message": pesan, "details": details or [], "request_id": request_id_ctx.get()}}),
        headers={"Cache-Control": "no-store"},
    )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    daftarkan_penangan()

    async def siapkan_bucket() -> None:
        try:
            await dapatkan_penyimpanan().pastikan_bucket()
        except Exception:
            logger.exception("Bucket penyimpanan tidak dapat disiapkan; unggah berkas tidak akan berfungsi.")

    tugas = asyncio.create_task(siapkan_bucket())
    yield
    tugas.cancel()
    await get_engine().dispose()


def create_app() -> FastAPI:
    cfg = get_settings()
    setup_logging()
    p = cfg.api_prefix
    app = FastAPI(
        title="SIMAK — Sistem Informasi Manajemen Akreditasi",
        version=VERSI,
        description="API monolit modular untuk LAMSAMA (IAPS 3.1) dan LAM INFOKOM (IAPS 2.1). Skema lengkap dihasilkan dari kode.",
        docs_url=f"{p}/docs",
        openapi_url=f"{p}/openapi.json",
        redoc_url=None,
        root_path=cfg.base_path,
        lifespan=lifespan,
    )

    if cfg.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=cfg.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    @app.middleware("http")
    async def id_permintaan(request: Request, call_next):  # noqa: ANN001, ANN202
        rid = request.headers.get("x-request-id") or secrets.token_hex(8)
        token = request_id_ctx.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = rid
        if request.url.path.startswith(p):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.exception_handler(GalatDomain)
    async def galat_domain(request: Request, exc: GalatDomain) -> JSONResponse:
        if isinstance(exc, AksesDitolak) and not exc.dicatat:
            pemanggil = getattr(request.state, "pemanggil", None)
            await audit.catat_mandiri(
                "akses.ditolak",
                pemanggil=pemanggil,
                ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                detail={"alasan": exc.alasan, "method": request.method, "path": request.url.path},
            )
        return _galat(exc.status, exc.kode, exc.pesan, exc.details)

    @app.exception_handler(RequestValidationError)
    async def galat_validasi(_: Request, exc: RequestValidationError) -> JSONResponse:
        rincian = [{"kolom": ".".join(str(x) for x in e["loc"] if x != "body"), "pesan": e["msg"]} for e in exc.errors()]
        return _galat(422, "VALIDASI_GAGAL", "Isian tidak sah.", rincian)

    @app.exception_handler(StarletteHTTPException)
    async def galat_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _galat(exc.status_code, _STATUS_KODE.get(exc.status_code, "GALAT"), str(exc.detail))

    @app.exception_handler(Exception)
    async def galat_tak_terduga(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Galat tak terduga: %s", exc)
        return _galat(500, "GALAT_INTERNAL", "Terjadi kesalahan pada server.")

    for router in (
        r_auth,
        r_pengguna,
        r_referensi,
        r_audit,
        r_notifikasi,
        r_instrumen,
        r_siklus,
        r_tridharma,
        r_bukti,
        r_ppepp,
        r_dokumen_eksternal,
        r_laporan,
        r_penilaian,
        r_asesmen,
        r_llm,
    ):
        app.include_router(router, prefix=p)

    @app.get(f"{p}/health", tags=["sistem"])
    async def health() -> dict[str, str]:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "versi": VERSI}

    return app
