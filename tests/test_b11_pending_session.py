"""Pre-resolution B11 interface must not construct/advertise a resolved bout."""
import json
import pytest

from kimarite.b11_pending_session import PendingB11Session
from kimarite.b10_human_session import ROSTER_PATH, roster


def test_pending_session_hides_opponent_opening_and_never_advances_turns():
    human, opponent = roster()[:2]
    cards = json.loads(ROSTER_PATH.read_text())["decks"][human]["cards"]
    session = PendingB11Session.start(human, opponent, cards[:3])
    view = session.snapshot()
    assert view["phase"] == "choose_tachiai"
    assert view["opening"] is None
    assert view["events"] == []
    assert view["legal_plays"] == []
    assert view["can_end_turn"] is False
    assert view["opponent"] == {"name": opponent}
    assert len(view["tachiai_choice"]["cards"]) == 3


def test_pending_session_rejects_impossible_allocations():
    human, opponent = roster()[:2]
    with pytest.raises(ValueError):
        PendingB11Session.start(human, opponent, ["Not a card", "Oshi", "Tsuki"])
    with pytest.raises(ValueError):
        PendingB11Session.start(human, opponent, ["Oshi", "Tsuki"])
