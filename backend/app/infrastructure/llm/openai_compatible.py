"""Klien LLM berantarmuka OpenAI (`/chat/completions`). Satu adaptor melayani model lokal (Ollama, vLLM) maupun penyedia daring;
bedanya hanya ``base_url``, ``model``, dan kunci API (docs/arsitektur/02-struktur-backend.md §8)."""

from __future__ import annotations

from typing import Any

import httpx

from app.modules.llm.domain.ports import HasilLlm


class GalatLlm(Exception):
    """Koneksi gagal, timeout, atau respons tidak sesuai."""


class KlienOpenAICompatible:
    def __init__(self, timeout: float = 120.0):
        self.timeout = timeout

    @staticmethod
    def _header(api_key: str | None) -> dict[str, str]:
        return {"Authorization": f"Bearer {api_key}"} if api_key else {}

    async def selesaikan(
        self, base_url: str, model: str, api_key: str | None, pesan: list[dict[str, str]], parameter: dict[str, Any]
    ) -> HasilLlm:
        isi = {"model": model, "messages": pesan, **{k: v for k, v in parameter.items() if k in {"temperature", "max_tokens", "top_p"}}}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as klien:
                resp = await klien.post(f"{base_url.rstrip('/')}/chat/completions", json=isi, headers=self._header(api_key))
                resp.raise_for_status()
                data = resp.json()
            teks = data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise GalatLlm(f"{type(exc).__name__}: {exc}"[:300]) from exc
        pakai = data.get("usage") or {}
        return HasilLlm(teks=teks or "", token_masuk=pakai.get("prompt_tokens"), token_keluar=pakai.get("completion_tokens"))

    async def uji(self, base_url: str, model: str, api_key: str | None) -> str:
        """Uji koneksi ringan: satu permintaan pendek. Mengembalikan ringkasan hasil."""
        hasil = await self.selesaikan(
            base_url, model, api_key, [{"role": "user", "content": "Balas dengan satu kata: siap"}], {"max_tokens": 8, "temperature": 0}
        )
        return f"OK ({hasil.teks.strip()[:40]})"
