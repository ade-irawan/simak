"""Penangan peristiwa domain → notifikasi dalam aplikasi dan surel (efek samping lintas modul tanpa impor langsung)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.events import pada
from app.core.permissions import SF, SP, D, K
from app.infrastructure.antrean import kirim_tugas
from app.modules.bukti.public import BuktiBermasalahTerdeteksi
from app.modules.laporan.public import LaporanDiajukan, LaporanDikembalikan, LaporanDisetujui
from app.modules.notifikasi.public import kirim
from app.modules.pengguna import public as pengguna
from app.modules.referensi import public as referensi

_terdaftar = False

TAUTAN = {"reset_sandi": "/reset-sandi", "buka_kunci": "/buka-kunci"}
JUDUL_SUREL = {"reset_sandi": "Atur sandi akun SIMAK Anda", "buka_kunci": "Buka kunci akun SIMAK Anda"}


def daftarkan_penangan() -> None:
    """Idempotent; dipanggil saat aplikasi dan worker start."""
    global _terdaftar
    if _terdaftar:
        return
    _terdaftar = True

    @pada(pengguna.TokenAkunDibuat)
    async def _token(p: pengguna.TokenAkunDibuat, session: AsyncSession) -> None:
        tautan = f"{get_settings().app_base_url}{TAUTAN[p.jenis]}?token={p.token}"
        isi = (
            f"Halo {p.nama},\n\nGunakan tautan berikut (berlaku terbatas dan hanya sekali pakai):\n{tautan}\n\n"
            "Abaikan surel ini bila Anda tidak memintanya."
        )
        kirim_tugas("simak.kirim_surel", p.email, JUDUL_SUREL[p.jenis], isi)

    @pada(LaporanDiajukan)
    async def _diajukan(p: LaporanDiajukan, session: AsyncSession) -> None:
        prodi = await referensi.ambil_prodi(session, p.prodi_id)
        for u in await pengguna.penerima(session, D):
            await kirim(
                session,
                u.id,
                "laporan.diajukan",
                f"Laporan {prodi.nama} menunggu validasi",
                f"Kaprodi mengajukan laporan pengajuan #{p.nomor}.",
                f"/laporan/{p.laporan_id}",
            )

    @pada(LaporanDisetujui)
    async def _disetujui(p: LaporanDisetujui, session: AsyncSession) -> None:
        prodi = await referensi.ambil_prodi(session, p.prodi_id)
        for peran in (K, SP):
            for u in await pengguna.penerima(session, peran, p.prodi_id):
                await kirim(
                    session,
                    u.id,
                    "laporan.disetujui",
                    f"Laporan {prodi.nama} disetujui Dekan",
                    f"Pengajuan #{p.nomor} disetujui. Dokumen final dapat diekspor.",
                    f"/siklus/{p.siklus_id}/laporan",
                )

    @pada(LaporanDikembalikan)
    async def _dikembalikan(p: LaporanDikembalikan, session: AsyncSession) -> None:
        prodi = await referensi.ambil_prodi(session, p.prodi_id)
        for peran in (K, SP):
            for u in await pengguna.penerima(session, peran, p.prodi_id):
                await kirim(
                    session,
                    u.id,
                    "laporan.dikembalikan",
                    f"Laporan {prodi.nama} dikembalikan",
                    f"Dekan mengembalikan pengajuan #{p.nomor} dengan catatan. Perbaiki lalu ajukan ulang.",
                    f"/siklus/{p.siklus_id}/laporan",
                )

    @pada(BuktiBermasalahTerdeteksi)
    async def _bukti(p: BuktiBermasalahTerdeteksi, session: AsyncSession) -> None:
        sasaran = {u.id for pr in p.prodi_ids for peran in (K, SP) for u in await pengguna.penerima(session, peran, pr)}
        sasaran |= {u.id for u in await pengguna.penerima(session, SF)}
        for uid in sasaran:
            await kirim(
                session,
                uid,
                "bukti.bermasalah",
                "Bukti tidak terjangkau",
                f'Bukti "{p.judul}" tidak dapat dijangkau. Perbaiki atau ganti sebelum laporan diajukan/divalidasi.',
                f"/bukti/{p.bukti_id}",
            )

    @pada(pengguna.AsesorDiaktifkan)
    async def _asesor(p: pengguna.AsesorDiaktifkan, session: AsyncSession) -> None:
        prodi = await referensi.ambil_prodi(session, p.prodi_id)
        await kirim(
            session,
            p.pengguna_id,
            "asesor.diaktifkan",
            f"Akses asesmen {prodi.nama} aktif",
            "Anda dapat menelaah versi laporan yang telah disetujui selama jendela asesmen.",
            "/asesmen",
        )
