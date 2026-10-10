"""Shiko Stomp has a real persistent defensive value for one-step AI."""
from kimarite.ai import score_state
from kimarite.catalog import card_by_name
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.temporary import add_temporary


def _state():
    k = card_by_name("Oshidashi")
    o = card_by_name("Oshi")
    a = Wrestler("A", 2, 2, 2, k, o, o)
    b = Wrestler("B", 2, 2, 2, k, o, o)
    return BoutState(FighterState(a), FighterState(b))


def test_shiko_stomp_has_positive_persistent_defensive_value():
    state = _state()
    baseline = score_state(state, Side.A)
    add_temporary(state, Side.A, card_by_name("Shiko Stomp"), phase="exchange")
    assert score_state(state, Side.A) > baseline + 10


def test_shiko_stomp_has_diminishing_returns_and_opponent_cost():
    state = _state()
    baseline = score_state(state, Side.A)
    add_temporary(state, Side.A, card_by_name("Shiko Stomp"), phase="exchange")
    first_gain = score_state(state, Side.A) - baseline
    add_temporary(state, Side.A, card_by_name("Shiko Stomp"), phase="exchange")
    second_gain = score_state(state, Side.A) - baseline - first_gain
    assert 0 < second_gain < first_gain
    add_temporary(state, Side.B, card_by_name("Shiko Stomp"), phase="exchange")
    assert score_state(state, Side.A) < baseline + first_gain + second_gain
