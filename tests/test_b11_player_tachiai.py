"""Tachiai comparison contract for player-controlled opening."""
from kimarite.b11_player_tachiai import compare_player_tachiai, player_tachiai_orbs
from kimarite.catalog import card_by_name
from kimarite.models import Stat, Wrestler
from kimarite.tachiai import compare_tachiai


def fighter(name):
    return Wrestler(name, 3, 0, 3, card_by_name("Oshidashi"),
                   card_by_name("Oshi"), card_by_name("Tsuki"),
                   primary=Stat.POWER, secondary=Stat.SPIRIT, tertiary=Stat.TECHNIQUE)


def test_zero_commits_use_only_base_and_universal_one():
    human = fighter("Player")
    result = player_tachiai_orbs(human, [])
    assert (result.power, result.technique, result.spirit) == (4, 1, 4)


def test_committed_orbs_only():
    human = fighter("Player")
    cards = [card_by_name("Oshi"), card_by_name("Oshi"), card_by_name("Shove")]
    result = player_tachiai_orbs(human, cards)
    assert (result.power, result.technique, result.spirit) == (6, 1, 6)


def test_ai_comparison_is_identical_to_classic_ai():
    human, ai = fighter("Player"), fighter("AI")
    baseline = compare_tachiai(human, ai)
    new = compare_player_tachiai(human, ai, [card_by_name("Oshi")])
    assert new.wrestler_b == baseline.wrestler_b
    assert new.wrestler_a.spirit == 5
