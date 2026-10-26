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


def test_http_preview_is_private_and_rejects_premature_actions():
    from http.server import ThreadingHTTPServer
    from threading import Thread
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    from kimarite.b10_web import Handler, _sessions

    human, opponent = roster()[:2]
    cards = json.loads(ROSTER_PATH.read_text())["decks"][human]["cards"][:3]
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = "http://127.0.0.1:" + str(server.server_port)
    token = None
    try:
        payload = {"human": human, "opponent": opponent,
                   "opening_mode": "b11_preview", "opening_cards": cards}
        request = Request(base + "/api/session", json.dumps(payload).encode(),
                          {"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=15) as response:
            assert response.status == 201
            result = json.load(response)
        token = result["token"]
        assert result["state"]["opponent"] == {"name": opponent}
        assert result["state"]["events"] == []
        with urlopen(base + "/api/session/" + token, timeout=15) as response:
            assert json.load(response) == result["state"]
        action = Request(base + "/api/session/" + token + "/action",
                         json.dumps({"type": "end_turn"}).encode(),
                         {"Content-Type": "application/json"}, method="POST")
        with pytest.raises(HTTPError) as exc:
            urlopen(action, timeout=15)
        assert exc.value.code == 409
        rejected = json.load(exc.value)
        assert rejected["code"] == "b11_preview_only"
        assert rejected["state"] == result["state"]
    finally:
        if token:
            _sessions.pop(token, None)
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


@pytest.mark.parametrize("indices", [[], [0], [1, 2], [0, 1, 2]])
def test_confirm_records_once_without_exposing_opponent(indices):
    human, opponent = roster()[:2]
    cards = json.loads(ROSTER_PATH.read_text())["decks"][human]["cards"][:3]
    session = PendingB11Session.start(human, opponent, cards)
    committed = session.confirm(indices)
    assert committed["phase"] == "tachiai_resolution_pending"
    assert committed["tachiai_choice"]["committed_indices"] == indices
    assert len(committed["tachiai_choice"]["retained"]) == 3 - len(indices)
    assert committed["opponent"] == {"name": opponent}
    assert committed["events"] == []
    assert committed["opening"] is None
    assert not committed["can_end_turn"]
    assert session.snapshot() == committed
    with pytest.raises(ValueError, match="already been made"):
        session.confirm([])


def test_invalid_confirmation_leaves_opening_uncommitted():
    human, opponent = roster()[:2]
    cards = json.loads(ROSTER_PATH.read_text())["decks"][human]["cards"][:3]
    session = PendingB11Session.start(human, opponent, cards)
    with pytest.raises(ValueError):
        session.confirm([0, 0])
    assert session.snapshot()["phase"] == "choose_tachiai"
