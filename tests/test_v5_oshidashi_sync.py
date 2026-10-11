"""V5.1 Oshidashi requires Position 2+ and Momentum 2+ without Tachiai caveats."""
from kimarite.catalog import card_by_name
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.models import BoutState, FighterState, Side, Wrestler


def make_state():
    k = card_by_name("Oshidashi")
    a = Wrestler("A", 2, 2, 2, k, k, k)
    b = Wrestler("B", 2, 2, 2, k, k, k)
    return BoutState(FighterState(a, power=3), FighterState(b, power=3),
                     momentum=1, position=2)


def test_oshidashi_ignores_tachiai_spirit_advantage_when_momentum_too_low():
    state = make_state()
    state.tachiai_spirit_advantage_a = 3
    assert not kimarite_is_satisfied(state, Side.A, card_by_name("Oshidashi"))


def test_oshidashi_accepts_momentum_two_without_power_advantage():
    state = make_state()
    state.momentum = 2
    assert kimarite_is_satisfied(state, Side.A, card_by_name("Oshidashi"))


def test_oshidashi_requires_both_position_and_momentum():
    state = make_state()
    state.momentum = 2
    state.position = 1
    assert not kimarite_is_satisfied(state, Side.A, card_by_name("Oshidashi"))
    state.position = 2
    state.momentum = 1
    assert not kimarite_is_satisfied(state, Side.A, card_by_name("Oshidashi"))
