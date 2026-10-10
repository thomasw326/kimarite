"""Tottari sees an opponent Grip interruption at the next turn start."""
from kimarite.catalog import card_by_name
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.tachiai import compare_tachiai
from kimarite.turns import start_exchange_turn


def test_tottari_start_check_preserves_prior_opponent_grip_event():
    starter = card_by_name("Oshidashi")
    a = Wrestler("A", 2, 2, 2, starter, starter, starter)
    b = Wrestler("B", 2, 2, 2, starter, starter, starter)
    state = BoutState(FighterState(a), FighterState(b))
    state.fighter_a.kimarite_zone.append(card_by_name("Tottari"))
    state.fighter_a.opponent_grip_reduced_this_turn = True
    start_exchange_turn(state, Side.A, compare_tachiai(a, b))
    assert state.winner is Side.A
    assert state.win_method == "Tottari"
    assert not state.fighter_a.opponent_grip_reduced_this_turn


def test_tottari_does_not_win_without_grip_event():
    starter = card_by_name("Oshidashi")
    a = Wrestler("A", 2, 2, 2, starter, starter, starter)
    b = Wrestler("B", 2, 2, 2, starter, starter, starter)
    state = BoutState(FighterState(a), FighterState(b))
    state.fighter_a.kimarite_zone.append(card_by_name("Tottari"))
    state.fighter_a.draw_pile = [card_by_name("Oshi"), card_by_name("Tsuki")]
    start_exchange_turn(state, Side.A, compare_tachiai(a, b))
    assert state.winner is None
