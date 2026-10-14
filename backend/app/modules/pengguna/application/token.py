"""Token penyegar (dirotasi) dan token akun sekali pakai (reset sandi, buka kunci)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import PermintaanTidakSah, TidakTerautentikasi
from app.core.security import buat_token_acak, hash_token
from app.modules.pengguna.domain.entities import JenisTokenAkun, StatusPengguna
from app.modules.pengguna.infrastructure.models import Pengguna, TokenAkun, TokenRefresh


def _sekarang() -> datetime:
    return datetime.now(UTC)


# ---------------- token akun ----------------
async def buat_token_akun(
    session: AsyncSession,
    pengguna_id: UUID,
    jenis: JenisTokenAkun,
    *,
    dibuat_oleh: UUID | None = None,
    menit: int = 60,
) -> str:
    # Token lama yang belum dipakai dibatalkan agar hanya satu tautan berlaku.
    await session.execute(
        update(TokenAkun)
        .where(TokenAkun.pengguna_id == pengguna_id, TokenAkun.jenis == jenis, TokenAkun.dipakai_pada.is_(None))
        .values(dipakai_pada=_sekarang())
    )
    token, hash_ = buat_token_acak()
    session.add(
        TokenAkun(
            pengguna_id=pengguna_id,
            jenis=jenis,
            token_hash=hash_,
            kedaluwarsa_pada=_sekarang() + timedelta(minutes=menit),
            dibuat_oleh=dibuat_oleh,
        )
    )
    await session.flush()
    return token


async def pakai_token_akun(session: AsyncSession, token: str, jenis: JenisTokenAkun) -> Pengguna:
    ta = (await session.execute(select(TokenAkun).where(TokenAkun.token_hash == hash_token(token)))).scalar_one_or_none()
    if ta is None or ta.jenis != jenis or ta.dipakai_pada is not None or ta.kedaluwarsa_pada < _sekarang():
        raise PermintaanTidakSah("Tautan tidak valid atau sudah kedaluwarsa.")
    pengguna = await session.get(Pengguna, ta.pengguna_id)
    if pengguna is None or pengguna.status != StatusPengguna.AKTIF:
        raise PermintaanTidakSah("Tautan tidak valid atau sudah kedaluwarsa.")
    ta.dipakai_pada = _sekarang()
    return pengguna


# ---------------- token penyegar ----------------
async def terbitkan_refresh(session: AsyncSession, pengguna_id: UUID, ip: str | None, user_agent: str | None) -> str:
    token, hash_ = buat_token_acak()
    session.add(
        TokenRefresh(
            pengguna_id=pengguna_id,
            token_hash=hash_,
            kedaluwarsa_pada=_sekarang() + timedelta(days=get_settings().refresh_token_hari),
            ip=ip,
            user_agent=user_agent,
        )
    )
    await session.flush()
    return token


async def cabut_semua_refresh(session: AsyncSession, pengguna_id: UUID) -> None:
    await session.execute(
        update(TokenRefresh)
        .where(TokenRefresh.pengguna_id == pengguna_id, TokenRefresh.dicabut_pada.is_(None))
        .values(dicabut_pada=_sekarang())
    )


async def putar_refresh(session: AsyncSession, token: str, ip: str | None, user_agent: str | None) -> tuple[UUID, str]:
    """Menukar token penyegar lama dengan yang baru. Pemakaian ulang token yang sudah dicabut
    dianggap pencurian: seluruh token penyegar pengguna itu dicabut."""
    tr = (
        await session.execute(select(TokenRefresh).where(TokenRefresh.token_hash == hash_token(token)).with_for_update())
    ).scalar_one_or_none()
    if tr is None:
        raise TidakTerautentikasi("Sesi tidak valid.")
    if tr.dicabut_pada is not None:
        await cabut_semua_refresh(session, tr.pengguna_id)
        await session.commit()
        raise TidakTerautentikasi("Sesi tidak valid.")
    if tr.kedaluwarsa_pada < _sekarang():
        raise TidakTerautentikasi("Sesi telah berakhir.")
    tr.dicabut_pada = _sekarang()
    baru = await terbitkan_refresh(session, tr.pengguna_id, ip, user_agent)
    return tr.pengguna_id, baru


async def cabut_refresh(session: AsyncSession, token: str) -> None:
    await session.execute(
        update(TokenRefresh)
        .where(TokenRefresh.token_hash == hash_token(token), TokenRefresh.dicabut_pada.is_(None))
        .values(dicabut_pada=_sekarang())
    )
