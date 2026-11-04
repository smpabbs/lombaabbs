import pytest

from app.extract.llm import ExtractionError, parse_json_object


def test_parse_json_plain():
    assert parse_json_object('{"judul": "Lomba"}') == {"judul": "Lomba"}


def test_parse_json_fenced():
    assert parse_json_object('```json\n{"judul": "Lomba"}\n```') == {"judul": "Lomba"}


def test_parse_json_with_preamble_and_trailer():
    raw = 'Berikut hasilnya:\n{"judul": "Lomba"}\nSemoga membantu.'
    assert parse_json_object(raw) == {"judul": "Lomba"}


def test_parse_json_nested_braces_preserved():
    raw = '{"ringkasan": "pakai {kurung} di dalam", "judul": "Lomba"}'
    assert parse_json_object(raw)["judul"] == "Lomba"


@pytest.mark.parametrize("raw", ["", "   ", "tidak ada json", "[1, 2]", '"teks"', "42"])
def test_parse_json_rejects_invalid(raw):
    with pytest.raises(ExtractionError):
        parse_json_object(raw)
