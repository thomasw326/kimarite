"""Katasukashi requires a Position loss during the owner's turn."""
from kimarite.catalog import card_by_name
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.models import BoutState, FighterState, Wrestler, Card, Side


def test_opponent_max_momentum_does_not_trigger_katasukashi():
    k = card_by_name("Katasukashi")
    blank = Card(90100, "Test Blank")
    a = Wrestler("A", 2, 2, 2, k, blank, blank)
    b = Wrestler("B", 2, 2, 2, k, blank, blank)
    state = BoutState(FighterState(a, kimarite_zone=[k]), FighterState(b, kimarite_zone=[k]))
    state.momentum = -3
    assert not kimarite_is_satisfied(state, Side.A, k)
    state.momentum = 0
    state.fighter_a.lost_position_this_turn = True
    assert kimarite_is_satisfied(state, Side.A, k)
