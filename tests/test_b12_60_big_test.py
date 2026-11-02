"""B12 15 AI personalities × four unique decks each, in two physical modes."""
from collections import Counter

from kimarite.catalog import card_by_name
from scripts.b12_60_big_test import AI_GROUPS, load_designs, make_fighter, schedule


def test_all_sixty_28_12_decks_and_exact_original_ai_groups():
    base, full = load_designs("base28"), load_designs("max40")
    assert len(base) == len(full) == 60
    assert len(AI_GROUPS) == 15
    assert Counter(e["style_proxy"] for e in full) == Counter({name: 4 for name in AI_GROUPS})
    for i, (a, b) in enumerate(zip(base, full), 1):
        assert a["id"] == b["id"] == f"{i:02d}"
        assert a["style_proxy"] == b["style_proxy"] == AI_GROUPS[(i-1)//4]
        assert len(a["cards"]) == 28
        assert len(b["cards"]) == 40
        assert len(set(a["cards"])) == 28
        assert max(Counter(b["cards"]).values()) == 2
        assert set(a["cards"]) == set(b["cards"])
        assert a["starting_kimarite"] in a["cards"]
        assert card_by_name(a["starting_kimarite"]).is_kimarite


def test_physical_opening_has_no_phantom_or_missing_copies():
    for mode in ("base28", "max40"):
        for entry in load_designs(mode):
            f, origins = make_fighter(entry, 4042, 1)
            assert len(f.draw_pile) + len(f.kimarite_zone) + 1 == len(entry["cards"])
            assert len(origins) == len(entry["cards"])
            assert f.wrestler.starting_kimarite.name == entry["starting_kimarite"]
            assert f.wrestler.prepared_tachiai_card.name != f.wrestler.top_of_deck_card.name
            assert f.draw_pile[0] is f.wrestler.top_of_deck_card
            assert id(f.wrestler.starting_kimarite) in origins
            assert id(f.wrestler.prepared_tachiai_card) in origins


def test_pair_mirror_schedule_covers_60_both_ways():
    pairs = schedule()
    assert len(pairs) == 1770
    assert len(set(pairs)) == len(pairs)
    assert all(a < b for a, b in pairs)
    assert len(schedule(smoke=True)) == 30
    assert sorted({j for pair in schedule(smoke=True) for j in pair}) == list(range(60))
