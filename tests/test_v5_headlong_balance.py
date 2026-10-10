"""Approved opening Power restoration and Headlong Charge choice reporting."""
from kimarite.catalog import card_by_name
from kimarite.models import Card
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.tachiai import compare_tachiai
from kimarite.tachiai_effects import resolve_prepared_tachiai
from kimarite.turns import apply_initial_power


def _bout(prepared: str):
    k = card_by_name("Oshidashi")
    t = card_by_name(prepared)
    blank = Card(90059, "Test Blank")
    a = Wrestler("A", 2, 2, 2, k, t, blank)
    b = Wrestler("B", 2, 2, 2, k, blank, blank)
    state = BoutState(
        FighterState(a, draw_pile=[blank, blank, blank, t], kimarite_zone=[k]),
        FighterState(b, draw_pile=[blank, blank, blank], kimarite_zone=[k]),
    )
    comparison = compare_tachiai(a, b)
    apply_initial_power(state, comparison)
    return state, comparison


def test_defensive_cards_restore_two_tachiai_power():
    for name in ("Hold Position", "Immovable"):
        state, comparison = _bout(name)
        starting_power = state.fighter_a.power
        resolve_prepared_tachiai(state, comparison)
        assert state.fighter_a.power == starting_power + 2


def test_headlong_decline_grants_no_bonus_and_discards_prepared_card():
    state, comparison = _bout("Headlong Charge")
    assert (card_by_name("Headlong Charge").power,
            card_by_name("Headlong Charge").technique,
            card_by_name("Headlong Charge").spirit) == (0, 0, 4)
    power = state.fighter_a.power
    resolve_prepared_tachiai(state, comparison, sacrifice_choices={Side.A: None})
    assert state.fighter_a.power == power
    assert state.headlong_decisions == [(Side.A, "Tachiai", "decline", None)]
    assert "Headlong Charge" not in [c.name for c in state.fighter_a.draw_pile]
    assert "Headlong Charge" in [c.name for c in state.fighter_a.discard_pile]


def test_headlong_sacrifice_grants_momentum_and_push_only():
    state, comparison = _bout("Headlong Charge")
    power = state.fighter_a.power
    resolve_prepared_tachiai(state, comparison, sacrifice_choices={Side.A: 0})
    assert state.fighter_a.power == power
    assert state.headlong_decisions == [(Side.A, "Tachiai", "sacrifice", "Oshidashi")]
    assert not state.fighter_a.kimarite_zone
    assert "Oshidashi" in [c.name for c in state.fighter_a.discard_pile]
    # The sacrifice adds +1 Momentum and +1 Push to the standard opening.
    assert state.momentum == 1
