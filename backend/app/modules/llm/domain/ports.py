from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol


class ModeLlm(StrEnum):
    OFFLINE = "offline"
    ONLINE = "online"


@dataclass(frozen=True)
class HasilLlm:
    teks: str
    token_masuk: int | None = None
    token_keluar: int | None = None


class KlienLlm(Protocol):
    async def selesaikan(
        self, base_url: str, model: str, api_key: str | None, pesan: list[dict[str, str]], parameter: dict[str, Any]
    ) -> HasilLlm: ...

    async def uji(self, base_url: str, model: str, api_key: str | None) -> str: ...
