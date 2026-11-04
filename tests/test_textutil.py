from datetime import date

import pytest

from app.textutil import (
    clean_url,
    days_until,
    format_date_id,
    format_deadline,
    fts_query,
    normalize_phone,
    parse_biaya,
    parse_date_id,
    truncate,
    whatsapp_url,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0812-3456-7890", "6281234567890"),
        ("+62 812 3456 7890", "6281234567890"),
        ("6281234567890", "6281234567890"),
        ("81234567890", "6281234567890"),
        ("620812345678", "62812345678"),
        ("021-555-1234", None),
        ("", None),
        (None, None),
        ("0888", None),
    ],
)
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


def test_whatsapp_url():
    assert whatsapp_url("0812-3456-7890") == "https://wa.me/6281234567890"
    assert whatsapp_url("021-555") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Gratis", 0),
        ("GRATIS untuk pelajar", 0),
        ("tanpa biaya", 0),
        ("Rp 50.000", 50_000),
        ("Rp1.500.000", 1_500_000),
        ("50rb", 50_000),
        ("1,5jt", 1_500_000),
        ("Rp 75.500,-", 75_500),
        ("50000", 50_000),
        ("250.000", 250_000),
        ("", None),
        (None, None),
        ("segera daftar", None),
    ],
)
def test_parse_biaya(raw, expected):
    assert parse_biaya(raw) == expected


def test_parse_date_iso():
    assert parse_date_id("2026-11-12") == "2026-11-12"
    assert parse_date_id("Deadline: 2026-01-05") == "2026-01-05"


def test_parse_date_numeric_indonesian_order():
    assert parse_date_id("12/11/2026") == "2026-11-12"
    assert parse_date_id("01-02-2027") == "2027-02-01"


def test_parse_date_numeric_swaps_when_month_overflow():
    assert parse_date_id("25/12/2026") == "2026-12-25"
    assert parse_date_id("12/25/2026") == "2026-12-25"


def test_parse_date_textual_indonesian():
    assert parse_date_id("12 November 2026") == "2026-11-12"
    assert parse_date_id("5 Agu 2026") == "2026-08-05"
    assert parse_date_id("31 Des 2026") == "2026-12-31"


def test_parse_date_without_year_rolls_forward():
    today = date(2026, 11, 4)
    assert parse_date_id("10 November", today=today) == "2026-11-10"
    # Sudah lewat > 30 hari → dianggap tahun depan.
    assert parse_date_id("1 Januari", today=today) == "2027-01-01"


def test_parse_date_invalid():
    assert parse_date_id("kapan-kapan") is None
    assert parse_date_id("32 Februari 2026") is None
    assert parse_date_id(None) is None


def test_format_and_days_until():
    today = date(2026, 11, 4)
    assert format_date_id("2026-11-12") == "12 Nov 2026"
    assert days_until("2026-11-12", today) == 8
    assert format_deadline("2026-11-12", today) == "12 Nov 2026 (H-8)"
    assert format_deadline("2026-11-04", today) == "4 Nov 2026 (HARI INI)"
    assert format_deadline("2026-10-01", today) == "1 Okt 2026 (ditutup)"
    assert format_deadline(None) is None


def test_clean_url():
    assert clean_url("https://contoh.id/daftar?x=1.") == "https://contoh.id/daftar?x=1"
    assert clean_url("daftar di https://contoh.id/a lalu isi form") == "https://contoh.id/a"
    assert clean_url("t.me/infolomba") == "https://t.me/infolomba"
    assert clean_url("bukan url") is None
    assert clean_url("") is None
    assert clean_url("ftp://contoh.id/a") is None
    assert clean_url("mailto:panitia@contoh.id") is None


def test_fts_query_quotes_tokens():
    assert fts_query("lomba matematika 2026") == '"lomba" "matematika" "2026"'
    assert fts_query("  ") == ""
    assert fts_query('kata"jahat OR (x)') == '"kata" "jahat" "x"'


def test_fts_query_drops_stopwords():
    assert fts_query("lomba esai untuk siswa SMP di Bandung") == (
        '"lomba" "esai" "siswa" "SMP" "Bandung"'
    )
    assert fts_query("dan atau yang") == ""


def test_truncate():
    assert truncate("abcdef", 10) == "abcdef"
    assert truncate("abcdef", 4) == "abc…"
    assert len(truncate("a" * 500, 100)) == 100
