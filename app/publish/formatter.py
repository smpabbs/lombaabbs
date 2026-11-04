"""Susun caption dan tombol inline untuk postingan kanal."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.textutil import clean_url, format_deadline, truncate, whatsapp_url

#: Batas karakter caption untuk pesan berfoto di Telegram.
CAPTION_LIMIT = 1024
#: Prioritas "jangan dibuang": blok wajib selalu dipertahankan.
KEEP_ALWAYS = 100
#: Prioritas blok opsional saat caption harus dipangkas (kecil = dibuang lebih dulu).
OPTIONAL_PRIORITY = {"ringkasan": 1, "tgl_lomba": 2, "hadiah": 3}


def _field(row: Any, name: str) -> Any:
    """Ambil kolom dari sqlite3.Row maupun dict, tanpa melempar error."""
    if row is None:
        return None
    try:
        return row[name]
    except (KeyError, IndexError, TypeError):
        return None


def _biaya_label(biaya: int | None) -> str | None:
    if biaya is None:
        return None
    if biaya == 0:
        return "Gratis"
    return f"Rp {biaya:,.0f}".replace(",", ".")


def _cp_label(nama: str | None, kontak: str | None) -> str | None:
    if nama and kontak:
        return f"{nama} — {kontak}"
    return nama or kontak


def _blocks(row: Any, today: date | None) -> list[dict[str, Any]]:
    """Blok caption berurutan. `priority` < KEEP_ALWAYS berarti boleh dibuang."""
    blocks: list[dict[str, Any]] = []

    def add(
        text: str | None,
        *,
        kind: str = "",
        required: bool = True,
        truncatable: bool = False,
    ) -> None:
        if not text:
            return
        priority = KEEP_ALWAYS if required else OPTIONAL_PRIORITY.get(kind, 1)
        blocks.append(
            {"text": text, "priority": priority, "truncatable": truncatable, "kind": kind}
        )

    judul = _field(row, "judul") or "Info Lomba SMP"
    header = [f"🎓 {judul}"]
    meta_parts = (_field(row, "penyelenggara"), _field(row, "bidang"))
    meta = " · ".join(part for part in meta_parts if part)
    if meta:
        header.append(f"🏫 {meta}")
    add("\n".join(header), required=True, truncatable=True)

    jenjang = _field(row, "jenjang") or "SMP"
    jenjang_line = f"👥 Jenjang: {jenjang}"
    if kelas := _field(row, "kelas"):
        jenjang_line += f" (Kelas {kelas})"
    if biaya := _biaya_label(_field(row, "biaya")):
        jenjang_line += f" · 💰 {biaya}"
    add(jenjang_line)

    if hadiah := _field(row, "hadiah"):
        add(f"🏆 Hadiah: {hadiah}", kind="hadiah", required=False)
    if ringkasan := _field(row, "ringkasan"):
        add(f"📝 {ringkasan}", kind="ringkasan", required=False, truncatable=True)
    if tgl := _field(row, "tgl_lomba"):
        add(f"📅 Pelaksanaan: {tgl}", kind="tgl_lomba", required=False)
    if deadline := format_deadline(_field(row, "deadline"), today):
        add(f"⏰ Deadline: {deadline}")
    if lokasi := _field(row, "lokasi"):
        add(f"📍 {lokasi}")
    if cp := _cp_label(_field(row, "cp_nama"), _field(row, "cp_kontak")):
        add(f"📞 CP: {cp}")
    if daftar := _field(row, "link_daftar"):
        add(f"🔗 Daftar: {daftar}")
    if sumber := _field(row, "sumber_url"):
        add(f"📄 Sumber: {sumber}")

    return blocks


def build_caption(
    row: Any, *, today: date | None = None, limit: int = CAPTION_LIMIT
) -> str:
    """Bentuk caption yang dijamin tidak melebihi batas karakter Telegram."""
    kept = _blocks(row, today)

    def render() -> str:
        return "\n".join(block["text"] for block in kept)

    while len(render()) > limit:
        droppable = [block for block in kept if block["priority"] < KEEP_ALWAYS]
        if not droppable:
            break
        kept.remove(min(droppable, key=lambda block: block["priority"]))

    for block in kept:
        text = render()
        if len(text) <= limit:
            break
        if not block["truncatable"]:
            continue
        overflow = len(text) - limit
        block["text"] = truncate(block["text"], max(12, len(block["text"]) - overflow))

    return truncate(render(), limit)


def build_keyboard(row: Any) -> InlineKeyboardMarkup | None:
    """Tombol Daftar / Chat CP / Sumber — hanya kalau URL-nya valid."""
    buttons: list[InlineKeyboardButton] = []
    if url := clean_url(_field(row, "link_daftar")):
        buttons.append(InlineKeyboardButton("🔗 Daftar", url=url))
    if wa := whatsapp_url(_field(row, "cp_wa") or _field(row, "cp_kontak")):
        buttons.append(InlineKeyboardButton("📞 Chat CP", url=wa))
    if sumber := clean_url(_field(row, "sumber_url")):
        buttons.append(InlineKeyboardButton("📄 Sumber", url=sumber))
    return InlineKeyboardMarkup([buttons]) if buttons else None


def topic_thread_id(row: Any, topic_map: Mapping[str, int] | None) -> int | None:
    """Cari message_thread_id berdasarkan kategori lalu bidang."""
    if not topic_map:
        return None
    for key in (_field(row, "kategori"), _field(row, "bidang")):
        if not key:
            continue
        thread = topic_map.get(str(key).strip().lower())
        if thread:
            return int(thread)
    return None
