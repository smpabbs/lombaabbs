"""Skema data lomba hasil ekstraksi LLM, plus normalisasi ke kolom database."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.store.dedup import dedup_key
from app.textutil import clean_url, normalize_phone, parse_biaya, parse_date_id

_TEXT_FIELDS = (
    "judul",
    "penyelenggara",
    "kategori",
    "bidang",
    "kelas",
    "biaya_text",
    "hadiah",
    "ringkasan",
    "tgl_lomba",
    "deadline",
    "lokasi",
    "link_daftar",
    "cp_nama",
    "cp_kontak",
    "sumber_url",
)


class LombaExtract(BaseModel):
    """Hasil ekstraksi. Semua field opsional kecuali `is_smp`."""

    is_smp: bool = Field(default=False, description="True kalau lomba untuk jenjang SMP/MTs")
    judul: str | None = None
    penyelenggara: str | None = None
    kategori: str | None = Field(default=None, description="akademik atau non-akademik")
    bidang: str | None = None
    kelas: str | None = None
    biaya_text: str | None = Field(default=None, description="Teks biaya apa adanya")
    hadiah: str | None = None
    ringkasan: str | None = None
    tgl_lomba: str | None = None
    deadline: str | None = Field(default=None, description="ISO YYYY-MM-DD bila diketahui")
    lokasi: str | None = None
    link_daftar: str | None = None
    cp_nama: str | None = None
    cp_kontak: str | None = None
    sumber_url: str | None = None

    @field_validator(*_TEXT_FIELDS, mode="before")
    @classmethod
    def _coerce_text(cls, value: Any) -> Any:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, str):
            return value.strip() or None
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, (list, tuple)):
            joined = ", ".join(str(item).strip() for item in value if str(item).strip())
            return joined or None
        return value

    @field_validator("is_smp", mode="before")
    @classmethod
    def _coerce_bool(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() in {"true", "ya", "yes", "1", "smp"}
        return value

    @field_validator("kategori")
    @classmethod
    def _normalize_kategori(cls, value: str | None) -> str | None:
        if not value:
            return None
        text = value.lower()
        if "non" in text or "ekstra" in text:
            return "non-akademik"
        if "akadem" in text:
            return "akademik"
        return None

    def to_fields(self, sumber_url: str | None = None) -> dict[str, Any]:
        """Ubah ke dict siap dimasukkan ke database."""
        return {
            "judul": self.judul,
            "penyelenggara": self.penyelenggara,
            "kategori": self.kategori,
            "bidang": self.bidang,
            "jenjang": "SMP",
            "kelas": self.kelas,
            "biaya": parse_biaya(self.biaya_text),
            "hadiah": self.hadiah,
            "ringkasan": self.ringkasan,
            "tgl_lomba": self.tgl_lomba,
            "deadline": parse_date_id(self.deadline),
            "lokasi": self.lokasi,
            "link_daftar": clean_url(self.link_daftar),
            "cp_nama": self.cp_nama,
            "cp_kontak": self.cp_kontak,
            "cp_wa": normalize_phone(self.cp_kontak),
            "sumber_url": clean_url(sumber_url or self.sumber_url),
            "dedup_key": dedup_key(self.judul, self.penyelenggara),
            "status": "draft",
        }
