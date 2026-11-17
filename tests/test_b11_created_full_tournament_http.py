"""Full 15-bout draft-created wrestler smoke through the real local HTTP API.

Covers five independent nine-card deals, 15 unique AI opponents, player-led
Tachiai, live human/AI turns, card-access choices, and bout completion. The
passive human intentionally skips card plays: we're testing continuity and
whether a bout terminates, not optimal human strategy or game balance.

This is NOT a browser clickthrough or an actual six-tournament campaign.
"""
import json
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from kimarite import b10_web
from kimarite.b10_human_session import roster
from kimarite.b11_player_draft import STARTERS


@pytest.fixture
def live_api(monkeypatch):
    # This is a local load/e2e test. It must not hit the public-preview
    # per-peer throttle for 15 scripted bouts and many turn actions.
    monkeypatch.setattr(b10_web, "MAX_POSTS_PER_CLIENT", 10_000)
    monkeypatch.setattr(b10_web, "MAX_BOUT_STARTS_PER_CLIENT", 100)
    with b10_web._lock:
        b10_web._rate_history.clear()
    server = ThreadingHTTPServer(("127.0.0.1", 0), b10_web.Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    tokens = []
    def post(path, payload):
        request = Request(
            f"http://127.0.0.1:{server.server_port}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                data = json.load(response)
                if path == "/api/session":
                    tokens.append(data["token"])
                return data
        except HTTPError as exc:
            raise AssertionError(f"{path}: HTTP {exc.code}: {exc.read().decode()}") from exc

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
        worker.join(timeout=5)


def draft_28(post, seed):
    starting = list(STARTERS)
    picks = []
    for _ in range(28 - len(starting)):
        offer = post("/api/b11/draft/offer", {
            "starting_cards": starting, "picks": picks, "seed": seed,
        })["choices"]
        assert len(offer) == 3
        assert all(item["name"] not in starting + picks for item in offer)
        picks.append(offer[0]["name"])
    assert len(starting) + len(picks) == 28
    return starting, picks


def finish_bout(post, token, state, *, bout):
    # A passive (non-drafting) human can always End Turn once any mandatory
    # card-access selection is resolved. AI and exchange rules remain real.
    for action_number in range(160):
        if state["finished"]:
            assert state["winner"] in ("A", "B"), (bout, state["stopped_reason"])
            return state, action_number
        if state["selection"] is not None:
            needed = state["selection"]["keep"]
            assert 0 <= needed <= len(state["selection"]["options"])
            command = {"type": "choose_cards", "indices": list(range(needed))}
        elif state["can_end_turn"]:
            command = {"type": "end_turn"}
        else:
            raise AssertionError(
                f"Bout {bout} stalled without an action: {state['phase']}"
            )
        state = post(f"/api/session/{token}/action", command)["state"]
    raise AssertionError(
        f"Bout {bout} did not finish in 160 human decisions; phase={state['phase']}"
    )


def test_created_wrestler_fifteen_bout_http_tournament(live_api):
    post = live_api
    starting, picks = draft_28(post, seed=20261117)
    opponents = list(roster())[:15]
    assert len(opponents) == len(set(opponents)) == 15
    record = []
    physical_cards_used = []
    for block in range(5):
        deal = post("/api/b11/draft/deal", {
            "starting_cards": starting, "picks": picks, "draft_seed": 20261117,
            "duplicated_indices": [], "seed": 21000 + block,
        })
        assert deal["deck_size"] == 28
        cards = deal["cards"]
        assert len(cards) == 9 and len({c["instance_id"] for c in cards}) == 9
        block_used = []
        for group in range(3):
            n = block * 3 + group
            opening = cards[group * 3 : group * 3 + 3]
            original_ids = [c["instance_id"] for c in opening]
            assert len(set(original_ids)) == 3
            block_used.extend(original_ids)
            request = {
                "human": "Tournament Test Rikishi", "opponent": opponents[n],
                "seed": 55000 + n, "opening_mode": "b11_live",
                "opening_cards": [c["name"] for c in opening],
                "starting_cards": starting, "draft_picks": picks,
                "draft_seed": 20261117, "duplicated_indices": [],
                "created_stats": {"power": 2, "technique": 1, "spirit": 0},
            }
            started = post("/api/session", request)
            assert started["state"]["phase"] == "choose_tachiai", n
            assert started["state"]["opening"] is None
            assert started["state"]["human"]["name"] == "Tournament Test Rikishi"
            committed = post(f"/api/session/{started['token']}/action", {
                "type": "commit_tachiai", "indices": [0],
            })["state"]
            assert committed["opening"]["human"]["base_stats"] == [2, 1, 0]
            state, decisions = finish_bout(post, started["token"], committed, bout=n + 1)
            record.append((opponents[n], state["winner"], state["win_method"], decisions))
        assert len(set(block_used)) == 9
        physical_cards_used.append(block_used)
    assert len(record) == 15
    assert len({r[0] for r in record}) == 15
    assert len(physical_cards_used) == 5
    assert all(winner in ("A", "B") for _, winner, _, _ in record)


def test_created_wrestler_six_tournament_http_year(live_api):
    """Exercise 90 real HTTP bouts with a fresh 28-card draft each tournament.

    This deliberately stays at the API layer. The browser's save/resume,
    reward-click UI, and manual device flows still require separate testing.
    Results, rather than assumed wins, determine which assigned ORIGINAL
    cards can be carried into the following tournament as earned duplicates.
    """
    post = live_api
    opponents = list(roster())[:15]
    assert len(opponents) == len(set(opponents)) == 15

    inherited = list(STARTERS)
    history = []
    completed_bouts = 0
    for tournament in range(1, 7):
        starting = list(inherited)
        draft_seed = 20261117 + tournament
        picks = []
        while len(starting) + len(picks) < 28:
            offers = post("/api/b11/draft/offer", {
                "starting_cards": starting,
                "picks": picks,
                "seed": draft_seed,
            })["choices"]
            assert len(offers) == 3, tournament
            assert all(c["name"] not in starting + picks for c in offers)
            picks.append(offers[0]["name"])
        originals = starting + picks
        assert len(originals) == 28
        assert len(starting) <= 12
        duplicate_indices = []
        results = []

        for block in range(5):
            dealt = post("/api/b11/draft/deal", {
                "starting_cards": starting,
                "picks": picks,
                "draft_seed": draft_seed,
                "duplicated_indices": duplicate_indices,
                "seed": 310000 + tournament * 100 + block,
            })
            assert dealt["deck_size"] == 28 + len(duplicate_indices)
            cards = dealt["cards"]
            assert len(cards) == len({c["instance_id"] for c in cards}) == 9

            # A complete block assigns all nine physical cards across three
            # bouts. A physical card may not serve two openings in the block.
            block_ids = set()
            for group in range(3):
                bout_index = block * 3 + group
                opening = cards[group * 3: group * 3 + 3]
                assigned_ids = {c["instance_id"] for c in opening}
                assert len(assigned_ids) == 3
                assert block_ids.isdisjoint(assigned_ids)
                block_ids.update(assigned_ids)

                started = post("/api/session", {
                    "human": "Six Tournament Test Rikishi",
                    "opponent": opponents[bout_index],
                    "seed": 610000 + tournament * 100 + bout_index,
                    "opening_mode": "b11_live",
                    "opening_cards": [c["name"] for c in opening],
                    "starting_cards": starting,
                    "draft_picks": picks,
                    "draft_seed": draft_seed,
                    "duplicated_indices": duplicate_indices,
                    "created_stats": {"power": 2, "technique": 1, "spirit": 0},
                })
                assert started["state"]["phase"] == "choose_tachiai"
                assert started["state"]["opening"] is None
                token = started["token"]
                committed = post(f"/api/session/{token}/action", {
                    "type": "commit_tachiai",
                    "indices": [0],
                })["state"]
                assert committed["opening"]["human"]["base_stats"] == [2, 1, 0]
                outcome, _ = finish_bout(
                    post, token, committed,
                    bout=f"T{tournament} B{bout_index + 1}",
                )
                assert outcome["winner"] in ("A", "B")
                results.append(outcome["winner"])
                completed_bouts += 1

                # The browser offers a duplicate after a winning bout, up to
                # 12 per tournament, only among that bout's assigned originals
                # that have not already been duplicated. Use the first legal
                # option to make the API continuation reproducible.
                if outcome["winner"] == "A" and len(duplicate_indices) < 12:
                    eligible = [
                        int(c["instance_id"].split(":")[1])
                        for c in opening
                        if c["instance_id"].startswith("original:")
                        and int(c["instance_id"].split(":")[1]) not in duplicate_indices
                    ]
                    if eligible:
                        duplicate_indices.append(eligible[0])
            assert len(block_ids) == 9

        assert len(results) == 15
        assert len(duplicate_indices) <= 12
        assert len(set(duplicate_indices)) == len(duplicate_indices)
        wins = results.count("A")
        history.append({"tournament": tournament, "wins": wins, "losses": 15 - wins})
        inherited = [originals[i] for i in duplicate_indices]
        assert len(inherited) == len(duplicate_indices)

    assert completed_bouts == 90
    assert [t["tournament"] for t in history] == [1, 2, 3, 4, 5, 6]
    assert sum(t["wins"] + t["losses"] for t in history) == 90
    assert sum(t["wins"] for t in history) + sum(t["losses"] for t in history) == 90
