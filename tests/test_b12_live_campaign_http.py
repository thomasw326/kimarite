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


@pytest.mark.parametrize("index", [0, 1, 2])
def test_rematch_top_card_waits_for_commit_and_replays(client, monkeypatch, index):
    from kimarite import b11_live_opening

    post = client
    campaign = post("/api/b12/campaign/new", {"player_name": "Rematch Rikishi", "seed": 117})
    request = {key: campaign[key] for key in ("roster", "league")}
    next_foe = campaign["opponents"][0]
    assert not post("/api/b12/campaign/pair", request)["rematch_tachiai"]

    prior_loss = {"opponent": next_foe["name"], "won": False}  # Older campaign save.
    later_win = {"opponent_id": next_foe["id"], "opponent": next_foe["name"], "won": True}
    assert not post("/api/b12/campaign/pair", {
        **request, "tournament_history": [{"results": [prior_loss]}, {"results": [later_win]}],
    })["rematch_tachiai"]
    id_only_loss = {"opponent_id": next_foe["id"], "opponent": "Old label", "won": False}
    paired = post("/api/b12/campaign/pair", {
        **request, "tournament_history": [{"results": [prior_loss]},
                                         {"results": [id_only_loss if index else prior_loss]}],
    })
    assert paired["rematch_tachiai"]
    foe = paired["opponent"]
    starting, picks = draft(post, 121)
    setup = {
        "human": "Rematch Rikishi", "opponent": foe["name"], "seed": 122,
        "opening_mode": "b11_live", "opening_cards": starting[:3],
        "starting_cards": starting, "draft_picks": picks, "draft_seed": 121,
        "created_stats": {"power": 2, "technique": 1, "spirit": 0},
        "b12_opponent_ai": foe, "b12_player_rank": 42,
        "b12_campaign": {"seed": 117, "basho": 0, "day": 0, "opponent_id": foe["id"]},
        "b12_rematch_tachiai": paired["rematch_tachiai"],
    }

    captures = []
    resolve = b11_live_opening.resolve_prepared_tachiai

    def record_opening(state, comparison, **kwargs):
        ai = state.fighter_b
        captures.append((list(ai.draw_pile), list(ai.kimarite_zone), ai.wrestler, comparison.wrestler_b))
        return resolve(state, comparison, **kwargs)

    monkeypatch.setattr(b11_live_opening, "resolve_prepared_tachiai", record_opening)
    original = post("/api/session", {**setup, "b12_rematch_tachiai": False}, expected=201)
    commit = {"type": "commit_tachiai", "indices": [0, 2]}
    post(f"/api/session/{original['token']}/action", commit)
    baseline, opening_zone, wrestler, stats = captures.pop()

    def begin_rematch():
        created = post("/api/session", setup, expected=201)
        path = f"/api/session/{created['token']}/action"
        assert created["state"]["phase"] == "choose_tachiai"
        assert created["state"]["opponent"] == {"name": foe["name"]}
        assert created["state"]["opening"] is None
        assert "rematch_tachiai" not in created["state"]
        post(path, {"type": "choose_rematch_top", "index": index}, expected=409)
        offered = post(path, commit)["state"]
        assert offered["phase"] == "choose_rematch_top"
        assert offered["tachiai_commitment"] == [0, 2]
        assert offered["events"] == []
        assert offered["opening"] is None
        assert not offered["can_end_turn"]
        assert [c["name"] for c in offered["rematch_tachiai"]["cards"]] == [
            wrestler.starting_kimarite.name, wrestler.prepared_tachiai_card.name,
            wrestler.top_of_deck_card.name,
        ]
        assert post(path, commit)["state"] == offered  # Lost response retry.
        post(path, {**commit, "indices": [1]}, expected=409)
        assert not captures
        return path, offered

    path, offered = begin_rematch()
    for invalid in (-1, 3, False, "0", None):
        post(path, {"type": "choose_rematch_top", "index": invalid}, expected=400)
    action = {"type": "choose_rematch_top", "index": index}
    live = post(path, action)["state"]
    assert live["rematch_tachiai_index"] == index
    assert live["opening"]["opponent"]["top_of_deck"] == offered["rematch_tachiai"]["cards"][index]
    assert post(path, action)["state"] == live
    post(path, {**action, "index": (index + 1) % 3}, expected=409)
    pile, zone, opening, orbs = captures.pop()
    assert orbs == stats
    assert zone == opening_zone
    assert opening.prepared_tachiai_card == wrestler.prepared_tachiai_card
    if index == 2:
        assert pile == baseline
    else:
        assert pile[1:] == baseline
        assert pile[0] is not zone[0] and pile[0] is not opening.prepared_tachiai_card
    assert pile[0] is opening.top_of_deck_card

    restored_path, restored_offer = begin_rematch()
    assert restored_offer == offered
    assert post(restored_path, action)["state"] == live
