"""Konfigurasi aplikasi dari environment (.env)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Konfigurasi wajib tidak lengkap atau tidak valid."""


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"Environment variable {name} wajib diisi (lihat .env.example)")
    return value


def _split_admin_ids(raw: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError as exc:
            raise ConfigError(f"TELEGRAM_ADMIN_IDS berisi ID bukan angka: {part!r}") from exc
    return frozenset(ids)


def parse_chat_id(raw: str) -> str | int:
    """Kanal bisa berupa @username atau ID numerik (termasuk negatif)."""
    raw = raw.strip()
    if raw.lstrip("-").isdigit():
        return int(raw)
    return raw


def _parse_topic_map(raw: str) -> dict[str, int]:
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError("TELEGRAM_TOPIC_MAP harus JSON, contoh: {\"akademik\": 12}") from exc
    if not isinstance(data, dict):
        raise ConfigError("TELEGRAM_TOPIC_MAP harus berupa objek JSON")
    return {str(key).strip().lower(): int(value) for key, value in data.items()}


@dataclass(frozen=True)
class Settings:
    bot_token: str
    channel_id: str | int
    admin_ids: frozenset[int]
    topic_map: dict[str, int]
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    llm_vision_model: str
    db_path: Path
    media_dir: Path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    default_model = os.getenv("LLM_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    vision_model = os.getenv("LLM_VISION_MODEL", "").strip() or default_model
    return Settings(
        bot_token=_require("TELEGRAM_BOT_TOKEN"),
        channel_id=parse_chat_id(_require("TELEGRAM_CHANNEL_ID")),
        admin_ids=_split_admin_ids(os.getenv("TELEGRAM_ADMIN_IDS", "")),
        topic_map=_parse_topic_map(os.getenv("TELEGRAM_TOPIC_MAP", "")),
        llm_api_key=_require("LLM_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").strip(),
        llm_model=default_model,
        llm_vision_model=vision_model,
        db_path=Path(os.getenv("DB_PATH", "data/infolomba.db")),
        media_dir=Path(os.getenv("MEDIA_DIR", "data/media")),
    )
