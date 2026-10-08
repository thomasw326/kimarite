from kimarite.models import Card, Side, Stat, Wrestler
from kimarite.tachiai import (
    compare_tachiai,
    first_exchange_side,
    push_from_power_advantage,
    spirit_rewards,
    technique_access,
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
    assert technique_access(2) == (4, 2)
    assert technique_access(3) == (5, 3)
    assert technique_access(6) == (8, 4)


def test_spirit_reward_scaling():
    assert spirit_rewards(2) == (0, 0)
    assert spirit_rewards(3) == (1, 0)
    assert spirit_rewards(6) == (1, 1)


def test_first_exchange_priority_spirit_then_power_then_technique():
    blank = Card(1, "Blank")
    a = Wrestler("A", 1, 1, 3, blank, blank, blank)
    b = Wrestler("B", 5, 5, 2, blank, blank, blank)

    comparison = compare_tachiai(a, b)

    assert first_exchange_side(comparison, a, b) is Side.A
