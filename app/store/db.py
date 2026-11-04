"""Penyimpanan SQLite + FTS5 untuk data lomba."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.textutil import fts_query

COLUMNS: tuple[str, ...] = (
    "judul",
    "penyelenggara",
    "kategori",
    "bidang",
    "jenjang",
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
    "cp_wa",
    "sumber_url",
    "flyer_file_id",
    "flyer_url",
    "flyer_local_path",
    "flyer_kind",
    "needs_flyer",
    "status",
    "dedup_key",
    "channel_message_id",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS lomba (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  judul TEXT NOT NULL,
  penyelenggara TEXT,
  kategori TEXT,
  bidang TEXT,
  jenjang TEXT DEFAULT 'SMP',
  kelas TEXT,
  biaya INTEGER,
  hadiah TEXT,
  ringkasan TEXT,
  tgl_lomba TEXT,
  deadline TEXT,
  lokasi TEXT,
  link_daftar TEXT,
  cp_nama TEXT,
  cp_kontak TEXT,
  cp_wa TEXT,
  sumber_url TEXT,
  flyer_file_id TEXT,
  flyer_url TEXT,
  flyer_local_path TEXT,
  flyer_kind TEXT,
  needs_flyer INTEGER DEFAULT 0,
  status TEXT DEFAULT 'draft',
  dedup_key TEXT,
  channel_message_id INTEGER,
  created_at TEXT,
  updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_lomba_status ON lomba(status);
CREATE INDEX IF NOT EXISTS idx_lomba_dedup ON lomba(dedup_key);
CREATE INDEX IF NOT EXISTS idx_lomba_deadline ON lomba(deadline);
CREATE UNIQUE INDEX IF NOT EXISTS idx_lomba_sumber ON lomba(sumber_url)
  WHERE sumber_url IS NOT NULL;

CREATE VIRTUAL TABLE IF NOT EXISTS lomba_fts USING fts5(
  judul, penyelenggara, bidang, hadiah, ringkasan, lokasi,
  content='lomba', content_rowid='id', tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS lomba_ai AFTER INSERT ON lomba BEGIN
  INSERT INTO lomba_fts(rowid, judul, penyelenggara, bidang, hadiah, ringkasan, lokasi)
  VALUES (new.id, new.judul, new.penyelenggara, new.bidang, new.hadiah, new.ringkasan, new.lokasi);
END;

CREATE TRIGGER IF NOT EXISTS lomba_ad AFTER DELETE ON lomba BEGIN
  INSERT INTO lomba_fts(lomba_fts, rowid, judul, penyelenggara, bidang, hadiah, ringkasan, lokasi)
  VALUES ('delete', old.id, old.judul, old.penyelenggara, old.bidang,
          old.hadiah, old.ringkasan, old.lokasi);
END;

CREATE TRIGGER IF NOT EXISTS lomba_au AFTER UPDATE ON lomba BEGIN
  INSERT INTO lomba_fts(lomba_fts, rowid, judul, penyelenggara, bidang, hadiah, ringkasan, lokasi)
  VALUES ('delete', old.id, old.judul, old.penyelenggara, old.bidang,
          old.hadiah, old.ringkasan, old.lokasi);
  INSERT INTO lomba_fts(rowid, judul, penyelenggara, bidang, hadiah, ringkasan, lokasi)
  VALUES (new.id, new.judul, new.penyelenggara, new.bidang, new.hadiah, new.ringkasan, new.lokasi);
END;
"""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Database:
    """Akses SQLite. Satu koneksi per operasi, aman untuk pemakaian async single-thread."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            self._migrate(conn)

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Lengkapi kolom baru pada basis data yang dibuat versi lama.

        `CREATE TABLE IF NOT EXISTS` tidak mengubah tabel yang sudah ada, jadi
        kolom yang ditambahkan belakangan harus dipasang lewat ALTER.
        """
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(lomba)")}
        if "flyer_kind" not in existing:
            conn.execute("ALTER TABLE lomba ADD COLUMN flyer_kind TEXT")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _clean(fields: Mapping[str, Any]) -> dict[str, Any]:
        unknown = set(fields) - set(COLUMNS)
        if unknown:
            raise ValueError(f"Kolom tidak dikenal: {sorted(unknown)}")
        return {key: fields[key] for key in fields if fields[key] is not None}

    def insert(self, fields: Mapping[str, Any]) -> int:
        data = self._clean(fields)
        if not data.get("judul"):
            raise ValueError("judul wajib diisi")
        data.setdefault("status", "draft")
        data.setdefault("jenjang", "SMP")
        data["created_at"] = _now()
        data["updated_at"] = data["created_at"]
        names = ", ".join(data)
        placeholders = ", ".join("?" for _ in data)
        with self._connect() as conn:
            cur = conn.execute(
                f"INSERT INTO lomba ({names}) VALUES ({placeholders})", list(data.values())
            )
            return int(cur.lastrowid)

    def update(self, lomba_id: int, fields: Mapping[str, Any]) -> None:
        data = self._clean(fields)
        if not data:
            return
        data["updated_at"] = _now()
        assignments = ", ".join(f"{key} = ?" for key in data)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE lomba SET {assignments} WHERE id = ?",
                [*data.values(), lomba_id],
            )

    def set_status(self, lomba_id: int, status: str) -> None:
        self.update(lomba_id, {"status": status})

    def get(self, lomba_id: int) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM lomba WHERE id = ?", (lomba_id,)).fetchone()

    def find_by_dedup_key(self, key: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM lomba WHERE dedup_key = ? AND status != 'rejected' LIMIT 1",
                (key,),
            ).fetchone()

    def find_by_sumber(self, sumber_url: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM lomba WHERE sumber_url = ? LIMIT 1", (sumber_url,)
            ).fetchone()

    def candidates(self, limit: int = 500) -> Sequence[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT id, judul, penyelenggara FROM lomba "
                "WHERE status != 'rejected' ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()

    def recent(self, status: str | None = None, limit: int = 10) -> Sequence[sqlite3.Row]:
        with self._connect() as conn:
            if status:
                return conn.execute(
                    "SELECT * FROM lomba WHERE status = ? ORDER BY id DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            return conn.execute(
                "SELECT * FROM lomba ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()

    def search(
        self, query: str, limit: int = 10, status: str = "published"
    ) -> Sequence[sqlite3.Row]:
        match = fts_query(query)
        if not match:
            return []
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT l.* FROM lomba l
                JOIN (SELECT rowid, rank FROM lomba_fts WHERE lomba_fts MATCH ?) f
                  ON f.rowid = l.id
                WHERE l.status = ?
                ORDER BY f.rank
                LIMIT ?
                """,
                (match, status, limit),
            ).fetchall()

    def attach_flyer(
        self,
        lomba_id: int,
        *,
        file_id: str | None = None,
        url: str | None = None,
        local_path: str | None = None,
    ) -> None:
        self.update(
            lomba_id,
            {
                "flyer_file_id": file_id,
                "flyer_url": url,
                "flyer_local_path": local_path,
                "flyer_kind": "poster",
                "needs_flyer": 0,
            },
        )

    def counts(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS total FROM lomba GROUP BY status"
            ).fetchall()
        return {row["status"]: row["total"] for row in rows}
