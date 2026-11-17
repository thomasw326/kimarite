"""Deterministic 42-rikishi banzuke ledger and three-bout planning.

A basho has 42 wrestlers, 21 matches/day and 15 days. The player's next
three opponents are announced before each Heya allocation. Rankings do NOT
change mid-basho; actual winner IDs must be supplied by the bout engine.
This module does not invent match results or change any combat AI.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib

from .b12_division_roster import ACTIVE_AI, BASHO_COUNT, PLAYER_RANK, validate_roster

BASHO_DAYS = 15
BOUT_BLOCK = 3
WRESTLERS = 42
MATCHES_PER_DAY = WRESTLERS // 2
PLAYER = "player"


def new_basho(roster: dict) -> dict:
    """Create fixed opening banzuke with 42 records at 0–0."""
    validate_roster(roster)
    active = sorted((w for w in roster["wrestlers"] if w["division"] == "top"),
                    key=lambda w: w["rank"])
    if len(active) != ACTIVE_AI:
        raise ValueError("Exactly 41 AI wrestlers must enter the top division")
    rows = []
    for w in active:
        rows.append({"id": w["wrestler_id"], "name": w["name"],
                     "style": w["ai_style"], "format_id": w["format_id"],
                     "format_description": w["format_description"],
                     "rank": w["rank"], "wins": 0, "losses": 0, "played": []})
    rows.append({"id": PLAYER, "name": roster["player"]["name"],
                 "style": "Player-created", "format_id": None,
                 "format_description": None, "rank": PLAYER_RANK,
                 "wins": 0, "losses": 0, "played": []})
    if [r["rank"] for r in rows] != list(range(1, WRESTLERS + 1)):
        raise ValueError("Banzuke must have every rank from 1 to 42 exactly once")
    return {"schema": "b12-basho-ledger-v1", "seed": roster["seed"],
            "day": 0, "wrestlers": rows, "player_id": PLAYER,
            "block_player_opponents": [], "pending_matches": [],
            "results": []}


def banzuke(league: dict) -> list[dict]:
    """Public ranked standings, ordered by initial basho rank."""
    return [{"id": w["id"], "name": w["name"], "style": w["style"],
             "rank": w["rank"], "wins": w["wins"], "losses": w["losses"]}
            for w in sorted(league["wrestlers"], key=lambda x: x["rank"])]


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def _seed_tie(seed: int, day: int, a: str, b: str) -> int:
    raw = f"{seed}:{day}:{a}:{b}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:4], "big")


def _opponent_score(day: int, left: dict, right: dict, seed: int) -> tuple:
    rank_gap = abs(left["rank"] - right["rank"])
    record_gap = abs(left["wins"] - right["wins"])
    tie = _seed_tie(seed, day, left["id"], right["id"])
    # R1–R3 (days 1–9) primarily near-rank; R4/R5 record-matched.
    return (record_gap, rank_gap, tie) if day >= 9 else (rank_gap, record_gap, tie)


def plan_block(league: dict) -> list[dict]:
    """Lock the next 3 player opponents, never reroll within the block.

    R4 opponents are picked after day 9; R5 after day 12. Planning does not
    simulate or reveal any future results. This is safe on repeated Heya views.
    """
    day = league["day"]
    if not 0 <= day < BASHO_DAYS:
        raise ValueError("The tournament is complete")
    block_start = (day // BOUT_BLOCK) * BOUT_BLOCK
    assigned = league["block_player_opponents"]
    if assigned:
        if len(assigned) != BOUT_BLOCK:
            raise ValueError("Malformed three-opponent block")
        return next_opponents(league)
    if day != block_start:
        raise ValueError("Missing an already-started opponent block")
    if league["pending_matches"]:
        raise ValueError("Cannot change opponents after a day has been scheduled")
    by_id = {w["id"]: w for w in league["wrestlers"]}
    player = by_id[PLAYER]
    candidates = [w for w in league["wrestlers"]
                  if w["id"] != PLAYER and w["id"] not in player["played"]]
    if len(candidates) < BOUT_BLOCK:
        raise ValueError("Not enough fresh AI opponents")
    selected = sorted(candidates, key=lambda w:
                      _opponent_score(day, player, w, league["seed"]))[:BOUT_BLOCK]
    league["block_player_opponents"] = [w["id"] for w in selected]
    return next_opponents(league)


def next_opponents(league: dict) -> list[dict]:
    """Three previews with records AS OF the last completed matchday."""
    assigned = league["block_player_opponents"]
    if not assigned:
        return []
    by_id = {w["id"]: w for w in league["wrestlers"]}
    start = (league["day"] // BOUT_BLOCK) * BOUT_BLOCK
    return [{"id": wid, "name": by_id[wid]["name"], "style": by_id[wid]["style"],
             "rank": by_id[wid]["rank"], "wins": by_id[wid]["wins"],
             "losses": by_id[wid]["losses"],
             "format_description": by_id[wid]["format_description"],
             "status": "completed" if start+i < league["day"] else "upcoming"}
            for i, wid in enumerate(assigned)]


def _match_remaining(pool: list[dict], day: int, seed: int) -> list[list[str]]:
    """Build 20 disjoint, nonrepeated AI matches using simple backtracking.

    With at most 14 prior opponents per wrestler among 40 peers, every
    unmatched AI has many fresh partners. Search explores nearest-record or
    nearest-rank partners first. No externally installed graph dependency.
    """
    ids = {w["id"] for w in pool}
    rows = {w["id"]: w for w in pool}
    def recurse(remaining: frozenset[str]) -> list[list[str]] | None:
        if not remaining:
            return []
        feasible = {}
        for a in remaining:
            w = rows[a]
            partners = [b for b in remaining
                        if b != a and b not in w["played"]]
            if not partners:
                return None
            feasible[a] = partners
        # Most-constrained-first avoids leaving a wrestler with no partner.
        a = min(remaining, key=lambda x: (len(feasible[x]), rows[x]["rank"]))
        partners = sorted(feasible[a], key=lambda b:
                          _opponent_score(day, rows[a], rows[b], seed))
        for b in partners:
            tail = recurse(remaining - {a, b})
            if tail is not None:
                return [[a, b], *tail]
        return None
    matches = recurse(frozenset(ids))
    if matches is None or len(matches) != 20:
        raise ValueError("Cannot construct a nonrepeating 20-pair AI matchday")
    return matches


def next_day_matches(league: dict) -> list[list[str]]:
    """Create or return the current day's 21 immutable pending pairings."""
    if league["day"] >= BASHO_DAYS:
        raise ValueError("The tournament has finished 15 matchdays")
    if league["pending_matches"]:
        return deepcopy(league["pending_matches"])
    if not league["block_player_opponents"]:
        plan_block(league)
    d = league["day"]
    by_id = {w["id"]: w for w in league["wrestlers"]}
    opponent = league["block_player_opponents"][d % BOUT_BLOCK]
    if opponent in by_id[PLAYER]["played"]:
        raise ValueError("Repeated player opponent")
    ai = [w for w in league["wrestlers"] if w["id"] not in {PLAYER, opponent}]
    matches = [[PLAYER, opponent], *_match_remaining(ai, d, league["seed"])]
    ids = [wid for pair in matches for wid in pair]
    if len(matches) != MATCHES_PER_DAY or len(set(ids)) != WRESTLERS:
        raise ValueError("Matchday pairs do not cover all 42 wrestlers once")
    league["pending_matches"] = deepcopy(matches)
    return matches


