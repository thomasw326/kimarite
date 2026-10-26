"""Explain the exact winning Sukuinage values in B11 without changing Classic."""
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler
from kimarite.turns import check_kimarite_zone
from kimarite.catalog import card_by_name


def test_b11_sukuinage_victory_explains_actual_conditions():
    blank = Card(99123, "Blank")
    a = FighterState(Wrestler("Winner", 0, 0, 0, blank, blank, blank))
    b = FighterState(Wrestler("Opponent", 0, 0, 0, blank, blank, blank))
    a.kimarite_zone.append(card_by_name("Sukuinage"))
    a.hand = [blank] * 5
    b.hand = [blank]
    state = BoutState(a, b, momentum=3)
    state.b11_explain_wins = True
    check_kimarite_zone(state, Side.A)
    assert state.winner is Side.A
    assert state.event_log[-2] == (
        "Sukuinage conditions satisfied: Grip 0 (required 0); "
        "Momentum advantage 3 (required ≥2); Hand advantage 4 (required ≥4)."
    )
    assert state.event_log[-1] == "Winner wins by Sukuinage."


def test_classic_win_event_remains_unchanged():
    blank = Card(99124, "Blank")
    a = FighterState(Wrestler("Winner", 0, 0, 0, blank, blank, blank))
    b = FighterState(Wrestler("Opponent", 0, 0, 0, blank, blank, blank))
    a.kimarite_zone.append(card_by_name("Sukuinage"))
    a.hand = [blank] * 5
    b.hand = [blank]
    state = BoutState(a, b, momentum=3)
    check_kimarite_zone(state, Side.A)
    assert state.event_log == ["Winner wins by Sukuinage."]
