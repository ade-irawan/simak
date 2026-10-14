"""Aturan lembar kerja butir: siapa boleh menyunting, dan apa yang menghalangi pengajuan. Tanpa I/O."""

from __future__ import annotations

from uuid import UUID

from app.core.exceptions import AksesDitolak
from app.core.permissions import SF, SP, K, Pemanggil
from app.modules.siklus.domain.entities import PengelolaButir, StatusKelengkapan


def boleh_ubah_butir(pemanggil: Pemanggil, *, prodi_id: UUID, pengelola: PengelolaButir, penanggung_jawab_id: UUID | None) -> bool:
    """Hak ubah status/skor/catatan butir (bukan narasi).

    * Butir dikelola prodi: Kaprodi dan Staf Prodi pada prodinya. Staf Prodi yang ditunjuk Dekan
      sebagai penanggung jawab diutamakan; bila belum ada penanggung jawab, semua Staf Prodi boleh.
    * Butir dikelola fakultas (di luar kendali prodi): hanya Staf Fakultas yang ditugaskan (atau
      bila belum ada penanggung jawab, Staf Fakultas mana pun). Kaprodi hanya membaca.
    * Staf Fakultas yang ditunjuk Dekan membantu butir prodi juga boleh.
    """
    saya = pemanggil.id
    if pengelola == PengelolaButir.PRODI:
        if pemanggil.punya(K) and prodi_id in pemanggil.prodi_dari(K):
            return True
        if pemanggil.punya(SP) and prodi_id in pemanggil.prodi_dari(SP):
            return penanggung_jawab_id in (None, saya)
        if pemanggil.punya(SF):
            return penanggung_jawab_id == saya
        return False
    return pemanggil.punya(SF) and penanggung_jawab_id in (None, saya)


def wajib_ubah_butir(pemanggil: Pemanggil, **kw: object) -> None:
    if not boleh_ubah_butir(pemanggil, **kw):  # type: ignore[arg-type]
        raise AksesDitolak(alasan="bukan_pengelola_butir")


def masalah_pengajuan(
    *,
    status: StatusKelengkapan,
    bukti_bermasalah: int,
    menunggu_dokumen_eksternal: bool,
    sumber_data_kosong: list[str],
) -> list[str]:
    """Daftar alasan sebuah butir menghalangi pengajuan laporan (EC-06, EC-15, EC-23)."""
    masalah: list[str] = []
    if status == StatusKelengkapan.DRAFT:
        masalah.append("status_draft")
    elif status == StatusKelengkapan.BELUM_MULAI:
        masalah.append("belum_mulai")
    if bukti_bermasalah:
        masalah.append("bukti_tidak_terjangkau")
    if menunggu_dokumen_eksternal:
        masalah.append("menunggu_dokumen_eksternal")
    if sumber_data_kosong:
        masalah.append("data_kurang")
    return masalah
