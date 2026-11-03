"""B12 correction: Tachiai uses the full ±4 ring; Oshidashi requires +3 Position."""
import pytest

from kimarite.kimarite import kimarite_is_satisfied
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler
from kimarite.rules import POSITION_MIN, POSITION_MAX
from kimarite.tachiai import apply_tachiai_push


BLANK = Card(99010, "Blank")
OSHIDASHI = Card(99011, "Oshidashi", power=2, spirit=1, is_kimarite=True)


def bout():
    a = Wrestler("A", 0, 0, 0, OSHIDASHI, BLANK, BLANK)
    b = Wrestler("B", 0, 0, 0, OSHIDASHI, BLANK, BLANK)
    return BoutState(FighterState(a), FighterState(b))


@pytest.mark.parametrize("side,expected", [(Side.A, 4), (Side.B, -4)])
def test_tachiai_four_push_stays_on_ring(side, expected):
    state = bout()
    assert (POSITION_MIN, POSITION_MAX) == (-4, 4)
    assert apply_tachiai_push(state, side, 4) == 4
    assert state.position == expected
    assert state.winner is None


@pytest.mark.parametrize("side,expected", [(Side.A, 4), (Side.B, -4)])
def test_tachiai_five_push_is_ringout(side, expected):
    state = bout()
    assert apply_tachiai_push(state, side, 5) == 5
    assert state.position == expected
    assert state.winner is side
    assert state.win_source == "ringout"
    assert state.win_method == "Oshidashi"


@pytest.mark.parametrize("side", [Side.A, Side.B])
def test_tachiai_push_from_three_to_four_then_ringout(side):
    state = bout()
    state.position = 3 * state.sign(side)
    assert apply_tachiai_push(state, side, 1) == 1
    assert state.position == 4 * state.sign(side)
    assert state.winner is None
    assert apply_tachiai_push(state, side, 1) == 1
    assert state.position == 4 * state.sign(side)
    assert state.winner is side


@pytest.mark.parametrize("side", [Side.A, Side.B])
def test_oshidashi_requires_three_position_and_two_momentum(side):
    state = bout()
    state.momentum = 2 * state.sign(side)
    state.position = 2 * state.sign(side)
    assert not kimarite_is_satisfied(state, side, OSHIDASHI)
    state.position = 3 * state.sign(side)
    assert kimarite_is_satisfied(state, side, OSHIDASHI)
    state.momentum = 1 * state.sign(side)
    assert not kimarite_is_satisfied(state, side, OSHIDASHI)
    state.momentum = 2 * state.sign(side)
    state.position = 4 * state.sign(side)
    assert kimarite_is_satisfied(state, side, OSHIDASHI)
