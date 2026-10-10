"""Printed Sidestep: suppress ALL Push until its Temporary resolves."""
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.rules import gain_push
from kimarite.temporary import resolve_start_of_turn_temporaries


def make_bout():
    k = card_by_name("Oshidashi")
    a = Wrestler("A", 2, 2, 2, k, k, k)
    b = Wrestler("B", 2, 2, 2, k, k, k)
    return BoutState(FighterState(a), FighterState(b), position=2)


def test_sidestep_suppresses_push_from_both_sides_until_resolution():
    state = make_bout()
    resolve_exchange_effect(state, Side.A, card_by_name("Sidestep"), EffectContext())
    assert state.position == 0
    assert state.side_by_side_owner is Side.A
    gain_push(state, Side.A, 2)
    gain_push(state, Side.B, 2)
    assert state.position == 0
    assert state.side_by_side_owner is Side.A
    resolve_start_of_turn_temporaries(state, Side.A)
    assert state.position == 2
    assert state.side_by_side_owner is None


def test_sidestep_resolves_unfavorable_with_opponent_orientation():
    state = make_bout()
    resolve_exchange_effect(state, Side.A, card_by_name("Sidestep"), EffectContext())
    state.momentum = -1
    resolve_start_of_turn_temporaries(state, Side.A)
    assert state.position == -2
    assert state.side_by_side_owner is None


def test_sidestep_disruption_releases_push_lock():
    from kimarite.temporary import remove_temporary
    state = make_bout()
    resolve_exchange_effect(state, Side.A, card_by_name("Sidestep"), EffectContext())
    instance = state.fighter_a.temporary_zone[0]
    remove_temporary(state, Side.A, instance, disrupted=True)
    assert state.side_by_side_owner is None
    assert state.side_by_side_distance == 0
    gain_push(state, Side.B, 1)
    assert state.position == -1
