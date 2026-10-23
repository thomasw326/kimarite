"""Focused B10 card rules and engine smoke after reconciliation."""
from kimarite.catalog import card_by_name
from kimarite.effects import EffectContext, resolve_exchange_effect
from kimarite.models import BoutState, FighterState, GripState, Side, Wrestler
from kimarite.temporary import resolve_start_of_turn_temporaries


def state():
    starter = card_by_name("Oshidashi")
    basic = card_by_name("Oshi")
    a = FighterState(Wrestler("A", 4, 1, 1, starter, basic, basic), power=7)
    b = FighterState(Wrestler("B", 4, 1, 1, starter, basic, basic), power=6)
    return BoutState(a, b)


def play_effect(bout, name):
    resolve_exchange_effect(bout, Side.A, card_by_name(name), EffectContext())


def test_regain_balance_has_one_momentum_and_two_power_when_behind():
    bout = state()
    bout.momentum = -2
    bout.fighter_a.draw_pile = [card_by_name("Oshi")]
    play_effect(bout, "Regain Balance")
    assert bout.momentum == -1
    assert bout.fighter_a.power == 9
    assert len(bout.fighter_a.hand) == 1


def test_yori_delayed_grip_lead_awards_two_momentum():
    bout = state()
    bout.fighter_a.left_grip = GripState.GRIP
    play_effect(bout, "Yori")
    assert bout.momentum == 0
    resolve_start_of_turn_temporaries(bout, Side.A)
    assert bout.momentum == 2


def test_denshamichi_momentum_is_delayed():
    bout = state()
    play_effect(bout, "Denshamichi")
    assert bout.position == 1
    assert bout.momentum == 0
    resolve_start_of_turn_temporaries(bout, Side.A)
    assert bout.momentum == 1
    assert bout.position == 2


def test_tawara_searches_first_kimarite_without_temporary():
    bout = state()
    bout.fighter_a.draw_pile = [card_by_name("Oshi"), card_by_name("Kotenage"), card_by_name("Yorikiri")]
    play_effect(bout, "Use the Tawara")
    assert bout.position == -1
    assert bout.momentum == 1
    assert [c.name for c in bout.fighter_a.hand] == ["Kotenage"]
    assert not bout.fighter_a.temporary_zone
