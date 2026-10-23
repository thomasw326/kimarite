"""Kannuki stops Grip setup cards before they can enter the board."""
import pytest

from kimarite.catalog import card_by_name
from kimarite.effects import IllegalPlay
from kimarite.legality import can_play_card
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.playing import play_card
from kimarite.temporary import add_temporary, resolve_start_of_turn_temporaries


@pytest.mark.parametrize("name", [
    "Attempt Two-Handed Grip",
    "Attempt Deep Outside Grip",
    "Attempt Deep Inside Grip",
    "Gain Left Grip",
    "Gain Right Grip",
    "Uwate",
    "Shitate",
])
def test_kannuki_disallows_grip_setup_before_placement(name):
    blank = card_by_name("Oshi")
    a = Wrestler("A", 2, 2, 2, blank, blank, blank)
    b = Wrestler("B", 2, 2, 2, blank, blank, blank)
    state = BoutState(FighterState(a), FighterState(b))
    card = card_by_name(name)
    state.fighter_b.hand.append(card)
    state.fighter_b.plays_remaining = 2
    add_temporary(state, Side.A, card_by_name("Kannuki"), phase="exchange")

    assert not can_play_card(state, Side.B, card)
    with pytest.raises(IllegalPlay):
        play_card(state, Side.B, card)
    assert card in state.fighter_b.hand
    assert state.fighter_b.plays_remaining == 2
    assert not state.fighter_b.temporary_zone

    # Once Kannuki actually leaves, setup can be attempted normally.
    resolve_start_of_turn_temporaries(state, Side.A)
    assert can_play_card(state, Side.B, card)
    play_card(state, Side.B, card)
    if name.startswith("Attempt"):
        assert any(item.card.name == name for item in state.fighter_b.temporary_zone)