def commit_day(league: dict, results: list[dict]) -> dict:
    """Atomically accept exactly 21 externally resolved bout winners.

    Each result is {a, b, winner}. A partial, duplicate or future result
    cannot advance the standings. Return a NEW league state for safe save.
    """
    if league["day"] >= BASHO_DAYS or not league["pending_matches"]:
        raise ValueError("No active matchday awaiting results")
    pairs = {_pair_key(*pair) for pair in league["pending_matches"]}
    if len(pairs) != MATCHES_PER_DAY or len(results) != MATCHES_PER_DAY:
        raise ValueError("Expected exactly 21 match results")
    seen: set[tuple[str, str]] = set()
    for item in results:
        if not isinstance(item, dict):
            raise ValueError("Match results must be dictionaries")
        a, b, winner = item.get("a"), item.get("b"), item.get("winner")
        if not isinstance(a, str) or not isinstance(b, str):
            raise ValueError("Invalid match participant")
        key = _pair_key(a, b)
        if key not in pairs or key in seen or winner not in {a, b}:
            raise ValueError("Unscheduled, duplicate or invalid match result")
        seen.add(key)
    if seen != pairs:
        raise ValueError("All 21 match results must be supplied")
    updated = deepcopy(league)
    by_id = {w["id"]: w for w in updated["wrestlers"]}
    result_map = {_pair_key(item["a"], item["b"]): item for item in results}
    matches = []
    for a, b in updated["pending_matches"]:
        item = result_map[_pair_key(a, b)]
        victor = item["winner"]
        loser = b if victor == a else a
        by_id[victor]["wins"] += 1
        by_id[loser]["losses"] += 1
        by_id[a]["played"].append(b)
        by_id[b]["played"].append(a)
        matches.append({"a": a, "b": b, "winner": victor})
    updated["results"].append(matches)
    updated["day"] += 1
    updated["pending_matches"] = []
    if updated["day"] % BOUT_BLOCK == 0:
        updated["block_player_opponents"] = []
    completed = updated["day"]
    if any(w["wins"]+w["losses"] != completed for w in updated["wrestlers"]):
        raise ValueError("Matchday ledger and banzuke are out of sync")
    return updated
