"""HTTP smoke: a named, drafted player wrestles against an existing AI style."""
import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

from kimarite.b10_web import Handler
from kimarite.b11_player_draft import STARTERS, options_for


def post(port, path, data):
    request = Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        return response.status, json.load(response)


def test_api_accepts_drafted_custom_player_and_completes_tachiai_handoff():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        seed = 1624
        starting = list(STARTERS)
        picks = []
        while len(starting) + len(picks) < 28:
            picks.append(options_for(starting, picks, seed)[0])
        request = {
            "human": "My Rikishi",
            "opponent": "The Technician",
            "seed": seed,
            "opening_mode": "b11_live",
            "opening_cards": starting[:3],
            "starting_cards": starting,
            "draft_picks": picks,
            "draft_seed": seed,
            "created_stats": {"power": 2, "technique": 1, "spirit": 0},
            "duplicated_indices": [],
        }
        status, started = post(server.server_port, "/api/session", request)
        assert status == 201
        assert started["state"]["phase"] == "choose_tachiai"
        assert started["state"]["human"]["name"] == "My Rikishi"
        assert started["state"]["opponent"]["name"] == "The Technician"
        assert started["state"]["opening"] is None
        assert "cards" not in started["state"]["opponent"]

        status, live = post(
            server.server_port,
            f"/api/session/{started['token']}/action",
            {"type": "commit_tachiai", "indices": [0]},
        )
        assert status == 200
        assert live["state"]["human"]["name"] == "My Rikishi"
        assert live["state"]["opponent"]["name"] == "The Technician"
        assert live["state"]["opening"]["human"]["base_stats"] == [2, 1, 0]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
