"""Pre-draft B11 campaign boundary regression: 15 dealt bouts and physical card conservation.

The 15-bout loop tests deterministic 9-card deals and valid disjoint allocations.
The opening handoff tests the 40 approved original copies, not generated cantrips.
"""
from collections import Counter
import json

import pytest

from kimarite.b10_human_session import ROSTER_PATH, management_deal, roster
from kimarite.b11_live_opening import build_resolved_b11_opening
from kimarite.b11_pending_session import PendingB11Session
from kimarite.catalog import card_by_name


def physical_cards(fighter):
    return (
        fighter.draw_pile + fighter.hand + fighter.discard_pile
        + fighter.kimarite_zone + [temporary.card for temporary in fighter.temporary_zone]
    )


@pytest.mark.parametrize("commit_indices", [[], [0], [1, 2], [0, 1, 2]])
def test_approved_deck_copy_conservation_across_commit_counts(commit_indices):
    human, opponent = roster()[:2]
    deck_names = json.loads(ROSTER_PATH.read_text())["decks"][human]["cards"]
    # Kimarite alone have no opening side effects that generate or exhaust cards.
    picked = [name for name in deck_names if card_by_name(name).is_kimarite][:3]
    assert len(picked) == 3
    pending = PendingB11Session.start(human, opponent, picked, seed=4141)
    pending.confirm(commit_indices)
    first = build_resolved_b11_opening(pending, seed=4141)
    again = build_resolved_b11_opening(pending, seed=4141)
    expected = Counter(deck_names)
    assert Counter(card.name for card in physical_cards(first.state.fighter_a)) == expected
    assert Counter(card.name for card in physical_cards(again.state.fighter_a)) == expected
    assert [card.name for card in first.state.fighter_a.draw_pile] == [
        card.name for card in again.state.fighter_a.draw_pile
    ]
    assert [card.name for card in first.state.fighter_a.hand] == [
        card.name for card in again.state.fighter_a.hand
    ]


def test_15_deal_allocations_are_disjoint_and_seed_replay_stable():
    human, opponent = roster()[:2]
    deck_names = json.loads(ROSTER_PATH.read_text())["decks"][human]["cards"]
    for round_number in range(5):
        deal = management_deal(human, seed=82000 + round_number)
        replay = management_deal(human, seed=82000 + round_number)
        assert deal == replay
        dealt = deal["cards"]
        assert len(dealt) == 9
        assert {card["deal_index"] for card in dealt} == set(range(9))
        assert Counter(card["name"] for card in dealt) <= Counter(deck_names)
        for group in range(3):
            choices = [dealt[group * 3 + i]["name"] for i in range(3)]
            pending = PendingB11Session.start(
                human, opponent, choices, seed=82000 + round_number * 3 + group
            )
            pending.confirm([])
            resolved = build_resolved_b11_opening(pending, seed=pending.seed)
            assert Counter(card.name for card in physical_cards(resolved.state.fighter_a)) == Counter(deck_names)
