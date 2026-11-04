from app.extract.schema import LombaExtract


def test_to_fields_normalizes_values():
    extract = LombaExtract(
        is_smp=True,
        judul="  Olimpiade Matematika  ",
        penyelenggara="UI",
        kategori="Non-Akademik",
        biaya_text="Rp 50.000",
        deadline="12 November 2026",
        link_daftar="contoh.id/daftar",
        cp_kontak="0812-3456-7890",
        sumber_url="https://contoh.id/info",
    )
    fields = extract.to_fields()
    assert fields["judul"] == "Olimpiade Matematika"
    assert fields["jenjang"] == "SMP"
    assert fields["kategori"] == "non-akademik"
    assert fields["biaya"] == 50_000
    assert fields["deadline"] == "2026-11-12"
    assert fields["link_daftar"] == "https://contoh.id/daftar"
    assert fields["cp_wa"] == "6281234567890"
    assert fields["status"] == "draft"
    assert fields["dedup_key"] == "olimpiade matematika|ui"


def test_to_fields_keeps_only_known_columns():
    from app.store.db import COLUMNS

    fields = LombaExtract(is_smp=True, judul="X").to_fields()
    assert set(fields) <= set(COLUMNS)


def test_to_fields_coerces_non_string_values():
    extract = LombaExtract(is_smp="ya", judul=123, hadiah=["A", "B"], biaya_text=50_000)
    assert extract.is_smp is True
    fields = extract.to_fields()
    assert fields["judul"] == "123"
    assert fields["hadiah"] == "A, B"
    assert fields["biaya"] == 50_000


def test_to_fields_sumber_url_override():
    extract = LombaExtract(is_smp=True, judul="X", sumber_url="https://a.id/1")
    assert extract.to_fields(sumber_url="https://b.id/2")["sumber_url"] == "https://b.id/2"


def test_to_fields_without_optional_values():
    fields = LombaExtract(is_smp=True, judul="X").to_fields()
    assert fields["biaya"] is None
    assert fields["deadline"] is None
    assert fields["cp_wa"] is None
    assert fields["sumber_url"] is None


def test_kategori_unknown_becomes_none():
    assert LombaExtract(is_smp=True, judul="X", kategori="umum").kategori is None
    assert LombaExtract(is_smp=True, judul="X", kategori="Akademik").kategori == "akademik"


def test_is_smp_default_false():
    assert LombaExtract(judul="X").is_smp is False
