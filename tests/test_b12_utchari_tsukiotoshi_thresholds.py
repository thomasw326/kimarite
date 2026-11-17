"""B12 threshold changes for Utchari and Tsukiotoshi."""
import pytest
from kimarite.catalog import card_by_name
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler, GripState

@pytest.fixture
def state():
    blank = Card(99998, "Blank")
    a = Wrestler("A", 1, 1, 1, blank, blank, blank)
    b = Wrestler("B", 1, 1, 1, blank, blank, blank)
    return BoutState(FighterState(a, power=3), FighterState(b, power=7))

@pytest.mark.parametrize("side", [Side.A, Side.B])
def test_utchari_requires_minus_four_and_momentum_gain_this_turn(state, side):
    card = card_by_name("Utchari")
    state.fighter(side).gained_momentum_this_turn = True
    state.position = -3 * state.sign(side)
    assert not kimarite_is_satisfied(state, side, card)
    state.position = -4 * state.sign(side)
    assert kimarite_is_satisfied(state, side, card)
    state.fighter(side).gained_momentum_this_turn = False
    assert not kimarite_is_satisfied(state, side, card)

@pytest.mark.parametrize("side", [Side.A, Side.B])
def test_tsukiotoshi_requires_two_momentum_other_conditions_unchanged(state, side):
    card = card_by_name("Tsukiotoshi")
    attacker, defender = state.fighter(side), state.opponent(side)
    attacker.power, defender.power = 3, 7
    attacker.left_grip = GripState.NONE
    attacker.right_grip = GripState.NONE
    defender.unstable = True
    state.momentum = state.sign(side)
    assert not kimarite_is_satisfied(state, side, card)
    state.momentum = 2 * state.sign(side)
    assert kimarite_is_satisfied(state, side, card)
    attacker.left_grip = GripState.GRIP
    assert not kimarite_is_satisfied(state, side, card)
    attacker.left_grip = GripState.NONE
    defender.unstable = False
    assert not kimarite_is_satisfied(state, side, card)
    defender.unstable = True
    attacker.power = 5
    assert not kimarite_is_satisfied(state, side, card)
