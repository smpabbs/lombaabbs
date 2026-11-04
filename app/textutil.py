"""Normalisasi teks: nomor kontak, biaya, tanggal, dan tokenisasi FTS."""

from __future__ import annotations

import re
from datetime import date, timedelta

MONTHS_ID = [
    "januari", "februari", "maret", "april", "mei", "juni",
    "juli", "agustus", "september", "oktober", "november", "desember",
]
MONTHS_SHORT_ID = [
    "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
    "Jul", "Agu", "Sep", "Okt", "Nov", "Des",
]

_MONTH_LOOKUP: dict[str, int] = {}
for _index, _name in enumerate(MONTHS_ID, start=1):
    _MONTH_LOOKUP[_name] = _index
    _MONTH_LOOKUP[_name[:3]] = _index
_MONTH_LOOKUP.update({"agu": 8, "ags": 8, "okt": 10, "des": 12})

_FREE_RE = re.compile(r"\b(gratis|free|tanpa\s+biaya|no\s+fee|tidak\s+dipungut)\b", re.IGNORECASE)
_AMOUNT_RE = re.compile(
    r"(?:rp\.?\s*)?(\d[\d.,]*)\s*(rb|ribu|k|jt|juta|m)\b|(?:rp\.?\s*)(\d[\d.,]*)",
    re.IGNORECASE,
)
_BARE_NUMBER_RE = re.compile(r"\d[\d.,]*")
_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_NUM_DATE_RE = re.compile(r"\b(\d{1,2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{2,4})\b")
_TEXT_DATE_RE = re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?\s*(\d{4})?\b")
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)

MULTIPLIERS = {
    "rb": 1_000,
    "ribu": 1_000,
    "k": 1_000,
    "jt": 1_000_000,
    "juta": 1_000_000,
    "m": 1_000_000,
}


def normalize_phone(raw: str | None) -> str | None:
    """Ubah nomor seluler Indonesia menjadi format 62xxxxxxxxxx, atau None.

    Hanya menerima nomor seluler (awalan 8) karena dipakai untuk tautan WhatsApp;
    nomor rumah/kantor seperti 021-… ditolak.
    """
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    if digits.startswith("620"):
        national = digits[3:]
    elif digits.startswith("62"):
        national = digits[2:]
    elif digits.startswith("0"):
        national = digits[1:]
    else:
        national = digits
    if not national.startswith("8"):
        return None
    normalized = "62" + national
    if not 10 <= len(normalized) <= 15:
        return None
    return normalized


def whatsapp_url(raw: str | None) -> str | None:
    phone = normalize_phone(raw)
    return f"https://wa.me/{phone}" if phone else None


def _to_float(number: str) -> float | None:
    number = number.strip().rstrip(".,")
    if not number:
        return None
    if "," in number and "." in number:
        number = number.replace(".", "").replace(",", ".")
    elif "," in number:
        number = number.replace(",", ".")
    elif "." in number:
        parts = number.split(".")
        if len(parts) > 2 or len(parts[-1]) == 3:
            number = number.replace(".", "")
    try:
        return float(number)
    except ValueError:
        return None


def parse_biaya(text: str | None) -> int | None:
    """Tebak biaya pendaftaran dalam rupiah. 0 berarti gratis."""
    if not text:
        return None
    if _FREE_RE.search(text):
        return 0
    # Field biaya yang isinya murni angka (mis. LLM mengembalikan 50000).
    if _BARE_NUMBER_RE.fullmatch(text.strip()):
        value = _to_float(text.strip())
        return int(value) if value is not None else None
    match = _AMOUNT_RE.search(text)
    if not match:
        return None
    raw_number = match.group(1) or match.group(3)
    if not raw_number:
        return None
    value = _to_float(raw_number)
    if value is None:
        return None
    suffix = (match.group(2) or "").lower()
    if suffix:
        value *= MULTIPLIERS.get(suffix, 1)
    elif value < 1000 and "rp" not in text.lower():
        return None
    return int(value)


