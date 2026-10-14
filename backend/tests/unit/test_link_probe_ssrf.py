"""Link-checker memeriksa URL dari pengguna; alamat internal tidak boleh dijangkau (SSRF)."""

import pytest

from app.infrastructure.http.link_probe import HttpLinkProbe


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000/api/v1/health",
        "http://localhost/admin",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://[::1]/",
        "http://0.0.0.0/",
    ],
)
async def test_alamat_internal_diblokir(url):
    hasil = await HttpLinkProbe().periksa(url)
    assert hasil.ada is False and hasil.galat == "alamat_internal_diblokir"


async def test_skema_selain_http_ditolak():
    assert (await HttpLinkProbe().periksa("file:///etc/passwd")).galat == "url_tidak_valid"
    assert (await HttpLinkProbe().periksa("gopher://x/")).galat == "url_tidak_valid"
