"""Regression checks for approved Headlong Charge / Ottsuke / Abisetaoshi edits."""
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.kimarite_effects import resolve_kimarite_play_effect
from kimarite.legality import can_play_card
from kimarite.models import BoutState, FighterState, GripState, Side, Wrestler


def state_for(card_name):
    base = card_by_name("Oshi")
    w = Wrestler("W", 3, 2, 1, base, base, base)
    state = BoutState(FighterState(w), FighterState(w))
    card = card_by_name(card_name)
    state.fighter_a.hand.append(card)
    state.fighter_a.draw_pile.append(base)
    state.fighter_a.plays_remaining = 2
    return state, card


def test_headlong_requires_kimarite_to_play_and_sacrifice():
    state, card = state_for("Headlong Charge")
    assert not can_play_card(state, Side.A, card)
    state.fighter_a.kimarite_zone.append(card_by_name("Oshidashi"))
    assert can_play_card(state, Side.A, card)
    resolve_exchange_effect(state, Side.A, card, EffectContext(choices={"sacrifice_kimarite": 0}))
    assert not state.fighter_a.kimarite_zone
    assert state.momentum == 1


def test_ottsuke_can_draw_without_target():
    state, card = state_for("Ottsuke")
    state.fighter_b.kimarite_zone.clear()
    resolve_exchange_effect(state, Side.A, card, EffectContext(choices={"mode": "draw"}))
    assert len(state.fighter_a.hand) == 2


def test_abisetaoshi_current_exchange_and_win_threshold():
    state, card = state_for("Abisetaoshi")
    state.fighter_a.power = 5
    resolve_kimarite_play_effect(state, Side.A, card, EffectContext())
    assert state.fighter_a.total_grip == 0

    state.fighter_a.power = 6
    state.fighter_b.power = 3
    resolve_kimarite_play_effect(state, Side.A, card, EffectContext())
    assert state.fighter_a.total_grip == 1
    assert state.momentum == 0
    assert state.fighter_b.power == 3

    resolve_kimarite_play_effect(state, Side.A, card, EffectContext())
    assert state.fighter_a.power == 7
    assert state.momentum == 0
    assert state.fighter_b.power == 3

    state.fighter_a.left_grip = GripState.GRIP
    state.fighter_a.right_grip = GripState.GRIP
    state.fighter_a.power = 8
    assert not kimarite_is_satisfied(state, Side.A, card)
    state.fighter_a.power = 9
    assert not kimarite_is_satisfied(state, Side.A, card)
    state.fighter_a.power = 10
    assert kimarite_is_satisfied(state, Side.A, card)
