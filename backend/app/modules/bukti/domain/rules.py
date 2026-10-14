"""Aturan bukti: validasi berkas/tautan dan penentuan status keterjangkauan (link-checker, EC-23). Tanpa I/O."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.modules.bukti.domain.entities import AksesTautan, HasilCek, HasilProbe, JenisBukti, StatusCekBukti

# ekstensi → (mime yang diterima, awalan byte yang diharapkan; None = tak diperiksa)
FORMAT_BERKAS: dict[str, tuple[set[str], tuple[bytes, ...] | None]] = {
    ".pdf": ({"application/pdf"}, (b"%PDF",)),
    ".jpg": ({"image/jpeg"}, (b"\xff\xd8\xff",)),
    ".jpeg": ({"image/jpeg"}, (b"\xff\xd8\xff",)),
    ".png": ({"image/png"}, (b"\x89PNG",)),
    ".xlsx": ({"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}, (b"PK\x03\x04",)),
    ".docx": ({"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}, (b"PK\x03\x04",)),
    ".csv": ({"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain"}, None),
}


def ekstensi(nama: str) -> str:
    return "." + nama.rsplit(".", 1)[-1].lower() if "." in nama else ""


def periksa_berkas(nama: str, mime: str, ukuran_byte: int, maks_mb: int) -> list[str]:
    """Daftar alasan penolakan unggahan (EC-18); kosong bila diterima."""
    galat: list[str] = []
    eks = ekstensi(nama)
    if eks not in FORMAT_BERKAS:
        galat.append(f"Format {eks or '(tanpa ekstensi)'} tidak didukung. Gunakan: {', '.join(sorted(FORMAT_BERKAS))}.")
    elif mime.lower() not in FORMAT_BERKAS[eks][0]:
        galat.append(f"Tipe MIME {mime} tidak sesuai dengan ekstensi {eks}.")
    if ukuran_byte <= 0:
        galat.append("Berkas kosong.")
    if ukuran_byte > maks_mb * 1024 * 1024:
        galat.append(f"Ukuran berkas melebihi batas {maks_mb} MB.")
    return galat


def isi_sesuai_ekstensi(nama: str, awal_byte: bytes) -> bool:
    tanda = FORMAT_BERKAS.get(ekstensi(nama), (set(), None))[1]
    return tanda is None or any(awal_byte.startswith(t) for t in tanda)


def nama_aman(nama: str) -> str:
    dasar = nama.replace("\\", "/").rsplit("/", 1)[-1]
    return re.sub(r"[^A-Za-z0-9._-]+", "-", dasar).strip("-.")[:120] or "berkas"


def periksa_url(url: str) -> str | None:
    try:
        u = urlparse(url.strip())
    except ValueError:
        return "Format URL tidak valid."
    if u.scheme not in {"http", "https"} or not u.netloc or " " in url.strip():
        return "URL harus diawali http:// atau https:// dan berisi alamat yang valid."
    if len(url) > 2000:
        return "URL terlalu panjang."
    return None


def tentukan_status(
    jenis: JenisBukti,
    akses: AksesTautan | None,
    probe: HasilProbe,
    gagal_sebelumnya: int,
    *,
    gagal_sebelum_merah: int = 3,
) -> HasilCek:
    """Menerjemahkan hasil probe menjadi status bukti.

    * Berkas: hilang dari penyimpanan = langsung tidak terjangkau (kepastian, bukan gangguan sesaat).
    * Tautan publik: 2xx/3xx = ok; selain itu atau gagal jaringan dihitung gagal beruntun, dan baru ditandai
      tidak terjangkau setelah ``gagal_sebelum_merah`` kali berturut-turut (menghindari alarm palsu).
    * Tautan terbatas: 401/403 berarti alamatnya ada tetapi butuh login — tidak dihitung rusak.
    """
    if jenis == JenisBukti.BERKAS:
        if probe.ada:
            return HasilCek(StatusCekBukti.OK, 0, None)
        return HasilCek(StatusCekBukti.TIDAK_TERJANGKAU, gagal_sebelumnya + 1, None)

    kode = probe.kode_http
    if kode is not None and (200 <= kode < 400):
        return HasilCek(StatusCekBukti.OK, 0, kode)
    if akses == AksesTautan.TERBATAS and kode in (401, 403):
        return HasilCek(StatusCekBukti.OK, 0, kode)
    gagal = gagal_sebelumnya + 1
    status = StatusCekBukti.TIDAK_TERJANGKAU if gagal >= gagal_sebelum_merah else StatusCekBukti.BELUM_DICEK
    return HasilCek(status, gagal, kode)
