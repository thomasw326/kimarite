"""B11 direct-win result screens explain losses for either wrestler."""
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler


def game():
    card = Card(99921, "Blank")
    a = FighterState(Wrestler("Player", 0, 0, 0, card, card, card))
    b = FighterState(Wrestler("Opponent", 0, 0, 0, card, card, card))
    s = BoutState(a, b)
    s.b11_explain_wins = True
    return s


def test_opponent_ringout_explained_without_ki_zone():
    s = game()
    s.win_source = "ringout"
    s.declare_winner(Side.B, "Oshidashi")
    assert s.winner is Side.B
    details = s.b11_victory_details
    assert details["source"] == "ringout"
    assert "ring boundary" in details["requirement_text"]
    assert "not a Kimarite Zone requirement check" in details["requirement_text"]


def test_exhaustion_explained():
    s = game()
    s.declare_winner(Side.A, "Exhaustion")
    assert "no cards left to draw" in s.b11_victory_details["requirement_text"]


def test_classic_has_no_extra_result():
    s = game()
    s.b11_explain_wins = False
    s.win_source = "ringout"
    s.declare_winner(Side.B, "Oshidashi")
    assert not hasattr(s, "b11_victory_details")
