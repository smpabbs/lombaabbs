"""Handler bot: penerimaan forward, review queue, dan publikasi ke kanal."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from app.config import Settings
from app.extract import ExtractionError, Extractor, LombaExtract
from app.media import MediaStore
from app.publish import Publisher, PublishError, build_caption
from app.publish.formatter import CAPTION_LIMIT
from app.store import Database, find_duplicate
from app.store.dedup import dedup_key
from app.textutil import normalize_phone, parse_biaya, parse_date_id

logger = logging.getLogger(__name__)

FLYER_PATTERN = re.compile(r"#flyer\s+(\d+)", re.IGNORECASE)

#: Field yang boleh diperbaiki admin lewat JSON.
EDITABLE_FIELDS = (
    "judul",
    "penyelenggara",
    "kategori",
    "bidang",
    "kelas",
    "biaya",
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

HELP_PUBLIC = (
    "👋 Kirim atau *forward* poster informasi lomba SMP ke sini.\n\n"
    "Bot akan mengekstrak detailnya dan meneruskannya ke admin untuk ditayangkan "
    "di kanal. Pantau terus kanal kami ya!"
)

HELP_ADMIN = (
    "🛠 *Panel admin InfoLomba*\n\n"
    "• Forward poster / kirim teks info lomba → jadi draft untuk direview.\n"
    "• Kirim gambar dengan caption `#flyer <id>` → pasang flyer ke draft tersebut.\n"
    "• `/draft <id>` → tampilkan ulang draft.\n"
    "• `/recent [draft|published|rejected]` → daftar terbaru.\n\n"
    "Setiap draft dikirim dengan tombol ✅ Post / ✏️ Edit / 🗑️ Tolak."
)


def _settings(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    return context.bot_data["settings"]


def _db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    return context.bot_data["db"]


def _extractor(context: ContextTypes.DEFAULT_TYPE) -> Extractor:
    return context.bot_data["extractor"]


def _media(context: ContextTypes.DEFAULT_TYPE) -> MediaStore:
    return context.bot_data["media"]


def _publisher(context: ContextTypes.DEFAULT_TYPE) -> Publisher:
    return context.bot_data["publisher"]


def _is_admin(user_id: int | None, context: ContextTypes.DEFAULT_TYPE) -> bool:
    return user_id is not None and user_id in _settings(context).admin_ids


async def _download_image(
    message: Any, context: ContextTypes.DEFAULT_TYPE
) -> tuple[bytes, str] | None:
    """Ambil bytes gambar dari foto atau dokumen gambar."""
    if message.photo:
        tg_file = await context.bot.get_file(message.photo[-1].file_id)
        return bytes(await tg_file.download_as_bytearray()), "image/jpeg"
    document = message.document
    mime = getattr(document, "mime_type", None) if document else None
    if document and (mime or "").startswith("image/"):
        tg_file = await context.bot.get_file(document.file_id)
        return bytes(await tg_file.download_as_bytearray()), mime
    return None


def _review_keyboard(lomba_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Post", callback_data=f"pub:{lomba_id}"),
                InlineKeyboardButton("✏️ Edit", callback_data=f"edit:{lomba_id}"),
                InlineKeyboardButton("🗑️ Tolak", callback_data=f"rej:{lomba_id}"),
            ]
        ]
    )


def _flyer_source(row: Any) -> str | None:
    return row["flyer_file_id"] or row["flyer_local_path"] or row["flyer_url"]


async def _send_review(
    context: ContextTypes.DEFAULT_TYPE,
    chat_ids: list[int],
    row: Any,
    notes: list[str],
) -> None:
    """Kirim pratinjau draft ke admin beserta tombol review."""
    caption = build_caption(row)
    footer = "\n\n".join(notes)
    keyboard = _review_keyboard(row["id"])
    photo = _flyer_source(row)

    for chat_id in chat_ids:
        try:
            if photo:
                combined = caption + (f"\n\n{footer}" if footer else "")
                if len(combined) <= CAPTION_LIMIT:
                    await context.bot.send_photo(
                        chat_id, photo=photo, caption=combined, reply_markup=keyboard
                    )
                else:
                    await context.bot.send_photo(
                        chat_id, photo=photo, caption=caption, reply_markup=keyboard
                    )
                    if footer:
                        await context.bot.send_message(chat_id, footer)
            else:
                text = caption + (f"\n\n{footer}" if footer else "")
                await context.bot.send_message(chat_id, text=text, reply_markup=keyboard)
        except TelegramError as exc:
            logger.warning("Gagal mengirim pratinjau ke %s: %s", chat_id, exc)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if message is None:
        return
    text = HELP_ADMIN if _is_admin(user.id if user else None, context) else HELP_PUBLIC
    await message.reply_text(text, parse_mode="Markdown")


async def cmd_draft(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or not _is_admin(user.id if user else None, context):
        return
    args = context.args or []
    if not args or not args[0].isdigit():
        await message.reply_text("Pakai: /draft <id>")
        return
    row = _db(context).get(int(args[0]))
    if row is None:
        await message.reply_text("Draft tidak ditemukan.")
        return
    await _send_review(context, [message.chat_id], row, [f"🆔 Draft #{row['id']}"])


async def cmd_recent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or not _is_admin(user.id if user else None, context):
        return
    status = (context.args[0] if context.args else "").strip() or None
    rows = _db(context).recent(status, limit=10)
    if not rows:
        await message.reply_text("Belum ada data.")
        return
    lines = [f"#{row['id']} · {row['status']} · {row['judul']}" for row in rows]
    await message.reply_text("\n".join(lines))


def is_admin_editing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Filter: user admin sedang dalam mode perbaiki draft."""
    user = update.effective_user
    if not _is_admin(user.id if user else None, context):
        return False
    return bool(context.user_data) and "editing_id" in context.user_data


