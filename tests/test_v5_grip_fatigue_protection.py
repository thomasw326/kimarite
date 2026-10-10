"""A nonzero tied-or-leading Grip protects against discard-pile Power fatigue."""
import pytest

from kimarite.catalog import card_by_name
from kimarite.models import BoutState, FighterState, GripState, Side, Wrestler
from kimarite.turns import apply_start_of_turn_exhaustion


@pytest.mark.parametrize("own,other,protected", [
    (0, 0, False), (1, 0, True), (1, 1, True),
    (2, 1, True), (1, 2, False), (2, 2, True),
    (0, 1, False),
])
def test_grip_prevents_power_fatigue_only_when_nonzero_and_tied_or_leading(own, other, protected):
    card = card_by_name("Oshi")
    wrestler_a = Wrestler("A", 2, 2, 2, card, card, card)
    wrestler_b = Wrestler("B", 2, 2, 2, card, card, card)
    a = FighterState(wrestler_a)
    b = FighterState(wrestler_b)
    state = BoutState(a, b)
    a.power = 2
    a.left_grip = GripState(own)
    b.left_grip = GripState(other)
    a.discard_pile = [card] * 7
    a.draw_pile = [card]
    apply_start_of_turn_exhaustion(state, Side.A)
    assert a.power == (2 if protected else 1)


def test_grip_does_not_override_empty_draw_pile_loss():
    card = card_by_name("Oshi")
    wrestler = Wrestler("A", 2, 2, 2, card, card, card)
    state = BoutState(FighterState(wrestler), FighterState(wrestler))
    state.fighter_a.left_grip = GripState.GRIP
    state.fighter_a.discard_pile = [card] * 7
    state.fighter_a.draw_pile = []
    apply_start_of_turn_exhaustion(state, Side.A)
    assert state.winner is Side.B
    assert state.win_method == "Exhaustion"
