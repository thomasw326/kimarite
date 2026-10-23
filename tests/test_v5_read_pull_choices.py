"""Printed Read the Move and Pull alternative modes."""
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.temporary import add_temporary


def bout():
    k = card_by_name("Oshidashi")
    a = Wrestler("A", 2, 2, 2, k, k, k)
    b = Wrestler("B", 2, 2, 2, k, k, k)
    state = BoutState(FighterState(a), FighterState(b))
    state.fighter_a.draw_pile = [card_by_name("Oshi"), card_by_name("Tsuki")]
    return state


def test_read_the_move_draw_option_keeps_opponent_temporary():
    state = bout()
    add_temporary(state, Side.B, card_by_name("Pull"), phase="exchange")
    resolve_exchange_effect(state, Side.A, card_by_name("Read the Move"),
                            EffectContext(choices={"mode": "draw"}))
    assert len(state.fighter_b.temporary_zone) == 1
    assert len(state.fighter_a.hand) == 1
    assert state.momentum == 0


def test_read_the_move_remove_option_disrupts_temporary():
    state = bout()
    add_temporary(state, Side.B, card_by_name("Pull"), phase="exchange")
    resolve_exchange_effect(state, Side.A, card_by_name("Read the Move"),
                            EffectContext(choices={"mode": "remove"}))
    assert not state.fighter_b.temporary_zone
    assert len(state.fighter_a.hand) == 1
    assert state.momentum == 1


def test_pull_filter_option_does_not_create_temporary():
    state = bout()
    resolve_exchange_effect(state, Side.A, card_by_name("Pull"),
                            EffectContext(choices={"mode": "filter"}))
    assert not state.fighter_a.temporary_zone
    assert [c.name for c in state.fighter_a.discard_pile] == ["Oshi", "Pull"]


def test_pull_reversal_option_preserves_temporary():
    state = bout()
    state.fighter_a.discard_pile = [card_by_name("Harite")]
    resolve_exchange_effect(state, Side.A, card_by_name("Pull"),
                            EffectContext(choices={"mode": "reversal"}))
    assert len(state.fighter_a.temporary_zone) == 1
    assert state.fighter_a.draw_pile[0].name == "Harite"
