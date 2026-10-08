from kimarite.catalog import ORIGINAL_WRESTLERS
from kimarite.deck import build_seeded_deck


def test_fujinokawa_seed_102_matches_ai_vs_ai_sheet():
    wrestler = ORIGINAL_WRESTLERS["Fujinokawa"].build()
    exclusions = {7, 14, 15, 16, 29, 35, 43}

    deck = build_seeded_deck(wrestler, 102, exclusions)

    assert [(c.card_id, c.name) for c in deck[:7]] == [
        (1, "Oshi"),
        (30, "Get Underneath"),
        (25, "Ottsuke"),
        (3, "Tsuki"),
        (40, "Tsukidashi"),
        (39, "Oshidashi"),
        (23, "Yori"),
    ]


def test_tochinoshin_seed_911132_matches_ai_vs_ai_sheet():
    wrestler = ORIGINAL_WRESTLERS["Tochinoshin"].build()
    exclusions = {18, 19, 21, 28, 31, 32, 33}

    deck = build_seeded_deck(wrestler, 911132, exclusions)

    assert [(c.card_id, c.name) for c in deck[:7]] == [
        (37, "Morozashi"),
        (52, "Kotenage"),
        (7, "Headlong Charge"),
        (14, "Attempt Two-Handed Grip"),
        (47, "Hikiotoshi"),
        (38, "Yorikiri"),
        (9, "Harite"),
    ]


def test_all_fifteen_kimarite_are_in_every_unexcluded_ai_pool():
    from kimarite.catalog import STARTING_KIMARITE
    names = {card.name for card in STARTING_KIMARITE}
    for wrestler in ORIGINAL_WRESTLERS.values():
        deck = build_seeded_deck(wrestler.build(), 317)
        assert names <= {card.name for card in deck}
