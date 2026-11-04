from datetime import date

import pytest

from app.store.db import Database
from app.web.build import build_site, render_card, render_page
from app.web.seed import CATATAN_KURANG, SEED, seed

TODAY = date(2026, 11, 4)


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "test.db")


def test_render_page_empty_database():
    page = render_page([])
    assert "belum ada data" in page
    assert 'id="empty"' in page
    assert "<article" not in page


def test_render_page_escapes_untrusted_fields():
    row = {
        "judul": '<script>alert("xss")</script>',
        "penyelenggara": 'Kampus "Nakal" & Co',
        "kategori": "akademik",
        "status": "published",
    }
    page = render_page([row], today=TODAY)
    assert "<script>alert" not in page
    assert "&lt;script&gt;" in page
    assert "&quot;Nakal&quot;" in page
    assert "&amp; Co" in page


def test_render_card_escapes_title_in_alt_and_attributes():
    row = {"judul": 'Lomba "Gede" <b>', "flyer_url": "https://x.id/a.png"}
    html = render_card(row, today=TODAY)
    assert "<b>" not in html
    assert 'alt="Flyer resmi Lomba &quot;Gede&quot; &lt;b&gt;"' in html


def test_render_card_without_flyer_shows_placeholder(db):
    lomba_id = db.insert({"judul": "Tanpa Poster", "status": "published"})
    html = render_card(db.get(lomba_id), today=TODAY)
    assert "<img" not in html
    assert "nophoto" in html
    assert "belum tersedia" in html


def test_render_card_uses_local_media_when_available(db):
    lomba_id = db.insert(
        {
            "judul": "Ada Poster",
            "status": "published",
            "flyer_local_path": "data/media/abc123.png",
        }
    )
    html = render_card(db.get(lomba_id), today=TODAY)
    assert 'src="media/abc123.png"' in html


def test_render_card_rejects_dangerous_registration_url(db):
    lomba_id = db.insert(
        {
            "judul": "Jebakan",
            "status": "published",
            "link_daftar": "javascript:alert(1)",
            "sumber_url": "mailto:panitia@contoh.id",
        }
    )
    html = render_card(db.get(lomba_id), today=TODAY)
    # Teks caption boleh memuat URL apa adanya (sudah di-escape), tapi tidak
    # boleh ada satu pun href dengan skema berbahaya.
    assert 'href="javascript:' not in html
    assert 'href="mailto:' not in html
    assert ">🔗 Daftar</a>" not in html
    assert ">📄 Sumber</a>" not in html
    assert 'class="btn primary"' not in html


def test_render_card_badge_for_deadline_states():
    open_row = {"judul": "A", "deadline": "2026-12-31"}
    soon_row = {"judul": "B", "deadline": "2026-11-06"}
    dead_row = {"judul": "C", "deadline": "2026-10-31"}
    none_row = {"judul": "D"}

    assert "Sisa 57 hari" in render_card(open_row, today=TODAY)
    assert "Sisa 2 hari" in render_card(soon_row, today=TODAY)
    assert "Pendaftaran ditutup" in render_card(dead_row, today=TODAY)
    assert "Tanpa deadline" in render_card(none_row, today=TODAY)


def test_render_card_marks_expired_only_when_deadline_passed():
    past = {"judul": "Sudah Tutup", "deadline": "2026-10-31"}
    future = {"judul": "Masih Buka", "deadline": "2026-12-31"}
    none_row = {"judul": "Tanpa Deadline"}

    assert "expired" in render_card(past, today=TODAY)
    assert "expired" not in render_card(future, today=TODAY)
    # Tanpa deadline bukan berarti kadaluarsa.
    assert "expired" not in render_card(none_row, today=TODAY)


def test_render_page_has_toggle_to_reveal_expired():
    page = render_page([{"judul": "A", "deadline": "2026-10-31"}], today=TODAY)
    assert 'id="showClosed"' in page
    assert "Tampilkan yang sudah tutup" in page


