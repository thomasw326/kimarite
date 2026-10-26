"""B11 live session integration without modifying Classic B10 entrypoint."""
import json
import pytest
from kimarite.b10_human_session import ROSTER_PATH, roster, public_snapshot
from kimarite.b11_pending_session import PendingB11Session
from kimarite.b11_live_opening import start_b11_human_bout


@pytest.mark.parametrize("indices", [[], [0], [0, 2], [0, 1, 2]])
def test_live_b11_session_enters_human_bout_without_fake_opening(indices):
    human, opponent = roster()[:2]
    names = json.loads(ROSTER_PATH.read_text())["decks"][human]["cards"][:3]
    pending = PendingB11Session.start(human, opponent, names, seed=23)
    pending.confirm(indices)
    live = start_b11_human_bout(pending)
    snapshot = public_snapshot(live)
    assert snapshot["opening"]["human"]["mode"] == "player_controlled"
    assert len(snapshot["opening"]["human"]["committed"]) == len(indices)
    assert len(snapshot["opening"]["human"]["retained"]) == 3 - len(indices)
    assert "top_of_deck" not in snapshot["opening"]["human"]
    assert "prepared_tachiai" not in snapshot["opening"]["human"]
    assert "hand" not in snapshot["opponent"]
    assert snapshot["phase"] in {"select_cards", "human_turn", "finished"}
