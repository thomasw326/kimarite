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


def test_http_b11_live_commit_transitions_to_playable_snapshot():
    from http.server import ThreadingHTTPServer
    from threading import Thread
    from urllib.request import Request, urlopen
    from kimarite.b10_web import Handler, _sessions

    human, opponent = roster()[:2]
    names = json.loads(ROSTER_PATH.read_text())["decks"][human]["cards"][:3]
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = "http://127.0.0.1:" + str(server.server_port)
    token = None

    def post(path, payload):
        request = Request(base + path, json.dumps(payload).encode(),
                          {"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=15) as response:
            return json.load(response)

    try:
        created = post("/api/session", {
            "human": human, "opponent": opponent, "seed": 23,
            "opening_mode": "b11_live", "opening_cards": names,
        })
        token = created["token"]
        assert created["state"]["phase"] == "choose_tachiai"
        assert created["state"]["opponent"] == {"name": opponent}
        resolved = post("/api/session/" + token + "/action", {
            "type": "commit_tachiai", "indices": [0],
        })["state"]
        assert resolved["opening"]["human"]["mode"] == "player_controlled"
        assert resolved["phase"] != "choose_tachiai"
        assert "hand" not in resolved["opponent"]
        with urlopen(base + "/api/session/" + token, timeout=15) as response:
            assert json.load(response) == resolved
    finally:
        if token:
            _sessions.pop(token, None)
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
