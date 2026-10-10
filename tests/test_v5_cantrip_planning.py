"""V5-only AI may bank Draw+Play cards toward four-card finish setups."""
from kimarite.catalog import card_by_name
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.style_ai_v5 import _four_card_setup_hold_value


def _state(kimarite: str, *, momentum: int = 0, position: int = 0):
    k = card_by_name(kimarite)
    basic = card_by_name("Oshi")
    a = Wrestler("A", 2, 2, 2, k, basic, basic)
    b = Wrestler("B", 2, 2, 2, k, basic, basic)
    state = BoutState(FighterState(a), FighterState(b))
    state.fighter_a.kimarite_zone = [k]
    state.fighter_a.draw_pile = [card_by_name("Shove")]
    state.momentum = momentum
    state.position = position
    return state


def test_tsukidashi_setup_encourages_holding_cantrip():
    state = _state("Tsukidashi", position=2)
    assert _four_card_setup_hold_value(state, Side.A, "Oshi") == 35
    assert _four_card_setup_hold_value(state, Side.A, "Shove") == 0


def test_tsukitaoshi_setup_encourages_holding_cantrip():
    state = _state("Tsukitaoshi", momentum=2)
    assert _four_card_setup_hold_value(state, Side.A, "Power Water Cantrip") == 35


def test_no_bonus_when_unprepared_or_no_future_draw():
    state = _state("Tsukidashi", position=0)
    assert _four_card_setup_hold_value(state, Side.A, "Oshi") == 0
    state.position = 2
    state.fighter_a.draw_pile.clear()
    assert _four_card_setup_hold_value(state, Side.A, "Oshi") == 0


def test_no_bonus_during_active_four_card_sequence():
    state = _state("Tsukitaoshi", momentum=2)
    state.fighter_a.cards_played_this_turn = 2
    assert _four_card_setup_hold_value(state, Side.A, "Tsuki") == 0
