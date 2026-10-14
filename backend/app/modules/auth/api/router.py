from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Request, Response

from app.core.config import get_settings
from app.core.permissions import Pemanggil
from app.core.unit_of_work import UnitOfWork
from app.dependencies import get_pemanggil, get_uow
from app.modules.auth.api.schemas import (
    BukaKunciIn,
    GantiSandiIn,
    LoginIn,
    LupaSandiIn,
    ProfilOut,
    ResetSandiIn,
    TokenOut,
)
from app.modules.auth.application.sesi import HasilSesi, LayananSesi

router = APIRouter(prefix="/auth", tags=["auth"])


def _layanan(uow: UnitOfWork = Depends(get_uow)) -> LayananSesi:
    return LayananSesi(uow)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _set_cookie(response: Response, token: str) -> None:
    cfg = get_settings()
    response.set_cookie(
        cfg.cookie_name,
        token,
        max_age=cfg.refresh_token_hari * 86400,
        httponly=True,
        secure=cfg.cookie_secure,
        samesite="strict",
        path=f"{cfg.base_path}{cfg.api_prefix}/auth",
    )


def _token_out(hasil: HasilSesi) -> TokenOut:
    return TokenOut(access_token=hasil.access_token, expires_in=hasil.expires_in, pengguna=hasil.profil)  # type: ignore[arg-type]


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, request: Request, response: Response, svc: LayananSesi = Depends(_layanan)):
    hasil = await svc.masuk(str(data.email).lower(), data.password, _ip(request), request.headers.get("user-agent"))
    _set_cookie(response, hasil.refresh_token)
    return _token_out(hasil)


@router.post("/refresh", response_model=TokenOut)
async def refresh(
    request: Request,
    response: Response,
    svc: LayananSesi = Depends(_layanan),
    simak_refresh: str | None = Cookie(default=None, alias=get_settings().cookie_name),
):
    hasil = await svc.segarkan(simak_refresh, _ip(request), request.headers.get("user-agent"))
    _set_cookie(response, hasil.refresh_token)
    return _token_out(hasil)


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    svc: LayananSesi = Depends(_layanan),
    pemanggil: Pemanggil = Depends(get_pemanggil),
    simak_refresh: str | None = Cookie(default=None, alias=get_settings().cookie_name),
):
    await svc.keluar(simak_refresh, pemanggil)
    cfg = get_settings()
    response.delete_cookie(cfg.cookie_name, path=f"{cfg.base_path}{cfg.api_prefix}/auth")


@router.get("/me", response_model=ProfilOut)
async def saya(pemanggil: Pemanggil = Depends(get_pemanggil), svc: LayananSesi = Depends(_layanan)):
    return await svc.profil(pemanggil)


@router.put("/sandi", status_code=204)
async def ganti_sandi(data: GantiSandiIn, pemanggil: Pemanggil = Depends(get_pemanggil), svc: LayananSesi = Depends(_layanan)):
    await svc.ganti_sandi(pemanggil, data.sandi_lama, data.sandi_baru)


@router.post("/lupa-sandi", status_code=202)
async def lupa_sandi(data: LupaSandiIn, svc: LayananSesi = Depends(_layanan)):
    await svc.lupa_sandi(str(data.email).lower())
    return {"pesan": "Bila email terdaftar, tautan reset telah dikirim."}


@router.post("/reset-sandi", status_code=204)
async def reset_sandi(data: ResetSandiIn, svc: LayananSesi = Depends(_layanan)):
    await svc.reset_sandi(data.token, data.password_baru)


@router.post("/buka-kunci/minta", status_code=202)
async def minta_buka_kunci(data: LupaSandiIn, svc: LayananSesi = Depends(_layanan)):
    await svc.minta_buka_kunci(str(data.email).lower())
    return {"pesan": "Bila email terdaftar, tautan buka kunci telah dikirim."}


@router.post("/buka-kunci", status_code=204)
async def buka_kunci(data: BukaKunciIn, svc: LayananSesi = Depends(_layanan)):
    await svc.buka_kunci(data.token)
