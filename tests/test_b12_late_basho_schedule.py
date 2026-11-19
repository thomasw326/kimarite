"""Sumo-like B12 schedules: top-ranked rivals face later, leader climbers follow W–L."""
import json

import pytest

from kimarite.b12_division_roster import make_roster
from kimarite.b12_league import (
    BASHO_DAYS, FINAL_DAY, MARQUEE_RANK_PAIRS, PLAYER, RECORD_MATCH_START,
    TOP_TIER_MAX_RANK, banzuke, commit_day, new_basho, next_day_matches,
    next_opponents, plan_block,
)


def season(seed=122, *, player_rank=42):
    roster = make_roster(seed, "Player Rikishi")
    if player_rank != 42:
        displaced = next(w for w in roster["wrestlers"] if w["rank"] == player_rank)
        displaced["rank"] = 42
        roster["player"]["rank"] = player_rank
    return new_basho(roster)


def resolve_test_day(league, day, *, player_wins=True):
    """Controlled fixture outcomes, NEVER production AI match results."""
    matches = next_day_matches(league)
    results = []
    for a, b in matches:
        winner = PLAYER if a == PLAYER and player_wins else (b if a == PLAYER else a)
        results.append({"a": a, "b": b, "winner": winner})
    return commit_day(league, results), matches


def ranked_pair_ids(league, left_rank, right_rank):
    ranked = {w["rank"]: w["id"] for w in league["wrestlers"]}
    return frozenset((ranked[left_rank], ranked[right_rank]))


@pytest.mark.parametrize("seed", [4, 29, 106, 612, 20261118])
def test_final_day_reserves_top_four_marquee_pairs_without_rerolls(seed):
    league = season(seed)
    rivals = {ranked_pair_ids(league, a, b) for a, b in MARQUEE_RANK_PAIRS}
    seen = {}
    top_top_early = 0
    top_top_late = 0
    for day in range(BASHO_DAYS):
        if day % 3 == 0:
            first = plan_block(league)
            assert plan_block(league) == first
        if day == 12:
            frozen = json.loads(json.dumps(league))
            assert plan_block(frozen) == next_opponents(league)
        matches = next_day_matches(league)
        assert matches == next_day_matches(json.loads(json.dumps(league)))
        ranks = {w["id"]: w["rank"] for w in league["wrestlers"]}
        for a, b in matches:
            pair = frozenset((a, b))
            assert pair not in seen
            seen[pair] = day
            if ranks[a] <= TOP_TIER_MAX_RANK and ranks[b] <= TOP_TIER_MAX_RANK:
                if day < RECORD_MATCH_START:
                    top_top_early += 1
                else:
                    top_top_late += 1
            if day < FINAL_DAY:
                assert pair not in rivals
        if day == FINAL_DAY:
            assert rivals <= {frozenset(pair) for pair in matches}
        league, _ = resolve_test_day(league, day)
    assert all(seen[pair] == FINAL_DAY for pair in rivals)
    assert top_top_late > top_top_early
    assert len(seen) == 315
    assert sum(w["wins"] for w in banzuke(league)) == 315


@pytest.mark.parametrize("player_rank", [1, 2, 3, 4])
def test_top_ranked_player_gets_marquee_rival_as_last_bout(player_rank):
    league = season(475, player_rank=player_rank)
    rival_rank = {1: 2, 2: 1, 3: 4, 4: 3}[player_rank]
    rival_id = next(w["id"] for w in league["wrestlers"] if w["rank"] == rival_rank)
    ranked = {w["id"]: w["rank"] for w in league["wrestlers"]}
    for day in range(BASHO_DAYS):
        if day % 3 == 0:
            selected = plan_block(league)
            assert len(selected) == 3
            if day == 12:
                assert selected[2]["id"] == rival_id
                assert selected[2]["rank"] == rival_rank
                # The confirmed Day 15 opponent must survive browser save/reload.
                restored = json.loads(json.dumps(league))
                assert next_opponents(restored) == selected
        current = next_day_matches(league)
        player_foe = current[0][1]
        if day < FINAL_DAY:
            assert player_foe != rival_id
        else:
            assert player_foe == rival_id
        # Both top-4 rank pairs remain possible on the final matchday.
        if day == FINAL_DAY:
            rival_pairs = {ranked_pair_ids(league, a, b) for a, b in MARQUEE_RANK_PAIRS}
            assert rival_pairs <= {frozenset(pair) for pair in current}
        league, _ = resolve_test_day(league, day)
    assert len(league["wrestlers"][-1]["played"]) == 15


