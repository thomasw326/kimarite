"""Oshi and Tsuki Exchange effects must work even at negative Momentum."""
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.models import BoutState, FighterState, GripState, Wrestler, Side, Card


def _state():
    k = card_by_name("Oshidashi")
    blank = Card(91059, "Test Blank")
    a = Wrestler("A", 2, 2, 2, k, blank, blank)
    b = Wrestler("B", 2, 2, 2, k, blank, blank)
    state = BoutState(
        FighterState(a, draw_pile=[blank, blank, blank], kimarite_zone=[k]),
        FighterState(b, draw_pile=[blank, blank, blank], kimarite_zone=[k]),
    )
    state.momentum = -1
    return state


def test_oshi_push_despite_negative_momentum():
    state = _state()
    before = state.position
    resolve_exchange_effect(state, Side.A, card_by_name("Oshi"), EffectContext())
    assert state.position > before
    assert state.momentum == -1


def test_tsuki_reduces_grip_despite_negative_momentum():
    state = _state()
    state.fighter_b.left_grip = GripState.GRIP
    resolve_exchange_effect(state, Side.A, card_by_name("Tsuki"), EffectContext())
    assert state.fighter_b.left_grip is GripState.NONE
    assert state.momentum == -1
