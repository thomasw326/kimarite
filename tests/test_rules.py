from kimarite.models import BoutState, Card, FighterState, GripState, Side, Wrestler
from kimarite.rules import gain_momentum, gain_push


def wrestler(name: str) -> Wrestler:
    kimarite = Card(100, "Kimarite", is_kimarite=True)
    prepared = Card(101, "Prepared")
    top = Card(102, "Top")
    return Wrestler(name, 0, 0, 0, kimarite, prepared, top)


def state() -> BoutState:
    return BoutState(FighterState(wrestler("A")), FighterState(wrestler("B")))


def test_momentum_overflow_is_discarded_without_push():
    bout = state()
    bout.momentum = 3

    gain_momentum(bout, Side.A, 2)

    assert bout.momentum == 3
    assert bout.position == 0
    assert bout.winner is None


def test_push_overflow_converts_to_momentum():
    bout = state()
    bout.position = 2

    gain_push(bout, Side.A, 3)

    assert bout.position == 3
    assert bout.momentum == 2
    assert bout.winner is None


def test_overflow_loop_without_grip_is_ringout():
    bout = state()
    bout.position = 3
    bout.momentum = 3

    gain_push(bout, Side.A, 1)

    assert bout.winner is Side.A
    assert bout.win_method == "Ringout"


def test_momentum_overflow_even_at_both_caps_is_not_ringout():
    bout = state()
    bout.position = 3
    bout.momentum = 3
    bout.fighter_a.left_grip = GripState.GRIP

    gain_momentum(bout, Side.A, 1)

    assert bout.winner is None
    assert bout.win_method is None
    assert bout.position == 3


def test_shared_tracks_are_symmetric_for_side_b():
    bout = state()
    bout.position = -2

    gain_push(bout, Side.B, 3)

    assert bout.position == -3
    assert bout.momentum == -2


def test_momentum_overflow_is_symmetric_for_side_b():
    bout = state()
    bout.momentum = -3
    gain_momentum(bout, Side.B, 3)
    assert bout.momentum == -3
    assert bout.position == 0
    assert bout.winner is None
