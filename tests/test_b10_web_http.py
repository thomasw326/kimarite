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