async def on_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    raw = (message.text or "").strip()
    if raw in {"/batal", "/cancel"}:
        context.user_data.pop("editing_id", None)
        await message.reply_text("Perbaikan dibatalkan.")
        return
    if not raw:
        return

    lomba_id = context.user_data.get("editing_id")
    db = _db(context)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        await message.reply_text("Bukan JSON yang valid. Kirim ulang atau /batal.")
        return
    if not isinstance(payload, dict):
        await message.reply_text("JSON harus berupa objek.")
        return

    fields = {key: value for key, value in payload.items() if key in EDITABLE_FIELDS}
    if not fields:
        await message.reply_text("Tidak ada field yang dikenal. Kirim ulang atau /batal.")
        return
    if fields.get("judul") is not None and not str(fields["judul"]).strip():
        await message.reply_text("Judul tidak boleh kosong. Kirim ulang atau /batal.")
        return

    current = db.get(lomba_id)
    if current is None:
        context.user_data.pop("editing_id", None)
        await message.reply_text("Draft sudah tidak ada.")
        return

    if "cp_kontak" in fields:
        fields["cp_wa"] = normalize_phone(str(fields["cp_kontak"] or ""))
    if "deadline" in fields:
        fields["deadline"] = parse_date_id(str(fields["deadline"] or ""))
    if "biaya" in fields:
        fields["biaya"] = _coerce_biaya(fields["biaya"])

    judul = str(fields.get("judul") or current["judul"])
    penyelenggara = fields.get("penyelenggara", current["penyelenggara"])
    fields["dedup_key"] = dedup_key(judul, penyelenggara)

    try:
        db.update(lomba_id, fields)
    except (sqlite3.IntegrityError, ValueError) as exc:
        await message.reply_text(f"Gagal menyimpan: {exc}")
        return

    context.user_data.pop("editing_id", None)
    await _send_review(
        context, [message.chat_id], db.get(lomba_id), [f"🆔 Draft #{lomba_id} (hasil edit)"]
    )


