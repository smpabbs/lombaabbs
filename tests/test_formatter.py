from datetime import date

from app.publish.formatter import (
    CAPTION_LIMIT,
    build_caption,
    build_keyboard,
    topic_thread_id,
)

TODAY = date(2026, 11, 4)

ROW = {
    "id": 7,
    "judul": "Olimpiade Matematika Nasional 2026",
    "penyelenggara": "Universitas Indonesia",
    "bidang": "Matematika",
    "jenjang": "SMP",
    "kelas": "7-9",
    "biaya": 0,
    "hadiah": "Total Rp 20.000.000",
    "ringkasan": "Olimpiade matematika tingkat nasional untuk pelajar SMP.",
    "tgl_lomba": "20 Desember 2026",
    "deadline": "2026-11-12",
    "lokasi": "Online",
    "cp_nama": "Rani",
    "cp_kontak": "0812-3456-7890",
    "cp_wa": "6281234567890",
    "link_daftar": "https://contoh.id/daftar",
    "sumber_url": "https://contoh.id/info",
}


def test_caption_contains_all_key_lines():
    caption = build_caption(ROW, today=TODAY)
    assert caption.startswith("🎓 Olimpiade Matematika Nasional 2026")
    assert "🏫 Universitas Indonesia · Matematika" in caption
    assert "👥 Jenjang: SMP (Kelas 7-9) · 💰 Gratis" in caption
    assert "🏆 Hadiah: Total Rp 20.000.000" in caption
    assert "⏰ Deadline: 12 Nov 2026 (H-8)" in caption
    assert "📍 Online" in caption
    assert "📞 CP: Rani — 0812-3456-7890" in caption
    assert "🔗 Daftar: https://contoh.id/daftar" in caption
    assert "📄 Sumber: https://contoh.id/info" in caption


def test_caption_respects_telegram_limit():
    row = dict(ROW, ringkasan="x" * 900, hadiah="y" * 500)
    caption = build_caption(row, today=TODAY)
    assert len(caption) <= CAPTION_LIMIT
    assert "🔗 Daftar:" in caption
    assert "📄 Sumber:" in caption


def test_caption_drops_optional_before_truncating_required():
    row = dict(ROW, ringkasan="z" * 900)
    caption = build_caption(row, today=TODAY)
    assert "📝" not in caption
    assert "⏰ Deadline: 12 Nov 2026 (H-8)" in caption


def test_caption_truncates_long_judul():
    row = dict(ROW, judul="L" * 2000)
    caption = build_caption(row, today=TODAY)
    assert len(caption) <= CAPTION_LIMIT


def test_caption_without_deadline_and_lokasi():
    caption = build_caption(dict(ROW, deadline=None, lokasi=None), today=TODAY)
    assert "⏰" not in caption
    assert "📍" not in caption


def test_caption_handles_missing_optional_fields():
    caption = build_caption({"judul": "Lomba Puisi"}, today=TODAY)
    assert caption.startswith("🎓 Lomba Puisi")
    assert "👥 Jenjang: SMP" in caption
    assert "📄" not in caption


def test_caption_biaya_rendering():
    assert "💰 Gratis" in build_caption(dict(ROW, biaya=0), today=TODAY)
    assert "💰 Rp 50.000" in build_caption(dict(ROW, biaya=50_000), today=TODAY)
    assert "💰" not in build_caption(dict(ROW, biaya=None), today=TODAY)


def test_keyboard_builds_expected_buttons():
    keyboard = build_keyboard(ROW)
    buttons = keyboard.inline_keyboard[0]
    assert [button.text for button in buttons] == ["🔗 Daftar", "📞 Chat CP", "📄 Sumber"]
    assert [button.url for button in buttons] == [
        "https://contoh.id/daftar",
        "https://wa.me/6281234567890",
        "https://contoh.id/info",
    ]


def test_keyboard_none_without_any_url():
    assert build_keyboard({"judul": "Lomba Tanpa Info"}) is None


def test_keyboard_skips_invalid_cp():
    keyboard = build_keyboard(dict(ROW, cp_wa=None, cp_kontak="021-555"))
    assert [button.text for button in keyboard.inline_keyboard[0]] == ["🔗 Daftar", "📄 Sumber"]


def test_topic_thread_id_prefers_kategori_then_bidang():
    assert topic_thread_id({"kategori": "akademik", "bidang": "matematika"}, {"akademik": 12}) == 12
    assert topic_thread_id({"kategori": "non-akademik", "bidang": "seni"}, {"seni": 34}) == 34
    assert topic_thread_id({"kategori": "lain", "bidang": "lain"}, {}) is None
    assert topic_thread_id({"kategori": "lain"}, None) is None
