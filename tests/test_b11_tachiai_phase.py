"""Guard the one-shot B11 opening choice before Tachiai resolves."""
import pytest

from kimarite.b11_player_opening import PlayerOpening
from kimarite.b11_tachiai_phase import PendingPlayerTachiai
from kimarite.catalog import card_by_name


def fresh():
    deck = [card_by_name(n) for n in ("Oshi", "Oshi", "Tsuki", "Shove")]
    opening = PlayerOpening.from_names(deck, ("Oshi", "Oshi", "Tsuki"))
    return PendingPlayerTachiai(opening)


@pytest.mark.parametrize("indices", [[], [0], [0, 2], [0, 1, 2]])
def test_commit_zero_to_three_cards(indices):
    phase = fresh()
    assert phase.pending
    result = phase.choose(indices)
    assert not phase.pending
    assert len(result.allocated) == 3
    assert len(result.committed) == len(indices)
    assert len(result.retained) == 3 - len(indices)
    assert result.allocated == phase.opening.cards
    assert result.indices == tuple(sorted(indices))
    with pytest.raises(ValueError, match="already been made"):
        phase.choose([])


@pytest.mark.parametrize("indices", [[0, 0], [3], [-1], [False], ["0"]])
def test_invalid_choice_keeps_phase_pending(indices):
    phase = fresh()
    with pytest.raises(ValueError):
        phase.choose(indices)
    assert phase.pending
    assert phase.decision is None


def test_duplicate_copy_identity_preserved():
    phase = fresh()
    committed = phase.choose([1]).committed
    assert committed[0] is phase.opening.cards[1]
    assert phase.opening.deck_indices[0] != phase.opening.deck_indices[1]
    assert phase.opening.cards[0] in phase.decision.retained
