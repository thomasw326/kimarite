from kimarite.catalog import card_by_name
from kimarite.models import BoutState, FighterState, Side, Wrestler


def test_hiwaza_positions():
    c = card_by_name('Oshi')
    for pos, label in [(-3, 'Fumidashi'), (-2, 'Koshikudake'), (0, 'Koshikudake'), (2, 'Koshikudake'), (3, 'Fumidashi')]:
        a = FighterState(Wrestler('A', 2, 1, 0, c, c, c))
        b = FighterState(Wrestler('B', 0, 0, 0, c, c, c))
        s = BoutState(a, b, position=pos)
        s.b11_explain_wins = True
        s.declare_winner(Side.A, 'Exhaustion')
        assert s.win_method == label
        assert s.win_source == 'hiwaza'
        assert s.winner is Side.A


def test_classic_unchanged():
    c = card_by_name('Oshi')
    s = BoutState(FighterState(Wrestler('A', 2, 1, 0, c, c, c)), FighterState(Wrestler('B', 0, 0, 0, c, c, c)), position=3)
    s.declare_winner(Side.A, 'Exhaustion')
    assert s.win_method == 'Exhaustion'
