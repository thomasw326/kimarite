"""Every Classic Kimarite has a readable, predicate-aligned victory breakdown."""
from kimarite.b11_victory_checks import victory_checks
from kimarite.kimarite import KIMARITE_PREDICATES, kimarite_is_satisfied
from kimarite.catalog import card_by_name
from kimarite.models import BoutState, Card, FighterState, Side, Wrestler, GripState


def test_all_classic_kimarite_have_complete_checks():
    blank = Card(99901, "Blank")
    a = FighterState(Wrestler("A", 0, 0, 0, blank, blank, blank))
    b = FighterState(Wrestler("B", 0, 0, 0, blank, blank, blank))
    state = BoutState(a, b)
    for name in KIMARITE_PREDICATES:
        result = victory_checks(state, Side.A, name)
        assert result, f"Missing checks for {name}"
        assert all(set(x) == {"label","actual","required","met"} for x in result), name
        assert all(isinstance(x["met"], bool) for x in result), name


def test_display_conditions_agree_with_engine_on_sampled_states():
    blank = Card(99902, "Blank")
    for momentum in (-3, -1, 0, 1, 3):
        for position in (-3, 0, 3):
            for power in (4, 8, 12):
                a = FighterState(Wrestler("A", 0, 0, 0, blank, blank, blank))
                b = FighterState(Wrestler("B", 0, 0, 0, blank, blank, blank))
                state = BoutState(a, b, momentum=momentum, position=position)
                a.power = power
                b.power = 7
                a.left_grip = GripState.DEEP if power == 12 else GripState.NONE
                a.right_grip = GripState.GRIP if position == 3 else GripState.NONE
                b.left_grip = GripState.GRIP if momentum == -3 else GripState.NONE
                a.hand = [blank] * (6 if position == 3 else 1)
                b.hand = [blank] * (1 if position == 3 else 2)
                b.unstable = momentum > 0
                a.unstable = momentum < 0
                a.cards_played_this_turn = 4 if power == 12 else 1
                for name in KIMARITE_PREDICATES:
                    expected = kimarite_is_satisfied(state, Side.A, card_by_name(name))
                    actual = all(x["met"] for x in victory_checks(state, Side.A, name))
                    assert actual == expected, (name, momentum, position, power, actual, expected)
