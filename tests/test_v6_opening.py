"""Opt-in V6 opening contract; legacy B7 opening must remain unchanged."""
from copy import deepcopy

import pytest

from kimarite.models import BoutState, Card, FighterState, Side, Wrestler
from kimarite.opening_v6 import (
    OpeningCommitment, assign_starting_hand, commit_opening,
    first_exchange_side_v6,
)
from kimarite.tachiai import compare_tachiai, technique_access


def sample():
    blank = Card(999, "legacy placeholder")
    wrestler_a = Wrestler("Pressure Fighter", 3, 0, 3, blank, blank, blank)
    wrestler_b = Wrestler("Fast Grappler", 0, 2, 4, blank, blank, blank)
    fighter_a = FighterState(wrestler_a, draw_pile=[
        Card(10, "Tsukidashi", 1, 0, 2, True),
        Card(11, "Tsuppari", 2, 0, 1),
        Card(12, "Oshi", 0, 0, 1),
        Card(13, "Later", 0, 2, 0),
    ])
    fighter_b = FighterState(wrestler_b, draw_pile=[
        Card(20, "Yorikiri", 1, 1, 1, True),
        Card(21, "Gain Right Grip", 0, 3, 0),
        Card(22, "Explosive Step", 0, 0, 3),
        Card(23, "Later B", 0, 0, 1),
    ])
    return BoutState(fighter_a, fighter_b)


def ready():
    state = sample()
    assign_starting_hand(state.fighter_a, (10, 11, 12))
    assign_starting_hand(state.fighter_b, (20, 21, 22))
    return state


def test_assign_three_cards_preserves_identity_and_draw_pile():
    state = sample()
    cards = assign_starting_hand(state.fighter_a, (12, 10, 11))
    assert [c.card_id for c in cards] == [12, 10, 11]
    assert [c.card_id for c in state.fighter_a.hand] == [12, 10, 11]
    assert [c.card_id for c in state.fighter_a.draw_pile] == [13]
    assert not state.fighter_a.kimarite_zone


def test_commitment_counts_only_committed_orbs_and_kimarite_stays_active():
    state = ready()
    result = commit_opening(
        state, OpeningCommitment((10, 11)), OpeningCommitment((21,)),
    )
    assert [c.card_id for c in state.fighter_a.hand] == [12]
    assert [c.card_id for c in state.fighter_b.hand] == [20, 22]
    assert [c.card_id for c in state.fighter_a.tachiai_committed] == [10, 11]
    assert [c.card_id for c in state.fighter_a.kimarite_zone] == [10]
    assert [c.card_id for c in state.fighter_a.exhausted_cards] == [11]
    assert [c.card_id for c in state.fighter_b.exhausted_cards] == [21]
    assert [c.card_id for c in state.fighter_b.kimarite_zone] == []
    assert [c.card_id for c in result.side_a.effects_to_resolve] == [11]
    assert [c.card_id for c in result.side_b.effects_to_resolve] == [21]
    # +1 baseline applies to both sides, and only committed orbs count.
    assert (result.comparison.wrestler_a.power,
            result.comparison.wrestler_a.technique,
            result.comparison.wrestler_a.spirit) == (7, 1, 7)
    assert (result.comparison.wrestler_b.power,
            result.comparison.wrestler_b.technique,
            result.comparison.wrestler_b.spirit) == (1, 6, 5)
    assert result.comparison.power_advantage_a == 6
    assert result.comparison.technique_advantage_a == -5
    assert state.winner is None  # Committing a finisher does not win.


@pytest.mark.parametrize("a_choice,b_choice", [
    ((), ()),  # Both keep all three.
    ((10, 11, 12), (20, 21, 22)),  # Both commit all three.
    ((12,), (20, 22)),
])
def test_all_legal_commitment_sizes(a_choice, b_choice):
    state = ready()
    result = commit_opening(
        state, OpeningCommitment(a_choice), OpeningCommitment(b_choice),
    )
    assert len(state.fighter_a.hand) + len(state.fighter_a.tachiai_committed) == 3
    assert len(state.fighter_b.hand) + len(state.fighter_b.tachiai_committed) == 3
    assert len(result.side_a.committed) == len(a_choice)
    assert len(result.side_b.committed) == len(b_choice)
    assert set(c.card_id for c in state.fighter_a.exhausted_cards).isdisjoint(
        c.card_id for c in state.fighter_a.hand
    )


def test_empty_commitment_only_counts_base_stats_and_baseline():
    state = ready()
    result = commit_opening(state, OpeningCommitment(()), OpeningCommitment(()))
    assert result.comparison.wrestler_a.power == 4
    assert result.comparison.wrestler_a.technique == 1
    assert result.comparison.wrestler_a.spirit == 4
    assert all(not state.fighter(side).kimarite_zone for side in (Side.A, Side.B))


@pytest.mark.parametrize("invalid", [
    OpeningCommitment((10, 10)),
    OpeningCommitment((10, 999)),
    OpeningCommitment((True,)),
    OpeningCommitment((10, 11, 12, 13)),
])
def test_invalid_decisions_leave_both_sides_untouched(invalid):
    state = ready()
    before = deepcopy(state)
    with pytest.raises(ValueError):
        commit_opening(state, OpeningCommitment((10,)), invalid)
    assert state == before


def test_cannot_commit_same_hand_twice():
    state = ready()
    commit_opening(state, OpeningCommitment((10,)), OpeningCommitment((20,)))
    before = deepcopy(state)
    with pytest.raises(ValueError):
        commit_opening(state, OpeningCommitment(()), OpeningCommitment(()))
    assert state == before


def test_assign_rejects_duplicate_or_nonexistent_card_without_changes():
    state = sample()
    before = deepcopy(state)
    with pytest.raises(ValueError):
        assign_starting_hand(state.fighter_a, (10, 11, 11))
    assert state == before
    with pytest.raises(ValueError):
        assign_starting_hand(state.fighter_a, (10, 11, 9999))
    assert state == before


def test_old_comparison_and_technique_rules_remain_available():
    state = ready()
    # The old comparison still uses two fixed prepared sources, as before.
    old = compare_tachiai(state.fighter_a.wrestler, state.fighter_b.wrestler)
    assert old.wrestler_a.power == 4
    assert old.wrestler_b.spirit == 5
    assert technique_access(4) == (6, 4)


def test_v6_spirit_initiative_overrides_higher_opponent_technique():
    state = ready()
    opening = commit_opening(
        state, OpeningCommitment((11, 12)), OpeningCommitment((21,)),
    )
    # A has Spirit 6 vs B's 5, but B has Technique 6 vs A's 1.
    assert opening.comparison.spirit_advantage_a == 1
    assert opening.comparison.technique_advantage_a < 0
    assert first_exchange_side_v6(
        opening, state.fighter_a.wrestler, state.fighter_b.wrestler,
    ) is Side.A
