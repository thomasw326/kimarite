from kimarite.models import Card, Wrestler
from kimarite.tachiai import compare_tachiai


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
