from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.modules.llm.domain.ports import ModeLlm


class KonfigurasiIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nama: str = Field(min_length=3)
    mode: ModeLlm = ModeLlm.OFFLINE
    base_url: str = Field(description="mis. http://llm:11434/v1 (offline) atau https://api.penyedia.com/v1 (online)")
    model: str = Field(min_length=1)
    api_key: str | None = None
    parameter: dict[str, Any] = Field(default_factory=lambda: {"temperature": 0.3, "max_tokens": 1500})

    def model_post_init(self, _: Any) -> None:
        HttpUrl(self.base_url)  # validasi format URL


class KonfigurasiPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nama: str | None = None
    mode: ModeLlm | None = None
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    parameter: dict[str, Any] | None = None


class AktifkanIn(BaseModel):
    konfirmasi_online: bool = False


class DrafIn(BaseModel):
    arahan: str | None = Field(default=None, max_length=1000)
    sertakan_data_terpetakan: bool = True
