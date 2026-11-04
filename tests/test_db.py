import sqlite3

import pytest

from app.store.db import Database


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "test.db")


def test_insert_and_get(db):
    lomba_id = db.insert({"judul": "Lomba Matematika SMP", "penyelenggara": "UI"})
    row = db.get(lomba_id)
    assert row["judul"] == "Lomba Matematika SMP"
    assert row["jenjang"] == "SMP"
    assert row["status"] == "draft"
    assert row["created_at"] and row["updated_at"]


def test_insert_requires_judul(db):
    with pytest.raises(ValueError):
        db.insert({"penyelenggara": "UI"})


def test_insert_rejects_unknown_column(db):
    with pytest.raises(ValueError, match="tidak_dikenal"):
        db.insert({"judul": "X", "tidak_dikenal": 1})


def test_insert_keeps_zero_values(db):
    lomba_id = db.insert({"judul": "Gratis", "biaya": 0, "needs_flyer": 0})
    row = db.get(lomba_id)
    assert row["biaya"] == 0
    assert row["needs_flyer"] == 0


def test_set_status_and_recent(db):
    first = db.insert({"judul": "A"})
    db.insert({"judul": "B", "status": "published"})
    db.set_status(first, "published")
    assert [row["judul"] for row in db.recent("published")] == ["B", "A"]
    assert db.get(first)["status"] == "published"


def test_search_returns_only_published(db):
    db.insert({"judul": "Olimpiade Matematika Nasional", "status": "published"})
    db.insert({"judul": "Matematika Tingkat Kabupaten", "status": "draft"})
    results = db.search("matematika")
    assert [row["judul"] for row in results] == ["Olimpiade Matematika Nasional"]


def test_search_matches_ringkasan_and_bidang(db):
    db.insert(
        {
            "judul": "Kompetisi Sains",
            "bidang": "robotik",
            "ringkasan": "Membuat robot line follower",
            "status": "published",
        }
    )
    assert len(db.search("robotik")) == 1
    assert len(db.search("line follower")) == 1


def test_search_handles_syntax_characters(db):
    db.insert({"judul": "Lomba Robotik", "status": "published"})
    # Tanda kutip/kurung dikutip sebagai token, jadi tidak memicu error sintaks FTS5.
    assert db.search('"()*') == []
    # Kata kunci operator FTS5 dibuang sebagai stopword, bukan dianggap operator.
    assert db.search("NOT *") == []
    assert len(db.search('robotik" OR (')) == 1


def test_search_empty_query(db):
    db.insert({"judul": "Apa saja", "status": "published"})
    assert db.search("   ") == []
    assert db.search("dan atau") == []


def test_fts_index_updated_on_update(db):
    lomba_id = db.insert({"judul": "Lomba Lama", "status": "published"})
    db.update(lomba_id, {"judul": "Lomba Baru"})
    assert db.search("lama") == []
    assert len(db.search("baru")) == 1


def test_fts_index_cleared_on_delete(db):
    lomba_id = db.insert({"judul": "Lomba Sekali", "status": "published"})
    with db._connect() as conn:
        conn.execute("DELETE FROM lomba WHERE id = ?", (lomba_id,))
    assert db.search("sekali") == []


def test_sumber_url_is_unique(db):
    db.insert({"judul": "A", "sumber_url": "https://contoh.id/1"})
    with pytest.raises(sqlite3.IntegrityError):
        db.insert({"judul": "B", "sumber_url": "https://contoh.id/1"})


def test_find_by_sumber(db):
    db.insert({"judul": "A", "sumber_url": "https://contoh.id/1"})
    assert db.find_by_sumber("https://contoh.id/1")["judul"] == "A"
    assert db.find_by_sumber("https://contoh.id/2") is None


def test_find_by_dedup_key_ignores_rejected(db):
    lomba_id = db.insert({"judul": "A", "dedup_key": "a|b"})
    assert db.find_by_dedup_key("a|b") is not None
    db.set_status(lomba_id, "rejected")
    assert db.find_by_dedup_key("a|b") is None


def test_attach_flyer_clears_needs_flyer(db):
    lomba_id = db.insert({"judul": "A", "needs_flyer": 1})
    db.attach_flyer(lomba_id, file_id="FILEID")
    row = db.get(lomba_id)
    assert row["flyer_file_id"] == "FILEID"
    assert row["needs_flyer"] == 0
    assert row["flyer_local_path"] is None


def test_attach_flyer_marks_kind_as_poster(db):
    # Draft yang tadinya cuma berpaut logo naik kelas begitu poster asli dipasang.
    lomba_id = db.insert({"judul": "A", "flyer_kind": "logo"})
    db.attach_flyer(lomba_id, file_id="FILEID")
    assert db.get(lomba_id)["flyer_kind"] == "poster"


def test_migrates_legacy_db_without_flyer_kind(tmp_path):
    from app.store.db import SCHEMA

    path = tmp_path / "legacy.db"
    legacy = "\n".join(line for line in SCHEMA.splitlines() if "flyer_kind" not in line)
    conn = sqlite3.connect(path)
    conn.executescript(legacy)
    conn.commit()
    conn.close()

    db = Database(path)  # membuka basis data lama harus memasang kolom baru
    with db._connect() as conn:
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(lomba)")}
    assert "flyer_kind" in cols
    assert db.get(db.insert({"judul": "X", "flyer_kind": "logo"}))["flyer_kind"] == "logo"


def test_candidates_excludes_rejected(db):
    db.insert({"judul": "A"})
    rejected = db.insert({"judul": "B"})
    db.set_status(rejected, "rejected")
    assert [row["judul"] for row in db.candidates()] == ["A"]


def test_counts(db):
    db.insert({"judul": "A"})
    db.insert({"judul": "B", "status": "published"})
    assert db.counts() == {"draft": 1, "published": 1}
