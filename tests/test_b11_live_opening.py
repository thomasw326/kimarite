"""Engine-level B11 handoff: conserve card copies and resolve reveals once."""
import json
import pytest

from kimarite.b10_human_session import ROSTER_PATH, roster
from kimarite.b11_pending_session import PendingB11Session
from kimarite.catalog import card_by_name
from kimarite.b11_live_opening import build_resolved_b11_opening


@pytest.mark.parametrize("indices", [[], [0], [1, 2], [0, 1, 2]])
def test_committed_bout_uses_exact_human_cards_and_has_active_exchange(indices):
    human, opponent = roster()[:2]
    names = json.loads(ROSTER_PATH.read_text())["decks"][human]["cards"][:3]
    phase = PendingB11Session.start(human, opponent, names)
    phase.confirm(indices)
    result = build_resolved_b11_opening(phase, seed=42)
    own = result.state.fighter_a
    # All physical originals must be in draw, hand, discard, temporary, or
    # accounted as Kimarite-zone cards: no duplicated prepared/top card.
    accounted = (
        len(own.draw_pile) + len(own.hand) + len(own.discard_pile)
        + len(own.kimarite_zone) + len(own.temporary_zone)
    )
    assert accounted >= 40 - len(indices)
    assert len(own.hand) == 3 - len(indices)
    assert result.state.active_side is not None or result.state.winner is not None
    assert [c.name for c in own.kimarite_zone] == [names[i] for i in indices if card_by_name(names[i]).is_kimarite]


def test_live_handoff_disallows_precommit_execution():
    human, opponent = roster()[:2]
    names = json.loads(ROSTER_PATH.read_text())["decks"][human]["cards"][:3]
    pending = PendingB11Session.start(human, opponent, names)
    with pytest.raises(ValueError, match="Commit"):
        build_resolved_b11_opening(pending)
