"""Smoke the actual HTTP route and B10 browser session contract."""
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import json

from kimarite.b10_web import Handler


def test_browser_routes_and_session_round_trip():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = "http://127.0.0.1:" + str(server.server_port)
    def get(path):
        with urlopen(base + path, timeout=15) as response:
            return response.status, response.headers.get("Content-Type"), response.read()
    def post(path, payload):
        req = Request(base + path, json.dumps(payload).encode(), {"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=15) as response:
            return response.status, json.load(response)
    try:
        status, _, html = get("/")
        assert status == 200 and b"viewport" in html and b"style.css" in html
        _, typ, css = get("/style.css")
        assert typ.startswith("text/css") and b"@media" in css
        _, typ, js = get("/client.js")
        assert typ.startswith("text/javascript") and b"choose_cards" in js
        _, _, raw_roster = get("/api/roster")
        roster = json.loads(raw_roster)["roster"]
        assert len(roster) == 26
        status, created = post("/api/session", {"human": "Arm Controller", "opponent": "The Technician", "seed": 42})
        assert status == 201
        token, state = created["token"], created["state"]
        assert "hand" not in state["opponent"]
        assert state["human"]["name"] == "Arm Controller"
        _, _, persisted = get("/api/session/" + token)
        assert json.loads(persisted)["turn"] == state["turn"]
        if state["selection"]:
            keep = state["selection"]["keep"]
            _, acted = post("/api/session/" + token + "/action", {"type": "choose_cards", "indices": list(range(keep))})
            assert acted["state"]["selection"] is None
        elif state["can_end_turn"]:
            _, acted = post("/api/session/" + token + "/action", {"type": "end_turn"})
            assert "state" in acted
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_rejected_end_turn_returns_authoritative_selection_state():
    from kimarite.b10_web import _sessions
    from kimarite.b10_human_session import new_b10_session
    from urllib.error import HTTPError
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    token = "pending-selection-regression"
    try:
        bout = new_b10_session("Hand-Size Specialist", "Outside Fighter", seed=20261021,
                               opening={"kimarite":"Katasukashi",
                                        "prepared":"Attempt Two-Handed Grip",
                                        "top":"Attempt Deep Outside Grip"})
        assert bout.pending_selection is not None
        _sessions[token] = bout
        req = Request("http://127.0.0.1:" + str(server.server_port) +
                      "/api/session/" + token + "/action",
                      json.dumps({"type":"end_turn"}).encode(),
                      {"Content-Type":"application/json"}, method="POST")
        try:
            urlopen(req, timeout=15)
            assert False, "Ending turn with outstanding selection must be rejected"
        except HTTPError as exc:
            payload = json.load(exc)
            assert exc.code == 409
            assert payload["code"] == "invalid_action"
            assert payload["state"]["selection"] is not None
            assert payload["state"]["human"]["name"] == "Hand-Size Specialist"
    finally:
        _sessions.pop(token, None)
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_indexed_choices_display_names_without_changing_engine_values():
    from kimarite.b10_web import labelled_choices
    from kimarite.effects import ChoiceRequired
    from kimarite.b10_human_session import new_b10_session
    from kimarite.catalog import card_by_name
    from kimarite.models import Side
    bout = new_b10_session("Arm Controller", "The Technician", seed=42)
    own = bout.state.fighter(Side.A)
    own.hand = [card_by_name("Oshi"), card_by_name("Tsuki"), card_by_name("Shove")]
    result = labelled_choices(bout, ChoiceRequired("Oshi", "hand_index", [0, 1]), {"hand_index": 0})
    assert [o["value"] for o in result["options"]] == [0, 1]
    assert [o["label"] for o in result["options"]] == ["1. Tsuki", "2. Shove"]
    hidden = labelled_choices(bout, ChoiceRequired("Hatakikomi", "opponent_hand_index", [0, 1]))
    assert hidden["options"][0]["label"] == "Opponent hand position 1 (hidden card)"
    assert all("name" not in o for o in hidden["options"])
    boolean = labelled_choices(bout, ChoiceRequired("Hatakikomi", "use_optional", [True, False]))
    assert [o["label"] for o in boolean["options"]] == ["Yes", "No"]
