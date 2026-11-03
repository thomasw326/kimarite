"""Lock canonical orb-display colours independently of game mechanic stat values."""

import pytest

from kimarite.catalog import card_by_name
from kimarite.models import ORB_COLOURS, Stat, format_card_orbs


def test_canonical_stat_to_orb_colours():
    assert ORB_COLOURS == {
        Stat.POWER: "🟣",
        Stat.TECHNIQUE: "🟢",
        Stat.SPIRIT: "🟠",
    }


@pytest.mark.parametrize("name, expected", [
    ("Explosive Step — Fumikomi", "🟠🟠"),
    ("Get Underneath", "🟣🟢"),
    ("Give Ground", "🟢🟢🟠"),
    ("Henka", "🟢🟢"),
    ("Sidestep", "🟢🟢🟢"),
    ("Stare Down", "🟣🟢🟠"),
    ("Spin Away", "🟢🟠🟠"),
    ("Chiri-chozu", "🟣🟢🟢🟢🟠"),
    ("Hakkeyoi!", "🟠🟠🟠"),
    ("Shiko Stomp", "🟣🟠🟠🟠🟠"),
    ("Oshi", "🟠"),
    ("Crushing Pressure — Power Crusher", "🟣🟣🟣"),
])
def test_printed_orb_display_matches_approved_catalogue(name, expected):
    card = card_by_name(name)
    assert format_card_orbs(card) == expected
    assert len(expected) == card.power + card.technique + card.spirit
