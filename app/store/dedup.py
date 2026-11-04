"""Deteksi lomba ganda lintas sumber."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from difflib import SequenceMatcher
from typing import Any

#: Ambang skor gabungan untuk dianggap lomba yang sama.
THRESHOLD = 0.87
#: Skor minimum kemiripan judul; mencegah match liar saat penyelenggara kosong.
JUDUL_FLOOR = 0.70

_NON_ALNUM = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE = re.compile(r"\s+", re.UNICODE)


def normalize_text(value: str | None) -> str:
    """Huruf kecil, buang tanda baca, rapikan spasi."""
    if not value:
        return ""
    text = _NON_ALNUM.sub(" ", value.lower())
    return _WHITESPACE.sub(" ", text).strip()


def dedup_key(judul: str | None, penyelenggara: str | None) -> str:
    return f"{normalize_text(judul)}|{normalize_text(penyelenggara)}"


def similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def match_score(
    judul: str | None,
    penyelenggara: str | None,
    other_judul: str | None,
    other_penyelenggara: str | None,
) -> float:
    """Skor gabungan 0..1 antara dua kandidat lomba."""
    judul_score = similarity(normalize_text(judul), normalize_text(other_judul))
    left_peny = normalize_text(penyelenggara)
    right_peny = normalize_text(other_penyelenggara)
    # Kalau salah satu penyelenggara tidak diketahui, jangan menaikkan skor:
    # pakai skor judul sebagai gantinya.
    peny_score = similarity(left_peny, right_peny) if (left_peny and right_peny) else judul_score
    return 0.65 * judul_score + 0.35 * peny_score


def find_duplicate(
    candidates: Iterable[Mapping[str, Any]],
    judul: str | None,
    penyelenggara: str | None,
    *,
    threshold: float = THRESHOLD,
) -> tuple[Mapping[str, Any], float] | None:
    """Kembalikan (kandidat, skor) paling mirip kalau di atas ambang, selain itu None."""
    best: tuple[Mapping[str, Any], float] | None = None
    for candidate in candidates:
        score = match_score(
            judul, penyelenggara, candidate["judul"], candidate["penyelenggara"]
        )
        if score < threshold:
            continue
        judul_score = similarity(normalize_text(judul), normalize_text(candidate["judul"]))
        if judul_score < JUDUL_FLOOR:
            continue
        if best is None or score > best[1]:
            best = (candidate, score)
    return best
