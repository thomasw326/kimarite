"""Current-sheet Tachiai/finish condition regression checks."""
from kimarite.catalog import card_by_name
from kimarite.kimarite import kimarite_is_satisfied
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler


def make_state():
    starter = card_by_name("Oshidashi")
    a = Wrestler("A", 2, 2, 2, starter, starter, starter)
    b = Wrestler("B", 2, 2, 2, starter, starter, starter)
    return BoutState(FighterState(a, power=3), FighterState(b, power=3),
                     momentum=1, position=2)


def test_oshidashi_accepts_spirit_advantage_three():
    state = make_state()
    assert not kimarite_is_satisfied(state, Side.A, card_by_name("Oshidashi"))
    state.tachiai_spirit_advantage_a = 3
    assert kimarite_is_satisfied(state, Side.A, card_by_name("Oshidashi"))


def test_oshidashi_accepts_one_power_advantage():
    state = make_state()
    state.fighter_a.power = 4
    assert kimarite_is_satisfied(state, Side.A, card_by_name("Oshidashi"))


def test_oshidashi_requires_position_and_momentum():
    state = make_state()
    state.tachiai_spirit_advantage_a = 3
    state.position = 1
    assert not kimarite_is_satisfied(state, Side.A, card_by_name("Oshidashi"))
    state.position = 2
    state.momentum = 0
    assert not kimarite_is_satisfied(state, Side.A, card_by_name("Oshidashi"))
