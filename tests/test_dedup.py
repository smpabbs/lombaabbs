from app.store.dedup import dedup_key, find_duplicate, match_score, normalize_text


def test_normalize_text():
    assert normalize_text("Lomba  Matematika, SMP!!") == "lomba matematika smp"
    assert normalize_text(None) == ""
    assert normalize_text("   ") == ""


def test_dedup_key_stable_across_formatting():
    assert dedup_key("Lomba Matematika!", "UI") == dedup_key("lomba matematika", "ui")
    assert dedup_key("Lomba Matematika", None) == "lomba matematika|"


def test_match_score_identical():
    assert match_score("Olimpiade Matematika", "UI", "Olimpiade Matematika", "UI") == 1.0


def test_match_score_without_penyelenggara_falls_back_to_judul():
    assert match_score("Olimpiade Matematika", None, "Olimpiade Matematika", None) == 1.0


def test_find_duplicate_fuzzy_across_sources():
    candidates = [
        {
            "id": 1,
            "judul": "Olimpiade Matematika Nasional 2026",
            "penyelenggara": "Universitas Indonesia",
        }
    ]
    hit = find_duplicate(
        candidates, "Olimpiade Matematika Nasional", "Universitas Indonesia"
    )
    assert hit is not None
    assert hit[0]["id"] == 1
    assert hit[1] > 0.87


def test_find_duplicate_rejects_different_events():
    candidates = [{"id": 1, "judul": "Lomba Puisi", "penyelenggara": "SMAN 1"}]
    assert find_duplicate(candidates, "Olimpiade Fisika", "ITB") is None


def test_find_duplicate_picks_best_match():
    candidates = [
        {"id": 1, "judul": "Lomba Esai Nasional", "penyelenggara": "UI"},
        {
            "id": 2,
            "judul": "Lomba Esai Nasional 2026",
            "penyelenggara": "Universitas Indonesia",
        },
    ]
    hit = find_duplicate(
        candidates, "Lomba Esai Nasional 2026", "Universitas Indonesia"
    )
    assert hit is not None
    assert hit[0]["id"] == 2


def test_find_duplicate_different_organizer_blocks_match():
    candidates = [
        {"id": 1, "judul": "Lomba Esai Nasional", "penyelenggara": "Universitas Brawijaya"}
    ]
    assert find_duplicate(candidates, "Lomba Esai Nasional", "Institut Teknologi Bandung") is None
