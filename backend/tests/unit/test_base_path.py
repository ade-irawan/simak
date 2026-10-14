"""Sub-path publik (BASE_PATH): normalisasi konfigurasi dan penyisipan prefiks pada URL bertanda tangan."""

from datetime import timedelta

import pytest

from app.core.config import Settings
from app.infrastructure.storage.minio_storage import MinioStorage


@pytest.mark.parametrize("mentah,hasil", [("", ""), ("/", ""), ("simak", "/simak"), ("/simak/", "/simak"), (" /a/b/ ", "/a/b")])
def test_base_path_dinormalkan(mentah, hasil):
    assert Settings(base_path=mentah).base_path == hasil


def _penyimpanan(monkeypatch, base_path: str) -> MinioStorage:
    monkeypatch.setenv("BASE_PATH", base_path)
    from app.core import config

    config.get_settings.cache_clear()
    try:
        return MinioStorage()
    finally:
        config.get_settings.cache_clear()


def test_url_unggah_tanpa_base_path_tidak_berubah(monkeypatch):
    url = _penyimpanan(monkeypatch, "").url_unggah("bukti/a.pdf", timedelta(minutes=5))
    assert "/simak-bukti/bukti/a.pdf?" in url and "/simak/simak-bukti" not in url


def test_url_unggah_menyisipkan_base_path_sebelum_bucket(monkeypatch):
    url = _penyimpanan(monkeypatch, "/simak").url_unggah("bukti/a.pdf", timedelta(minutes=5))
    assert url.startswith("http://localhost:8080/simak/simak-bukti/bukti/a.pdf?")
    assert "X-Amz-Signature=" in url
