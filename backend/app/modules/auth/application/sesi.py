"""Use case autentikasi: masuk, penyegaran, keluar, profil, ganti/reset sandi, buka kunci."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import audit
from app.core.exceptions import (
    AksesDitolak,
    AkunTerkunci,
    KredensialSalah,
    TidakTerautentikasi,
    ValidasiGagal,
)
from app.core.permissions import Pemanggil
from app.core.security import (
    HASH_TIRUAN,
    buat_access_token,
    hash_sandi,
    perlu_rehash,
    verifikasi_sandi,
    wajib_sandi_kuat,
)
from app.core.unit_of_work import UnitOfWork
from app.modules.instrumen import public as instrumen
from app.modules.pengguna import public as pengguna
from app.modules.referensi import public as referensi


@dataclass
class HasilSesi:
    access_token: str
    expires_in: int
    profil: dict[str, Any]
    refresh_token: str


def _sekarang() -> datetime:
    return datetime.now(UTC)


async def bangun_profil(session: AsyncSession, p: Pemanggil, wajib_ganti_sandi: bool) -> dict[str, Any]:
    prodi = {x.id: x for x in await referensi.daftar_prodi(session)}
    versi = await instrumen.versi_aktif_per_lam(session)
    peran = []
    for t in p.penugasan:
        pr = prodi.get(t.prodi_id) if t.prodi_id else None
        peran.append(
            {
                "penugasan_id": t.id,
                "peran": t.peran,
                "prodi": {"id": pr.id, "kode": pr.kode, "nama": pr.nama} if pr else None,
                # Instrumen mengikuti prodi secara otomatis (US-A1), bukan pilihan manual.
                "instrumen": {"lam": pr.lam_kode, "kode_versi": versi.get(pr.lam_kode)} if pr else None,
                "berlaku_sampai": t.berlaku_sampai,
            }
        )
    return {"id": p.id, "nama": p.nama, "email": p.email, "wajib_ganti_sandi": wajib_ganti_sandi, "peran": peran}


class LayananSesi:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.session = uow.session

    async def _kebijakan(self) -> tuple[int, int]:
        maks = int(await referensi.ambil_pengaturan(self.session, "login.maks_gagal", 5))
        menit = int(await referensi.ambil_pengaturan(self.session, "login.menit_kunci", 15))
        return maks, menit

    async def masuk(self, email: str, password: str, ip: str | None, user_agent: str | None) -> HasilSesi:
        sekarang = _sekarang()
        p = await pengguna.cari_by_email(self.session, email)
        ctx = {"ip": ip, "user_agent": user_agent}
        if p is None or p.status != pengguna.StatusPengguna.AKTIF:
            verifikasi_sandi(HASH_TIRUAN, password)  # samakan waktu respons
            await audit.catat_mandiri("login.gagal", detail={"email": email, "alasan": "akun_tidak_dikenal"}, **ctx)
            raise KredensialSalah()

        if pengguna.sedang_terkunci(p.terkunci_sampai, sekarang):
            await audit.catat_mandiri("login.ditolak_terkunci", pengguna_id=p.id, **ctx)
            raise AkunTerkunci(details=[{"terkunci_sampai": p.terkunci_sampai.isoformat()}])

        if not verifikasi_sandi(p.password_hash, password):
            maks, menit = await self._kebijakan()
            # Kunci yang masa tunggunya sudah lewat: hitungan dimulai dari nol.
            sebelumnya = 0 if p.terkunci_sampai else p.jumlah_gagal_login
            hasil = pengguna.hitung_gagal_login(sebelumnya, maks_gagal=maks, menit_kunci=menit, sekarang=sekarang)
            p.jumlah_gagal_login, p.terkunci_sampai = hasil.jumlah_gagal, hasil.terkunci_sampai
            await audit.catat(self.session, "login.gagal", pengguna_id=p.id, detail={"sisa": hasil.sisa_percobaan}, **ctx)
            if hasil.terkunci_sampai:
                await audit.catat(self.session, "akun.terkunci", pengguna_id=p.id, detail={"sampai": hasil.terkunci_sampai}, **ctx)
            await self.session.commit()  # hitungan gagal harus bertahan walau permintaan ditolak
            if hasil.terkunci_sampai:
                raise AkunTerkunci(details=[{"terkunci_sampai": hasil.terkunci_sampai.isoformat()}])
            raise KredensialSalah(details=[{"sisa_percobaan": hasil.sisa_percobaan}])

        pemanggil = await pengguna.muat_pemanggil(self.session, p.id, ip, user_agent)
        if pemanggil is None or not pemanggil.penugasan:
            # Mis. asesor di luar jendela asesmen (EC-26): ditolak total dan dicatat.
            await audit.catat_mandiri("akses.ditolak", pengguna_id=p.id, detail={"alasan": "tanpa_penugasan_aktif"}, **ctx)
            raise AksesDitolak(
                "Akun belum memiliki penugasan aktif atau masa aksesnya telah berakhir.", alasan="tanpa_penugasan_aktif", dicatat=True
            )

        async with self.uow:
            p.jumlah_gagal_login, p.terkunci_sampai, p.login_terakhir = 0, None, sekarang
            if perlu_rehash(p.password_hash):
                p.password_hash = hash_sandi(password)
            refresh = await pengguna.terbitkan_refresh(self.session, p.id, ip, user_agent)
            await audit.catat(self.session, "login.sukses", pemanggil=pemanggil)
        token, ttl = buat_access_token(p.id)
        return HasilSesi(token, ttl, await bangun_profil(self.session, pemanggil, p.wajib_ganti_sandi), refresh)

    async def segarkan(self, token_refresh: str | None, ip: str | None, user_agent: str | None) -> HasilSesi:
        if not token_refresh:
            raise TidakTerautentikasi("Sesi tidak ditemukan.")
        async with self.uow:
            pengguna_id, baru = await pengguna.putar_refresh(self.session, token_refresh, ip, user_agent)
        pemanggil = await pengguna.muat_pemanggil(self.session, pengguna_id, ip, user_agent)
        if pemanggil is None or not pemanggil.penugasan:
            raise TidakTerautentikasi("Sesi tidak berlaku.")
        p = await self.session.get(pengguna.Pengguna, pengguna_id)
        token, ttl = buat_access_token(pengguna_id)
        return HasilSesi(token, ttl, await bangun_profil(self.session, pemanggil, bool(p and p.wajib_ganti_sandi)), baru)

    async def keluar(self, token_refresh: str | None, pemanggil: Pemanggil | None) -> None:
        if token_refresh:
            async with self.uow:
                await pengguna.cabut_refresh(self.session, token_refresh)
                if pemanggil:
                    await audit.catat(self.session, "logout", pemanggil=pemanggil)

    async def profil(self, pemanggil: Pemanggil) -> dict[str, Any]:
        p = await self.session.get(pengguna.Pengguna, pemanggil.id)
        return await bangun_profil(self.session, pemanggil, bool(p and p.wajib_ganti_sandi))

    # ---------- sandi ----------
    async def ganti_sandi(self, pemanggil: Pemanggil, lama: str, baru: str) -> None:
        p = await self.session.get(pengguna.Pengguna, pemanggil.id)
        if p is None or not verifikasi_sandi(p.password_hash, lama):
            raise ValidasiGagal("Sandi lama salah.", details=[{"kolom": "sandi_lama"}])
        wajib_sandi_kuat(baru)
        async with self.uow:
            p.password_hash, p.wajib_ganti_sandi = hash_sandi(baru), False
            await pengguna.cabut_semua_refresh(self.session, p.id)
            await audit.catat(self.session, "sandi.ganti", pemanggil=pemanggil)

    async def lupa_sandi(self, email: str) -> None:
        """Selalu berakhir sukses di sisi pemanggil agar keberadaan email tidak bocor."""
        p = await pengguna.cari_by_email(self.session, email)
        if p is None or p.status != pengguna.StatusPengguna.AKTIF:
            return
        async with self.uow:
            token = await pengguna.buat_token_akun(self.session, p.id, pengguna.JenisTokenAkun.RESET_SANDI)
            self.uow.terbitkan(pengguna.TokenAkunDibuat(p.id, p.email, p.nama, "reset_sandi", token))
            await audit.catat(self.session, "sandi.minta_reset", pengguna_id=p.id)

    async def reset_sandi(self, token: str, password_baru: str) -> None:
        wajib_sandi_kuat(password_baru)
        async with self.uow:
            p = await pengguna.pakai_token_akun(self.session, token, pengguna.JenisTokenAkun.RESET_SANDI)
            p.password_hash, p.wajib_ganti_sandi = hash_sandi(password_baru), False
            p.jumlah_gagal_login, p.terkunci_sampai = 0, None
            await pengguna.cabut_semua_refresh(self.session, p.id)
            await audit.catat(self.session, "sandi.reset", pengguna_id=p.id)

    # ---------- buka kunci swalayan ----------
    async def minta_buka_kunci(self, email: str) -> None:
        p = await pengguna.cari_by_email(self.session, email)
        if p is None or p.status != pengguna.StatusPengguna.AKTIF:
            return
        async with self.uow:
            token = await pengguna.buat_token_akun(self.session, p.id, pengguna.JenisTokenAkun.BUKA_KUNCI, menit=30)
            self.uow.terbitkan(pengguna.TokenAkunDibuat(p.id, p.email, p.nama, "buka_kunci", token))
            await audit.catat(self.session, "akun.minta_buka_kunci", pengguna_id=p.id)

    async def buka_kunci(self, token: str) -> None:
        async with self.uow:
            p = await pengguna.pakai_token_akun(self.session, token, pengguna.JenisTokenAkun.BUKA_KUNCI)
            p.jumlah_gagal_login, p.terkunci_sampai = 0, None
            await audit.catat(self.session, "akun.buka_kunci_swalayan", pengguna_id=p.id)
