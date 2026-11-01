"""Live engine reveal-path regression for B11 multi-commit Tachiai."""
from kimarite.catalog import card_by_name
from kimarite.models import BoutState, FighterState, Side, Wrestler
from kimarite.tachiai import compare_tachiai
from kimarite.tachiai_effects import _reveal_tachiai_orbs


def fighter(name, pile):
    wrestler = Wrestler(
        name, 3, 0, 3, card_by_name("Oshidashi"),
        card_by_name("Oshi"), card_by_name("Tsuki")
    )
    return FighterState(wrestler, draw_pile=[card_by_name(n) for n in pile])


def test_explicit_double_oshi_reveals_two_chains():
    human = fighter("Human", ["Tsuki", "Shove", "Oshi", "Harite", "Salt Throw"])
    ai = fighter("AI", [])
    state = BoutState(human, ai)
    comparison = compare_tachiai(human.wrestler, ai.wrestler)
    before = comparison.wrestler_a
    _reveal_tachiai_orbs(
        state, comparison,
        committed_cards={Side.A: (card_by_name("Oshi"), card_by_name("Oshi"))},
    )
    assert [c.name for c in human.discard_pile] == [
        "Tsuki", "Shove", "Oshi", "Harite"
    ]
    assert [c.name for c in human.draw_pile] == ["Salt Throw"]
    assert comparison.wrestler_a.power == before.power + 6
    assert comparison.wrestler_a.spirit == before.spirit + 2


def test_classic_prepared_oshi_still_only_starts_one_chain():
    human = fighter("Human", ["Oshi", "Shove", "Harite"])
    ai = fighter("AI", [])
    state = BoutState(human, ai)
    comparison = compare_tachiai(human.wrestler, ai.wrestler)
    _reveal_tachiai_orbs(state, comparison)
    assert [c.name for c in human.discard_pile] == ["Oshi", "Shove"]
    assert [c.name for c in human.draw_pile] == ["Harite"]


def test_explicit_zero_commits_does_not_reveal_for_human():
    human = fighter("Human", ["Shove", "Harite"])
    ai = fighter("AI", [])
    state = BoutState(human, ai)
    comparison = compare_tachiai(human.wrestler, ai.wrestler)
    _reveal_tachiai_orbs(state, comparison, committed_cards={Side.A: ()})
    assert not human.discard_pile
    assert [c.name for c in human.draw_pile] == ["Shove", "Harite"]