def test_undefeated_low_ranked_player_still_gets_record_matched_late_opponents():
    league = season(173, player_rank=42)
    for day in range(9):
        league, _ = resolve_test_day(league, day, player_wins=True)
    assert league["day"] == RECORD_MATCH_START
    player = next(w for w in league["wrestlers"] if w["id"] == PLAYER)
    assert player["wins"] == 9
    candidates = [w for w in league["wrestlers"]
                  if w["id"] != PLAYER and w["id"] not in player["played"]]
    minimum = min(abs(w["wins"] - player["wins"]) for w in candidates)
    previews = plan_block(league)
    # The same best-result contenders would be drawn even if the player
    # began the basho at #42; late scheduling is not fixed rank proximity.
    assert len(previews) == 3
    assert all(p["wins"] + p["losses"] == 9 for p in previews)
    assert min(abs(p["wins"] - 9) for p in previews) == minimum
    assert [p["rank"] for p in previews] != [39, 40, 41]
    for day in range(9, 15):
        league, _ = resolve_test_day(league, day, player_wins=True)
    assert next(w for w in league["wrestlers"] if w["id"] == PLAYER)["wins"] == 15


def test_old_saved_tournament_with_early_marquee_result_remains_playable():
    # Before the matchmaking patch, #1 and #2 could already have met early.
    # Don't demand a rematch or reject an in-progress player's old ledger.
    league = season(83)
    top_one, top_two = (next(w for w in league["wrestlers"] if w["rank"] == r)
                        for r in (1, 2))
    top_one["played"].append(top_two["id"])
    top_two["played"].append(top_one["id"])
    # This artificial prior edge is only a feasibility fixture. The normal
    # live ledger is always consistent across all participants' day records.
    for day in range(BASHO_DAYS):
        pairs = next_day_matches(league)
        assert frozenset((top_one["id"], top_two["id"])) not in {
            frozenset(p) for p in pairs}
        league, _ = resolve_test_day(league, day)
    assert league["day"] == BASHO_DAYS


@pytest.mark.parametrize("player_rank", [22, 42])
def test_player_opening_samples_rank_window_and_next_block_varies(player_rank):
    first_blocks, second_blocks = set(), set()
    for seed in range(8):
        league = season(seed, player_rank=player_rank)
        first = plan_block(league)
        ranks = {foe["rank"] for foe in first}
        assert len(ranks) == 3
        assert all(0 < abs(rank - player_rank) <= 7 for rank in ranks)
        assert plan_block(json.loads(json.dumps(league))) == first
        first_blocks.add(frozenset(ranks))
        for day in range(3):
            league, _ = resolve_test_day(league, day)
        second = {foe["rank"] for foe in plan_block(league)}
        assert len(second) == 3 and not second & ranks
        assert all(abs(rank - player_rank) <= 10 for rank in second)
        second_blocks.add(frozenset(second))
    assert len(first_blocks) > 1
    assert len(second_blocks) > 1


@pytest.mark.parametrize("player_rank", [1, 2, 8, 9, 16, 42])
def test_early_yokozuna_komusubi_pairings_include_player_when_ranked_there(player_rank):
    league = season(133, player_rank=player_rank)
    for day, ranks in enumerate((((1, 9), (2, 8)), ((1, 8), (2, 9)))):
        league, matches = resolve_test_day(league, day)
        assert {ranked_pair_ids(league, a, b) for a, b in ranks} <= {
            frozenset(pair) for pair in matches
        }
