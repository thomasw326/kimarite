"""B12 division ledger invariants: 21 simultaneous matches × 15 days."""
from collections import Counter
from copy import deepcopy
import json

import pytest

from kimarite.b12_division_roster import make_roster
from kimarite.b12_league import (
    BASHO_DAYS, MATCHES_PER_DAY, PLAYER, banzuke, commit_day,
    new_basho, next_day_matches, next_opponents, plan_block,
)


def outcomes(matches, seed, day):
    """Test-only known winners; production must use the actual bout engine."""
    return [{"a": a, "b": b, "winner": a if (seed + day + i) % 2 else b}
            for i, (a, b) in enumerate(matches)]


def make_world(seed=412, player="My Rikishi"):
    return new_basho(make_roster(seed, player))


def test_start_has_42_unique_ranked_names_styles_and_zero_records():
    world = make_world()
    rows = banzuke(world)
    assert len(rows) == 42
    assert [r["rank"] for r in rows] == list(range(1, 43))
    assert all(r["wins"] == r["losses"] == 0 for r in rows)
    assert all(r["style"] != "Player-created" for r in rows[:-1])
    assert rows[-1]["name"] == "My Rikishi"
    assert world["day"] == 0
    assert world["results"] == []


@pytest.mark.parametrize("seed", [0, 1, 3, 19, 42, 20261117])
def test_full_basho_has_315_results_without_any_repeat_or_double_booking(seed):
    league = make_world(seed)
    seen_pairs = set()
    previous_rank_names = [(r["rank"], r["name"], r["style"]) for r in banzuke(league)]
    last_player_opps = set()
    for day in range(BASHO_DAYS):
        if day % 3 == 0:
            upcoming = plan_block(league)
            assert len(upcoming) == 3
            assert all(o["status"] == "upcoming" for o in upcoming)
            assert not (set(o["id"] for o in upcoming) & last_player_opps)
            last_player_opps |= {o["id"] for o in upcoming}
            assert plan_block(league) == upcoming  # Heya redraw cannot reroll opponents.
        else:
            upcoming = next_opponents(league)
            assert len(upcoming) == 3
            assert sum(o["status"] == "completed" for o in upcoming) == day % 3
            assert all(o["wins"]+o["losses"] == day for o in upcoming)
        matches = next_day_matches(league)
        assert matches == next_day_matches(league)
        assert len(matches) == MATCHES_PER_DAY == 21
        assert len(set(w for a,b in matches for w in (a,b))) == 42
        assert matches[0] == [PLAYER, upcoming[day % 3]["id"]]
        for a, b in matches:
            assert a != b
            pair = frozenset((a, b))
            assert pair not in seen_pairs
            seen_pairs.add(pair)
        original = deepcopy(league)
        league = commit_day(league, outcomes(matches, seed, day))
        assert original["day"] == day
        assert original["results"] == league["results"][:-1]
        assert league["day"] == day + 1
        assert league["pending_matches"] == []
        assert len(league["results"]) == day + 1
        assert [(r["rank"], r["name"], r["style"]) for r in banzuke(league)] == previous_rank_names
        assert all(r["wins"] + r["losses"] == day + 1 for r in banzuke(league))
        assert sum(r["wins"] for r in banzuke(league)) == (day + 1) * 21
        assert sum(r["losses"] for r in banzuke(league)) == (day + 1) * 21
        if (day + 1) % 3 == 0:
            assert league["block_player_opponents"] == []
    assert league["day"] == 15
    assert len(seen_pairs) == 315
    assert len(league["results"]) == 15
    assert len({o for o in league["wrestlers"][-1]["played"]}) == 15
    assert len(league["wrestlers"][-1]["played"]) == 15
    assert all(len(r["played"]) == 15 for r in league["wrestlers"])
    assert all(len(day_matches) == 21 for day_matches in league["results"])
    with pytest.raises(ValueError):
        next_day_matches(league)


def test_round_4_and_5_are_planned_from_current_records_not_day_zero():
    league = make_world(900)
    for day in range(15):
        if day % 3 == 0:
            previews = plan_block(league)
            if day >= 9:
                player = next(w for w in league["wrestlers"] if w["id"] == PLAYER)
                allowed = [w for w in league["wrestlers"]
                           if w["id"] != PLAYER and w["id"] not in player["played"]]
                near_records = sorted(allowed, key=lambda w:
                    (abs(w["wins"]-player["wins"]), abs(w["rank"]-player["rank"])))
                cutoff = abs(near_records[2]["wins"]-player["wins"])
                assert all(abs(p["wins"]-player["wins"]) <= cutoff for p in previews)
        league = commit_day(league, outcomes(next_day_matches(league), 900, day))


def test_matches_are_saved_and_pending_opponents_recover_without_reroll():
    league = make_world(12)
    plan_block(league)
    first = next_day_matches(league)
    recovered = json.loads(json.dumps(league))
    assert first == next_day_matches(recovered)
    assert next_opponents(recovered) == next_opponents(league)
    recovered = commit_day(recovered, outcomes(first, 12, 0))
    again = json.loads(json.dumps(recovered))
    assert next_opponents(again) == next_opponents(recovered)
    assert all(w["wins"]+w["losses"] == 1 for w in again["wrestlers"])
    assert again["wrestlers"][-1]["played"] == recovered["wrestlers"][-1]["played"]


def test_all_21_results_are_required_atomically_and_cannot_commit_twice():
    league = make_world(512)
    matches = next_day_matches(league)
    good = outcomes(matches, 512, 0)
    before = deepcopy(league)
    bad_results = [
        good[:-1],
        good[:-1] + [good[0]],
        [*good[:-1], dict(good[-1], winner="not-a-wrestler")],
        [*good[:-1], dict(good[-1], a="unlisted")],
    ]
    for bad in bad_results:
        with pytest.raises(ValueError):
            commit_day(league, bad)
        assert league == before
    committed = commit_day(league, good)
    assert league == before
    with pytest.raises(ValueError):
        commit_day(committed, good)


def test_player_opponents_are_new_after_each_block_with_frozen_rank():
    league = make_world(201)
    first_block = plan_block(league)
    assert len(first_block) == 3
    assert [x["rank"] for x in first_block] == sorted(x["rank"] for x in first_block)[::-1]
    for day in range(3):
        league = commit_day(league, outcomes(next_day_matches(league), 201, day))
    second_block = plan_block(league)
    assert not set(x["id"] for x in first_block) & set(x["id"] for x in second_block)
    assert all(x["wins"]+x["losses"] == 3 for x in second_block)
    assert banzuke(league)[-1]["rank"] == 42
