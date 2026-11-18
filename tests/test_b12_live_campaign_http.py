"""End-to-end B12 six-basho backend and actual playable player/AI HTTP flow."""
from copy import deepcopy
import json
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from kimarite import b10_web
from kimarite.b11_player_draft import STARTERS
from kimarite.b12_league import PLAYER, banzuke, commit_day, next_day_matches


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(b10_web, "MAX_POSTS_PER_CLIENT", 10000)
    monkeypatch.setattr(b10_web, "MAX_BOUT_STARTS_PER_CLIENT", 300)
    with b10_web._lock:
        b10_web._rate_history.clear()
    server = ThreadingHTTPServer(("127.0.0.1", 0), b10_web.Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    tokens = []

    def post(path, body, *, expected=200):
        req = Request(
            f"http://127.0.0.1:{server.server_port}{path}",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=75) as response:
                result = json.load(response)
                status = response.status
        except HTTPError as exc:
            status = exc.code
            result = json.loads(exc.read().decode("utf-8"))
        assert status == expected, (path, status, result)
        if path == "/api/session" and status == 201:
            tokens.append(result["token"])
        return result
    try:
        yield post
    finally:
        with b10_web._lock:
            for token in tokens:
                b10_web._sessions.pop(token, None)
                b10_web._session_activity.pop(token, None)
            b10_web._rate_history.clear()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def draft(post, seed):
    starting = list(STARTERS)
    picks = []
    while len(starting) + len(picks) < 28:
        offer = post("/api/b11/draft/offer",
                     {"starting_cards": starting, "picks": picks, "seed": seed})
        picks.append(offer["choices"][0]["name"])
    return starting, picks


def play_passive(post, token, state):
    for _ in range(160):
        if state["finished"]:
            assert state["winner"] in ("A", "B")
            return state
        if state.get("selection"):
            indices = list(range(state["selection"]["keep"]))
            command = {"type": "choose_cards", "indices": indices}
        elif state.get("can_end_turn"):
            command = {"type": "end_turn"}
        else:
            raise AssertionError("Human bout cannot advance")
        state = post(f"/api/session/{token}/action", command)["state"]
    raise AssertionError("Playable B12 player bout exceeded 160 decisions")


def test_real_player_bout_plus_20_real_ai_bouts_is_one_atomic_day(client):
    post = client
    started = post("/api/b12/campaign/new",
                   {"player_name": "My Shikona", "seed": 20261117})
    roster, league = started["roster"], started["league"]
    assert len(roster["wrestlers"]) == 60
    assert len({w["format_id"] for w in roster["wrestlers"]}) == 60
    assert len(started["banzuke"]) == 42
    assert all(row["wins"] == row["losses"] == 0 for row in started["banzuke"])
    assert [row["rank"] for row in started["banzuke"]] == list(range(1, 43))
    assert len(started["opponents"]) == 3
    assert all(p["status"] == "upcoming" for p in started["opponents"])

    # Heya redraws do not reroll any opponents already announced.
    repeat = post("/api/b12/campaign/plan", {"roster": roster, "league": league})
    assert repeat["league"] == league
    assert repeat["opponents"] == started["opponents"]
    paired = post("/api/b12/campaign/pair", {"roster": roster, "league": league})
    pending = paired["league"]
    opponent = paired["opponent"]
    assert len(pending["pending_matches"]) == 21
    assert pending["pending_matches"][0] == ["player", opponent["id"]]
    assert opponent["id"] == started["opponents"][0]["id"]
    assert opponent["name"] == started["opponents"][0]["name"]
    assert post("/api/b12/campaign/pair", {"roster": roster, "league": pending})["league"] == pending

    starting, picks = draft(post, 20261211)
    deal = post("/api/b11/draft/deal", {
        "starting_cards": starting, "picks": picks,
        "draft_seed": 20261211, "seed": 20261211,
    })
    opening = [c["name"] for c in deal["cards"][:3]]
    response = post("/api/session", {
        "human": "My Shikona", "opponent": opponent["name"],
        "seed": 25252, "opening_mode": "b11_live",
        "opening_cards": opening, "starting_cards": starting,
        "draft_picks": picks, "draft_seed": 20261211,
        "duplicated_indices": [],
        "created_stats": {"power": 2, "technique": 1, "spirit": 0},
        "b12_opponent_ai": opponent, "b12_player_rank": roster["player"]["rank"],
        "b12_campaign": {
            "seed": roster["seed"],
            "basho": 0,
            "day": 0,
            "opponent_id": opponent["id"],
        },
    }, expected=201)
    assert response["state"]["phase"] == "choose_tachiai"
    assert response["state"]["opening"] is None  # AI Tachiai stays secret.
    assert response["state"]["opponent"]["name"] == opponent["name"]
    token = response["token"]
    premature = post("/api/b12/campaign/resolve",
                     {"roster": roster, "league": pending, "token": token},
                     expected=409)
    assert premature["code"] == "campaign_conflict"
    begun = post(f"/api/session/{token}/action",
                 {"type": "commit_tachiai", "indices": [0]})["state"]
    assert begun["opening"]["opponent"] is not None
    state = play_passive(post, token, begun)
    assert state["winner"] in ("A", "B")
    saved_pending = json.loads(json.dumps(pending))
    resolved = post("/api/b12/campaign/resolve",
                    {"roster": roster, "league": pending, "token": token})
    assert resolved["ai_matches"] == 20
    assert len(resolved["league"]["results"]) == 1
    assert len(resolved["league"]["results"][0]) == 21
    assert len(resolved["league"]["ai_bout_audit"][0]) == 20
    assert resolved["player_winner"] == (
        "player" if state["winner"] == "A" else opponent["id"])
    assert sum(r["wins"] for r in resolved["banzuke"]) == 21
    assert all(r["wins"]+r["losses"] == 1 for r in resolved["banzuke"])
    assert roster == started["roster"]
    assert pending == saved_pending  # Input cannot be advanced behind browser's back.
    # Duplicate response request returns the previously saved matchday, not
    # a new 20-bout simulation or a second increment.
    assert post("/api/b12/campaign/resolve",
                {"roster": roster, "league": pending, "token": token}) == resolved
    reloaded = json.loads(json.dumps(resolved["league"]))
    after_day = post("/api/b12/campaign/plan",
                     {"roster": roster, "league": reloaded})
    assert after_day["league"] == reloaded
    assert after_day["opponents"][1]["id"] == started["opponents"][1]["id"]
    assert after_day["opponents"][1]["wins"] + after_day["opponents"][1]["losses"] == 1
    second = post("/api/b12/campaign/pair", {"roster": roster, "league": reloaded})
    assert second["opponent"]["id"] == started["opponents"][1]["id"]
    assert second["opponent"]["wins"] + second["opponent"]["losses"] == 1


def test_five_basho_transitions_keep_exact_rank_and_one_way_reserves(client):
    post = client
    start = post("/api/b12/campaign/new",
                 {"player_name": "Six-Basho Rikishi", "seed": 22339})
    roster, league = start["roster"], start["league"]
    initial_ids = {w["wrestler_id"] for w in roster["wrestlers"]}
    initial_formats = {w["format_id"] for w in roster["wrestlers"]}
    all_promoted = set()
    for basho in range(5):
        opening_player_rank = roster["player"]["rank"]
        for day in range(15):
            matches = next_day_matches(league)
            # These outcomes are ONLY test fixtures for a lightweight
            # transition check. Live AI engine is tested by the HTTP test
            # above and by test_b12_real_ai_day's full 300-AI-bout basho.
            outcomes = [
                {"a": a, "b": b,
                 "winner": (PLAYER if a == PLAYER and day < 9 else
                            b if a == PLAYER else a)}
                for a, b in matches
            ]
            league = commit_day(league, outcomes)
            assert all(w["wins"]+w["losses"] == day+1
                       for w in league["wrestlers"])
        transitioned = post("/api/b12/campaign/advance",
                            {"roster": roster, "league": league})
        report = transitioned["changes"]
        assert report["player_from"] == opening_player_rank
        assert report["player_to"] == max(1, min(42, opening_player_rank - 6))
        assert len(report["promoted"]) == len(report["relegated"]) <= 3
        assert not set(report["promoted"]) & all_promoted
        all_promoted.update(report["promoted"])
        roster, league = transitioned["roster"], transitioned["league"]
        assert roster["completed_basho"] == basho+1
        assert league["day"] == 0
        assert len(transitioned["opponents"]) == 3
        assert all(w["wins"] == w["losses"] == 0 for w in league["wrestlers"])
        assert {w["wrestler_id"] for w in roster["wrestlers"]} == initial_ids
        assert {w["format_id"] for w in roster["wrestlers"]} == initial_formats
        assert sorted(w["rank"] for w in league["wrestlers"]) == list(range(1, 43))
    assert len(all_promoted) <= 15
    assert len(roster["reserve_queue"]) >= 4


@pytest.mark.parametrize("card_name,extra", [("Sonkyo", 0), (None, 1)])
def test_saved_rematch_card_tops_only_player_deck(client, monkeypatch, card_name, extra):
    from kimarite.human_bout import HumanBout

    campaign = client("/api/b12/campaign/new", {"player_name": "Rematch Rikishi", "seed": 117})
    paired = client("/api/b12/campaign/pair", {k: campaign[k] for k in ("roster", "league")})
    foe = paired["opponent"]
    starting, picks = draft(client, 121)
    if card_name is None:
        from kimarite.b11_player_draft import AVAILABLE

        card_name = next(name for name in AVAILABLE if name not in starting + picks)
    setup = {
        "human": "Rematch Rikishi", "opponent": foe["name"], "seed": 122,
        "opening_mode": "b11_live", "opening_cards": starting[:3],
        "starting_cards": starting, "draft_picks": picks, "draft_seed": 121,
        "created_stats": {"power": 2, "technique": 1, "spirit": 0},
        "b12_opponent_ai": foe, "b12_player_rank": 42,
        "b12_campaign": {"seed": 117, "basho": 1, "day": 0, "opponent_id": foe["id"]},
    }
    captured = []
    advance = HumanBout.advance

    def capture(bout):
        captured.append(tuple(tuple(c.name for c in fighter.draw_pile)
                              for fighter in (bout.state.fighter_a, bout.state.fighter_b)))
        return advance(bout)

    monkeypatch.setattr(HumanBout, "advance", capture)

    def opening(override):
        session = client("/api/session", {**setup, **override}, expected=201)
        return client(f"/api/session/{session['token']}/action",
                      {"type": "commit_tachiai", "indices": []})["state"]

    opening({})
    baseline, opponent = captured[0]
    captured.clear()
    rematch = opening({"b12_rematch_top_card": card_name})
    own, rematch_opponent = captured[0]
    assert own[0] == card_name
    assert len(own) == len(baseline) + extra
    assert rematch_opponent == opponent
    assert any(f"Rematch reward: {card_name}" in event for event in rematch["events"])
    captured.clear()
    opening({"b12_rematch_top_card": card_name})
    assert captured[0] == (own, rematch_opponent)
