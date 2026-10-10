"""Current V5 print-pool deck construction checks (old sheet seeds retired)."""
from kimarite.catalog import CARD_POOL, ORIGINAL_WRESTLERS
from kimarite.deck import build_seeded_deck


def test_seeded_decks_cover_current_active_pool():
    for name, seed in (("Fujinokawa", 102), ("Tochinoshin", 911132)):
        wrestler = ORIGINAL_WRESTLERS[name].build()
        excluded = {18, 19, 21}
        first = build_seeded_deck(wrestler, seed, excluded)
        second = build_seeded_deck(wrestler, seed, excluded)
        assert first == second
        assert first[0].name == wrestler.top_of_deck_card.name
        reserved = {
            wrestler.starting_kimarite.name,
            wrestler.prepared_tachiai_card.name,
            wrestler.top_of_deck_card.name,
        }
        expected = {
            card.card_id for card in CARD_POOL
            if card.name not in reserved and card.card_id not in excluded
        }
        assert {card.card_id for card in first[1:]} == expected
        assert not any(card.card_id in excluded for card in first)


def test_current_deck_can_include_newer_cards():
    wrestler = ORIGINAL_WRESTLERS["Fujinokawa"].build()
    deck = build_seeded_deck(wrestler, 102)
    names = {card.name for card in deck}
    assert "Shove" in names
    assert "Explosive Step — Fumikomi" in names
    assert "Injury" in names
