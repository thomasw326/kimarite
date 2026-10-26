"""B11 finished bout captures server-authoritative victory requirements."""
from kimarite.catalog import card_by_name
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler, GripState
from kimarite.turns import check_kimarite_zone


def state_for(method):
    blank = Card(89991, "Blank")
    a = FighterState(Wrestler("Player", 0, 0, 0, blank, blank, blank))
    b = FighterState(Wrestler("Opponent", 0, 0, 0, blank, blank, blank))
    a.kimarite_zone.append(card_by_name(method))
    s = BoutState(a, b)
    s.b11_explain_wins = True
    return s, a, b


def test_abisetaoshi_result_captures_power_grip_and_checks():
    state, winner, loser = state_for("Abisetaoshi")
    winner.power = 11
    winner.left_grip = GripState.GRIP
    winner.right_grip = GripState.GRIP
    check_kimarite_zone(state, Side.A)
    assert state.winner is Side.A
    result = state.b11_victory_details
    assert result["kimarite"] == "Abisetaoshi"
    assert result["power"] == 11
    assert result["effective_grip"] == 2
    assert all(item["met"] for item in result["checks"])


def test_sukuinage_result_captures_hand_advantage():
    state, winner, loser = state_for("Sukuinage")
    state.momentum = 3
    winner.hand = [card_by_name("Oshi")] * 5
    loser.hand = [card_by_name("Oshi")]
    check_kimarite_zone(state, Side.A)
    assert state.winner is Side.A
    assert state.b11_victory_details["hand_advantage"] == 4
    assert all(item["met"] for item in state.b11_victory_details["checks"])


def test_no_extra_result_capture_in_classic():
    state, winner, loser = state_for("Abisetaoshi")
    state.b11_explain_wins = False
    winner.power = 11
    winner.left_grip = GripState.DEEP
    check_kimarite_zone(state, Side.A)
    assert state.winner is Side.A
    assert not hasattr(state, "b11_victory_details")
