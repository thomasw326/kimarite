"""B11 player Tachiai allocation contract tests.

These validate the selection boundary independently of the older B10
single-prepared-card Tachiai resolver, which remains unchanged until the
pending-selection phase is integrated.
"""
import pytest
from collections import Counter

from kimarite.b11_player_opening import PlayerOpening
from kimarite.catalog import card_by_name


def cards():
    return [card_by_name(n) for n in (
        "Oshi", "Tsuki", "Shove", "Oshidashi", "Oshi", "Harite"
    )]


def test_each_legal_commit_count_preserves_card_ownership():
    deck = cards()
    opening = PlayerOpening.from_names(deck, ["Oshidashi", "Oshi", "Tsuki"])
    for indices in ([], [0], [2, 0], [0, 1, 2]):
        committed, retained = opening.partition(indices)
        assert len(committed) + len(retained) == 3
        assert len(committed) == len(indices)
        assert len(committed) + len(retained) == len(opening.cards)
        assert Counter(c.name for c in committed + retained) == Counter(c.name for c in opening.cards)
    assert len(opening.remaining_deck(deck)) == len(deck) - 3


def test_no_kimarite_required():
    opening = PlayerOpening.from_names(cards(), ["Oshi", "Tsuki", "Shove"])
    assert not any(card.is_kimarite for card in opening.cards)
    committed, retained = opening.partition([])
    assert committed == ()
    assert retained == opening.cards


def test_duplicate_names_require_real_deck_copies():
    deck = cards()
    opening = PlayerOpening.from_names(deck, ["Oshi", "Oshi", "Tsuki"])
    assert opening.deck_indices[0] != opening.deck_indices[1]
    assert len(opening.remaining_deck(deck)) == len(deck) - 3
    with pytest.raises(ValueError):
        PlayerOpening.from_names(deck, ["Oshi", "Oshi", "Oshi"])


@pytest.mark.parametrize("indices", [[0, 0], [3], [-1], [True], ["0"], [0, 1, 1]])
def test_invalid_commit_indices_rejected(indices):
    opening = PlayerOpening.from_names(cards(), ["Oshi", "Tsuki", "Shove"])
    with pytest.raises(ValueError):
        opening.partition(indices)


def test_invalid_allocations_rejected():
    with pytest.raises(ValueError):
        PlayerOpening.from_names(cards(), ["Oshi", "Tsuki"])
    with pytest.raises(ValueError):
        PlayerOpening.from_names(cards(), ["Oshi", "Tsuki", "Not a card"])
