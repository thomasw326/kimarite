"""Regression cases for current-sheet Pull and Get Underneath."""
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.temporary import resolve_start_of_turn_temporaries


def make_bout():
    starter = card_by_name("Oshidashi")
    wrestler_a = Wrestler("A", 2, 2, 2, starter, starter, starter)
    wrestler_b = Wrestler("B", 2, 2, 2, starter, starter, starter)
    return BoutState(FighterState(wrestler_a), FighterState(wrestler_b))


def test_pull_exchange_is_immediate_draw_discard_and_unstable():
    state = make_bout()
    state.fighter_a.draw_pile = [card_by_name("Oshi"), card_by_name("Tsuki")]
    resolve_exchange_effect(state, Side.A, card_by_name("Pull"), EffectContext())
    assert not state.fighter_a.hand
    assert [c.name for c in state.fighter_a.discard_pile] == ["Oshi"]
    assert (state.position, state.momentum) == (-1, 1)
    assert state.fighter_b.unstable
    assert not state.fighter_a.temporary_zone


def test_pull_has_no_delayed_reversal_anymore():
    state = make_bout()
    state.momentum = 2
    state.fighter_a.draw_pile = [card_by_name("Oshi")]
    resolve_exchange_effect(state, Side.A, card_by_name("Pull"), EffectContext())
    assert state.momentum == 3
    assert state.position == -1
    assert state.fighter_b.unstable
    resolve_start_of_turn_temporaries(state, Side.A)
    assert state.momentum == 3
    assert state.position == -1


def test_get_underneath_forces_opponent_kimarite_search():
    state = make_bout()
    state.fighter_b.draw_pile = [card_by_name("Oshi"), card_by_name("Yorikiri")]
    resolve_exchange_effect(state, Side.A, card_by_name("Get Underneath"), EffectContext())
    assert state.momentum == 1
    assert state.position == 1
    assert not state.fighter_a.temporary_zone
    assert [c.name for c in state.fighter_b.kimarite_zone] == ["Yorikiri"]


def test_get_underneath_ignores_choice_and_uses_topmost_kimarite():
    state = make_bout()
    state.fighter_b.draw_pile = [
        card_by_name("Yorikiri"), card_by_name("Oshi"), card_by_name("Oshidashi")
    ]
    resolve_exchange_effect(
        state, Side.A, card_by_name("Get Underneath"),
        EffectContext(choices={"kimarite_index": 2}),
    )
    assert [c.name for c in state.fighter_b.kimarite_zone] == ["Yorikiri"]
    assert [c.name for c in state.fighter_b.draw_pile] == ["Oshi", "Oshidashi"]


def test_tawara_search_takes_topmost_kimarite_not_first_card():
    state = make_bout()
    state.fighter_a.draw_pile = [
        card_by_name("Oshi"), card_by_name("Yorikiri"), card_by_name("Oshidashi")
    ]
    resolve_exchange_effect(state, Side.A, card_by_name("Use the Tawara"), EffectContext())
    assert [c.name for c in state.fighter_a.hand] == ["Yorikiri"]
    assert [c.name for c in state.fighter_a.draw_pile][:2] == ["Oshi", "Oshidashi"]


def test_ai_tawara_search_defaults_to_first_eligible():
    state = make_bout()
    state.fighter_a.draw_pile = [card_by_name("Yorikiri"), card_by_name("Oshidashi")]
    resolve_exchange_effect(state, Side.A, card_by_name("Use the Tawara"), EffectContext())
    assert [c.name for c in state.fighter_a.hand] == ["Yorikiri"]
