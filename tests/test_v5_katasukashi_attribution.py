"""Katasukashi winning attribution must identify position-loss source cards."""
from kimarite.catalog import card_by_name
from kimarite.models import BoutState, FighterState, Wrestler, Card, Side
from kimarite.rules import lose_position
from kimarite.turns import check_kimarite_zone, reset_turn_events


def test_katasukashi_records_triggering_card():
    k = card_by_name("Katasukashi")
    blank = Card(90112, "Test Blank")
    a = Wrestler("A", 2, 2, 2, k, blank, blank)
    b = Wrestler("B", 2, 2, 2, k, blank, blank)
    state = BoutState(FighterState(a, kimarite_zone=[k]), FighterState(b))
    state.turn_number = 2
    lose_position(state, Side.A, 1, source="Give Ground")
    assert check_kimarite_zone(state, Side.A).name == "Katasukashi"
    assert state.katasukashi_win_sources == ["Give Ground"]


def test_position_loss_attribution_resets_each_turn():
    k = card_by_name("Katasukashi")
    blank = Card(90112, "Test Blank")
    a = Wrestler("A", 2, 2, 2, k, blank, blank)
    b = Wrestler("B", 2, 2, 2, k, blank, blank)
    state = BoutState(FighterState(a, kimarite_zone=[k]), FighterState(b))
    lose_position(state, Side.A, 1, source="Pull")
    reset_turn_events(state, Side.A)
    assert not state.fighter_a.lost_position_this_turn
    assert not state.position_loss_events
    assert check_kimarite_zone(state, Side.A) is None