def _coerce_biaya(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    return parse_biaya(str(value))


def _edit_prompt(row: Any) -> str:
    current = {key: row[key] for key in EDITABLE_FIELDS if row[key] is not None}
    return (
        f"✏️ Kirim JSON koreksi untuk draft #{row['id']}. "
        "Hanya field yang kamu kirim yang diubah.\n\n"
        f"{json.dumps(current, ensure_ascii=False, indent=2)}\n\n"
        "Kirim /batal untuk membatalkan."
    )


async def _mark_reviewed(query: Any, note: str) -> None:
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except TelegramError as exc:
        logger.warning("Gagal menghapus tombol review: %s", exc)
    await query.message.reply_text(note)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if query is None:
        return
    if not _is_admin(user.id if user else None, context):
        await query.answer("Hanya admin yang bisa melakukan ini.", show_alert=True)
        return

    action, _, raw_id = (query.data or "").partition(":")
    if not raw_id.isdigit():
        await query.answer("Data tombol tidak dikenal.")
        return
    lomba_id = int(raw_id)
    db = _db(context)

    if action == "pub":
        try:
            message_id = await _publisher(context).publish(lomba_id)
        except PublishError as exc:
            await query.answer(f"Gagal: {exc}", show_alert=True)
            return
        await query.answer("Terbit ✅")
        await _mark_reviewed(query, f"✅ Draft #{lomba_id} terbit di kanal (pesan {message_id}).")
    elif action == "rej":
        db.set_status(lomba_id, "rejected")
        await query.answer("Ditolak")
        await _mark_reviewed(query, f"🗑️ Draft #{lomba_id} ditolak.")
    elif action == "edit":
        row = db.get(lomba_id)
        if row is None:
            await query.answer("Draft tidak ditemukan.", show_alert=True)
            return
        context.user_data["editing_id"] = lomba_id
        await query.answer()
        await query.message.reply_text(_edit_prompt(row))
    else:
        await query.answer("Aksi tidak dikenal.")


async def _attach_flyer(
    context: ContextTypes.DEFAULT_TYPE,
    lomba_id: int,
    message: Any,
    image: tuple[bytes, str],
) -> None:
    """Pasang flyer asli ke draft yang tadinya belum punya gambar."""
    db = _db(context)
    row = db.get(lomba_id)
    if row is None:
        await message.reply_text(f"Draft #{lomba_id} tidak ditemukan.")
        return
    data, mime = image
    path = _media(context).save_bytes(data, mime)
    file_id = message.photo[-1].file_id if message.photo else None
    db.attach_flyer(
        lomba_id,
        file_id=file_id,
        local_path=None if file_id else str(path),
        url=None,
    )
    await message.reply_text(f"✅ Flyer terpasang ke draft #{lomba_id}.")
    updated = db.get(lomba_id)
    admin_ids = sorted(_settings(context).admin_ids)
    await _send_review(context, admin_ids, updated, [f"🆔 Draft #{lomba_id} (flyer diperbarui)"])


async def on_submission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    user = update.effective_user
    admin = _is_admin(user.id if user else None, context)
    text = (message.text or message.caption or "").strip()

    image = await _download_image(message, context)

    if admin and image:
        match = FLYER_PATTERN.search(text)
        if match:
            await _attach_flyer(context, int(match.group(1)), message, image)
            return

    if not image and not text:
        await message.reply_text(
            "Kirim poster (foto) atau teks info lomba untuk ditambahkan."
        )
        return

    if not admin:
        await message.reply_text("⏳ Memproses…")

    try:
        if image:
            extract = await _extractor(context).from_image(image[0], image[1], caption=text)
        else:
            extract = await _extractor(context).from_text(text)
    except ExtractionError as exc:
        logger.warning("Ekstraksi gagal: %s", exc)
        await message.reply_text(f"❌ Gagal mengekstrak info lomba: {exc}")
        return
    except Exception as exc:  # noqa: BLE001 - laporkan kegagalan LLM ke pengguna
        logger.exception("Error tak terduga saat ekstraksi")
        await message.reply_text(f"❌ Terjadi error saat memproses: {exc}")
        return

    if not extract.is_smp:
        await message.reply_text("ℹ️ Info ini bukan untuk jenjang SMP, jadi dilewati.")
        return
    if not extract.judul:
        await message.reply_text(
            "❌ Judul lomba tidak terdeteksi. Coba kirim ulang dengan keterangan judul."
        )
        return

    await _store_draft(context, message, extract, image, admin)


async def _store_draft(
    context: ContextTypes.DEFAULT_TYPE,
    message: Any,
    extract: LombaExtract,
    image: tuple[bytes, str] | None,
    admin: bool,
) -> None:
    db = _db(context)
    fields = extract.to_fields()
    notes: list[str] = []

    if fields.get("sumber_url"):
        existing = db.find_by_sumber(fields["sumber_url"])
        if existing is not None:
            notes.append(
                f"⚠️ Sumber ini sudah ada di draft #{existing['id']} ({existing['status']})."
            )

    duplicate = db.find_by_dedup_key(fields["dedup_key"])
    if duplicate is None:
        fuzzy = find_duplicate(db.candidates(), extract.judul, extract.penyelenggara)
        duplicate = fuzzy[0] if fuzzy else None
    if duplicate is not None:
        notes.append(f"⚠️ Mirip dengan #{duplicate['id']} · {duplicate['judul']}")

    fields["needs_flyer"] = 1
    if image:
        path = _media(context).save_bytes(image[0], image[1])
        fields["needs_flyer"] = 0
        if message.photo:
            fields["flyer_file_id"] = message.photo[-1].file_id
        else:
            fields["flyer_local_path"] = str(path)

    try:
        lomba_id = db.insert(fields)
    except (sqlite3.IntegrityError, ValueError) as exc:
        await message.reply_text(f"❌ Gagal menyimpan draft: {exc}")
        return

    submitter = "admin"
    if update_user := message.from_user:
        handle = f"@{update_user.username}" if update_user.username else None
        submitter = update_user.full_name or handle or "pengguna"
    notes.insert(0, f"🆔 Draft #{lomba_id} · dari {submitter}")

    row = db.get(lomba_id)
    admin_ids = sorted(_settings(context).admin_ids)
    if admin_ids:
        await _send_review(context, admin_ids, row, notes)

    if not admin:
        await message.reply_text(
            "✅ Info lomba terkirim untuk direview admin. Terima kasih!"
        )