def _build_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _resolve_year(year_text: str | None, month: int, day: int, today: date) -> date | None:
    if year_text:
        year = int(year_text)
        if year < 100:
            year += 2000
        return _build_date(year, month, day)
    candidate = _build_date(today.year, month, day)
    if candidate and candidate < today - timedelta(days=30):
        candidate = _build_date(today.year + 1, month, day)
    return candidate


def parse_date_id(text: str | None, today: date | None = None) -> str | None:
    """Parse tanggal berbahasa Indonesia menjadi ISO (YYYY-MM-DD).

    Mendukung: 2026-11-12, 12/11/2026, 12-11-2026, "12 November 2026", "12 Nov 2026",
    serta tanpa tahun (diasumsikan tahun terdekat ke depan).
    """
    if not text:
        return None
    today = today or date.today()
    found: date | None = None

    if match := _ISO_DATE_RE.search(text):
        found = _build_date(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    if found is None and (match := _NUM_DATE_RE.search(text)):
        day, month = int(match.group(1)), int(match.group(2))
        if day > 12 and month <= 12:
            pass
        elif month > 12 and day <= 12:
            day, month = month, day
        found = _resolve_year(match.group(3), month, day, today)

    if found is None and (match := _TEXT_DATE_RE.search(text)):
        month = _MONTH_LOOKUP.get(match.group(2).lower())
        if month:
            found = _resolve_year(match.group(3), month, int(match.group(1)), today)

    return found.isoformat() if found else None


def format_date_id(iso: str | None) -> str | None:
    if not iso:
        return None
    try:
        parsed = date.fromisoformat(iso)
    except ValueError:
        return None
    return f"{parsed.day} {MONTHS_SHORT_ID[parsed.month - 1]} {parsed.year}"


def days_until(iso: str | None, today: date | None = None) -> int | None:
    if not iso:
        return None
    try:
        target = date.fromisoformat(iso)
    except ValueError:
        return None
    return (target - (today or date.today())).days


def format_deadline(iso: str | None, today: date | None = None) -> str | None:
    """Contoh keluaran: '12 Nov 2026 (H-10)'."""
    pretty = format_date_id(iso)
    if not pretty:
        return None
    remaining = days_until(iso, today)
    if remaining is None:
        return pretty
    if remaining < 0:
        return f"{pretty} (ditutup)"
    if remaining == 0:
        return f"{pretty} (HARI INI)"
    return f"{pretty} (H-{remaining})"


def tokenize(text: str | None) -> list[str]:
    return _TOKEN_RE.findall(text or "")


_STOPWORDS = frozenset(
    {
        "dan", "atau", "yang", "untuk", "dengan", "pada", "dari", "di", "ke",
        "ini", "itu", "adalah", "serta", "bagi", "buat", "si", "sang",
        "the", "and", "or", "not", "near", "of", "in", "to", "for",
    }
)


def fts_query(text: str | None) -> str:
    """Bangun MATCH query FTS5 yang aman dari karakter sintaksis.

    Setiap token dikutip (jadi kata kunci FTS5 seperti OR/AND diperlakukan
    literal), dan kata fungsi umum dibuang supaya tidak memaksa AND yang
    mustahil cocok.
    """
    tokens = [token for token in tokenize(text) if token.lower() not in _STOPWORDS]
    return " ".join(f'"{token}"' for token in tokens)


_URL_RE = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)


def clean_url(value: str | None) -> str | None:
    """Ambil URL pertama yang valid dari sebuah teks, atau None."""
    if not value:
        return None
    candidate = value.strip()
    if match := _URL_RE.search(candidate):
        return match.group(0).rstrip(".,);]")
    # Sisanya hanya boleh domain telanjang (contoh.id/daftar). Skema lain
    # seperti ftp:// / mailto: ditolak, bukan dipaksa jadi https://.
    if "://" in candidate or " " in candidate or "." not in candidate:
        return None
    host, _, _ = candidate.lstrip("/").partition("/")
    if ":" in host:
        _, _, maybe_port = host.partition(":")
        if not maybe_port.isdigit():
            return None
    tld = host.rsplit(".", 1)[-1].split(":")[0]
    if len(tld) < 2 or not tld.isalpha():
        return None
    return f"https://{candidate.lstrip('/')}"


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit <= 1:
        return text[:limit]
    return text[: limit - 1].rstrip() + "…"
