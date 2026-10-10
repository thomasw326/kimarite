"""Verify live-sheet style data resolves against the current game catalog."""
from kimarite.catalog import CARD_POOL, STARTING_KIMARITE
from kimarite.styles_v5 import STYLES, preference_bonus, preferred_card_pool, preferred_kimarite, ranked_pool, resolve_card


def test_fifteen_styles_have_seven_resolvable_preferences():
    assert len(STYLES) == 15
    for profile in STYLES.values():
        assert len(profile.preferred_cards) == 7
        assert len(set(profile.preferred_cards)) == 7
        assert len(profile.six_axis_weights) == 6
        assert len(preferred_card_pool(profile)) == 7
        assert len(preferred_kimarite(profile)) == 2


def test_affinity_is_soft_and_nonpreferred_cards_remain_eligible():
    style = STYLES["Mountain"]
    assert preference_bonus(style, "Immovable") == 7
    assert preference_bonus(style, "Oshi") == 0
    original = [resolve_card("Oshi"), resolve_card("Immovable"), resolve_card("Hold Position")]
    ranked = ranked_pool(style, original)
    assert [c.name for c in ranked] == ["Immovable", "Hold Position", "Oshi"]
    assert sorted(c.card_id for c in original) == sorted(c.card_id for c in ranked)


def test_short_card_names_resolve_without_mutating_spreadsheet_rank():
    style = STYLES["Speed Demon"]
    assert style.preferred_cards[1] == "Explosive Step"
    assert resolve_card("Explosive Step").name == "Explosive Step — Fumikomi"
    assert preference_bonus(style, "Explosive Step — Fumikomi") == 6
