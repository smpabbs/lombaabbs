"""Titik masuk bot InfoLomba (long polling, tanpa webhook)."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.bot import handlers
from app.config import Settings, get_settings
from app.extract import Extractor
from app.media import MediaStore
from app.publish import Publisher
from app.store import Database

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def build_application(settings: Settings | None = None) -> Application:
    settings = settings or get_settings()
    db = Database(settings.db_path)

    application = ApplicationBuilder().token(settings.bot_token).build()
    application.bot_data["settings"] = settings
    application.bot_data["db"] = db
    application.bot_data["extractor"] = Extractor(settings)
    application.bot_data["media"] = MediaStore(settings.media_dir)
    application.bot_data["publisher"] = Publisher(application.bot, db, settings)

    application.add_handler(CommandHandler(["start", "help"], handlers.cmd_help))
    application.add_handler(CommandHandler("draft", handlers.cmd_draft))
    application.add_handler(CommandHandler("recent", handlers.cmd_recent))
    # Harus terdaftar sebelum handler submission agar koreksi admin tidak
    # diperlakukan sebagai forward lomba baru.
    application.add_handler(
        MessageHandler(filters.TEXT & handlers.is_admin_editing, handlers.on_edit_text)
    )
    application.add_handler(CallbackQueryHandler(handlers.on_callback))
    application.add_handler(
        MessageHandler(
            filters.UpdateType.MESSAGE
            & ~filters.COMMAND
            & (filters.TEXT | filters.PHOTO | filters.Document.IMAGE),
            handlers.on_submission,
        )
    )
    return application


def main() -> None:
    application = build_application()
    logger.info("InfoLomba bot berjalan — mode long polling.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
