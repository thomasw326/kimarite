"""Lightweight banzuke update after a completed 15-day B12 basho.

The player's rank follows the EXACT designer formula. Five inaugural elite
AI identities retain their relative order in positions 1–5 (or shift into
position 6 only if the player enters that group). All other AI rankings are
a stable projected-score sort. At most three unbounded-overflow AI wrestlers
are replaced by previously unseen reserves between tournaments.
"""
from __future__ import annotations

from copy import deepcopy

from .b12_division_roster import BASHO_COUNT, PLAYER_RANK, validate_world
from .b12_league import BASHO_DAYS, PLAYER


def project_rank(rank: int, wins: int, losses: int) -> int:
    """Unbounded projection; caller clamps ONLY the created player."""
    return rank - 2 * (wins - losses)


def end_of_basho(roster: dict, league: dict) -> tuple[dict, dict]:
    """Return a fresh ranked world plus movement summary, without mutations."""
    validate_world(roster)
    if roster.get("completed_basho", 0) >= BASHO_COUNT - 1:
        raise ValueError("No seventh tournament in a six-basho year")
    if league.get("day") != BASHO_DAYS or len(league.get("results", [])) != BASHO_DAYS:
        raise ValueError("Rankings cannot change until all 15 days are complete")
    rows = league["wrestlers"]
    by_id = {w["id"]: w for w in rows}
    if len(by_id) != 42 or PLAYER not in by_id:
        raise ValueError("A complete 42-rikishi ledger is required")
    if any(w["wins"] + w["losses"] != BASHO_DAYS for w in rows):
        raise ValueError("Every wrestler must have exactly 15 bout results")
    old = {w["wrestler_id"]: w for w in roster["wrestlers"]}
    if {w["wrestler_id"] for w in old.values() if w["division"] == "top"} != set(by_id) - {PLAYER}:
        raise ValueError("The results and ranked AI roster disagree")
    if by_id[PLAYER]["rank"] != roster["player"]["rank"]:
        raise ValueError("Player's previous rank and results rank disagree")
    for wid, w in old.items():
        if w["division"] == "top" and by_id[wid]["rank"] != w["rank"]:
            raise ValueError("One or more AI ranks changed during the tournament")
    updated = deepcopy(roster)
    wrestlers = {w["wrestler_id"]: w for w in updated["wrestlers"]}
    elites = updated.get("protected_elites") or [
        w["wrestler_id"] for w in sorted(
            (r for r in roster["wrestlers"] if r["division"] == "top"),
            key=lambda w: w["rank"]
        )[:5]
    ]
    updated["protected_elites"] = list(elites)
    ai_projected = {}
    for w in roster["wrestlers"]:
        if w["division"] != "top":
            continue
        result = by_id[w["wrestler_id"]]
        ai_projected[w["wrestler_id"]] = project_rank(w["rank"], result["wins"], result["losses"])
    # Demote up to three WORST unbounded-overflow AI, excluding protected elites.
    qualifying = [w for w in roster["wrestlers"]
                  if w["division"] == "top" and w["wrestler_id"] not in elites
                  and ai_projected[w["wrestler_id"]] > PLAYER_RANK]
    worst = sorted(qualifying, key=lambda w:
                   (-ai_projected[w["wrestler_id"]], -w["rank"], w["wrestler_id"]))
    candidates = worst[:min(3, len(updated["reserve_queue"]))]
    demoted = [w["wrestler_id"] for w in candidates]
    promoted = updated["reserve_queue"][:len(demoted)]
    updated["reserve_queue"] = updated["reserve_queue"][len(promoted):]
    archive = updated.setdefault("archived_wrestlers", [])
    for wid in demoted:
        w = wrestlers[wid]
        w["division"], w["rank"] = "archived", None
        archive.append(wid)
    for wid in promoted:
        w = wrestlers[wid]
        w["division"], w["rank"] = "top", None
    # Player receives EXACT two ranks for each net win, clamped 1–42.
    previous_player_rank = roster["player"]["rank"]
    p = by_id[PLAYER]
    next_player_rank = max(1, min(PLAYER_RANK,
                                project_rank(previous_player_rank, p["wins"], p["losses"])))
    updated["player"]["rank"] = next_player_rank
    positions = {next_player_rank: PLAYER}
    # Five fixed elite IDs stay #1–#5 unless the player displaces one. Then
    # the fifth elite moves to #6, without elite membership/order changing.
    elite_slots = [rank for rank in range(1, 7 if next_player_rank <= 5 else 6)
                   if rank != next_player_rank]
    for rank, wid in zip(elite_slots, elites):
        positions[rank] = wid
    if len(elite_slots) != 5 or len(positions) != 6:
        raise ValueError("Could not place the fixed top five and player")
    remaining = [w for w in updated["wrestlers"]
                 if w["division"] == "top" and w["wrestler_id"] not in elites]
    # Previously ranked AI get a stable projected-rank sort; promoted reserves
    # have no bout history in the top division and join from the bottom.
    previous = {w["wrestler_id"]: w["rank"] for w in roster["wrestlers"]}
    def score(w: dict) -> tuple:
        wid = w["wrestler_id"]
        prev = previous[wid]
        if prev is None:
            return (float("inf"), float("inf"), promoted.index(wid) if wid in promoted else 9999, wid)
        return (ai_projected[wid], prev, 0, wid)
    remaining.sort(key=score)
    slots = [rank for rank in range(1, 43) if rank not in positions]
    if len(remaining) != len(slots):
        raise ValueError("Wrong number of ranked AI after promotions")
    for rank, w in zip(slots, remaining):
        positions[rank] = w["wrestler_id"]
    if len(positions) != 42:
        raise ValueError("Missing a banzuke rank")
    for rank, wid in positions.items():
        if wid != PLAYER:
            wrestlers[wid]["rank"] = rank
    updated["completed_basho"] = roster.get("completed_basho", 0) + 1
    validate_world(updated)
    movement = {
        "completed_basho": updated["completed_basho"],
        "player_from": previous_player_rank,
        "player_to": next_player_rank,
        "player_wins": p["wins"],
        "player_losses": p["losses"],
        "protected_elites": list(elites),
        "relegated": demoted,
        "promoted": promoted,
        "rank_changes": [
            {"id": w["wrestler_id"], "from": previous[w["wrestler_id"]],
             "to": w["rank"]}
            for w in updated["wrestlers"]
            if w["division"] == "top" and previous[w["wrestler_id"]] != w["rank"]
        ],
    }
    return updated, movement
