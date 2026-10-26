"""V4.4 Tachiai stat reassignment, no card orb changes."""
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler
from kimarite.tachiai import (
    apply_tachiai_power_push, compare_tachiai, first_exchange_side,
    technique_access, technique_thresholds,
)


BLANK = Card(9000, "Blank")


def wrestler(name, power, technique, spirit, ranking=1):
    return Wrestler(name, power, technique, spirit, BLANK, BLANK, BLANK, ranking=ranking)


def test_spirit_generates_push_and_power_defends():
    a = wrestler("A", 1, 0, 7)
    b = wrestler("B", 5, 0, 0)
    comparison = compare_tachiai(a, b)
    state = BoutState(FighterState(a), FighterState(b))
    winner, push = apply_tachiai_power_push(state, comparison)
    # Current 1/4/7 Spirit threshold: advantage 7 gives 3 Push;
    # Power defense of 2 reduces this to one.
    assert winner is Side.A
    assert push == 1
    assert state.position == 1


def test_power_advantage_by_itself_creates_no_push():
    a = wrestler("A", 10, 0, 0)
    b = wrestler("B", 0, 0, 0)
    comparison = compare_tachiai(a, b)
    state = BoutState(FighterState(a), FighterState(b))
    assert apply_tachiai_power_push(state, comparison) == (None, 0)
    assert state.position == 0


def test_technique_card_access_new_thresholds():
    assert [technique_access(x) for x in range(0, 8)] == [
        (2, 2), (2, 2), (2, 2), (3, 3),
        (3, 3), (3, 3), (4, 4), (4, 4),
    ]
    assert [technique_thresholds(x) for x in (1, 4, 7, 10)] == [1, 2, 3, 4]


def test_initiative_technique_then_spirit_then_power():
    assert first_exchange_side(
        compare_tachiai(wrestler("A", 0, 2, 0), wrestler("B", 4, 1, 5)),
        wrestler("A", 0, 2, 0), wrestler("B", 4, 1, 5)
    ) is Side.A
    assert first_exchange_side(
        compare_tachiai(wrestler("A", 5, 2, 1), wrestler("B", 0, 2, 2)),
        wrestler("A", 5, 2, 1), wrestler("B", 0, 2, 2)
    ) is Side.B
    assert first_exchange_side(
        compare_tachiai(wrestler("A", 4, 2, 1), wrestler("B", 3, 2, 1)),
        wrestler("A", 4, 2, 1), wrestler("B", 3, 2, 1)
    ) is Side.A
