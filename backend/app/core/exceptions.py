"""Galat domain dan pemetaannya ke HTTP (docs/arsitektur/03-spesifikasi-api.md §1)."""

from __future__ import annotations

from typing import Any


class GalatDomain(Exception):
    status = 400
    kode = "PERMINTAAN_TIDAK_SAH"
    pesan_bawaan = "Permintaan tidak sah."

    def __init__(self, pesan: str | None = None, details: list[Any] | None = None, **ekstra: Any):
        self.pesan = pesan or self.pesan_bawaan
        self.details = details or []
        self.ekstra = ekstra
        super().__init__(self.pesan)


class PermintaanTidakSah(GalatDomain):
    status, kode = 400, "PERMINTAAN_TIDAK_SAH"


class TidakTerautentikasi(GalatDomain):
    status, kode, pesan_bawaan = 401, "TIDAK_TERAUTENTIKASI", "Autentikasi diperlukan."


class KredensialSalah(GalatDomain):
    status, kode, pesan_bawaan = 401, "KREDENSIAL_SALAH", "Email atau sandi salah."


class AksesDitolak(GalatDomain):
    status, kode, pesan_bawaan = 403, "AKSES_DITOLAK", "Akses ditolak."

    def __init__(self, pesan: str | None = None, alasan: str = "peran_tidak_sesuai", dicatat: bool = False, **kw: Any):
        super().__init__(pesan, **kw)
        self.alasan = alasan
        #: True bila pemanggil sudah menulis log audit sendiri (penangan global tidak mencatat ulang)
        self.dicatat = dicatat


class TidakDitemukan(GalatDomain):
    status, kode, pesan_bawaan = 404, "TIDAK_DITEMUKAN", "Data tidak ditemukan."


class KonflikVersi(GalatDomain):
    status, kode = 409, "KONFLIK_VERSI"
    pesan_bawaan = "Data telah diubah pengguna lain. Muat versi terbaru sebelum menyimpan."


class Duplikat(GalatDomain):
    status, kode, pesan_bawaan = 409, "DUPLIKAT", "Data serupa sudah ada."


class LaporanTerkunci(GalatDomain):
    status, kode = 409, "LAPORAN_TERKUNCI"
    pesan_bawaan = "Laporan sedang menunggu validasi atau sudah disetujui; perubahan dikunci."


class BuktiBermasalah(GalatDomain):
    status, kode, pesan_bawaan = 409, "BUKTI_BERMASALAH", "Ada bukti yang tidak terjangkau."


class LaporanBelumDisetujui(GalatDomain):
    status, kode = 409, "LAPORAN_BELUM_DISETUJUI"
    pesan_bawaan = "Laporan prodi belum disetujui; asesor belum dapat diaktifkan."


class KonflikStatus(GalatDomain):
    """409 umum untuk transisi status yang tidak diizinkan."""

    status, kode, pesan_bawaan = 409, "KONFLIK_STATUS", "Operasi tidak diizinkan pada status saat ini."


class ValidasiGagal(GalatDomain):
    status, kode, pesan_bawaan = 422, "VALIDASI_GAGAL", "Isian tidak sah."


class LaporanBelumLengkap(GalatDomain):
    status, kode, pesan_bawaan = 422, "LAPORAN_BELUM_LENGKAP", "Masih ada butir yang belum lengkap."


class AkunTerkunci(GalatDomain):
    status, kode = 423, "AKUN_TERKUNCI"
    pesan_bawaan = "Akun terkunci sementara. Coba lagi nanti, atau buka kunci lewat surel."


class LlmTidakTersedia(GalatDomain):
    status, kode, pesan_bawaan = 503, "LLM_TIDAK_TERSEDIA", "Tidak ada konfigurasi LLM aktif atau koneksi gagal."
