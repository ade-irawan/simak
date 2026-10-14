"""Aturan arsitektur (docs/arsitektur/02-struktur-backend.md §4) ditegakkan otomatis seperti `import-linter` di CI:

1. Lapisan ``domain`` murni — tanpa FastAPI, SQLAlchemy, httpx, dan lapisan lain.
2. Modul hanya boleh mengimpor ``public`` milik modul lain (tidak isi dalamnya).
3. ``public.py`` dan ``domain`` tidak mengimpor ``application``/``api`` modul lain.
"""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
MODUL = APP / "modules"
DILARANG_DOMAIN = ("fastapi", "starlette", "sqlalchemy", "httpx", "celery", "redis", "minio", "pydantic_settings")


def _impor(path: Path) -> list[tuple[int, str]]:
    pohon = ast.parse(path.read_text(encoding="utf-8"))
    hasil = []
    for node in ast.walk(pohon):
        if isinstance(node, ast.Import):
            hasil += [(node.lineno, a.name) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            # `from app.modules.x import public` setara dengan `import app.modules.x.public`
            hasil += [(node.lineno, f"{node.module}.{a.name}" if node.module.count(".") <= 2 else node.module) for a in node.names]
    return hasil


def test_domain_murni():
    pelanggaran = []
    for f in MODUL.rglob("domain/*.py"):
        for baris, nama in _impor(f):
            akar = nama.split(".")[0]
            if akar in DILARANG_DOMAIN or ".infrastructure" in nama or ".api" in nama or ".application" in nama:
                pelanggaran.append(f"{f.relative_to(APP)}:{baris} mengimpor {nama}")
    assert not pelanggaran, "\n".join(pelanggaran)


def test_antarmodul_hanya_lewat_public():
    pelanggaran = []
    for f in MODUL.rglob("*.py"):
        sendiri = f.relative_to(MODUL).parts[0]
        for baris, nama in _impor(f):
            bagian = nama.split(".")
            if (
                bagian[:2] == ["app", "modules"]
                and len(bagian) >= 3
                and bagian[2] != sendiri
                and (len(bagian) < 4 or bagian[3] != "public")
            ):
                pelanggaran.append(f"{f.relative_to(APP)}:{baris} mengimpor {nama}")
    assert not pelanggaran, "\n".join(pelanggaran)


def test_public_ringan():
    """public.py hanya boleh mengimpor model/domain modulnya sendiri dan public modul lain — bukan application/api."""
    pelanggaran = []
    for f in MODUL.glob("*/public.py"):
        sendiri = f.parent.name
        for baris, nama in _impor(f):
            if nama.startswith(f"app.modules.{sendiri}.api"):
                pelanggaran.append(f"{f.relative_to(APP)}:{baris} mengimpor {nama}")
    assert not pelanggaran, "\n".join(pelanggaran)
