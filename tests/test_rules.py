from kimarite.models import BoutState, Card, FighterState, GripState, Side, Wrestler
from kimarite.rules import gain_momentum, gain_push, gain_position, lose_position, POSITION_MIN, POSITION_MAX


def wrestler(name: str) -> Wrestler:
    kimarite = Card(100, "Kimarite", is_kimarite=True)
    prepared = Card(101, "Prepared")
    top = Card(102, "Top")
    return Wrestler(name, 0, 0, 0, kimarite, prepared, top)


def state() -> BoutState:
    return BoutState(FighterState(wrestler("A")), FighterState(wrestler("B")))


def test_momentum_overflow_is_capped_without_push():
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

    assert bout.position == 4
    assert bout.winner is Side.A


def test_overflow_loop_without_grip_is_oshidashi():
    bout = state()
    bout.position = 4
    bout.momentum = 3

    gain_push(bout, Side.A, 1)

    assert bout.winner is Side.A
    assert bout.win_method == "Oshidashi"


def test_overflow_loop_with_grip_is_yorikiri():
    bout = state()
    bout.position = 4
    bout.momentum = 3
    bout.fighter_a.left_grip = GripState.GRIP

    gain_push(bout, Side.A, 1)

    assert bout.winner is Side.A
    assert bout.win_method == "Yorikiri"


def test_shared_tracks_are_symmetric_for_side_b():
    bout = state()
    bout.position = -1

    gain_push(bout, Side.B, 3)

    assert bout.position == -4
    assert bout.momentum == 0


def test_four_is_safe_five_is_ringout():
    bout = state()
    gain_push(bout, Side.A, 4)
    assert bout.position == 4 and bout.winner is None
    gain_push(bout, Side.A, 1)
    assert bout.winner is Side.A and bout.win_source == "ringout"


def test_direct_position_ringout_both_sides():
    bout = state()
    gain_position(bout, Side.B, 4)
    assert bout.position == -4 and bout.winner is None
    lose_position(bout, Side.A, 1)
    assert bout.winner is Side.B


def test_momentum_overflow_does_not_create_push():
    bout = state()
    gain_momentum(bout, Side.A, 4)
    assert bout.momentum == 3 and bout.position == 0
