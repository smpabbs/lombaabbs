"""Penyimpanan salinan lokal flyer sebagai backup di samping file_id Telegram."""

from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path

MIME_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def extension_for(mime_type: str | None, fallback: str = ".jpg") -> str:
    if not mime_type:
        return fallback
    if mime_type in MIME_EXTENSIONS:
        return MIME_EXTENSIONS[mime_type]
    guessed = mimetypes.guess_extension(mime_type)
    return guessed or fallback


class MediaStore:
    """Simpan berkas flyer dengan nama berbasis hash isi (idempoten)."""

    def __init__(self, media_dir: str | Path):
        self.root = Path(media_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, data: bytes, mime_type: str | None = None) -> Path:
        digest = hashlib.sha1(data).hexdigest()[:20]
        path = self.root / f"{digest}{extension_for(mime_type)}"
        if not path.exists():
            path.write_bytes(data)
        return path
