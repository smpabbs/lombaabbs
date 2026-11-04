"""Ekstraksi informasi lomba dari teks maupun gambar poster memakai LLM."""

from __future__ import annotations

import base64
import json
import re
from typing import Any

from openai import AsyncOpenAI, BadRequestError
from pydantic import ValidationError

from app.config import Settings
from app.extract.schema import LombaExtract


class ExtractionError(RuntimeError):
    """Ekstraksi gagal: respons LLM tidak bisa dipakai."""


SYSTEM_PROMPT = """Kamu mengekstrak informasi lomba untuk jenjang SMP di Indonesia.

Aturan:
- Balas HANYA dengan satu objek JSON. Tanpa penjelasan, tanpa blok markdown.
- `is_smp` = true hanya kalau lomba ini untuk SMP/MTs/sederajat (kelas 7-9).
  Kalau khusus SD, SMA/SMK, atau mahasiswa, isi false.
- Gunakan null untuk field yang tidak ada di sumber. JANGAN mengarang data.
- `deadline` = batas akhir pendaftaran, format YYYY-MM-DD kalau bisa.
- `biaya_text` = teks biaya apa adanya, contoh "Gratis" atau "Rp 50.000".
- `cp_kontak` = nomor telepon/WhatsApp contact person apa adanya.
- `link_daftar` = tautan pendaftaran, bukan tautan sumber informasi.
- `ringkasan` = 1-2 kalimat, maksimal 200 karakter.
- `kategori` = "akademik" (olimpiade, sains, esai, karya tulis) atau
  "non-akademik" (olahraga, seni, musik, desain).

Bentuk JSON:
{
  "is_smp": true,
  "judul": "…",
  "penyelenggara": "…",
  "kategori": "akademik",
  "bidang": "…",
  "kelas": "7-9",
  "biaya_text": "Gratis",
  "hadiah": "…",
  "ringkasan": "…",
  "tgl_lomba": "…",
  "deadline": "2026-11-12",
  "lokasi": "Online atau nama kota",
  "link_daftar": "https://…",
  "cp_nama": "…",
  "cp_kontak": "0812…",
  "sumber_url": "https://…"
}"""

_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")


def parse_json_object(raw: str) -> dict[str, Any]:
    """Ambil objek JSON dari respons LLM, tahan terhadap pagar markdown dan teks pengiring."""
    text = _FENCE_RE.sub("", (raw or "").strip()).strip()
    if not text:
        raise ExtractionError("Respons LLM kosong")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ExtractionError(f"Respons LLM bukan JSON: {raw[:200]!r}") from None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"Respons LLM bukan JSON valid: {raw[:200]!r}") from exc
    if not isinstance(data, dict):
        raise ExtractionError(f"Respons LLM bukan objek JSON: {type(data).__name__}")
    return data


class Extractor:
    """Pembungkus LLM untuk ekstraksi teks dan poster."""

    def __init__(self, settings: Settings):
        self._client = AsyncOpenAI(
            api_key=settings.llm_api_key, base_url=settings.llm_base_url
        )
        self._text_model = settings.llm_model
        self._vision_model = settings.llm_vision_model

    @staticmethod
    def _user_prompt(text: str | None, sumber_url: str | None) -> str:
        parts = ["Ekstrak informasi lomba dari sumber berikut."]
        if sumber_url:
            parts.append(f"URL sumber: {sumber_url}")
        if text and text.strip():
            parts.append("Isi sumber:\n" + text.strip())
        else:
            parts.append("Isi sumber ada pada gambar yang dilampirkan.")
        return "\n\n".join(parts)

    async def from_text(self, text: str, sumber_url: str | None = None) -> LombaExtract:
        prompt = self._user_prompt(text, sumber_url)
        return await self._run(self._text_model, prompt)

    async def from_image(
        self,
        image: bytes,
        mime_type: str = "image/jpeg",
        caption: str | None = None,
        sumber_url: str | None = None,
    ) -> LombaExtract:
        encoded = base64.b64encode(image).decode("ascii")
        content: list[dict[str, Any]] = [
            {"type": "text", "text": self._user_prompt(caption, sumber_url)},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
            },
        ]
        return await self._run(self._vision_model, content)

    async def _run(self, model: str, user_content: str | list[dict[str, Any]]) -> LombaExtract:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        try:
            raw = await self._complete(model, messages, json_mode=True)
        except BadRequestError:
            # Sebagian provider tidak mendukung response_format json_object.
            raw = await self._complete(model, messages, json_mode=False)
        try:
            return LombaExtract.model_validate(parse_json_object(raw))
        except ValidationError as exc:
            raise ExtractionError(f"Data hasil ekstraksi tidak valid: {exc}") from exc

    async def _complete(
        self, model: str, messages: list[dict[str, Any]], *, json_mode: bool
    ) -> str:
        kwargs: dict[str, Any] = {"model": model, "messages": messages}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = await self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise ExtractionError("LLM mengembalikan respons kosong")
        return content
