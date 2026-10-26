"""B11 multi-commit card ownership and sequential reveal integration."""
import pytest

from kimarite.b11_player_opening import PlayerOpening
from kimarite.b11_tachiai_phase import PendingPlayerTachiai
from kimarite.b11_tachiai_resolution import prepare_human_tachiai
from kimarite.catalog import card_by_name


@pytest.mark.parametrize("indices", [[], [0], [1, 2], [0, 1, 2]])
def test_all_commit_counts_preserve_every_physical_card_once(indices):
    names = ("Oshi", "Oshi", "Tsuki", "Shove", "Harite", "Oshi")
    deck = [card_by_name(name) for name in names]
    opening = PlayerOpening.from_names(deck, ("Oshi", "Oshi", "Tsuki"))
    decision = PendingPlayerTachiai(opening).choose(indices)
    result = prepare_human_tachiai(opening, decision, deck)
    assert len(result.retained_hand) == 3 - len(indices)
    assert len(result.committed) == len(indices)
    assert (len(result.committed) + len(result.retained_hand)
            + len(result.revealed_discard) + len(result.draw_pile)) == len(deck)
    assert [card.name for card in result.retained_hand] == [
        card.name for i, card in enumerate(opening.cards) if i not in indices
    ]


def test_two_committed_oshi_chains_consume_distinct_stop_cards():
    names = ("Oshi", "Oshi", "Tsuki", "Oshi", "Harite", "Tsuki", "Shove", "Yori")
    deck = [card_by_name(name) for name in names]
    opening = PlayerOpening.from_names(deck, ("Oshi", "Oshi", "Tsuki"))
    decision = PendingPlayerTachiai(opening).choose([0, 1])
    result = prepare_human_tachiai(opening, decision, deck)
    assert [c.name for c in result.revealed_discard] == [
        "Oshi", "Harite", "Tsuki", "Shove"
    ]
    assert [c.name for c in result.draw_pile] == ["Yori"]
    assert [c.name for c in result.retained_hand] == ["Tsuki"]
    assert result.reveal_orbs == (4, 0, 3)


def test_uncommitted_oshi_does_not_start_reveal_chain():
    deck = [card_by_name(name) for name in ("Oshi", "Oshi", "Tsuki", "Shove")]
    opening = PlayerOpening.from_names(deck, ("Oshi", "Oshi", "Tsuki"))
    decision = PendingPlayerTachiai(opening).choose([])
    result = prepare_human_tachiai(opening, decision, deck)
    assert result.revealed_discard == ()
    assert result.reveal_orbs == (0, 0, 0)
    assert [c.name for c in result.draw_pile] == ["Shove"]
