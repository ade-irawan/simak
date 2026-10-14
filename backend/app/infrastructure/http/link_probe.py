"""Adaptor HTTP untuk port ``ProbeTautan`` (link-checker).

URL berasal dari pengguna, sehingga pemeriksa ini dapat disalahgunakan untuk memindai jaringan internal (SSRF).
Pencegahan: host di-resolve lebih dulu dan alamat privat/loopback/link-local/cadangan ditolak; pengalihan (redirect)
diikuti manual dan setiap lompatan divalidasi ulang.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

from app.modules.bukti.domain.entities import HasilProbe

UA = "SIMAK-LinkChecker/1.0"
MAKS_REDIRECT = 5


async def _alamat_publik(host: str, port: int) -> bool:
    try:
        info = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return True  # biarkan httpx melaporkan galat DNS sebagai "tidak terjangkau"
    for _, _, _, _, sockaddr in info:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return False
    return True


class HttpLinkProbe:
    def __init__(self, timeout: float = 10.0, izinkan_privat: bool = False):
        self.timeout, self.izinkan_privat = timeout, izinkan_privat

    async def periksa(self, url: str) -> HasilProbe:
        saat_ini = url
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False, headers={"User-Agent": UA}) as klien:
                for _ in range(MAKS_REDIRECT + 1):
                    u = urlparse(saat_ini)
                    if u.scheme not in {"http", "https"} or not u.hostname:
                        return HasilProbe(ada=False, galat="url_tidak_valid")
                    if not self.izinkan_privat and not await _alamat_publik(u.hostname, u.port or (443 if u.scheme == "https" else 80)):
                        return HasilProbe(ada=False, galat="alamat_internal_diblokir")
                    resp = await klien.head(saat_ini)
                    if resp.status_code in (403, 405, 501):  # sebagian server menolak HEAD; ulangi dengan GET
                        async with klien.stream("GET", saat_ini) as stream:
                            kode, lokasi = stream.status_code, stream.headers.get("location")
                    else:
                        kode, lokasi = resp.status_code, resp.headers.get("location")
                    if 300 <= kode < 400 and lokasi:
                        saat_ini = urljoin(saat_ini, lokasi)
                        continue
                    return HasilProbe(ada=kode < 400, kode_http=kode)
                return HasilProbe(ada=False, galat="terlalu_banyak_redirect")
        except httpx.HTTPError as exc:
            return HasilProbe(ada=False, kode_http=None, galat=type(exc).__name__)
