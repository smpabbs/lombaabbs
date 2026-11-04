"""CLI situs statis.

    python -m app.web          # isi snapshot kalau perlu, lalu bangun situs
    python -m app.web seed     # hanya isi snapshot
    python -m app.web build    # hanya bangun situs

Sengaja membaca DB_PATH/MEDIA_DIR langsung dari environment, tanpa lewat
`app.config.get_settings()`, supaya membangun situs tidak perlu token Telegram
atau kunci LLM.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from app.store.db import Database
from app.web.build import DEFAULT_TITLE, build_site
from app.web.seed import CATATAN_KURANG, SNAPSHOT_DATE, seed

DEFAULT_DB = "data/infolomba.db"
DEFAULT_MEDIA = "data/media"
DEFAULT_OUT = "site"


def _default_db() -> Path:
    return Path(os.getenv("DB_PATH", DEFAULT_DB))


def _default_media() -> Path:
    return Path(os.getenv("MEDIA_DIR", DEFAULT_MEDIA))


def _run_seed(db: Database) -> None:
    new_ids = seed(db)
    print(f"Snapshot {SNAPSHOT_DATE}: {len(new_ids)} entri baru disisipkan.")
    if CATATAN_KURANG:
        print("Yang masih kurang di tiap entri:")
        for judul, note in CATATAN_KURANG.items():
            print(f"  - {judul}: {note}")
    print(f"Total di database: {db.counts() or 'kosong'}")


def _run_build(db: Database, out_dir: Path, media_dir: Path) -> None:
    index = build_site(db, out_dir, media_dir=media_dir)
    print(f"Situs dibangun: {index.resolve()}")
    print("Buka file itu di peramban (klik dua kali) untuk melihat hasilnya.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app.web", description="Bangun situs statis dari basis data InfoLomba."
    )
    parser.add_argument(
        "aksi", nargs="?", choices=("semua", "seed", "build"), default="semua"
    )
    parser.add_argument("--db", type=Path, default=None, help=f"path DB (default {DEFAULT_DB})")
    parser.add_argument("--media", type=Path, default=None, help="folder media flyer")
    parser.add_argument("--out", type=Path, default=Path(DEFAULT_OUT), help="folder keluaran")
    parser.add_argument("--judul", default=DEFAULT_TITLE, help="judul halaman")
    args = parser.parse_args(argv)

    db = Database(args.db or _default_db())
    media_dir = args.media or _default_media()

    if args.aksi in ("semua", "seed"):
        _run_seed(db)
    if args.aksi in ("semua", "build"):
        _run_build(db, args.out, media_dir)


if __name__ == "__main__":
    main()
