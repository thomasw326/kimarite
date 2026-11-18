"""Stateless B12 six-basho campaign endpoints for the browser Heya.

The browser persists the seeded world and day's ledger. Every API transition
validates the roster and uses the shared league, matchmaking, and actual
20-bout AI gameplay modules. There is no server process-global campaign
state to lose on restart; the in-progress *player bout* retains its
existing session token and replay journal.
"""
from __future__ import annotations

from copy import deepcopy

from .b12_ai_day import commit_real_ai_matchday
from .b12_banzuke import end_of_basho
from .b12_division_roster import make_roster, validate_world
from .b12_league import (
    PLAYER, banzuke, new_basho, next_day_matches, next_opponents, plan_block,
)
from .models import Side


def _aligned(roster: dict, league: dict) -> None:
    """Reject mismatched/mutated campaign identities before using a day."""
    validate_world(roster)
    if league.get("seed") != roster["seed"]:
        raise ValueError("Basho seed does not match the wrestler world")
    rows = league.get("wrestlers")
    if not isinstance(rows, list) or len(rows) != 42:
        raise ValueError("Exactly 42 ranked wrestlers must be in the league")
    actual = {w["id"]: w for w in rows}
    active = {w["wrestler_id"]: w for w in roster["wrestlers"]
              if w["division"] == "top"}
    if set(actual) != set(active) | {PLAYER}:
        raise ValueError("League and campaign have different ranked wrestlers")
    p = actual[PLAYER]
    if p["name"] != roster["player"]["name"] or p["rank"] != roster["player"]["rank"]:
        raise ValueError("Player name and banzuke rank must match the campaign")
    day = league.get("day")
    if type(day) is not int or not 0 <= day <= 15 or len(league.get("results", [])) != day:
        raise ValueError("Matchday and result history are inconsistent")
    for wid, w in active.items():
        row = actual[wid]
        if (row["name"], row["style"], row["rank"], row["format_id"]) != (
                w["name"], w["ai_style"], w["rank"], w["format_id"]):
            raise ValueError("Wrestler identity or deck changed during the basho")
    if any(w["wins"] + w["losses"] != day or len(w["played"]) != day
           for w in rows):
        raise ValueError("Wrestlers must all have exactly one result per completed day")


def _preview(roster: dict, league: dict) -> dict:
    return {"roster": roster, "league": league,
            "opponents": next_opponents(league),
            "banzuke": banzuke(league)}


def campaign_request(path: str, request: dict, *, session=None) -> dict:
    """Handle a single POST; no room for random or probability-only winners."""
    if path == "/api/b12/campaign/new":
        player_name = request["player_name"]
        seed = request["seed"]
        roster = make_roster(seed, player_name)
        league = new_basho(roster)
        plan_block(league)
        return _preview(roster, league)

    roster = request["roster"]
    league = deepcopy(request["league"])
    _aligned(roster, league)

    if path == "/api/b12/campaign/plan":
        plan_block(league)
        return _preview(roster, league)

    if path == "/api/b12/campaign/pair":
        matches = next_day_matches(league)
        opponent_id = matches[0][1]
        by_id = {w["id"]: w for w in league["wrestlers"]}
        foe = by_id[opponent_id]
        details = {key: foe[key] for key in (
            "id", "name", "style", "rank", "format_id", "wins", "losses",
        )}
        return {**_preview(roster, league),
                "opponent": details}

    if path == "/api/b12/campaign/advance":
        updated, changes = end_of_basho(roster, league)
        fresh = new_basho(updated)
        plan_block(fresh)
        return {**_preview(updated, fresh), "changes": changes}

    if path == "/api/b12/campaign/resolve":
        if session is None:
            raise ValueError("The finished player bout must be restored before standings update")
        if not session.finished or session.state.winner not in (Side.A, Side.B):
            raise ValueError("Player bout has not produced a winner")
        day = league["day"]
        scheduled = league.get("pending_matches") or []
        if len(scheduled) != 21 or scheduled[0][0] != PLAYER:
            raise ValueError("Player match was not scheduled for the current day")
        other_id = scheduled[0][1]
        by_id = {w["id"]: w for w in league["wrestlers"]}
        foe = by_id[other_id]
        tagged = getattr(session, "b12_campaign", None)
        if not isinstance(tagged, dict) or (
            tagged.get("seed"), tagged.get("basho"), tagged.get("day"),
            tagged.get("opponent_id")) != (
                roster["seed"], roster.get("completed_basho", 0), day, other_id):
            raise ValueError("Finished bout does not belong to this tournament matchday")
        if (session.state.fighter_a.wrestler.name != roster["player"]["name"] or
                session.state.fighter_b.wrestler.name != foe["name"]):
            raise ValueError("Player bout participants differ from saved matchday")
        cached = getattr(session, "b12_campaign_commit", None)
        if cached is not None:
            return cached
        winner = PLAYER if session.state.winner is Side.A else other_id
        updated, audit = commit_real_ai_matchday(roster, league, winner)
        payload = {**_preview(roster, updated), "ai_matches": len(audit),
                   "player_winner": winner}
        # Retain the exact commit result if the browser loses the HTTP response.
        # Browser save/reload uses the persisted new ledger, not another call.
        session.b12_campaign_commit = payload
        return payload

    raise ValueError("Unknown B12 campaign operation")
