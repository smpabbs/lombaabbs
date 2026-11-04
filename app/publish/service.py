"""Kirim postingan lomba ke kanal Telegram."""

from __future__ import annotations

from telegram import Bot
from telegram.error import TelegramError

from app.config import Settings
from app.publish.formatter import build_caption, build_keyboard, topic_thread_id
from app.store.db import Database


class PublishError(RuntimeError):
    """Gagal mempublikasikan lomba ke kanal."""


class Publisher:
    """Publikasi memakai flyer resmi apa adanya — tidak pernah membuat gambar sendiri."""

    def __init__(self, bot: Bot, db: Database, settings: Settings):
        self._bot = bot
        self._db = db
        self._settings = settings

    async def publish(self, lomba_id: int) -> int:
        row = self._db.get(lomba_id)
        if row is None:
            raise PublishError(f"Draft #{lomba_id} tidak ditemukan")

        caption = build_caption(row)
        keyboard = build_keyboard(row)
        thread_id = topic_thread_id(row, self._settings.topic_map)
        # Flyer resmi penyelenggara: file_id Telegram lebih diprioritaskan,
        # lalu salinan lokal, terakhir URL gambar asli dari sumber.
        # Tidak pernah membuat gambar sendiri.
        photo = row["flyer_file_id"] or row["flyer_local_path"] or row["flyer_url"]

        try:
            if photo:
                message = await self._bot.send_photo(
                    chat_id=self._settings.channel_id,
                    photo=photo,
                    caption=caption,
                    reply_markup=keyboard,
                    message_thread_id=thread_id,
                )
            else:
                message = await self._bot.send_message(
                    chat_id=self._settings.channel_id,
                    text=caption,
                    reply_markup=keyboard,
                    message_thread_id=thread_id,
                )
        except TelegramError as exc:
            raise PublishError(f"Telegram menolak postingan #{lomba_id}: {exc}") from exc

        self._db.update(
            lomba_id,
            {"status": "published", "channel_message_id": message.message_id},
        )
        return message.message_id