def test_render_page_chips_only_for_present_categories():
    rows = [
        {"judul": "A", "kategori": "akademik"},
        {"judul": "B", "kategori": "non-akademik"},
    ]
    page = render_page(rows, today=TODAY)
    assert 'data-kategori="semua"' in page
    assert 'data-kategori="akademik"' in page
    assert 'data-kategori="non-akademik"' in page
    assert 'data-kategori="olahraga"' not in page


def test_build_site_writes_index_and_excludes_rejected(db, tmp_path):
    db.insert({"judul": "Terbit", "status": "published"})
    db.insert({"judul": "Draf", "status": "draft"})
    rejected = db.insert({"judul": "Ditolak", "status": "rejected"})

    index = build_site(db, tmp_path / "site", today=TODAY)
    page = index.read_text(encoding="utf-8")

    assert index == tmp_path / "site" / "index.html"
    assert "Terbit" in page
    assert "Draf" in page
    assert "Ditolak" not in page
    assert db.get(rejected)["status"] == "rejected"


def test_build_site_copies_media_and_removes_empty_dir(db, tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    (media / "abc.png").write_bytes(b"PNG")
    db.insert(
        {
            "judul": "Ada Poster",
            "status": "published",
            "flyer_local_path": str(media / "abc.png"),
        }
    )

    out = tmp_path / "site"
    build_site(db, out, media_dir=media, today=TODAY)
    assert (out / "media" / "abc.png").read_bytes() == b"PNG"

    # Baris yang menunjuk berkas hilang tidak boleh meninggalkan folder media kosong.
    other = Database(tmp_path / "lain.db")
    other.insert(
        {
            "judul": "Hilang",
            "status": "published",
            "flyer_local_path": str(media / "tidak-ada.png"),
        }
    )
    out2 = tmp_path / "site2"
    build_site(other, out2, media_dir=tmp_path / "kosong", today=TODAY)
    assert not (out2 / "media").exists()


def test_seed_catatan_keys_match_judul_exactly():
    titles = [entry["judul"] for entry in SEED]
    assert sorted(CATATAN_KURANG) == sorted(titles)


def test_seed_flyer_urls_are_https_and_not_flagged_missing():
    """Tiap entri harus punya flyer resmi (https) ATAU ditandai `needs_flyer`.

    Tidak boleh keduanya sekaligus (sudah ada tapi masih ditandai kurang), dan
    tidak boleh tidak punya jejak sama sekali (tanpa flyer tapi tak ditandai).
    """
    for entry in SEED:
        flyer = entry.get("flyer_url")
        if flyer:
            assert flyer.startswith("https://"), entry["judul"]
            assert not entry.get("needs_flyer"), entry["judul"]
        else:
            assert entry.get("needs_flyer"), f"tanpa flyer tapi tak ditandai: {entry['judul']}"


def test_seed_logo_images_are_flagged_as_logo():
    """Entri yang gambarnya cuma logo resmi harus ditandai `flyer_kind=logo`."""
    for entry in SEED:
        if entry.get("flyer_kind") == "logo":
            assert entry.get("flyer_url"), entry["judul"]


def test_render_card_labels_logo_image_honestly(db):
    lomba_id = db.insert(
        {
            "judul": "Festival Logo",
            "status": "published",
            "flyer_url": "https://x.id/logo.png",
            "flyer_kind": "logo",
        }
    )
    html = render_card(db.get(lomba_id), today=TODAY)
    assert 'alt="Logo resmi Festival Logo"' in html
    assert "Flyer resmi" not in html
    assert "Poster resmi belum dirilis" in html


def test_seed_is_idempotent_and_keeps_provenance(db, tmp_path):
    assert len(seed(db)) == len(SEED)
    assert seed(db) == []

    for entry in SEED:
        row = db.find_by_sumber(entry["sumber_url"])
        assert row is not None, entry["judul"]
        assert row["status"] == "published"
        assert row["jenjang"] == "SMP"
        assert int(row["needs_flyer"] or 0) == int(entry.get("needs_flyer", 0))


def test_render_card_rejects_dangerous_flyer_url(db):
    lomba_id = db.insert(
        {"judul": "Poster Jebakan", "status": "published", "flyer_url": "javascript:alert(9)"}
    )
    html = render_card(db.get(lomba_id), today=TODAY)
    assert 'src="javascript:' not in html
    assert "nophoto" in html
