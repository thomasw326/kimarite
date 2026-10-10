"""Seeded V5 archetypes retain setups and respect seven-card exclusions."""
import pytest

from kimarite.catalog import CARD_POOL
from kimarite.exclusions import GAIN_OR_ESTABLISH_GRIP, REQUIRES_GRIP
from kimarite.style_builds_v5 import build_style
from kimarite.styles_v5 import STYLES


@pytest.mark.parametrize("style", sorted(STYLES))
def test_style_build_is_deterministic_and_excludes_seven(style):
    a = build_style(style, seed=420)
    b = build_style(style, seed=420)
    assert a == b
    assert len(a.excluded_ids) == 7
    assert len(a.fighter.draw_pile) > 20
    assert a.fighter.draw_pile[0] == a.fighter.wrestler.top_of_deck_card
    assert a.fighter.draw_pile[-1] == a.fighter.wrestler.prepared_tachiai_card
    assert a.fighter.kimarite_zone == [a.fighter.wrestler.starting_kimarite]
    assert not set(c.card_id for c in a.fighter.draw_pile) & a.excluded_ids


def test_grip_dependent_kimarite_preserves_grip_starters():
    for seed in range(8):
        wrestler = build_style("Mawashi Specialist", seed=seed).fighter
        if wrestler.wrestler.starting_kimarite.name in REQUIRES_GRIP:
            assert any(c.name in GAIN_OR_ESTABLISH_GRIP for c in wrestler.draw_pile)


def test_style_difficulty_modifies_exclusion_count():
    assert len(build_style("Mountain", difficulty=-2).excluded_ids) == 5
    assert len(build_style("Mountain", difficulty=2).excluded_ids) == 9


def test_unknown_style_rejected():
    with pytest.raises(KeyError):
        build_style("Unknown Style")
