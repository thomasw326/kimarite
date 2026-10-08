from kimarite.models import BoutState, FighterState, Card, Side, Stat, Wrestler
from kimarite.tachiai import (
    compare_tachiai,
    first_exchange_side,
    push_from_power_advantage,
    spirit_rewards,
    technique_access,
    technique_thresholds,
    apply_tachiai_power_push,
)


def test_tachiai_uses_base_stats_starting_kimarite_and_prepared_card():
    kimarite = Card(100, "Test Kimarite", power=1, technique=2, spirit=0, is_kimarite=True)
    prepared = Card(101, "Prepared Card", power=2, technique=0, spirit=3)
    top = Card(102, "Top Card")

    a = Wrestler("A", 1, 1, 1, kimarite, prepared, top)
    b = Wrestler("B", 2, 0, 0, kimarite, prepared, top)

    result = compare_tachiai(a, b)

    assert result.wrestler_a.power == 4
    assert result.wrestler_a.technique == 3
    assert result.wrestler_a.spirit == 4
    assert result.power_advantage_a == -1
    assert result.technique_advantage_a == 1
    assert result.spirit_advantage_a == 1


def test_power_advantage_scaling():
    assert push_from_power_advantage(0) == 0
    assert push_from_power_advantage(1) == 1
    assert push_from_power_advantage(2) == 1
    assert push_from_power_advantage(3) == 2
    assert push_from_power_advantage(6) == 3


def test_technique_access_scaling():
    assert technique_access(0) == (2, 2)
    assert technique_access(1) == (3, 3)
    assert technique_access(3) == (5, 4)
    assert technique_access(4) == (6, 4)
    assert technique_access(6) == (8, 5)
    assert technique_access(7) == (9, 6)
    assert technique_access(10) == (12, 7)
    assert [technique_thresholds(x) for x in range(0, 11)] == [
        0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4
    ]


def test_power_defense_blocks_spirit_push_example():
    blank = Card(99, "Blank")
    a = Wrestler("A", 3, 3, 9, blank, blank, blank)
    b = Wrestler("B", 6, 9, 3, blank, blank, blank)
    comparison = compare_tachiai(a, b)
    state = BoutState(FighterState(a), FighterState(b))
    winner, push = apply_tachiai_power_push(state, comparison)
    assert winner is Side.A
    assert push == 0
    assert state.position == 0


def test_power_defense_never_reverses_push():
    blank = Card(99, "Blank")
    a = Wrestler("A", 3, 7, 6, blank, blank, blank)
    b = Wrestler("B", 2, 2, 5, blank, blank, blank)
    comparison = compare_tachiai(a, b)
    state = BoutState(FighterState(a), FighterState(b))
    _, push = apply_tachiai_power_push(state, comparison)
    assert push == 1
    assert state.position == 1


def test_spirit_reward_scaling():
    assert spirit_rewards(2) == (0, 0)
    assert spirit_rewards(3) == (1, 0)
    assert spirit_rewards(6) == (1, 1)


def test_first_exchange_priority_technique_then_spirit_then_power():
    blank = Card(1, "Blank")
    a = Wrestler("A", 1, 1, 3, blank, blank, blank)
    b = Wrestler("B", 5, 5, 2, blank, blank, blank)

    comparison = compare_tachiai(a, b)

    assert first_exchange_side(comparison, a, b) is Side.B
